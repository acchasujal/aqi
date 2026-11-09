"""Compact regularised LightGBM model for residual PM2.5 prediction over climatology."""
from __future__ import annotations

from typing import Any, ClassVar

import numpy as np
import pandas as pd


class LightGBMResidualModel:
    """Multi-seed averaged compact LightGBM predicting (pm25 - climatology)."""

    FEATURE_COLS: ClassVar[list[str]] = [
        "lead_hours",
        "hour",
        "dayofweek",
        "doy",
        "clim",
        "a24",
        "a72",
        "a168",
        "count_168",
        "std_168",
        "staleness_hours",
        "station_id",
    ]

    def __init__(
        self,
        seeds: tuple[int, ...] = (42, 123, 999),
        learning_rate: float = 0.03,
        n_estimators: int = 300,
        num_leaves: int = 8,
        min_child_samples: int = 300,
        subsample: float = 0.7,
        colsample_bytree: float = 0.7,
        reg_lambda: float = 10.0,
        n_jobs: int = 4,
    ) -> None:
        self.seeds = seeds
        self.learning_rate = learning_rate
        self.n_estimators = n_estimators
        self.num_leaves = num_leaves
        self.min_child_samples = min_child_samples
        self.subsample = subsample
        self.colsample_bytree = colsample_bytree
        self.reg_lambda = reg_lambda
        self.n_jobs = n_jobs
        self.models_: list[Any] = []
        self.feature_names_: list[str] = []

    def _prepare_df(self, X: pd.DataFrame) -> pd.DataFrame:
        df = X.copy()
        # Ensure categorical type for station_id if present
        if "station_id" in df.columns:
            df["station_id"] = df["station_id"].astype("category")
        return df

    def fit(
        self,
        X: pd.DataFrame,
        y_residual: pd.Series | np.ndarray,
    ) -> LightGBMResidualModel:
        """Fit 3 seeded LightGBM regressors on raw-scale residual (pm25 - clim)."""
        import lightgbm as lgb

        df = self._prepare_df(X)
        available_cols = [c for c in self.FEATURE_COLS if c in df.columns]
        self.feature_names_ = available_cols

        X_mat = df[available_cols]
        y_vec = np.asarray(y_residual, dtype=float)

        cats = ["station_id"] if "station_id" in available_cols else "auto"

        self.models_ = []
        for seed in self.seeds:
            params = {
                "objective": "regression",
                "metric": "rmse",
                "learning_rate": self.learning_rate,
                "n_estimators": self.n_estimators,
                "num_leaves": self.num_leaves,
                "min_child_samples": self.min_child_samples,
                "subsample": self.subsample,
                "subsample_freq": 1,
                "colsample_bytree": self.colsample_bytree,
                "reg_lambda": self.reg_lambda,
                "random_state": seed,
                "verbosity": -1,
                "n_jobs": self.n_jobs,
            }
            model = lgb.LGBMRegressor(**params)
            model.fit(X_mat, y_vec, categorical_feature=cats)
            self.models_.append(model)

        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Predict ensemble average residual."""
        if not self.models_:
            raise ValueError("Model is not fitted. Call fit() first.")

        df = self._prepare_df(X)
        X_mat = df[self.feature_names_]

        preds = np.zeros(len(X_mat), dtype=float)
        for model in self.models_:
            preds += model.predict(X_mat)
        return preds / float(len(self.models_))

    def get_feature_importances(self) -> pd.Series:
        """Return average feature importances across seeds."""
        if not self.models_:
            raise ValueError("Model is not fitted.")
        imp = np.zeros(len(self.feature_names_), dtype=float)
        for model in self.models_:
            imp += model.feature_importances_
        return pd.Series(imp / len(self.models_), index=self.feature_names_).sort_values(ascending=False)
