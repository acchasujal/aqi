"""Tests for atmospheric micro-meteorology physics features, GAM, and horizon stabilization."""

import numpy as np
import pandas as pd

from mumbai_pm25.climatology.horizon_stabilizer import (
    ConstrainedStackingEnsemble,
    HorizonStabilizer,
)
from mumbai_pm25.features.physics import (
    compute_atmospheric_physics_features,
    compute_station_geometry,
    extract_interstation_advection,
)
from mumbai_pm25.models.physics_gam import DualScalePhysicsGAM


def test_station_geometry_correctness():
    dist_km, _dir_east, _dir_north = compute_station_geometry()
    assert dist_km.shape == (4, 4)
    # Diagonal should be zero
    np.testing.assert_allclose(np.diag(dist_km), 0.0)
    # Distances between distinct stations should be positive (5-30 km in Mumbai)
    assert (dist_km[~np.eye(4, dtype=bool)] > 2.0).all()
    assert (dist_km[~np.eye(4, dtype=bool)] < 50.0).all()


def test_atmospheric_physics_feature_generation():
    df = pd.DataFrame({
        "location_id": [11606, 11611, 3409510, 3409511],
        "hour": [3, 9, 14, 21],
        "target_start": pd.date_range("2026-11-10 00:00:00", periods=4, freq="h", tz="Asia/Kolkata"),
    })
    enriched = compute_atmospheric_physics_features(df)

    expected_cols = [
        "pblh", "log_pblh", "vc", "log1p_vc",
        "u10", "v10", "onshore_breeze",
        "deonar_transport_proxy", "thane_creek_transport_proxy",
        "dewpoint_depression", "stagnation_index",
    ]
    for col in expected_cols:
        assert col in enriched.columns, f"Missing column: {col}"
        assert np.isfinite(enriched[col]).all(), f"Non-finite values in {col}"

    # Afternoon ventilation should be higher than nocturnal ventilation
    assert enriched.loc[2, "vc"] > enriched.loc[0, "vc"]


def test_interstation_advection():
    pm_dict = {11606: 30.0, 11611: 40.0, 3409510: 50.0, 3409511: 80.0}
    # Wind blowing from 75° (ENE -> WSW)
    advected = extract_interstation_advection(pm_dict, wind_speed=3.0, wind_dir_rad=np.deg2rad(75.0))
    assert len(advected) == 4
    for sid in [11606, 11611, 3409510, 3409511]:
        assert sid in advected
        assert advected[sid] > 0.0


def test_dual_scale_physics_gam():
    np.random.seed(42)
    n = 100
    df = pd.DataFrame({
        "location_id": np.random.choice([11606, 11611, 3409510, 3409511], size=n),
        "hour": np.random.randint(0, 24, size=n),
        "log1p_vc": np.random.uniform(4.0, 8.0, size=n),
        "onshore_breeze": np.random.uniform(-2.0, 3.0, size=n),
        "deonar_transport_proxy": np.random.uniform(0.0, 2.0, size=n),
        "median_72": np.random.uniform(30.0, 70.0, size=n),
    })
    y = df["median_72"] + 10.0 * np.sin(2.0 * np.pi * df["hour"] / 24.0) + np.random.normal(0, 3, size=n)

    gam = DualScalePhysicsGAM(alpha=5.0)
    gam.fit(df, y)
    preds = gam.predict(df)

    assert len(preds) == n
    assert (preds > 0.0).all()
    assert np.isfinite(preds).all()


def test_horizon_stabilizer():
    stabilizer = HorizonStabilizer(near_horizon_cutoff=24.0, far_horizon_cutoff=72.0, max_prior_weight=0.50)
    leads = np.array([12.0, 24.0, 48.0, 72.0, 96.0])
    weights = stabilizer.compute_prior_weights(leads)

    assert weights[0] == 0.0  # h < 24
    assert weights[1] == 0.0  # h == 24
    assert 0.20 < weights[2] < 0.30  # h == 48
    assert weights[3] == 0.50  # h == 72
    assert weights[4] == 0.50  # h > 72 capped at max_prior_weight


def test_constrained_stacking_ensemble():
    n = 120
    np.random.seed(42)
    y_true = np.random.uniform(30.0, 80.0, size=n)
    p1 = y_true + np.random.normal(0, 5, size=n)
    p2 = y_true + np.random.normal(0, 8, size=n)
    p3 = y_true + np.random.normal(0, 10, size=n)
    P = np.column_stack([p1, p2, p3])
    station_ids = np.random.choice([11606, 11611, 3409510, 3409511], size=n)

    ensemble = ConstrainedStackingEnsemble(apply_station_shrinkage=True)
    ensemble.fit(y_true, P, ["m1", "m2", "m3"], station_ids=station_ids)

    assert ensemble.weights_ is not None
    assert np.isclose(np.sum(ensemble.weights_), 1.0)
    assert (ensemble.weights_ >= 0.0).all()

    preds = ensemble.predict(P, station_ids=station_ids)
    assert len(preds) == n
    assert (preds >= 0.0).all()
