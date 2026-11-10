"""Regression checks for TASK010 calendar alignment and raw target scoring."""
from __future__ import annotations

import pandas as pd

from mumbai_pm25.historical_archive import P_FIX_SERIES, build_seasonal_features
from scripts.run_task010 import legacy_doy_same_hour, score


def test_exact_calendar_uses_2024_month_day_across_leap_offset():
    # 2026-11-09 is day 313; in leap year 2024 the same month/day is day 314.
    # The legacy 365-day DOY window drops Nov 23 at its upper edge; exact month/day includes it.
    history = pd.DataFrame({
        "series_id": [P_FIX_SERIES[11606][0]] * 3,
        "hour_start": pd.to_datetime([
            "2024-10-26 00:00+05:30", "2024-11-22 00:00+05:30", "2024-11-23 00:00+05:30"
        ], utc=True).tz_convert("Asia/Kolkata"),
        "pm25": [3.0, 6.0, 9.0],
    })
    target = pd.DataFrame({"location_id": [11606],
                           "target_start": [pd.Timestamp("2026-11-09 00:00", tz="Asia/Kolkata")]})
    legacy = legacy_doy_same_hour(history, target).iloc[0]
    exact = build_seasonal_features(history, target, series_map=P_FIX_SERIES).hist24_same_hour_mean.iloc[0]
    assert pd.isna(legacy)
    assert exact == 6.0


def test_task010_primary_score_keeps_extreme_validation_label():
    rows = pd.DataFrame({"fold_id": ["a", "a"], "y": [20.0, 688.065],
                         "P_fix": [20.0, 250.0]})
    scored = score(rows, ["P_fix"]).iloc[0]
    assert scored.rows == 2
    assert scored.rows_y_ge_250 == 1
    assert scored.full_target_rmse == ((688.065-250.0)**2/2)**0.5
