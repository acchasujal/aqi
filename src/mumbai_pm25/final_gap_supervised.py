"""Compact residual LightGBM challengers, fitted only after block availability."""
from __future__ import annotations

import numpy as np
import pandas as pd

from mumbai_pm25.final_gap import FEATURES, SEED, eligible_training_rows

SUPERVISED_MODELS = ("lgbm_delta", "lgbm_logratio", "lgbm_sqrt")


def fit_predict(training: pd.DataFrame, validation: pd.DataFrame,
                model_name: str, *, fitting_cutoff: pd.Timestamp) -> np.ndarray:
    """Use all labels; log1p offsets handle zero without deleting any label."""
    from lightgbm import LGBMRegressor

    eligible = eligible_training_rows(training, fitting_cutoff)
    if len(eligible) != len(training) or len(training) < 500:
        raise ValueError("Need >=500 eligible labels from complete available training blocks")
    if model_name not in SUPERVISED_MODELS:
        raise ValueError(f"Unknown supervised model {model_name}")
    y = training.y.to_numpy(dtype=float)
    level = training.median72.to_numpy(dtype=float)
    if model_name == "lgbm_delta":
        response = y-level
    elif model_name == "lgbm_logratio":
        response = np.log1p(y)-np.log1p(level)
    else:
        response = np.sqrt(y)
    model = LGBMRegressor(n_estimators=160, learning_rate=.03, num_leaves=7,
                          min_child_samples=120, reg_lambda=10., random_state=SEED,
                          n_jobs=2, deterministic=True, force_col_wise=True, verbosity=-1)
    # Native missing handling is learned within this fitting fold; no global imputer.
    model.fit(training.reindex(columns=FEATURES).astype(float), response)
    prediction = model.predict(validation.reindex(columns=FEATURES).astype(float))
    if model_name == "lgbm_delta":
        prediction += validation.median72.to_numpy(dtype=float)
    elif model_name == "lgbm_logratio":
        prediction = np.expm1(prediction + np.log1p(validation.median72.to_numpy(dtype=float)))
    else:
        prediction = np.maximum(prediction, 0)**2
    prediction = np.maximum(prediction, 0)
    if not np.isfinite(prediction).all():
        raise ValueError("LightGBM generated nonfinite predictions")
    return prediction
