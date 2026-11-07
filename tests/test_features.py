"""Unit tests for feature engineering system."""
from __future__ import annotations

import numpy as np
import pandas as pd

from mumbai_pm25.features.calendar import build_calendar_features
from mumbai_pm25.features.pipeline import build_feature_matrix
from mumbai_pm25.features.pm_history import extract_station_pm_features


def test_calendar_features():
    target_start = pd.date_range("2026-11-11 00:00:00", periods=24, freq="h", tz="Asia/Kolkata")
    locs = pd.Series([11606] * 12 + [11611] * 12)
    df = build_calendar_features(pd.Series(target_start), locs)

    expected_cols = {
        "hour", "weekday", "month", "day_of_year",
        "hour_sin", "hour_cos", "weekday_sin", "weekday_cos",
        "doy_sin", "doy_cos", "horizon_hours", "station_id",
        "station_11606", "station_11611", "station_3409510", "station_3409511",
    }
    assert expected_cols <= set(df.columns)
    assert len(df) == 24
    assert np.isfinite(df.to_numpy()).all()


def test_pm_history_features_strictly_past_only():
    starts = pd.date_range("2026-10-01 00:00:00", periods=24 * 10, freq="h", tz="Asia/Kolkata")
    vals = [20.0 + (i % 24) for i in range(len(starts))]
    series = pd.Series(vals, index=starts)

    cutoff = pd.Timestamp("2026-10-08 12:00:00", tz="Asia/Kolkata")
    feats = extract_station_pm_features(series, cutoff)

    assert feats["obs_count_24"] == 24
    assert feats["obs_count_72"] == 72
    assert feats["obs_age_hours"] == 0.0
    assert feats["median_24"] > 0
    assert feats["coverage_72"] == 1.0


def test_feature_matrix_pipeline():
    starts = pd.date_range("2026-10-01 00:00:00", periods=24 * 10, freq="h", tz="Asia/Kolkata")
    series1 = pd.Series([30.0] * len(starts), index=starts)
    series2 = pd.Series([45.0] * len(starts), index=starts)
    histories = {11606: series1, 11611: series2}

    target_df = pd.DataFrame({
        "location_id": [11606, 11611],
        "target_start": pd.date_range("2026-10-10 00:00:00", periods=2, freq="h", tz="Asia/Kolkata"),
        "horizon_hours": [1, 2],
    })
    cutoff = pd.Timestamp("2026-10-08 00:00:00", tz="Asia/Kolkata")

    X = build_feature_matrix(histories, target_df, cutoff, include_seasonal=False, include_spatial=True)
    assert len(X) == 2
    assert "hour_sin" in X.columns
    assert "median_72" in X.columns
    assert "city_median_pm25" in X.columns
    assert np.isfinite(X.to_numpy()).all()
