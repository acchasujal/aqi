"""Supervised forecasting models module: LightGBM, CatBoost, XGBoost, and Random Forest.

Provides a unified interface with target transformations (raw, sqrt, log1p, residual)
and strict non-negative, finite prediction outputs.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


class SupervisedForecaster:
    """Unified wrapper for gradient-boosted and tree-based forecasting models."""

    def __init__(
        self,
        model_family: str = "lightgbm",
        *,
        target_transform: str = "raw",
        params: dict[str, Any] | None = None,
        random_seed: int = 42,
    ) -> None:
        self.model_family = model_family.lower()
        self.target_transform = target_transform.lower()
        self.params = params or {}
        self.random_seed = random_seed
        self.model_: Any = None
        self.feature_names_: list[str] = []

    def _transform_target(self, y: np.ndarray, X: pd.DataFrame) -> np.ndarray:
        y_clean = np.maximum(0.0, y)
        if self.target_transform == "raw":
            return y_clean
        elif self.target_transform == "sqrt":
            return np.sqrt(y_clean)
        elif self.target_transform == "log1p":
            return np.log1p(y_clean)
        elif self.target_transform == "residual_median72":
            baseline = X["median_72"].to_numpy(dtype=float) if "median_72" in X else 40.0
            return y_clean - baseline
        else:
            raise ValueError(f"Unknown target transformation: {self.target_transform}")

    def _inverse_transform(self, pred: np.ndarray, X: pd.DataFrame) -> np.ndarray:
        if self.target_transform == "raw":
            inv = pred
        elif self.target_transform == "sqrt":
            inv = np.maximum(0.0, pred) ** 2
        elif self.target_transform == "log1p":
            inv = np.expm1(np.maximum(0.0, pred))
        elif self.target_transform == "residual_median72":
            baseline = X["median_72"].to_numpy(dtype=float) if "median_72" in X else 40.0
            inv = baseline + pred
        else:
            raise ValueError(f"Unknown target transformation: {self.target_transform}")
        return np.maximum(0.0, np.nan_to_num(inv, nan=40.0, posinf=1000.0, neginf=0.0))

    def _prepare_features(self, X: pd.DataFrame) -> pd.DataFrame:
        """Prepare dataframe features for modeling."""
        df = X.copy()
        # Drop raw timestamp columns if present
        for col in ["target_start", "target_end", "timestamp_ist"]:
            if col in df.columns:
                df = df.drop(columns=[col])
        return df

    def fit(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series | np.ndarray,
        X_val: pd.DataFrame | None = None,
        y_val: pd.Series | np.ndarray | None = None,
    ) -> SupervisedForecaster:
        """Fit the specified model family with target transformation."""
        X_tr = self._prepare_features(X_train)
        self.feature_names_ = list(X_tr.columns)
        y_tr = np.asarray(y_train, dtype=float)
        z_tr = self._transform_target(y_tr, X_tr)

        val_set = None
        if X_val is not None and y_val is not None:
            X_v = self._prepare_features(X_val)
            y_v = np.asarray(y_val, dtype=float)
            z_v = self._transform_target(y_v, X_v)
            val_set = (X_v, z_v)

        if self.model_family == "lightgbm":
            import lightgbm as lgb
            lgb_params = {
                "n_estimators": 150,
                "learning_rate": 0.05,
                "num_leaves": 31,
                "min_child_samples": 20,
                "subsample": 0.8,
                "colsample_bytree": 0.8,
                "reg_alpha": 0.1,
                "reg_lambda": 1.0,
                "random_state": self.random_seed,
                "n_jobs": 1,
                "verbose": -1,
            }
            user_params = self.params.copy()
            if "iterations" in user_params:
                user_params.setdefault("n_estimators", user_params.pop("iterations"))
            lgb_params.update(user_params)
            cats = ["station_id"] if "station_id" in X_tr.columns else "auto"
            self.model_ = lgb.LGBMRegressor(**lgb_params)
            eval_set = [val_set] if val_set is not None else None
            self.model_.fit(X_tr, z_tr, eval_set=eval_set, categorical_feature=cats)

        elif self.model_family == "catboost":
            import catboost as cb
            cb_params = {
                "iterations": 150,
                "learning_rate": 0.05,
                "depth": 6,
                "l2_leaf_reg": 3.0,
                "random_seed": self.random_seed,
                "thread_count": 1,
                "verbose": 0,
            }
            user_params = self.params.copy()
            if "n_estimators" in user_params:
                user_params.setdefault("iterations", user_params.pop("n_estimators"))
            cb_params.update(user_params)
            cats = ["station_id"] if "station_id" in X_tr.columns else []
            self.model_ = cb.CatBoostRegressor(**cb_params)
            eval_set = val_set if val_set is not None else None
            self.model_.fit(X_tr, z_tr, eval_set=eval_set, cat_features=cats)

        elif self.model_family == "xgboost":
            import xgboost as xgb
            xgb_params = {
                "n_estimators": 150,
                "learning_rate": 0.05,
                "max_depth": 6,
                "subsample": 0.8,
                "colsample_bytree": 0.8,
                "reg_alpha": 0.1,
                "reg_lambda": 1.0,
                "random_state": self.random_seed,
                "n_jobs": 1,
                "enable_categorical": "station_id" in X_tr.columns,
            }
            user_params = self.params.copy()
            if "iterations" in user_params:
                user_params.setdefault("n_estimators", user_params.pop("iterations"))
            xgb_params.update(user_params)
            self.model_ = xgb.XGBRegressor(**xgb_params)
            eval_set = [val_set] if val_set is not None else None
            self.model_.fit(X_tr, z_tr, eval_set=eval_set, verbose=False)

        elif self.model_family in {"random_forest", "rf"}:
            from sklearn.ensemble import RandomForestRegressor
            rf_params = {
                "n_estimators": 100,
                "max_depth": 12,
                "min_samples_leaf": 5,
                "random_state": self.random_seed,
                "n_jobs": 1,
            }
            user_params = self.params.copy()
            user_params.pop("iterations", None)
            user_params.pop("learning_rate", None)
            rf_params.update(user_params)
            self.model_ = RandomForestRegressor(**rf_params)
            self.model_.fit(X_tr, z_tr)

        else:
            raise ValueError(f"Unknown model family: {self.model_family}")

        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Generate original-scale non-negative predictions."""
        if self.model_ is None:
            raise ValueError("Model has not been fitted. Call fit() first.")
        X_p = self._prepare_features(X)
        z_pred = self.model_.predict(X_p)
        return self._inverse_transform(z_pred, X_p)

    def get_feature_importances(self) -> pd.Series:
        """Return feature importance scores indexed by feature name."""
        if self.model_ is None:
            raise ValueError("Model has not been fitted.")
        if hasattr(self.model_, "feature_importances_"):
            return pd.Series(self.model_.feature_importances_, index=self.feature_names_).sort_values(ascending=False)
        return pd.Series(dtype=float)
