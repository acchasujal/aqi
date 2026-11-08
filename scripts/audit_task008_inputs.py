"""Freeze TASK008 inputs without changing challenge or supplied files."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mumbai_pm25.data import load_data
from mumbai_pm25.forecast import validate_submission


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True,
                          capture_output=True, text=True).stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--supplied-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "reports/ml_pipeline/task008")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    raw = ROOT / "data/raw/challenge"
    train, test, sample, _ = load_data(raw)
    paths = list(raw.iterdir()) + list((ROOT / "artifacts/submissions").iterdir())
    paths += list((ROOT / "reports/ml_pipeline").rglob("*.csv*"))
    supplied = ["low.csv", "high.csv", "TASK006_exploratory_experiments.zip",
                "TASK006_PRELIMINARY_EXECUTION_REPORT.md", "AQI_TASK008_ROADMAP_2026-11-08.md",
                "CHAT.md", "VERIFIED_VAIBHAV_MODEL_AUDIT_AND_INTEGRATION_PLAN (1).md"]
    paths += [args.supplied_dir / name for name in supplied]
    records = []
    for path in sorted(set(paths)):
        if not path.is_file():
            records.append({"path": path.name, "status": "MISSING"})
            continue
        try:
            label = path.relative_to(ROOT).as_posix()
        except ValueError:
            label = "supplied/" + path.name
        records.append({"path": label, "bytes": path.stat().st_size,
                        "sha256": sha256(path), "status": "present"})
    (args.output / "input_hashes.txt").write_text("\n".join(
        f"{r.get('sha256', 'MISSING')}  {r['path']}" for r in records
    ) + "\n", encoding="utf-8")
    candidates = []
    for path in sorted((ROOT / "artifacts/submissions").glob("*.csv")):
        frame = pd.read_csv(path)
        validate_submission(frame, test)
        manifest = path.with_suffix(".manifest.txt")
        candidates.append({"file": path.name, "sha256": sha256(path), "rows": len(frame),
                           "manifest": manifest.read_text(encoding="utf-8") if manifest.exists()
                           else "MISSING; provenance unknown; excluded from selection",
                           "superseded": path.with_suffix(".superseded.txt").exists()})
    low = pd.read_csv(args.supplied_dir / "low.csv")
    high = pd.read_csv(args.supplied_dir / "high.csv")
    validate_submission(low, test)
    validate_submission(high, test)
    if low.ID.tolist() != sample.ID.tolist():
        raise ValueError("Supplied low IDs differ from sample")
    deviation = float(np.max(np.abs(high.Target - low.Target * (1.40 / .95))))
    if not np.allclose(high.Target, low.Target * (1.40 / .95), rtol=1e-12, atol=1e-12):
        raise ValueError("High/Low scalar relationship failed")
    base = low.assign(Target=low.Target / .95)
    base_path = ROOT / "artifacts/submissions/task008_vaibhav_base_reference.csv"
    if base_path.exists() and not np.allclose(pd.read_csv(base_path).Target, base.Target):
        raise FileExistsError("Refusing to overwrite different reference predictions")
    base.to_csv(base_path, index=False)
    cutoffs = train.groupby("location_id").timestamp_ist.max()
    private = test.loc[test.target_start.ge(pd.Timestamp("2026-11-11", tz="Asia/Kolkata"))]
    private = private.loc[private.target_start.lt(pd.Timestamp("2026-11-13", tz="Asia/Kolkata"))]
    leads = private.assign(last_pm_end=private.location_id.map(cutoffs))
    leads["actual_pm_lead_hours"] = (leads.target_start - leads.last_pm_end).dt.total_seconds()/3600
    leads.to_csv(args.output / "current_private_leads.csv", index=False)
    members = {}
    for path in [raw / "AdditionalHistory.zip", args.supplied_dir / "TASK006_exploratory_experiments.zip"]:
        with zipfile.ZipFile(path) as archive:
            members[path.name] = [{"name": n, "bytes": archive.getinfo(n).file_size,
                                   "sha256": hashlib.sha256(archive.read(n)).hexdigest()}
                                  for n in archive.namelist() if not n.endswith("/")]
    packages = {}
    for name in ["numpy", "pandas", "scipy", "lightgbm", "scikit-learn", "pytest", "ruff"]:
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = "NOT_INSTALLED"
    payload = {"commit": git("rev-parse", "HEAD"), "branch": git("branch", "--show-current"),
               "working_tree": git("status", "--short"), "python": sys.version,
               "platform": platform.platform(), "packages": packages, "inputs": records,
               "zip_members": members, "candidates": candidates, "train_rows": len(train),
               "station_pm_cutoffs": {str(k): v.isoformat() for k, v in cutoffs.items()},
               "vaibhav": {"rows": len(base), "high_low_max_deviation": deviation,
                           "reference_sha256": sha256(base_path), "issue_time": "UNKNOWN",
                           "training_lineage": "UNKNOWN", "eligible_for_oof_blending": False}}
    (args.output / "candidate_provenance.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    (args.output / "INPUT_INVENTORY.md").write_text(
        "# TASK008 input freeze — EXP-016\n\n"
        f"Code: `{payload['commit']}` on `{payload['branch']}`. Started clean on TASK007; "
        "current changes are the TASK008 task record and audit script. Raw files read only.\n\n"
        f"Train: {len(train):,} rows; Test/Sample: {len(test):,} exact ordered IDs; four stations.\n\n"
        "All raw files, supplied materials, previous candidate CSVs/manifests and OOF/metric CSVs "
        "are hashed in input_hashes.txt. ZIP member hashes, environment, candidate manifests and "
        "per-station cutoffs are in candidate_provenance.json. Unknown historical provenance "
        "remains unknown; prior outputs are evidence, not inputs to new model selection.\n\n"
        f"Vaibhav Low/High: both valid; max high−low×(1.40/.95) deviation {deviation:.3g}. "
        "Reconstructed low/.95 is a black-box reference with unknown issue time and training lineage. "
        "No public score reproduced, no OOF or blend weight assigned. Originals unchanged.\n\n"
        "TASK005/006 and EXP-008–015 records on origin/main are reviewed separately by Git object; "
        "they are absent from this isolated TASK007-based working tree. Main is preserved without merging. "
        "Archive/source timestamp equivalence remains unverified.\n", encoding="utf-8")
    print(json.dumps({"train_rows": len(train), "candidate_count": len(candidates),
                      "inputs": len(records), "vaibhav_deviation": deviation, "packages": packages}))


if __name__ == "__main__":
    main()
