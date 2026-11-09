"""Experimental station calibration of genuine past-only OOF forecasts.

Not used by production inference. Identity priors constrain corrections when
station evidence is sparse. Huber is an explicit loss ablation, not label cleaning.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize

METHODS = ("cal_offset", "cal_affine", "cal_huber")
PRIOR_ROWS = 500.0
PREDICTOR_SCALE = 50.0
HUBER_DELTA = 20.0
MIN_ORIGINS = 4
CLOCKS = ("fold_id", "prediction_origin", "pm_history_cutoff", "target_start",
          "target_end", "block_target_end")


def validate_oof(rows: pd.DataFrame) -> None:
    """Fail on malformed, overlapping, nonfinite or causally invalid OOF rows."""
    required = set(CLOCKS) | {"location_id", "P_fix", "y", "split"}
    if not required.issubset(rows):
        raise ValueError(f"Missing OOF columns: {sorted(required - set(rows))}")
    for name in CLOCKS:
        if rows[name].isna().any() or not isinstance(rows[name].dtype, pd.DatetimeTZDtype):
            raise ValueError(f"OOF {name} must be present and timezone-aware")
    if rows.duplicated(["location_id", "target_start"]).any():
        raise ValueError("OOF station-hour keys must be unique")
    if not np.isfinite(rows[["P_fix", "y"]].to_numpy(dtype=float)).all():
        raise ValueError("OOF forecasts and labels must be finite")
    if (rows[["P_fix", "y"]] < 0).any().any():
        raise ValueError("OOF forecasts and labels must be nonnegative")
    if not (rows.pm_history_cutoff.le(rows.prediction_origin)
            & rows.prediction_origin.lt(rows.target_start)
            & rows.target_end.eq(rows.target_start + pd.Timedelta(hours=1))
            & rows.target_start.ge(rows.fold_id)
            & rows.block_target_end.eq(rows.fold_id + pd.Timedelta(hours=48))
            & rows.target_end.le(rows.block_target_end)).all():
        raise ValueError("Invalid OOF information clocks or target intervals")
    constants = ["prediction_origin", "pm_history_cutoff", "block_target_end", "split"]
    if rows.groupby("fold_id")[constants].nunique().gt(1).any().any():
        raise ValueError("Each OOF fold must freeze one set of clocks and split")
    starts = rows.fold_id.drop_duplicates().sort_values()
    if starts.diff().dropna().lt(pd.Timedelta(hours=48)).any():
        raise ValueError("OOF blocks must not overlap")


def _coefficients(training: pd.DataFrame, method: str) -> np.ndarray:
    """Fit a correction a + c * (forecast / 50), shrinking a,c toward zero."""
    residual = (training.y - training.P_fix).to_numpy(dtype=float)
    if method == "cal_offset":
        return np.array([residual.sum() / (len(residual) + PRIOR_ROWS), 0.0])
    design = np.column_stack([np.ones(len(training)), training.P_fix / PREDICTOR_SCALE])
    if method == "cal_affine":
        return np.linalg.solve(design.T @ design + PRIOR_ROWS * np.eye(2),
                               design.T @ residual)

    def objective(beta: np.ndarray) -> tuple[float, np.ndarray]:
        error = design @ beta - residual
        absolute = np.abs(error)
        loss = np.where(absolute <= HUBER_DELTA, .5 * error**2,
                        HUBER_DELTA * (absolute - .5 * HUBER_DELTA))
        gradient = design.T @ np.clip(error, -HUBER_DELTA, HUBER_DELTA) + PRIOR_ROWS * beta
        return float(loss.sum() + .5 * PRIOR_ROWS * (beta @ beta)), gradient

    fitted = minimize(objective, np.zeros(2), jac=True, method="L-BFGS-B")
    if not fitted.success or not np.isfinite(fitted.x).all():
        raise RuntimeError(f"Huber calibration failed: {fitted.message}")
    return fitted.x


def rolling_calibration(rows: pd.DataFrame, method: str) -> tuple[pd.Series, pd.DataFrame]:
    """Refit only on whole prior OOF blocks available at each PM-history cutoff.

    Returns predictions in input order plus explicit station/fold fitting lineage.
    Unseen or under-supported stations retain their original forecast.
    """
    if method not in METHODS:
        raise ValueError(f"Unknown calibration method: {method}")
    validate_oof(rows)
    if not rows.index.is_unique:
        raise ValueError("OOF row index must be unique")
    prediction = rows.P_fix.astype(float).copy()
    lineage = []
    for fold, validation in rows.groupby("fold_id", sort=True):
        cutoff = validation.pm_history_cutoff.iloc[0]
        eligible = rows.loc[rows.block_target_end.le(cutoff)]
        for station, part in validation.groupby("location_id", sort=True):
            training = eligible.loc[eligible.location_id.eq(station)]
            supported = training.fold_id.nunique() >= MIN_ORIGINS
            beta = _coefficients(training, method) if supported else np.zeros(2)
            value = part.P_fix.to_numpy() + beta[0] + beta[1] * part.P_fix.to_numpy() / PREDICTOR_SCALE
            if not np.isfinite(value).all():
                raise ValueError("Calibration produced nonfinite predictions")
            prediction.loc[part.index] = np.maximum(0, value)
            lineage.append({"model": method, "fold_id": fold, "location_id": station,
                            "fitting_cutoff": cutoff, "training_rows": len(training),
                            "training_origins": training.fold_id.nunique(),
                            "training_end_max": training.block_target_end.max(),
                            "identity_fallback": not supported, "intercept": beta[0],
                            "slope": 1 + beta[1] / PREDICTOR_SCALE})
    return prediction, pd.DataFrame(lineage)
