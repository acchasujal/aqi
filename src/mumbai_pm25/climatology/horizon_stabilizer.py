"""Horizon-aware variance stabilization and constrained multi-scale ensemble stacking."""

from __future__ import annotations

import numpy as np
from scipy.optimize import minimize
from sklearn.metrics import root_mean_squared_error

TARGET_STATIONS = [11606, 11611, 3409510, 3409511]


class HorizonStabilizer:
    """Stabilizes forecast variance at deep horizons by blending towards the climatological prior.

    At short horizons (h <= 24h), dynamic atmospheric and diurnal models provide superior tracking.
    At long horizons (h >= 48h to 96h), forecast uncertainty compounds; decaying volatile residual
    components into the ultra-stable Climatology-First prior prevents explosive error.
    """

    def __init__(
        self,
        near_horizon_cutoff: float = 24.0,
        far_horizon_cutoff: float = 72.0,
        max_prior_weight: float = 0.40,
    ) -> None:
        self.near_horizon_cutoff = float(near_horizon_cutoff)
        self.far_horizon_cutoff = float(far_horizon_cutoff)
        self.max_prior_weight = float(max_prior_weight)

    def compute_prior_weights(self, lead_hours: np.ndarray) -> np.ndarray:
        """Compute horizon-dependent blend weight on the climatology prior [0.0, max_prior_weight]."""
        leads = np.asarray(lead_hours, dtype=float)
        span = max(self.far_horizon_cutoff - self.near_horizon_cutoff, 1.0)
        norm_lead = np.clip((leads - self.near_horizon_cutoff) / span, 0.0, 1.0)
        return norm_lead * self.max_prior_weight

    def stabilize(
        self,
        p_dynamic: np.ndarray,
        p_prior: np.ndarray,
        lead_hours: np.ndarray,
    ) -> np.ndarray:
        """Apply smooth horizon stabilization to combine dynamic predictions with prior."""
        w_prior = self.compute_prior_weights(lead_hours)
        p_dyn = np.asarray(p_dynamic, dtype=float)
        p_pri = np.asarray(p_prior, dtype=float)
        return (1.0 - w_prior) * p_dyn + w_prior * p_pri


class ConstrainedStackingEnsemble:
    """SLSQP-optimized constrained stacking ensemble with station-specific calibration."""

    def __init__(
        self,
        apply_station_shrinkage: bool = True,
        shrinkage_bounds: tuple[float, float] = (0.85, 1.15),
    ) -> None:
        self.apply_station_shrinkage = bool(apply_station_shrinkage)
        self.shrinkage_bounds = shrinkage_bounds
        self.weights_: np.ndarray | None = None
        self.station_alphas_: dict[int, float] = {sid: 1.0 for sid in TARGET_STATIONS}
        self.station_shifts_: dict[int, float] = {sid: 0.0 for sid in TARGET_STATIONS}
        self.model_names_: list[str] = []

    def fit(
        self,
        y_true: np.ndarray,
        predictions_matrix: np.ndarray,
        model_names: list[str],
        station_ids: np.ndarray | None = None,
    ) -> ConstrainedStackingEnsemble:
        """Fit non-negative weights summing to 1 minimizing RMSE via SLSQP."""
        Y = np.asarray(y_true, dtype=float)
        P = np.asarray(predictions_matrix, dtype=float)  # shape (N, M)
        _n_samples, n_models = P.shape
        self.model_names_ = list(model_names)

        # Initial uniform weights
        w0 = np.full(n_models, 1.0 / n_models, dtype=float)
        bounds = [(0.0, 1.0) for _ in range(n_models)]
        constraints = {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}

        def loss_fn(w: np.ndarray) -> float:
            pred = P @ w
            return float(root_mean_squared_error(Y, pred))

        res = minimize(
            loss_fn,
            w0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"maxiter": 300, "ftol": 1e-6},
        )
        self.weights_ = res.x / np.sum(res.x)

        # Station-specific shrinkage calibration
        if self.apply_station_shrinkage and station_ids is not None:
            raw_ensemble_pred = P @ self.weights_
            s_ids = np.asarray(station_ids, dtype=int)

            for sid in np.unique(s_ids):
                mask = s_ids == sid
                if np.sum(mask) < 10:
                    continue
                y_s = Y[mask]
                p_s = raw_ensemble_pred[mask]

                # Fit scale alpha and shift beta: y ≈ alpha * p + beta
                def station_loss(params: np.ndarray, y_target: np.ndarray = y_s, p_pred: np.ndarray = p_s) -> float:
                    a, b = params
                    return float(root_mean_squared_error(y_target, a * p_pred + b))

                p0 = np.array([1.0, 0.0])
                st_bounds = [self.shrinkage_bounds, (-10.0, 10.0)]
                st_res = minimize(
                    station_loss,
                    p0,
                    method="L-BFGS-B",
                    bounds=st_bounds,
                )
                self.station_alphas_[int(sid)] = float(st_res.x[0])
                self.station_shifts_[int(sid)] = float(st_res.x[1])

        return self

    def predict(
        self,
        predictions_matrix: np.ndarray,
        station_ids: np.ndarray | None = None,
    ) -> np.ndarray:
        """Generate final calibrated ensemble predictions."""
        if self.weights_ is None:
            raise ValueError("Ensemble has not been fitted.")

        P = np.asarray(predictions_matrix, dtype=float)
        pred = P @ self.weights_

        if self.apply_station_shrinkage and station_ids is not None:
            s_ids = np.asarray(station_ids, dtype=int)
            calibrated = np.copy(pred)
            for sid, alpha in self.station_alphas_.items():
                mask = s_ids == sid
                shift = self.station_shifts_.get(sid, 0.0)
                calibrated[mask] = alpha * pred[mask] + shift
            return np.maximum(0.0, calibrated)

        return np.maximum(0.0, pred)
