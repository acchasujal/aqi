"""EXP-012 robust history candidate invariants."""
import numpy as np
import pandas as pd
import pytest

from mumbai_pm25.november_candidates import bounded_trend48, recent_median


def test_recent_median_irregular_missing_and_exact_cutoff():
    index = pd.DatetimeIndex(["2026-01-01 00:00", "2026-01-03 00:00",
                              "2026-01-04 23:00", "2026-01-05 00:00"], tz="Asia/Kolkata")
    history = pd.Series([10.0, np.nan, 30.0, 9999.0], index=index)
    cutoff = pd.Timestamp("2026-01-05 00:00", tz="Asia/Kolkata")
    assert recent_median(history, cutoff, 24) == 30.0
    assert recent_median(history, cutoff, 72) == 30.0
    assert recent_median(history, cutoff, 120) == 20.0
    assert recent_median(history, cutoff, 1) == 30.0
    assert recent_median(history.loc[history.index < cutoff], cutoff + pd.Timedelta(days=5), 1) == 20.0  # all-eligible fallback
    assert recent_median(history, pd.Timestamp("2025-12-31", tz="Asia/Kolkata"), 24) is None


def test_trend_bounded_decays_nonnegative_and_deterministic():
    cutoff = pd.Timestamp("2026-01-05 00:00", tz="Asia/Kolkata")
    index = pd.date_range(cutoff-pd.Timedelta(hours=96), periods=96, freq="h")
    history = pd.Series([5.0] * 48 + [200.0] * 48, index=index)
    targets = pd.DatetimeIndex([cutoff+pd.Timedelta(hours=48), cutoff+pd.Timedelta(hours=240)])
    first = bounded_trend48(history, cutoff, targets)
    second = bounded_trend48(history, cutoff, targets)
    np.testing.assert_array_equal(first, second)
    assert np.isfinite(first).all() and (first >= 0).all()
    assert 200 < first[1] < first[0] < 205


def test_trend_no_earlier_window_stays_at_recent_level():
    cutoff = pd.Timestamp("2026-01-05 00:00", tz="Asia/Kolkata")
    history = pd.Series([30.0], index=pd.DatetimeIndex([cutoff-pd.Timedelta(hours=1)]))
    target = pd.DatetimeIndex([cutoff+pd.Timedelta(hours=192)])
    assert bounded_trend48(history, cutoff, target)[0] == 30.0


def test_timezone_and_parameters_rejected():
    history = pd.Series([30.0], index=pd.DatetimeIndex(["2026-01-01"]))
    with pytest.raises(ValueError, match="timezone-aware"):
        recent_median(history, pd.Timestamp("2026-01-02"), 24)
    aware = history.copy()
    aware.index = aware.index.tz_localize("Asia/Kolkata")
    with pytest.raises(ValueError, match="hours"):
        recent_median(aware, pd.Timestamp("2026-01-02", tz="Asia/Kolkata"), 0)
