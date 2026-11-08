"""Audit supplied forecasts and evaluate fixed past-only station calibrations."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mumbai_pm25.calibration import CLOCKS, METHODS, rolling_calibration
from mumbai_pm25.data import load_data
from mumbai_pm25.final_gap import paired_bootstrap, score_predictions
from mumbai_pm25.forecast import validate_submission

FILES = (
    "task008_provisional_pfix_20261108_1558.csv",
    "task007_provisional_pfix_current_train_v2.csv",
    "submission_B_robust_ensemble.csv", "submission_C_statistical_seasonal.csv", "low.csv",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit_supplied(directory: Path, test: pd.DataFrame,
                   stations: pd.DataFrame) -> dict[str, object]:
    """CSV agreement is descriptive only: no hidden labels or score inference."""
    frames = {}
    inputs = []
    for name in FILES:
        path = directory / name
        frame = pd.read_csv(path)
        validate_submission(frame, test)
        frames[name] = frame.Target.to_numpy(dtype=float)
        inputs.append({"file": name, "sha256": sha256(path), "rows": len(frame),
                       "min": float(frame.Target.min()), "max": float(frame.Target.max()),
                       "lineage": "TASK008 frozen manifest" if name == FILES[0]
                       else "TASK007 matched artifact" if name == FILES[1] else "UNKNOWN"})
    merged = test[["location_id", "target_start"]].copy()
    merged["station"] = merged.location_id.map(stations.set_index("location_id").station_name)
    for name, values in frames.items():
        merged[name] = values
    windows = {}
    for label, start, end in (("full_grid", None, None),
                              ("public_3_4_diagnostic_only", "2026-11-03", "2026-11-05"),
                              ("private_11_12_forecasts_only", "2026-11-11", "2026-11-13")):
        part = merged if start is None else merged.loc[
            merged.target_start.ge(pd.Timestamp(start, tz="Asia/Kolkata"))
            & merged.target_start.lt(pd.Timestamp(end, tz="Asia/Kolkata"))]
        windows[label] = {"rows": len(part), "means": part[list(FILES)].mean().to_dict(),
                          "station_means": part.groupby("station")[list(FILES)].mean().to_dict(),
                          "correlations": part[list(FILES)].corr().to_dict()}
    pairs = [{"first": first, "second": second,
              "identical_values": bool(np.array_equal(frames[first], frames[second])),
              "max_absolute_difference": float(np.max(np.abs(frames[first]-frames[second])))}
             for i, first in enumerate(FILES) for second in FILES[i+1:]]
    return {"inputs": inputs, "pairs": pairs, "windows": windows,
            "limits": "No candidate errors or private score inferred. Public window unresolved; all potential rows shown. B/C/Low code and issue lineage unavailable."}


def save_metrics(rows: pd.DataFrame, models: list[str], directory: Path) -> None:
    directory.mkdir()
    folds = score_predictions(rows, models, ("fold_id",))
    folds.to_csv(directory / "fold_metrics.csv", index=False)
    variability = folds.groupby("model").full_target_rmse.agg(
        fold_rmse_sd="std", fold_rmse_median="median")
    score_predictions(rows, models).merge(variability, on="model").to_csv(
        directory / "model_metrics.csv", index=False)
    score_predictions(rows, models, ("location_id",)).to_csv(directory / "station_metrics.csv", index=False)
    score_predictions(rows, models, ("forecast_lead_hours",)).to_csv(directory / "lead_metrics.csv", index=False)
    pd.DataFrame([paired_bootstrap(rows, method) for method in models if method != "P_fix"]).to_csv(
        directory / "paired_bootstrap.csv", index=False)


def run(source: Path, supplied: Path, output: Path) -> None:
    if output.exists():
        raise FileExistsError(f"Choose an unused run directory: {output}")
    raw = ROOT / "data/raw/challenge"
    source_manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    result_audit = json.loads((source / "result_audit.json").read_text(encoding="utf-8"))
    raw_hashes = {name: sha256(raw / name) for name in source_manifest["input_hashes"]}
    if raw_hashes != source_manifest["input_hashes"]:
        raise ValueError("Raw snapshot differs from frozen TASK008 OOF inputs; rebuild OOF first")
    oof = source / "matched_oof.csv.gz"
    if sha256(oof) != result_audit["output_files_sha256"]["matched_oof.csv.gz"]:
        raise ValueError("Frozen OOF fingerprint mismatch")
    train, test, sample, stations = load_data(raw)
    if test.ID.tolist() != sample.ID.tolist():
        raise ValueError("Test/sample ID order mismatch")
    audit = audit_supplied(supplied, test, stations)
    if audit["inputs"][0]["sha256"] != result_audit["submission_sha256"]:
        raise ValueError("Supplied TASK008 differs from frozen artifact")
    rows = pd.read_csv(oof)
    for name in CLOCKS:
        rows[name] = pd.to_datetime(rows[name], utc=True).dt.tz_convert("Asia/Kolkata")
    truth = rows.merge(train[["location_id", "target_start", "pm25"]],
                       on=["location_id", "target_start"], validate="one_to_one", how="left")
    if not np.array_equal(truth.y.to_numpy(), truth.pm25.to_numpy()):
        raise ValueError("OOF labels differ from unmodified official Train")
    output.mkdir(parents=True)
    lineages = []
    for method in METHODS:
        rows[method], lineage = rolling_calibration(rows, method)
        lineages.append(lineage)
    models = ["P_fix", "median24", "median72", "blend_recent_50", *METHODS]
    dev = rows.loc[rows.split.eq("development")]
    confirm = rows.loc[rows.split.eq("confirmation")]
    # Freeze development choice before reporting confirmation. No tuning grid.
    metrics = score_predictions(dev, ["P_fix", *METHODS])
    best = str(metrics.sort_values(["full_target_rmse", "model"]).iloc[0].model)
    selection = {"development_best": best, "parameters": "experiments/EXP-20261108-024.yaml",
                 "production_model": "P_fix", "promotion": False,
                 "reason": "Historical confirmation is analyst-exposed; fresh evidence required."}
    gates = {}
    for split, part in (("development", dev), ("confirmation", confirm)):
        stations_table = score_predictions(part, ["P_fix", *METHODS], ("location_id",)).pivot(
            index="location_id", columns="model", values="full_target_rmse")
        gates[split] = {}
        for method in METHODS:
            paired = paired_bootstrap(part, method)
            station_wins = int(stations_table[method].lt(stations_table.P_fix).sum())
            gates[split][method] = {**paired, "station_wins": station_wins,
                "passes_statistical_gate": bool(paired["upper95"] < 0
                    and paired["origin_wins"] > paired["origins"] / 2
                    and station_wins > len(stations_table) / 2)}
    selection["gates"] = gates
    (output / "selection.json").write_text(json.dumps(selection, indent=2)+"\n", encoding="utf-8")
    for split, part in (("development", dev), ("confirmation", confirm)):
        save_metrics(part, models, output / split)
    pd.concat(lineages, ignore_index=True).to_csv(output / "fitting_lineage.csv", index=False)
    keep = [*CLOCKS, "location_id", "split", "y", "forecast_lead_hours", *models]
    rows[keep].to_csv(output / "oof.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
    (output / "supplied_audit.json").write_text(json.dumps(audit, indent=2)+"\n", encoding="utf-8")
    sources = [ROOT / "src/mumbai_pm25/calibration.py", Path(__file__),
               ROOT / "experiments/EXP-20261108-024.yaml"]
    manifest = {"command": subprocess.list2cmdline(sys.argv),
                "git_commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                             capture_output=True, text=True, check=True).stdout.strip(),
                "source_oof_sha256": sha256(oof), "raw_hashes": raw_hashes,
                "source_hashes": {p.relative_to(ROOT).as_posix(): sha256(p) for p in sources},
                "packages": {p: importlib.metadata.version(p) for p in ("numpy", "pandas", "scipy")},
                "rows": len(rows), "origins": rows.fold_id.nunique(),
                "truth_unchanged": True, "availability_proxy": source_manifest["availability_proxy"]}
    if {name: sha256(raw / name) for name in raw_hashes} != raw_hashes:
        raise ValueError("Raw snapshot changed during evaluation")
    manifest["raw_hashes_unchanged"] = True
    manifest["output_hashes"] = {p.relative_to(output).as_posix(): sha256(p)
                                  for p in sorted(output.rglob("*")) if p.is_file()}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"rows": len(rows), "origins": rows.fold_id.nunique(), **selection}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "reports/ml_pipeline/task008/run01")
    parser.add_argument("--supplied-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.source, args.supplied_dir, args.output)


if __name__ == "__main__":
    main()
