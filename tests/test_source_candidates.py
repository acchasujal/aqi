"""Tests for the isolated candidate C reconstruction."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from mumbai_pm25.source_candidates import branch_c, branch_recent, branch_seasonal, normalized_days


def test_pooled_sensor_weighting_and_calendar():
    times = pd.date_range("2024-11-01", periods=3, freq="D", tz="Asia/Kolkata")
    history = pd.DataFrame({"hour_start": [times[0], times[0], times[1], times[2]],
        "station_name": "Borivali East, Mumbai - IITM", "pm25": [10., 30., 50., 80.]})
    target = pd.DataFrame({"location_id": [11606], "target_start": [pd.Timestamp("2026-11-02", tz="Asia/Kolkata")]})
    assert branch_seasonal(history, target)[0] == pytest.approx(50)
    dates = pd.Series(pd.to_datetime(["2024-02-29", "2024-03-01", "2026-03-01"], utc=True))
    np.testing.assert_array_equal(normalized_days(dates), [59.5, 60., 60.])
    assert np.isnan(branch_seasonal(history.iloc[:2], target)[0])


def test_cutoff_missing_hours_future_perturbation_and_sparse_fallback():
    cutoff = pd.Timestamp("2026-07-01", tz="Asia/Kolkata")
    train = pd.DataFrame({"location_id": 11606,
        "target_start": [cutoff-pd.Timedelta(hours=h) for h in [200, 100, 72, 1, 0]],
        "pm25": [10., 20., 30., 50., 999999.]})
    target = pd.DataFrame({"location_id": [11606], "target_start": [cutoff+pd.Timedelta(hours=193)]})
    assert branch_recent(train, target, cutoff)[0] == 40
    original = branch_c(train, target, np.array([60.]), cutoff)
    train.loc[train.target_start.ge(cutoff), "pm25"] = 0.
    np.testing.assert_array_equal(original, branch_c(train, target, np.array([60.]), cutoff))
    assert branch_recent(train.loc[train.target_start.lt(cutoff-pd.Timedelta(hours=72))], target, cutoff)[0] == 20
    assert branch_recent(train.iloc[:1], target, cutoff)[0] == 10
    assert branch_c(train.iloc[:1], target, np.array([np.nan]), cutoff)[0] == 10
    with pytest.raises(ValueError, match="hourly"):
        branch_recent(train, target, cutoff+pd.Timedelta(minutes=30))
    with pytest.raises(ValueError, match="Duplicate"):
        branch_recent(pd.concat([train, train]), target, cutoff)
    with pytest.raises(ValueError, match="seasonal"):
        branch_c(train, target, np.array([np.inf]), cutoff)


def test_reproduction_refuses_overwrite(tmp_path):
    from scripts.audit_exp025 import git_blob, run

    assert git_blob(b"") == "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"
    with pytest.raises(FileExistsError):
        run(tmp_path, tmp_path)
