"""Run the gated TASK008 common-origin experiment; never overwrite a run directory."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mumbai_pm25.data import load_data
from mumbai_pm25.final_gap import (
    BASE_MODELS,
    SEED,
    eligible_training_rows,
    labelled_blocks,
    make_blocks,
    paired_bootstrap,
    score_predictions,
)
from mumbai_pm25.final_gap_supervised import SUPERVISED_MODELS, fit_predict
from mumbai_pm25.forecast import derive_pm_history_cutoff
from mumbai_pm25.historical_archive import P_FIX_SERIES, load_2024_history


def save_tables(rows: pd.DataFrame, models: list[str], output: Path) -> None:
    for name, keys in (("model", ()), ("station", ("location_id",)),
                       ("fold", ("fold_id",)), ("lead", ("forecast_lead_hours",)),
                       ("day", ("target_day",))):
        table = score_predictions(rows, models, keys)
        if name == "model":
            folds = score_predictions(rows, models, ("fold_id",))
            variability = folds.groupby("model").full_target_rmse.agg(fold_rmse_sd="std", fold_rmse_median="median")
            table = table.merge(variability, on="model")
        table.to_csv(output / f"{name}_metrics.csv", index=False)
    pd.DataFrame([paired_bootstrap(rows, m) for m in models if m != "P_fix"]).to_csv(output / "paired_bootstrap.csv", index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data/raw/challenge")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--gap-hours", type=int, default=None)
    parser.add_argument("--skip-supervised", action="store_true")
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"Choose a new run directory: {args.output}")
    args.output.mkdir(parents=True)
    train, _, _, _ = load_data(args.data_dir)
    archive = load_2024_history(args.data_dir / "AdditionalHistory.zip")
    cutoff = derive_pm_history_cutoff(train)
    gap = args.gap_hours if args.gap_hours is not None else int((pd.Timestamp("2026-11-11", tz="Asia/Kolkata")-cutoff).total_seconds()/3600)
    if gap < 1:
        raise ValueError("Future target must follow PM cutoff; supply a valid historical gap")
    blocks = make_blocks(train, gap)
    pd.DataFrame([{"target_start": b.target_start, "target_end": b.target_end,
                   "pm_history_cutoff": b.pm_cutoff, "issue_time": b.issue_time,
                   "split": b.split} for b in blocks]).to_csv(args.output / "folds.csv", index=False)
    rows, coverage = labelled_blocks(train, archive, blocks)
    coverage.to_csv(args.output / "coverage.csv", index=False)
    rows.to_csv(args.output / "all_block_rows.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
    # Eligibility is predeclared from history/support and complete training-block
    # availability, never from candidate errors or finite predictions.
    labelled = rows.loc[rows.y.notna()].copy()
    supervised = [] if args.skip_supervised else list(SUPERVISED_MODELS)
    matched_parts = []
    support = []
    for block in blocks:
        validation = labelled.loc[labelled.fold_id.eq(block.target_start)].copy()
        training = eligible_training_rows(labelled, block.pm_cutoff)
        supported = len(training) >= 500 and not validation.empty and validation.median72.notna().all()
        support.append({"fold_id": block.target_start, "split": block.split,
                        "training_rows": len(training), "validation_rows": len(validation),
                        "eligible": supported, "training_block_end_max": training.block_target_end.max()})
        if not supported:
            continue
        for model in supervised:
            validation[model] = fit_predict(training, validation, model, fitting_cutoff=block.pm_cutoff)
        matched_parts.append(validation)
    pd.DataFrame(support).to_csv(args.output / "training_support.csv", index=False)
    matched = pd.concat(matched_parts, ignore_index=True)
    candidates = list(BASE_MODELS) + supervised
    dev = matched.loc[matched.split.eq("development")].copy()
    confirmation = matched.loc[matched.split.eq("confirmation")].copy()
    # Save development metrics, select compact families, freeze artifact, then
    # inspect confirmation metrics exactly once. No configuration is refitted.
    dev_dir = args.output / "development"
    dev_dir.mkdir()
    metric = score_predictions(dev, candidates)
    valid_metric = metric.dropna(subset=["full_target_rmse"]).set_index("model")
    recent = [m for m in candidates if m.startswith("recent_") or m in ("median24", "median168", "ewm72", "diurnal7_raw", "hour_week4")]
    anomaly = [m for m in candidates if m.startswith(("archive_", "current_"))]
    selected = {"recent": min(recent, key=lambda m: valid_metric.loc[m, "full_target_rmse"]),
                "anomaly": min(anomaly, key=lambda m: valid_metric.loc[m, "full_target_rmse"])}
    if supervised:
        selected["supervised"] = min(supervised, key=lambda m: valid_metric.loc[m, "full_target_rmse"])
    blends = []
    for family, name in selected.items():
        for weight in (.25, .5, .75):
            blend = f"blend_{family}_{int(100*weight)}"
            for frame in (dev, confirmation):
                frame[blend] = (1-weight)*frame.P_fix + weight*frame[name]
            blends.append(blend)
    all_candidates = candidates+blends
    grid = score_predictions(dev, all_candidates).dropna(subset=["full_target_rmse"])
    selected_model = str(grid.sort_values(["full_target_rmse", "model"]).iloc[0].model)
    frozen = {"seed": SEED, "gap_hours": gap, "selected_families": selected,
              "development_best": selected_model, "candidates": candidates, "blends": blends,
              "promotion_rule": "Require negative upper95 paired RMSE delta in development and confirmation, majority origin and station wins in both; historical confirmation is previously inspected so retain provisional status.",
              "holdout_limit": "Historical rows previously inspected; confirmation is chronological, not blind."}
    selection_path = args.output / "frozen_selection.json"
    selection_path.write_text(json.dumps(frozen, indent=2)+"\n", encoding="utf-8")
    save_tables(dev, all_candidates, dev_dir)
    confirm_dir = args.output / "confirmation"
    confirm_dir.mkdir()
    save_tables(confirmation, all_candidates, confirm_dir)
    combined = pd.concat([dev, confirmation], ignore_index=True)
    combined.to_csv(args.output / "matched_oof.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
    baseline_dir = args.output / "all_labelled_baselines"
    baseline_dir.mkdir()
    save_tables(labelled, list(BASE_MODELS), baseline_dir)
    promoted = "P_fix"
    details = {}
    if selected_model != "P_fix":
        for split, frame in (("development", dev), ("confirmation", confirmation)):
            paired = paired_bootstrap(frame, selected_model)
            stations = score_predictions(frame, ["P_fix", selected_model], ("location_id",)).pivot(index="location_id", columns="model", values="full_target_rmse")
            station_wins = int((stations[selected_model] < stations.P_fix).sum())
            details[split] = {**paired, "station_wins": station_wins}
        # Previously inspected historical confirmation cannot establish fresh promotion.
    decision = {"selected_model": promoted, "fallback": "median72", "development_best": selected_model,
                "candidate_evidence": details, "reason": "Retain provisional P_fix unless fresh evidence establishes stable superiority; historical confirmation has prior analyst exposure."}
    (args.output / "promotion_decision.json").write_text(json.dumps(decision, indent=2)+"\n", encoding="utf-8")
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    inputs = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in args.data_dir.iterdir() if p.is_file()}
    manifest = {"command": subprocess.list2cmdline(sys.argv), "git_commit": commit, "input_hashes": inputs,
                "source_policy": P_FIX_SERIES, "folds": len(blocks), "matched_origins": matched.fold_id.nunique(),
                "development_origins": dev.fold_id.nunique(), "confirmation_origins": confirmation.fold_id.nunique(),
                "development_rows": len(dev), "confirmation_rows": len(confirmation),
                "frozen_selection_sha256": hashlib.sha256(selection_path.read_bytes()).hexdigest(),
                "pm_history_cutoff": cutoff.isoformat(), "gap_hours": gap, "seed": SEED,
                "availability_proxy": "interval end <= cutoff; first-publication times unverified",
                "weather": "NOT TESTED: no permitted as-issued vintages available"}
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"manifest": manifest, "decision": decision}, indent=2))


if __name__ == "__main__":
    main()
