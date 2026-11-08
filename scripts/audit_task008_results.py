"""Verify frozen TASK008 outputs, raw-file immutability and exact code fingerprints."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mumbai_pm25.data import load_data
from mumbai_pm25.forecast import validate_submission


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    args = parser.parse_args()
    output = args.run_dir / "result_audit.json"
    if output.exists():
        raise FileExistsError("Preserve previous result audit; choose a new run")
    train, test, _, _ = load_data(ROOT / "data/raw/challenge")
    frozen = json.loads((args.run_dir.parent / "candidate_provenance.json").read_text())
    raw = [item for item in frozen["inputs"] if item["path"].startswith("data/raw/challenge/")]
    for record in raw:
        if sha(ROOT / record["path"]) != record["sha256"]:
            raise ValueError(f"Raw input changed: {record['path']}")
    oof = pd.read_csv(args.run_dir / "matched_oof.csv.gz")
    for column in ("fold_id", "prediction_origin", "pm_history_cutoff", "last_pm_end", "target_start", "target_end", "block_target_end"):
        oof[column] = pd.to_datetime(oof[column], utc=True).dt.tz_convert("Asia/Kolkata")
    if oof.duplicated(["fold_id", "location_id", "target_start"]).any():
        raise ValueError("Duplicate matched OOF rows")
    if not (oof.last_pm_end.le(oof.pm_history_cutoff) & oof.pm_history_cutoff.le(oof.prediction_origin) & oof.prediction_origin.lt(oof.target_start)).all():
        raise ValueError("Invalid availability clocks")
    if not (oof.target_end-oof.target_start).eq(pd.Timedelta(hours=1)).all():
        raise ValueError("Invalid target intervals")
    truth = oof.merge(train[["location_id", "target_start", "pm25"]], on=["location_id", "target_start"], validate="many_to_one")
    if len(truth) != len(oof):
        raise ValueError("OOF rows absent from raw Train")
    np.testing.assert_allclose(truth.y, truth.pm25, rtol=0, atol=1e-9)
    origins = oof.fold_id.drop_duplicates().sort_values()
    if not origins.diff().dropna().ge(pd.Timedelta(hours=48)).all():
        raise ValueError("Overlapping evaluation target blocks")
    support = pd.read_csv(args.run_dir / "training_support.csv")
    support = support.loc[support.eligible]
    max_ends = pd.to_datetime(support.training_block_end_max, utc=True)
    cutoffs = oof.groupby("fold_id").pm_history_cutoff.first()
    targets = pd.to_datetime(support.fold_id, utc=True)
    if not max_ends.le(targets.map(cutoffs)).all():
        raise ValueError("Training block target not fully available by fitting cutoff")
    candidate = pd.read_csv(args.candidate)
    validate_submission(candidate, test)
    prior = pd.read_csv(ROOT / "artifacts/submissions/task007_provisional_pfix_current_train_v2.csv")
    np.testing.assert_array_equal(candidate.ID, prior.ID)
    delta = float(np.abs(candidate.Target-prior.Target).max())
    sources = [*ROOT.glob("src/mumbai_pm25/*.py"), *ROOT.glob("scripts/*task008*.py"),
               ROOT / "tests/test_final_gap.py", ROOT / "experiments/EXP-20261108-016.yaml"]
    manifest = {"git_commit_at_run": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                    capture_output=True, text=True, check=True).stdout.strip(),
                "source_sha256": {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(sources)},
                "raw_hashes_unchanged": True, "raw_files_checked": len(raw),
                "unmodified_oof_truth": True, "unique_nonoverlapping_targets": True,
                "availability_clocks_valid": True, "training_blocks_fully_available": True,
                "matched_rows": len(oof), "matched_origins": oof.fold_id.nunique(),
                "submission_rows": len(candidate), "submission_sha256": sha(args.candidate),
                "pfix_max_abs_difference_from_task007_v2": delta,
                "output_files_sha256": {p.relative_to(args.run_dir).as_posix(): sha(p)
                                         for p in sorted(args.run_dir.rglob("*")) if p.is_file()}}
    output.write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in manifest.items() if not k.endswith("sha256")}, indent=2))


if __name__ == "__main__":
    main()
