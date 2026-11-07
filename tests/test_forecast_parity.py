"""EXP-009 shared forecast and end-to-end parity checks."""
import numpy as np
import pandas as pd
import pytest

from mumbai_pm25.forecast import combine_forecasts, predict_test_with_hist24_blend, recent_median72
from scripts.validate_seasonal_history import _seasonal_baseline_for_fold


@pytest.mark.parametrize("recent,seasonal,expected", [
    (20.0, 40.0, 30.0), (20.0, None, 20.0), (None, 40.0, 40.0),
])
def test_fallback_contract(recent, seasonal, expected):
    assert combine_forecasts(recent, seasonal) == expected


def test_missing_and_invalid_components():
    with pytest.raises(ValueError, match="Neither"):
        combine_forecasts(None, None)
    for bad in [-1.0, np.nan, np.inf]:
        with pytest.raises(ValueError, match="finite and non-negative"):
            combine_forecasts(bad, 30.0)


def test_recent_cutoff_window_and_boundary():
    idx = pd.DatetimeIndex(["2026-01-01 00:00", "2026-01-04 00:00", "2026-01-05 00:00"], tz="Asia/Kolkata")
    values = pd.Series([10.0, np.nan, 999.0], index=idx)
    cutoff = pd.Timestamp("2026-01-05 00:00", tz="Asia/Kolkata")
    assert recent_median72(values, cutoff) == 10.0
    assert recent_median72(values, pd.Timestamp("2025-12-31", tz="Asia/Kolkata")) is None
    with pytest.raises(ValueError, match="timezone-aware"):
        recent_median72(values, pd.Timestamp("2026-01-05"))


def test_actual_validation_inference_seasonal_only_parity():
    starts = pd.date_range("2024-01-01", periods=24 * 20, freq="h", tz="Asia/Kolkata")
    archive = pd.DataFrame({"station_name": "Borivali East, Mumbai - IITM", "hour_start": starts,
                            "pm25": 40.0, "source": "cpcb_caaqm"})
    target = pd.Timestamp("2026-01-05 10:00", tz="Asia/Kolkata")
    cutoff = pd.Timestamp("2026-01-04 10:00", tz="Asia/Kolkata")
    fold = pd.DataFrame({"location_id": [11606], "target_start": [target], "cutoff": [cutoff]})
    validation = _seasonal_baseline_for_fold(archive, fold, {})["hist24_blend50_median72"][0]
    train = pd.DataFrame({"location_id": [9999], "target_start": [cutoff - pd.Timedelta(hours=2)], "pm25": [20.0]})
    test = pd.DataFrame({"ID": ["one"], "location_id": [11606], "target_start": [target]})
    production = predict_test_with_hist24_blend(train, test, archive, issue_time=target,
                                                pm_history_cutoff=cutoff).Target.iloc[0]
    assert validation == production == 40.0
    assert predict_test_with_hist24_blend(train, test, archive, issue_time=target,
                                          pm_history_cutoff=cutoff).Target.iloc[0] == production


def test_no_eligible_pm_anywhere_uses_seasonal_or_errors():
    starts = pd.date_range("2024-01-01", periods=24 * 20, freq="h", tz="Asia/Kolkata")
    archive = pd.DataFrame({"station_name": "Borivali East, Mumbai - IITM", "hour_start": starts,
                            "pm25": 40.0, "source": "cpcb_caaqm"})
    issue = pd.Timestamp("2026-01-05 10:00", tz="Asia/Kolkata")
    train = pd.DataFrame({"location_id": [11606], "target_start": [issue], "pm25": [9999.0]})
    test = pd.DataFrame({"ID": ["one"], "location_id": [11606], "target_start": [issue]})
    assert predict_test_with_hist24_blend(train, test, archive, issue_time=issue).Target.iloc[0] == 40.0
    no_archive = archive.iloc[:0]
    with pytest.raises(ValueError, match="Neither recent PM nor seasonal history"):
        predict_test_with_hist24_blend(train, test, no_archive, issue_time=issue)


def test_actual_validation_inference_both_components_parity():
    starts = pd.date_range("2024-01-01", periods=24 * 20, freq="h", tz="Asia/Kolkata")
    archive = pd.DataFrame({"station_name": "Borivali East, Mumbai - IITM", "hour_start": starts,
                            "pm25": 40.0, "source": "cpcb_caaqm"})
    target = pd.Timestamp("2026-01-05 10:00", tz="Asia/Kolkata")
    cutoff = target - pd.Timedelta(hours=24)
    observed = cutoff - pd.Timedelta(hours=1)
    train = pd.DataFrame({"location_id": [11606], "target_start": [observed], "pm25": [20.0]})
    fold = pd.DataFrame({"location_id": [11606], "target_start": [target], "cutoff": [cutoff]})
    history = pd.Series([20.0], index=pd.DatetimeIndex([observed]))
    validation = _seasonal_baseline_for_fold(archive, fold, {11606: history})["hist24_blend50_median72"][0]
    test = pd.DataFrame({"ID": ["one"], "location_id": [11606], "target_start": [target]})
    production = predict_test_with_hist24_blend(train, test, archive, issue_time=target,
                                                pm_history_cutoff=cutoff).Target.iloc[0]
    assert validation == production == 30.0
