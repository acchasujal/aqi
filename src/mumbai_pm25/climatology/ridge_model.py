"""Lead-bucket Ridge regression for regularised anomaly decay modeling."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge


class LeadBucketRidge:
    """Interpretable anomaly model fitting separate Ridge regressions per lead-time bucket."""

    def __init__(
        self,
        n_buckets: int = 5,
        alpha: float = 100.0,
        feature_cols: list[str] | None = None,
    ) -> None:
        if n_buckets < 1:
            raise ValueError(f"n_buckets must be >= 1, got {n_buckets}")
        if alpha < 0:
            raise ValueError(f"alpha must be non-negative, got {alpha}")

        self.n_buckets = int(n_buckets)
        self.alpha = float(alpha)
        self.feature_cols = feature_cols or ["a24", "a72", "a168"]
        self.bucket_edges_: np.ndarray | None = None
        self.models_: dict[int, Ridge] = {}
        self.bucket_stats_: list[dict] = []

    def fit(
        self,
        X: pd.DataFrame,
        y_residual: pd.Series | np.ndarray,
        lead_col: str = "lead_hours",
    ) -> LeadBucketRidge:
        """Fit separate Ridge regressions across lead-time buckets.

        Parameters:
            X: Feature matrix containing `lead_col` and `self.feature_cols`.
            y_residual: Target residual to predict: (future_pm25 - climatology).
            lead_col: Column name identifying forecast lead time.
        """
        leads = X[lead_col].to_numpy(dtype=float)
        y_res = np.asarray(y_residual, dtype=float)

        min_lead = float(np.min(leads))
        max_lead = float(np.max(leads))

        # Build equal-width bucket edges
        if min_lead == max_lead:
            self.bucket_edges_ = np.array([min_lead - 1.0, max_lead + 1.0])
        else:
            self.bucket_edges_ = np.linspace(min_lead, max_lead + 1e-5, self.n_buckets + 1)

        bucket_indices = np.digitize(leads, self.bucket_edges_) - 1
        bucket_indices = np.clip(bucket_indices, 0, len(self.bucket_edges_) - 2)

        X_feats = X[self.feature_cols].fillna(0.0).to_numpy(dtype=float)

        self.models_ = {}
        self.bucket_stats_ = []

        for b_idx in range(len(self.bucket_edges_) - 1):
            mask = bucket_indices == b_idx
            n_samples = int(np.sum(mask))

            model = Ridge(alpha=self.alpha, fit_intercept=True)
            if n_samples >= 10:
                model.fit(X_feats[mask], y_res[mask])
            else:
                # Fallback to zero residual if sample size in bucket is too small
                model.fit(np.zeros((2, len(self.feature_cols))), np.zeros(2))

            self.models_[b_idx] = model

            stat_row = {
                "bucket_index": b_idx,
                "lead_min": float(self.bucket_edges_[b_idx]),
                "lead_max": float(self.bucket_edges_[b_idx + 1]),
                "sample_count": n_samples,
                "intercept": float(model.intercept_),
            }
            for f_name, coef in zip(self.feature_cols, model.coef_):
                stat_row[f"coef_{f_name}"] = float(coef)
            self.bucket_stats_.append(stat_row)

        return self

    def predict(
        self,
        X: pd.DataFrame,
        lead_col: str = "lead_hours",
    ) -> np.ndarray:
        """Predict expected residual (pm25 - clim) for given features."""
        if self.bucket_edges_ is None:
            raise ValueError("Model is not fitted. Call fit() first.")

        leads = X[lead_col].to_numpy(dtype=float)
        bucket_indices = np.digitize(leads, self.bucket_edges_) - 1
        bucket_indices = np.clip(bucket_indices, 0, len(self.bucket_edges_) - 2)

        X_feats = X[self.feature_cols].fillna(0.0).to_numpy(dtype=float)
        preds = np.zeros(len(X), dtype=float)

        for b_idx in range(len(self.bucket_edges_) - 1):
            mask = bucket_indices == b_idx
            if np.any(mask):
                model = self.models_[b_idx]
                preds[mask] = model.predict(X_feats[mask])

        return preds

    def get_bucket_coefficients(self) -> pd.DataFrame:
        """Return table of fitted coefficients and sample counts per lead bucket."""
        return pd.DataFrame(self.bucket_stats_)
