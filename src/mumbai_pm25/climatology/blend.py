"""Simplex grid search and temporally separated weight fitting for Climatology Blend."""
from __future__ import annotations

import itertools

import numpy as np
from sklearn.metrics import root_mean_squared_error


class ClimatologyBlend:
    """Estimates optimal non-negative ensemble weights over {clim, ridge, lgbm}."""

    def __init__(self, step: float = 0.1) -> None:
        self.step = step
        self.weights_: dict[str, float] = {"clim": 1.0, "ridge": 0.0, "lgbm": 0.0}

    def _generate_simplex_grid(self) -> list[tuple[float, float, float]]:
        grid = []
        n_steps = round(1.0 / self.step)
        for i, j in itertools.product(range(n_steps + 1), repeat=2):
            k = n_steps - i - j
            if k >= 0:
                grid.append((i * self.step, j * self.step, k * self.step))
        return grid

    def fit(
        self,
        y_true: np.ndarray,
        p_clim: np.ndarray,
        p_ridge: np.ndarray | None = None,
        p_lgbm: np.ndarray | None = None,
    ) -> ClimatologyBlend:
        """Find non-negative weights summing to 1 minimizing RMSE."""
        y_t = np.asarray(y_true, dtype=float)
        c = np.asarray(p_clim, dtype=float)
        r = np.asarray(p_ridge, dtype=float) if p_ridge is not None else c
        l = np.asarray(p_lgbm, dtype=float) if p_lgbm is not None else c

        grid = self._generate_simplex_grid()
        best_rmse = float("inf")
        best_w = (1.0, 0.0, 0.0)

        for w_c, w_r, w_l in grid:
            pred = w_c * c + w_r * r + w_l * l
            rmse = root_mean_squared_error(y_t, pred)
            if rmse < best_rmse:
                best_rmse = rmse
                best_w = (w_c, w_r, w_l)

        self.weights_ = {"clim": best_w[0], "ridge": best_w[1], "lgbm": best_w[2]}
        return self

    def predict(
        self,
        p_clim: np.ndarray,
        p_ridge: np.ndarray | None = None,
        p_lgbm: np.ndarray | None = None,
    ) -> np.ndarray:
        """Apply fitted weights to component predictions."""
        c = np.asarray(p_clim, dtype=float)
        r = np.asarray(p_ridge, dtype=float) if p_ridge is not None else c
        l = np.asarray(p_lgbm, dtype=float) if p_lgbm is not None else c

        w_c = self.weights_.get("clim", 1.0)
        w_r = self.weights_.get("ridge", 0.0)
        w_l = self.weights_.get("lgbm", 0.0)

        return np.maximum(0.0, w_c * c + w_r * r + w_l * l)
