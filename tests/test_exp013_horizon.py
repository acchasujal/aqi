"""Competition-window PM lead and submission integrity checks."""
import hashlib

import numpy as np
import pandas as pd
import pytest

from mumbai_pm25.forecast import validate_submission
from mumbai_pm25.horizon import station_last_pm_end, target_leads, target_window
from scripts.refresh_official_snapshot import sha256


def _target(station: int, start: str, identifier: str) -> dict:
    t = pd.Timestamp(start, tz="Asia/Kolkata")
    return {"ID": identifier, "location_id": station, "target_start": t,
            "target_end": t + pd.Timedelta(hours=1)}


def test_station_specific_last_eligible_pm_end_and_leads():
    train = pd.DataFrame([
        {"location_id": 1, "target_start": pd.Timestamp("2026-11-02 21:00", tz="Asia/Kolkata"), "pm25": 20.0},
        {"location_id": 1, "target_start": pd.Timestamp("2026-11-02 22:00", tz="Asia/Kolkata"), "pm25": np.nan},
        {"location_id": 1, "target_start": pd.Timestamp("2026-11-03 00:00", tz="Asia/Kolkata"), "pm25": 1000.0},
        {"location_id": 2, "target_start": pd.Timestamp("2026-11-02 22:00", tz="Asia/Kolkata"), "pm25": 30.0},
    ])
    cutoff = pd.Timestamp("2026-11-02 23:00", tz="Asia/Kolkata")
    ends = station_last_pm_end(train, cutoff)
    assert ends[1] == cutoff - pd.Timedelta(hours=1)
    assert ends[2] == cutoff
    targets = pd.DataFrame([_target(1, "2026-11-11 00:00", "a"),
                            _target(2, "2026-11-11 00:00", "b")])
    leads = target_leads(targets, ends)
    assert leads.forecast_lead_hours.tolist() == [194.0, 193.0]
    assert target_leads(targets, ends).equals(leads)


def test_private_window_is_exact_48_hour_half_open_interval():
    start = pd.Timestamp("2026-11-11", tz="Asia/Kolkata")
    hours = pd.date_range(start - pd.Timedelta(hours=1), periods=50, freq="h")
    test = pd.DataFrame({"target_start": hours, "location_id": 1})
    window = target_window(test, start, 48)
    assert len(window) == 48
    assert window.target_start.iloc[0] == start
    assert window.target_start.iloc[-1] == start + pd.Timedelta(hours=47)
    with pytest.raises(ValueError, match="timezone-aware"):
        target_window(test, pd.Timestamp("2026-11-11"), 48)


def test_missing_station_and_naive_cutoff_are_rejected():
    train = pd.DataFrame([{"location_id": 1, "target_start": pd.Timestamp("2026-11-02", tz="Asia/Kolkata"), "pm25": 5.0}])
    with pytest.raises(ValueError, match="timezone-aware"):
        station_last_pm_end(train, pd.Timestamp("2026-11-03"))
    with pytest.raises(ValueError, match="lacks eligible"):
        target_leads(pd.DataFrame([_target(2, "2026-11-11 00:00", "b")]),
                     station_last_pm_end(train, pd.Timestamp("2026-11-03", tz="Asia/Kolkata")))


def test_submission_order_duplicates_missing_and_invalid_targets():
    test = pd.DataFrame({"ID": ["a", "b"]})
    valid = pd.DataFrame({"ID": ["a", "b"], "Target": [0.0, 10.0]})
    validate_submission(valid, test)
    for bad in (valid.iloc[::-1].reset_index(drop=True),
                pd.DataFrame({"ID": ["a", "a"], "Target": [1.0, 2.0]}),
                pd.DataFrame({"ID": ["a"], "Target": [1.0]}),
                pd.DataFrame({"ID": ["a", "b"], "Target": [1.0, np.nan]}),
                pd.DataFrame({"ID": ["a", "b"], "Target": [1.0, -1.0]})):
        with pytest.raises(ValueError):
            validate_submission(bad, test)


def test_snapshot_sha256_records_exact_bytes(tmp_path):
    path = tmp_path / "official.csv"
    path.write_bytes(b"ID,Target\na,1\n")
    assert sha256(path) == hashlib.sha256(path.read_bytes()).hexdigest()
    first = sha256(path)
    path.write_bytes(b"ID,Target\na,2\n")
    assert sha256(path) != first
