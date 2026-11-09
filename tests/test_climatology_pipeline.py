"""Unit and regression tests for Climatology-First Mumbai PM2.5 pipeline."""
from __future__ import annotations

import numpy as np
import pandas as pd

from mumbai_pm25.climatology.anomaly import extract_recent_anomalies
from mumbai_pm25.climatology.blend import ClimatologyBlend
from mumbai_pm25.climatology.kernel import (
    KernelClimatology,
    circular_doy_distance,
    circular_hour_distance,
    normalized_doy,
)
from mumbai_pm25.climatology.lgbm_residual import LightGBMResidualModel
from mumbai_pm25.climatology.ridge_model import LeadBucketRidge


def test_normalized_doy_leap_and_non_leap():
    # 2024 is a leap year
    t_2024_feb28 = pd.Timestamp("2024-02-28 12:00:00", tz="Asia/Kolkata")
    t_2024_feb29 = pd.Timestamp("2024-02-29 12:00:00", tz="Asia/Kolkata")
    t_2024_mar01 = pd.Timestamp("2024-03-01 12:00:00", tz="Asia/Kolkata")

    # 2026 is a common year
    t_2026_feb28 = pd.Timestamp("2026-02-28 12:00:00", tz="Asia/Kolkata")
    t_2026_mar01 = pd.Timestamp("2026-03-01 12:00:00", tz="Asia/Kolkata")

    assert normalized_doy(t_2024_feb28) == 59.0
    assert normalized_doy(t_2024_feb29) == 59.5
    assert normalized_doy(t_2024_mar01) == 60.0

    assert normalized_doy(t_2026_feb28) == 59.0
    assert normalized_doy(t_2026_mar01) == 60.0


def test_circular_doy_distance():
    # Adjacent days across new year boundary: DOY 1 and DOY 365
    assert circular_doy_distance(1.0, 365.0) == 1.0
    assert circular_doy_distance(365.0, 1.0) == 1.0

    # Opposite sides of year: DOY 1 and DOY 183
    assert circular_doy_distance(1.0, 183.0) == 182.0

    # Vectorized computation
    d1 = np.array([1.0, 10.0, 360.0])
    d2 = np.array([365.0, 20.0, 5.0])
    expected = np.array([1.0, 10.0, 10.0])
    np.testing.assert_allclose(circular_doy_distance(d1, d2), expected)


def test_circular_hour_distance():
    # Adjacent hours across midnight boundary: 23:00 and 00:00
    assert circular_hour_distance(23.0, 0.0) == 1.0
    assert circular_hour_distance(0.0, 23.0) == 1.0

    # Midday vs midnight
    assert circular_hour_distance(0.0, 12.0) == 12.0
    assert circular_hour_distance(6.0, 18.0) == 12.0

    # Same hour
    assert circular_hour_distance(15.0, 15.0) == 0.0


def test_14_day_causality_gap():
    clim = KernelClimatology(sigma_doy=10.0, sigma_hour=1.0, clim_gap_days=14)
    origin = pd.Timestamp("2026-11-10 12:00:00", tz="Asia/Kolkata")

    # Dates including inside the 14-day gap
    dates = pd.date_range("2026-10-01", "2026-11-10", freq="h", tz="Asia/Kolkata")
    df = pd.DataFrame({"timestamp": dates, "pm25": 50.0})

    eligible = clim._extract_eligible_history(df, origin)
    assert not eligible.empty

    # Max timestamp in eligible history must be <= origin - 14 days
    cutoff = origin - pd.Timedelta(days=14)
    assert eligible["timestamp"].max() <= cutoff


def test_climatology_fallback_on_sparse_history():
    clim = KernelClimatology(sigma_doy=10.0, sigma_hour=1.0, min_weight=5.0)
    origin = pd.Timestamp("2026-11-10 12:00:00", tz="Asia/Kolkata")

    # History with only 1 observation far in time
    df = pd.DataFrame({
        "timestamp": [pd.Timestamp("2026-05-01 12:00:00", tz="Asia/Kolkata")],
        "pm25": [75.0],
    })
    target = pd.Timestamp("2026-11-12 12:00:00", tz="Asia/Kolkata")

    eligible = clim._extract_eligible_history(df, origin)
    res = clim.estimate(eligible, target)

    # With weight < min_weight, fallback triggers
    assert res["clim_source_type"] in ("hour_fallback", "median_fallback")
    assert res["clim_prediction"] == 75.0
    assert np.isfinite(res["clim_prediction"])


def test_extract_recent_anomalies():
    clim = KernelClimatology()
    origin = pd.Timestamp("2026-11-10 12:00:00", tz="Asia/Kolkata")

    # 30 days of hourly data up to origin so history older than 14-day gap exists
    dates = pd.date_range(origin - pd.Timedelta(days=30), origin, freq="h")
    df = pd.DataFrame({"timestamp": dates, "pm25": 60.0})

    anom = extract_recent_anomalies(df, origin, clim, window_hours=168)
    assert "a24" in anom
    assert "a72" in anom
    assert "a168" in anom
    assert anom["count_168"] > 0
    assert anom["staleness_hours"] == 0.0


def test_lead_bucket_ridge_fit_predict():
    ridge = LeadBucketRidge(n_buckets=5, alpha=10.0)

    # Mock features and residuals
    n_samples = 150
    leads = np.random.uniform(41, 90, n_samples)
    a24 = np.random.normal(5.0, 2.0, n_samples)
    a72 = np.random.normal(3.0, 1.5, n_samples)
    a168 = np.random.normal(1.0, 1.0, n_samples)

    # True decay: effect decreases with lead
    decay = np.maximum(0.0, 1.0 - (leads - 40.0) / 60.0)
    y_res = decay * a24 + np.random.normal(0, 0.5, n_samples)

    df = pd.DataFrame({
        "lead_hours": leads,
        "a24": a24,
        "a72": a72,
        "a168": a168,
    })

    ridge.fit(df, y_res, lead_col="lead_hours")
    assert len(ridge.models_) == 5
    assert len(ridge.bucket_stats_) == 5

    preds = ridge.predict(df, lead_col="lead_hours")
    assert len(preds) == n_samples
    assert np.all(np.isfinite(preds))


def test_lightgbm_residual_fit_predict():
    lgbm = LightGBMResidualModel(seeds=(42,), num_leaves=4, min_child_samples=5, n_estimators=10)

    n_samples = 100
    df = pd.DataFrame({
        "lead_hours": np.random.uniform(41, 90, n_samples),
        "hour": np.random.randint(0, 24, n_samples),
        "dayofweek": np.random.randint(0, 7, n_samples),
        "doy": np.random.uniform(1, 365, n_samples),
        "clim": np.random.uniform(20, 80, n_samples),
        "a24": np.random.normal(0, 5, n_samples),
        "a72": np.random.normal(0, 5, n_samples),
        "a168": np.random.normal(0, 5, n_samples),
        "count_168": np.full(n_samples, 168),
        "std_168": np.random.uniform(5, 15, n_samples),
        "staleness_hours": np.zeros(n_samples),
        "station_id": np.random.choice([11606, 11611], n_samples),
    })
    y_res = np.random.normal(0, 2, n_samples)

    lgbm.fit(df, y_res)
    preds = lgbm.predict(df)
    assert len(preds) == n_samples
    assert np.all(np.isfinite(preds))


def test_climatology_blend_simplex():
    blender = ClimatologyBlend(step=0.1)

    y_true = np.array([50.0, 60.0, 70.0, 80.0])
    p_clim = np.array([48.0, 62.0, 68.0, 81.0])
    p_ridge = np.array([50.0, 60.0, 70.0, 80.0])  # perfect
    p_lgbm = np.array([40.0, 50.0, 60.0, 70.0])

    blender.fit(y_true, p_clim, p_ridge, p_lgbm)
    weights = blender.weights_

    assert np.isclose(weights["clim"] + weights["ridge"] + weights["lgbm"], 1.0)
    assert weights["ridge"] >= 0.8  # should heavily favor p_ridge

    p_out = blender.predict(p_clim, p_ridge, p_lgbm)
    assert len(p_out) == len(y_true)
    assert np.all(p_out >= 0)
