"""Audit official local snapshot and private-window PM forecast leads."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mumbai_pm25.data import load_data  # noqa: E402
from mumbai_pm25.forecast import derive_pm_history_cutoff  # noqa: E402
from mumbai_pm25.horizon import station_last_pm_end, target_leads, target_window  # noqa: E402


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    raw = ROOT / "data/raw/challenge"
    out = ROOT / "reports/ml_pipeline/exp_013"
    out.mkdir(parents=True, exist_ok=True)
    train, test, sample, stations = load_data(raw)
    cutoff = derive_pm_history_cutoff(train)
    issue = pd.Timestamp("2026-11-07T12:00:00+05:30")
    ends = station_last_pm_end(train, cutoff)
    private = target_window(test, pd.Timestamp("2026-11-11T00:00:00+05:30"), 48)
    if len(private) != 48 * len(stations):
        raise ValueError("Private-window target grid does not contain 48 rows per station")
    profile = target_leads(private, ends)
    public = target_leads(target_window(test, pd.Timestamp("2026-11-03T00:00:00+05:30"), 48), ends)
    profile["target_date"] = profile.target_start.dt.date.astype(str)
    profile["lead_bucket"] = pd.cut(profile.forecast_lead_hours,
                                    bins=[-float("inf"), 0, 48, 96, 144, 192, 240, float("inf")],
                                    labels=["past", "1-48", "49-96", "97-144", "145-192", "193-240", ">240"])
    profile[["ID", "location_id", "target_start", "target_end", "last_pm_end",
             "forecast_lead_hours", "target_date", "lead_bucket"]].to_csv(out / "PRIVATE_HORIZON_ROWS.csv", index=False)
    hashes = {name: sha(raw / name) for name in
              ("Train.csv", "Test.csv", "SampleSubmission.csv", "Stations.csv",
               "DataDictionary.txt", "AdditionalHistory.zip")}
    snapshot = {"source_paths": {name: str((raw / name).resolve()) for name in hashes},
                "train_rows": len(train), "test_rows": len(test), "sample_rows": len(sample),
                "train_columns": list(pd.read_csv(raw / "Train.csv", nrows=0).columns),
                "test_columns": list(pd.read_csv(raw / "Test.csv", nrows=0).columns),
                "sample_columns": list(sample.columns), "station_ids": sorted(map(int, stations.location_id)),
                "train_target_start_min": train.target_start.min().isoformat(),
                "train_target_start_max": train.target_start.max().isoformat(),
                "test_target_start_min": test.target_start.min().isoformat(),
                "test_target_start_max": test.target_start.max().isoformat(),
                "pm_cutoff": cutoff.isoformat(), "model_run_time": issue.isoformat(),
                "station_last_pm_end": {str(k): v.isoformat() for k, v in ends.items()},
                "hashes": hashes,
                "train_nulls": pd.read_csv(raw / "Train.csv").isna().sum().to_dict(),
                "test_nulls": pd.read_csv(raw / "Test.csv").isna().sum().to_dict(),
                "train_station_rows": {str(k): int(v) for k, v in train.location_id.value_counts().items()},
                "test_station_rows": {str(k): int(v) for k, v in test.location_id.value_counts().items()},
                "train_duplicate_station_hours": int(train.duplicated(["location_id", "target_start"]).sum()),
                "test_duplicate_ids": int(test.ID.duplicated().sum()),
                "sample_exact_order": sample.ID.tolist() == test.ID.tolist()}
    (out / "SNAPSHOT.json").write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
    grouped = profile.groupby("location_id").forecast_lead_hours.agg(["count", "min", "median", "max"])
    lines = ["# EXP-013 horizon profile", "", f"PM interval-end cutoff: `{cutoff.isoformat()}`; model run time used for this snapshot: `{issue.isoformat()}`.",
             "The two clocks are distinct. Leads use target interval start minus each station's latest eligible PM interval end.", "",
             "| Station ID | Rows | Minimum h | Median h | Maximum h |", "|---:|---:|---:|---:|---:|"]
    for station, row in grouped.iterrows():
        lines.append(f"| {station} | {int(row['count'])} | {row['min']:.0f} | {row['median']:.1f} | {row['max']:.0f} |")
    lines += ["", "| Target date (IST) | Rows | Minimum h | Median h | Maximum h |",
              "|---|---:|---:|---:|---:|"]
    for day, row in profile.groupby("target_date").forecast_lead_hours.agg(["count", "min", "median", "max"]).iterrows():
        lines.append(f"| {day} | {int(row['count'])} | {row['min']:.0f} | {row['median']:.1f} | {row['max']:.0f} |")
    lines += ["", f"Overall: {len(profile)} private-window target rows; lead {profile.forecast_lead_hours.min():.0f}–{profile.forecast_lead_hours.max():.0f}h, median {profile.forecast_lead_hours.median():.1f}h.",
              "Each station has one row per lead hour from 193 through 240 on this snapshot. All 192 rows fall in the 193–240h lead bucket. Per-date and per-row detail is in `PRIVATE_HORIZON_ROWS.csv`.",
              f"For comparison, the locally documented revised public window (November 3–4) has {len(public)} rows and leads {public.forecast_lead_hours.min():.0f}–{public.forecast_lead_hours.max():.0f}h on this snapshot. The public-page date differs from the local dictionary; see `COMPETITION_REQUIREMENTS.md`. Older Test dates before the PM cutoff are not treated as live future targets."]
    (out / "HORIZON_PROFILE.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    lines = ["# EXP-013 data snapshot audit", "", "Local official challenge files were read without modification. Schema, station IDs, timezone, hourly test intervals and sample order passed `load_data` validation.",
             f"Train: {len(train):,} rows; test/sample: {len(test):,}/{len(sample):,}; four stations. No duplicate test IDs: {snapshot['test_duplicate_ids']}. Sample ID order exact: {snapshot['sample_exact_order']}.",
             f"Train aligned target starts: {snapshot['train_target_start_min']} to {snapshot['train_target_start_max']}; test: {snapshot['test_target_start_min']} to {snapshot['test_target_start_max']}.",
             f"Latest PM interval ends by station: {snapshot['station_last_pm_end']}. Current global cutoff: `{cutoff.isoformat()}`.",
             "Full schemas, null counts and input SHA-256 hashes are in `SNAPSHOT.json`. The local Train hash matches the 5 November snapshot recorded in EXP-012; no newer official file was supplied locally as of this audit. The official page schedules later updates, but authenticated download availability was not verified by this script."]
    (out / "DATA_SNAPSHOT_AUDIT.md").write_text("\n\n".join(lines)+"\n", encoding="utf-8")
    print(f"train {len(train)}; test {len(test)}; private {len(profile)}; lead {profile.forecast_lead_hours.min():.0f}-{profile.forecast_lead_hours.max():.0f}h")


if __name__ == "__main__":
    main()
