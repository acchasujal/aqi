"""Generate the reproducible station-median control submission."""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd

from mumbai_pm25.data import load_data
from mumbai_pm25.forecast import predict_test, write_manifest


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=root / "data/raw/challenge")
    parser.add_argument("--output", type=Path, default=root / "artifacts/submissions/median72.csv")
    parser.add_argument("--issue-time", required=True, help="Prediction issue time with UTC offset, e.g. 2026-11-06T12:00:00+05:30")
    args = parser.parse_args()
    train, test, sample, stations = load_data(args.data_dir)
    issue_time = pd.Timestamp(datetime.fromisoformat(args.issue_time))
    if issue_time.tz is None:
        raise ValueError("--issue-time must include a timezone offset")
    prediction = predict_test(train, test, issue_time=issue_time)
    if prediction.ID.tolist() != sample.ID.tolist():
        raise ValueError("SampleSubmission IDs differ from Test IDs")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    prediction.to_csv(args.output, index=False)
    write_manifest(args.output.with_suffix(".manifest.txt"), train_path=args.data_dir / "Train.csv",
                   test_path=args.data_dir / "Test.csv", issue_time=issue_time, train=train, stations=stations,
                   model="median72")
    print(f"Wrote {len(prediction)} predictions to {args.output}")


if __name__ == "__main__":
    main()
