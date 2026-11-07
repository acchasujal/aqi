"""Unit tests for supervised forecasting models."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from mumbai_pm25.models.supervised import SupervisedForecaster


@pytest.fixture
def synthetic_features_and_target():
    np.random.seed(42)
    n = 120
    df = pd.DataFrame({
        "hour": np.random.randint(0, 24, n),
        "hour_sin": np.random.uniform(-1, 1, n),
        "hour_cos": np.random.uniform(-1, 1, n),
        "median_24": np.random.uniform(20, 80, n),
        "median_72": np.random.uniform(20, 80, n),
        "station_id": np.random.choice([11606, 11611, 3409510, 3409511], n),
        "city_median_pm25": np.random.uniform(25, 75, n),
    })
    y = df["median_72"] + np.random.normal(0, 5, n)
    y = np.maximum(5.0, y)
    return df, y


@pytest.mark.parametrize("family", ["lightgbm", "catboost", "xgboost", "random_forest"])
def test_all_model_families_fit_and_predict(family, synthetic_features_and_target):
    X, y = synthetic_features_and_target
    model = SupervisedForecaster(
        model_family=family,
        target_transform="raw",
        params={"n_estimators": 10, "iterations": 10},
    )
    model.fit(X, y)
    preds = model.predict(X)

    assert len(preds) == len(X)
    assert np.isfinite(preds).all()
    assert (preds >= 0.0).all()


@pytest.mark.parametrize("transform", ["raw", "sqrt", "log1p", "residual_median72"])
def test_all_target_transforms(transform, synthetic_features_and_target):
    X, y = synthetic_features_and_target
    model = SupervisedForecaster(
        model_family="lightgbm",
        target_transform=transform,
        params={"n_estimators": 10},
    )
    model.fit(X, y)
    preds = model.predict(X)

    assert len(preds) == len(X)
    assert np.isfinite(preds).all()
    assert (preds >= 0.0).all()


def test_feature_importance_extraction(synthetic_features_and_target):
    X, y = synthetic_features_and_target
    model = SupervisedForecaster(model_family="lightgbm", params={"n_estimators": 10})
    model.fit(X, y)
    imp = model.get_feature_importances()

    assert len(imp) == len(X.columns)
    assert (imp >= 0).all()
