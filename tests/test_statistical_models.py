"""Tests for statistical forecasting baselines."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from mumbai_pm25.models.statistical import (
    StatisticalForecaster,
    compute_station_history_stats,
)


@pytest.fixture
def sample_station_history():
    """Create a 14-day hourly history for station 11606."""
    starts = pd.date_range("2026-01-01 00:00:00", periods=24 * 14, freq="h", tz="Asia/Kolkata")
    values = [20.0 + (i % 24) * 2.0 for i in range(len(starts))]
    df = pd.DataFrame({
        "location_id": [11606] * len(starts),
        "target_start": starts,
        "pm25": values,
    })
    return df


def test_compute_station_history_stats(sample_station_history):
    cutoff = pd.Timestamp("2026-01-14 00:00:00", tz="Asia/Kolkata")
    series = sample_station_history.set_index("target_start")["pm25"]
    stats = compute_station_history_stats(series, cutoff, window_hours=72)

    assert stats.obs_count == 72
    assert stats.coverage_ratio == 1.0
    assert stats.age_hours == 0.0
    assert stats.latest_obs is not None
    assert stats.median is not None
    assert stats.mean is not None


def test_all_statistical_methods_produce_valid_predictions(sample_station_history):
    target_hours = pd.date_range("2026-01-14 00:00:00", periods=48, freq="h", tz="Asia/Kolkata")
    cutoff = pd.Timestamp("2026-01-12 00:00:00", tz="Asia/Kolkata")  # 48h gap

    methods = [
        "last",
        "median24",
        "median72",
        "median168",
        "mean24",
        "mean72",
        "mean168",
        "ewm72",
        "diurnal7",
        "hour_week4",
        "trend_adjusted_median",
        "seasonal_2024",
        "seasonal_blend50_median72",
    ]

    for method in methods:
        forecaster = StatisticalForecaster(method=method)
        forecaster.fit(sample_station_history)
        preds = forecaster.predict_station_block(11606, target_hours, cutoff)

        assert len(preds) == 48, f"Method {method} returned wrong length"
        assert np.isfinite(preds).all(), f"Method {method} returned non-finite predictions"
        assert (preds >= 0.0).all(), f"Method {method} returned negative predictions"


def test_trend_adjusted_median_direction(sample_station_history):
    """When recent 24h is higher than recent 72h, trend adjustment should be positive."""
    # Modify recent 24h to be sharply higher
    mod_history = sample_station_history.copy()
    cutoff = pd.Timestamp("2026-01-14 00:00:00", tz="Asia/Kolkata")
    mask = (mod_history.target_start >= cutoff - pd.Timedelta(hours=24)) & (mod_history.target_start < cutoff)
    mod_history.loc[mask, "pm25"] = 150.0

    target_hours = pd.date_range("2026-01-14 00:00:00", periods=10, freq="h", tz="Asia/Kolkata")
    m_base = StatisticalForecaster(method="median24").fit(mod_history).predict_station_block(11606, target_hours, cutoff)
    m_trend = StatisticalForecaster(method="trend_adjusted_median").fit(mod_history).predict_station_block(11606, target_hours, cutoff)

    assert m_trend[0] >= m_base[0]
