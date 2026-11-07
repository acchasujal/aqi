"""EXP-011 calendar matching and legacy preservation."""
import numpy as np
import pandas as pd
import pytest

from mumbai_pm25.historical_archive import build_seasonal_features


def history() -> pd.DataFrame:
    dates = pd.date_range("2024-01-01 10:00", "2024-12-31 10:00", freq="D", tz="Asia/Kolkata")
    return pd.DataFrame({"station_name": "Byculla, Mumbai - BMC", "hour_start": dates,
                         "pm25": np.arange(len(dates), dtype=float), "source": "cpcb_caaqm"})


def feature(target: str, mode: str, window: int = 14) -> pd.Series:
    t = pd.DataFrame({"location_id": [3409510], "target_start": [pd.Timestamp(target, tz="Asia/Kolkata")]})
    return build_seasonal_features(history(), t, calendar_mode=mode, window_days=window,
                                   min_obs=1).iloc[0]


@pytest.mark.parametrize("date,expected", [
    ("2026-02-28 10:00", 58.0), ("2026-03-01 10:00", 60.0),
    ("2026-11-11 10:00", 315.0), ("2026-11-12 10:00", 316.0),
])
def test_calendar_exact_month_day(date, expected):
    assert feature(date, "month_day_365", 0).hist24_same_hour_mean == expected


def test_feb29_excluded_and_target_missing():
    assert np.isnan(feature("2024-02-29 10:00", "month_day_365", 0).hist24_same_hour_mean)
    assert feature("2026-02-28 10:00", "month_day_365", 1).hist24_coverage == 3


def test_new_year_wrap_and_same_hour():
    assert feature("2026-01-01 10:00", "month_day_365", 1).hist24_coverage == 3
    assert feature("2026-12-31 10:00", "month_day_365", 1).hist24_coverage == 3


def test_legacy_unchanged_and_deterministic():
    old = feature("2026-11-11 10:00", "legacy_doy", 0)
    assert old.hist24_same_hour_mean == 314.0
    new = feature("2026-11-11 10:00", "month_day_365", 0)
    assert new.hist24_same_hour_mean == 315.0
    assert new.equals(feature("2026-11-11 10:00", "month_day_365", 0))


def test_missing_history_and_bad_mode():
    target = pd.DataFrame({"location_id": [3409510], "target_start": [pd.Timestamp("2026-11-11", tz="Asia/Kolkata")]})
    assert np.isnan(build_seasonal_features(history().iloc[:0], target,
                                             calendar_mode="month_day_365").hist24_same_hour_mean.iloc[0])
    with pytest.raises(ValueError, match="calendar_mode"):
        build_seasonal_features(history(), target, calendar_mode="unknown")
