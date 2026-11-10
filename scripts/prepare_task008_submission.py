"""Freeze a supplied snapshot, rerun selected inference twice, and audit output."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mumbai_pm25.data import load_data
from mumbai_pm25.forecast import (
    derive_pm_history_cutoff,
    predict_test,
    predict_test_with_hist24_blend,
    validate_submission,
)
from mumbai_pm25.historical_archive import P_FIX_SERIES, load_2024_history

CORE = ("Train.csv", "Test.csv", "SampleSubmission.csv", "Stations.csv",
        "DataDictionary.txt", "AdditionalHistory.zip")
INITIAL_TRAIN_HASHES = {
    "86a9efdcf458f02d46589f416c59057273574727478c5908a92f1e9fa626ec5",
    "fcee20ebf7bd9c4a4e2487bab0a4f81339d6c820a53862b14443031db1f18ad6",
}
NOV9_TRAIN_HASHES = {
    # Same official 9 Nov snapshot in Git's LF form and the supplied CRLF form.
    "e107dda18670583c333be0966530fc444c18fdb30c870156ac25688a2c152210",
    "11d6c4a4b20cc9ccf212b5e5f683ff5cc41f032fa0681e461b22fe0bd41047ee",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(data_dir: Path, output: Path, *, issue_time: pd.Timestamp,
            stage: str = "provisional", release_time: pd.Timestamp | None = None,
            model: str = "P_fix") -> dict[str, object]:
    if output.exists() or output.with_suffix(".audit.json").exists():
        raise FileExistsError("Choose a new output name; previous artifacts are immutable")
    if issue_time.tzinfo is None or stage not in {"provisional", "final"}:
        raise ValueError("Require timezone-aware issue time and provisional/final stage")
    if model not in {"P_fix", "median72"}:
        raise ValueError("Only selected P_fix and median72 fallback are supported")
    hashes = {name: digest(data_dir / name) for name in CORE}
    if stage == "final":
        refresh = pd.Timestamp("2026-11-10 09:00", tz="Asia/Kolkata")
        deadline = pd.Timestamp("2026-11-10 23:59:59", tz="Asia/Kolkata")
        if release_time is None or release_time.tzinfo is None or not refresh <= release_time <= issue_time <= deadline:
            raise ValueError("Final stage requires a final release time <= issue <= deadline")
        if hashes["Train.csv"] in INITIAL_TRAIN_HASHES:
            raise ValueError("Initial Train snapshot cannot be claimed as final refresh")
        if hashes["Train.csv"] in NOV9_TRAIN_HASHES:
            raise ValueError("9 November Train snapshot cannot be claimed as final; wait for the 10 November final Train release")
    train, test, sample, _stations = load_data(data_dir)
    cutoff = derive_pm_history_cutoff(train)
    if stage == "final" and cutoff <= pd.Timestamp("2026-11-09 07:00", tz="Asia/Kolkata"):
        raise ValueError("Final snapshot contains no PM history newer than the 9 November release")
    if cutoff > issue_time:
        raise ValueError("Snapshot contains PM intervals ending after issue_time")
    snapshot = ROOT / "data/processed/task008_snapshots" / hashes["Train.csv"]
    snapshot.mkdir(parents=True, exist_ok=True)
    for name, value in hashes.items():
        target = snapshot / name
        if target.exists():
            if digest(target) != value:
                raise ValueError(f"Snapshot collision for {name}; preserve and investigate")
        else:
            shutil.copyfile(data_dir / name, target)
    # Use the frozen snapshot for both independent inference calls.
    train, test, sample, _stations = load_data(snapshot)
    archive = load_2024_history(snapshot / "AdditionalHistory.zip") if model == "P_fix" else None

    def infer() -> pd.DataFrame:
        if model == "P_fix":
            return predict_test_with_hist24_blend(train, test, archive, issue_time=issue_time,
                                                 pm_history_cutoff=cutoff)
        return predict_test(train, test, issue_time=issue_time, pm_history_cutoff=cutoff)

    first, second = infer(), infer()
    validate_submission(first, test)
    pd.testing.assert_frame_equal(first, second, check_exact=True)
    if first.to_csv(index=False) != second.to_csv(index=False):
        raise ValueError("Deterministic CSV rerun differs")
    if first.ID.tolist() != sample.ID.tolist() or not first.ID.is_unique:
        raise ValueError("Output IDs/order differ or contain duplicates")
    output.parent.mkdir(parents=True, exist_ok=True)
    first.to_csv(output, index=False)
    cutoffs = train.groupby("location_id").timestamp_ist.max()
    audit_rows = test[["ID", "location_id", "target_start", "target_end"]].merge(first, on="ID", validate="one_to_one", sort=False)
    audit_rows["prediction_origin"] = issue_time
    audit_rows["pm_history_cutoff"] = cutoff
    audit_rows["last_pm_end"] = audit_rows.location_id.map(cutoffs)
    audit_rows["actual_pm_lead_hours"] = (audit_rows.target_start-audit_rows.last_pm_end).dt.total_seconds()/3600
    audit_rows.to_csv(output.with_suffix(".rows.csv"), index=False)
    current_hashes = {name: digest(data_dir / name) for name in CORE}
    if current_hashes != hashes:
        raise ValueError("Input files changed during inference")
    code_files = [ROOT / "src/mumbai_pm25/forecast.py", ROOT / "src/mumbai_pm25/historical_archive.py",
                  ROOT / "src/mumbai_pm25/data.py", Path(__file__).resolve()]
    private = audit_rows.loc[audit_rows.target_start.ge(pd.Timestamp("2026-11-11", tz="Asia/Kolkata")) & audit_rows.target_start.lt(pd.Timestamp("2026-11-13", tz="Asia/Kolkata"))]
    payload = {"stage": stage, "model": model, "model_run_time": issue_time.isoformat(),
               "release_time_user_asserted": release_time.isoformat() if release_time is not None else None,
               "release_provenance": "Final official release must be independently checked by operator",
               "git_commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip(),
               "source_sha256": {p.relative_to(ROOT).as_posix(): digest(p) for p in code_files},
               "input_sha256": hashes, "output_sha256": digest(output),
               "source_policy": P_FIX_SERIES if model == "P_fix" else None,
               "calendar": "2024 month/day anchor including leap day", "archive_interval_semantics": "unverified",
               "rows": len(first), "schema": list(first.columns), "exact_sample_id_order": True,
               "finite": bool(np.isfinite(first.Target).all()), "nonnegative": bool(first.Target.ge(0).all()),
               "deterministic_rerun": True, "pm_history_cutoff": cutoff.isoformat(),
               "station_last_pm_end": {str(k): v.isoformat() for k, v in cutoffs.items()},
               "private_rows": len(private), "private_lead_min": float(private.actual_pm_lead_hours.min()),
               "private_lead_max": float(private.actual_pm_lead_hours.max()),
               "input_files_unchanged": True, "python": sys.version, "platform": platform.platform(),
               "pandas": pd.__version__, "numpy": np.__version__, "weather": "NOT TESTED",
               "zindi_processing": "NOT SUBMITTED; human authorisation/platform verification pending"}
    output.with_suffix(".audit.json").write_text(json.dumps(payload, indent=2)+"\n", encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data/raw/challenge")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--issue-time", required=True)
    parser.add_argument("--stage", choices=("provisional", "final"), default="provisional")
    parser.add_argument("--release-time", default=None)
    parser.add_argument("--model", choices=("P_fix", "median72"), default="P_fix")
    args = parser.parse_args()
    print(json.dumps(prepare(args.data_dir, args.output, issue_time=pd.Timestamp(args.issue_time),
                             stage=args.stage, release_time=pd.Timestamp(args.release_time) if args.release_time else None,
                             model=args.model), indent=2))


if __name__ == "__main__":
    main()
