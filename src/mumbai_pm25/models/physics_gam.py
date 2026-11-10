"""Dual-scale synoptic-diurnal baseline (Physics GAM) using Fourier harmonics and atmospheric dispersion."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import HuberRegressor, Ridge

TARGET_STATIONS = [11606, 11611, 3409510, 3409511]


class DualScalePhysicsGAM:
    """Interpretable, regularised Generalized Additive Model combining:

    1. Multi-harmonic diurnal basis (24h, 12h, 8h Fourier cycles)
    2. Atmospheric dispersion regressors (VC, onshore breeze, source alignments)
    3. Station-specific intercepts and scale factors
    """

    def __init__(
        self,
        alpha: float = 10.0,
        use_huber: bool = True,
        huber_epsilon: float = 1.35,
    ) -> None:
        self.alpha = float(alpha)
        self.use_huber = bool(use_huber)
        self.huber_epsilon = float(huber_epsilon)
        self.models_: dict[int, Ridge | HuberRegressor] = {}
        self.station_baselines_: dict[int, float] = {}

    def _build_design_matrix(self, X: pd.DataFrame) -> np.ndarray:
        """Construct multi-harmonic Fourier diurnal basis and atmospheric physics columns."""
        n_rows = len(X)
        if "hour" in X.columns:
            hours = X["hour"].to_numpy(dtype=float)
        elif "target_start" in X.columns:
            hours = pd.to_datetime(X["target_start"]).dt.hour.to_numpy(dtype=float)
        else:
            hours = np.zeros(n_rows, dtype=float)

        # 3-harmonic Fourier diurnal basis
        t_rad = 2.0 * np.pi * hours / 24.0
        sin_24 = np.sin(t_rad)
        cos_24 = np.cos(t_rad)
        sin_12 = np.sin(2.0 * t_rad)
        cos_12 = np.cos(2.0 * t_rad)
        sin_8 = np.sin(3.0 * t_rad)
        cos_8 = np.cos(3.0 * t_rad)

        feats = [sin_24, cos_24, sin_12, cos_12, sin_8, cos_8]

        # Atmospheric dispersion terms if present
        disp_cols = [
            "log1p_vc",
            "onshore_breeze",
            "deonar_transport_proxy",
            "thane_creek_transport_proxy",
            "dewpoint_depression",
            "stagnation_index",
        ]
        for c in disp_cols:
            if c in X.columns:
                feats.append(X[c].fillna(0.0).to_numpy(dtype=float))
            else:
                feats.append(np.zeros(n_rows, dtype=float))

        # Recent station level if available
        if "median_72" in X.columns:
            feats.append(X["median_72"].fillna(40.0).to_numpy(dtype=float))
        elif "median72" in X.columns:
            feats.append(X["median72"].fillna(40.0).to_numpy(dtype=float))

        return np.column_stack(feats)

    def fit(self, X: pd.DataFrame, y: pd.Series | np.ndarray) -> DualScalePhysicsGAM:
        """Fit independent regularised physics GAM per monitoring station."""
        y_arr = np.asarray(y, dtype=float)
        locs = X["location_id"].to_numpy(dtype=int) if "location_id" in X.columns else np.full(len(X), 11606)

        for sid in np.unique(locs):
            mask = locs == sid
            X_s = X[mask]
            y_s = y_arr[mask]

            if len(y_s) < 5:
                continue

            Z_s = self._build_design_matrix(X_s)
            self.station_baselines_[sid] = float(np.median(y_s))

            if self.use_huber:
                reg = HuberRegressor(alpha=self.alpha, epsilon=self.huber_epsilon, max_iter=200)
            else:
                reg = Ridge(alpha=self.alpha)

            reg.fit(Z_s, y_s)
            self.models_[sid] = reg

        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Generate smooth physics-guided PM2.5 predictions."""
        preds = np.full(len(X), 40.0, dtype=float)
        locs = X["location_id"].to_numpy(dtype=int) if "location_id" in X.columns else np.full(len(X), 11606)

        for sid in np.unique(locs):
            mask = locs == sid
            if sid not in self.models_:
                preds[mask] = self.station_baselines_.get(sid, 40.0)
                continue

            X_s = X[mask]
            Z_s = self._build_design_matrix(X_s)
            p_s = self.models_[sid].predict(Z_s)
            preds[mask] = np.maximum(p_s, 2.0)

        return preds
