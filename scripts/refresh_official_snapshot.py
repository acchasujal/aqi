"""Version explicit official files and regenerate a validated W50 submission."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mumbai_pm25.data import load_data  # noqa: E402
from mumbai_pm25.forecast import (derive_pm_history_cutoff, predict_test_with_hist24_blend,  # noqa: E402
                                 validate_submission, write_manifest)
from mumbai_pm25.historical_archive import load_2024_history  # noqa: E402
from mumbai_pm25.horizon import station_last_pm_end, target_leads, target_window  # noqa: E402

FILES = ("Train.csv", "Test.csv", "SampleSubmission.csv", "Stations.csv",
         "DataDictionary.txt", "AdditionalHistory.zip")


def sha256(path: Path) -> str:
    """SHA-256 of an immutable input or generated artifact."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in FILES:
        parser.add_argument("--" + name.lower().replace(".", "-"), type=Path, required=True)
    parser.add_argument("--issue-time", required=True,
                        help="Timezone-aware ISO model run time")
    args = parser.parse_args()
    paths = {name: getattr(args, name.lower().replace(".", "_")) for name in FILES}
    for name, path in paths.items():
        if not path.is_file():
            parser.error(f"Missing {name}: {path}")
    issue = pd.Timestamp(args.issue_time)
    if issue.tz is None:
        parser.error("--issue-time must include timezone offset")
    hashes = {name: sha256(path) for name, path in paths.items()}
    # Any changed official input must create a distinct immutable snapshot.
    combined = hashlib.sha256("\n".join(
        f"{name}:{hashes[name]}" for name in FILES
    ).encode("ascii")).hexdigest()
    tag = f"{hashes['Train.csv'][:12]}_{combined[:12]}"
    snapshot = ROOT / "data/processed/official_snapshots" / tag
    snapshot.mkdir(parents=True, exist_ok=True)
    for name, source in paths.items():
        target = snapshot / name
        if target.exists():
            if sha256(target) != hashes[name]:
                raise ValueError(f"Versioned snapshot conflict at {target}")
        else:
            shutil.copy2(source, target)
            if sha256(target) != hashes[name]:
                raise ValueError(f"Copy verification failed for {name}")
    train, test, sample, stations = load_data(snapshot)
    cutoff = derive_pm_history_cutoff(train)
    if cutoff > issue:
        raise ValueError("PM snapshot contains an observation ending after issue time")
    archive = load_2024_history(snapshot / "AdditionalHistory.zip")
    if archive.hour_start.max() >= issue:
        raise ValueError("Historical archive is not fully available by issue time")
    private = target_window(test, pd.Timestamp("2026-11-11T00:00:00+05:30"), 48)
    if len(private) != 48 * len(stations):
        raise ValueError("Private-window test grid changed")
    leads = target_leads(private, station_last_pm_end(train, cutoff))
    output_dir = ROOT / "artifacts/submissions/exp013"
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"w50_{tag}_{issue.strftime('%Y%m%d_%H%M')}.csv"
    if output.exists() or output.with_suffix(".manifest.txt").exists():
        raise FileExistsError(f"Refusing to overwrite an existing submission artifact: {output}")
    prediction = predict_test_with_hist24_blend(train, test, archive, issue_time=issue,
                                                pm_history_cutoff=cutoff)
    validate_submission(prediction, test)
    if prediction.ID.tolist() != sample.ID.tolist() or prediction.ID.duplicated().any():
        raise ValueError("Prediction IDs are missing, duplicated or reordered")
    values = prediction.Target.to_numpy(dtype=float)
    if len(values) != len(sample) or not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("Invalid prediction values")
    prediction.to_csv(output, index=False)
    write_manifest(output.with_suffix(".manifest.txt"),
                   train_path=snapshot / "Train.csv", test_path=snapshot / "Test.csv",
                   issue_time=issue, pm_history_cutoff=cutoff, train=train,
                   stations=stations, model="hist24_blend50_median72",
                   extra_sources=[snapshot / "AdditionalHistory.zip"])
    record = {"source_paths": {k: str(v.resolve()) for k, v in paths.items()},
              "snapshot": str(snapshot), "input_sha256": hashes,
              "model": "hist24_blend50_median72", "seasonal_weight": 0.5,
              "calendar_mode": "legacy_doy", "issue_time": issue.isoformat(),
              "pm_cutoff": cutoff.isoformat(), "private_lead_min_h": float(leads.forecast_lead_hours.min()),
              "private_lead_median_h": float(leads.forecast_lead_hours.median()),
              "private_lead_max_h": float(leads.forecast_lead_hours.max()),
              "submission_rows": len(prediction), "submission_sha256": sha256(output),
              "prediction_min": float(np.min(values)), "prediction_median": float(np.median(values)),
              "prediction_mean": float(np.mean(values)), "prediction_max": float(np.max(values))}
    output.with_suffix(".json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"{output} rows={len(prediction)} sha256={record['submission_sha256']} "
          f"cutoff={cutoff.isoformat()} private_lead={record['private_lead_min_h']:.0f}-"
          f"{record['private_lead_max_h']:.0f}h")


if __name__ == "__main__":
    main()
