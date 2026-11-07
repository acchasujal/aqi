"""Chronological fixed-origin rolling validation framework.

This module implements a rigorous, leakage-free validation protocol for Mumbai PM2.5 forecasting:
- Target windows are fixed 48-hour blocks that do NOT shift when reporting gaps vary.
- All 48 hourly predictions in a fold use only information available at the declared PM cutoff.
- Explicit clocks are tracked: prediction_origin, pm_history_cutoff, target_start, target_end.
- For supervised models, training examples are generated from historical forecast origins,
  with labels strictly prior to the outer validation cutoff and purging of any overlapping target blocks.
- Comprehensive metric reporting: pooled RMSE (primary), clean-range RMSE (<500), MAE, bias,
  fold variability (median, std), per-station RMSE, per-horizon-bucket RMSE, and high-pollution error.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

MODELS = (
    "last", "mean72", "median72", "ewm72", "diurnal7", "hour_week4",
    "mean72_clip300", "mean72_exclude_gt1000", "year_ago"
)


@dataclass(frozen=True)
class ValidationFold:
    """Fixed-origin validation fold definition."""
    fold_id: str
    target_start: pd.Timestamp
    target_end: pd.Timestamp
    prediction_origin: pd.Timestamp
    pm_history_cutoff: pd.Timestamp
    gap_hours: int
    horizon_hours: int


def generate_fixed_target_folds(
    train: pd.DataFrame,
    *,
    gap_hours: int = 48,
    horizon_hours: int = 48,
    step_days: int = 14,
    holdout_hours: int = 48,
    min_history_days: int = 21,
) -> list[ValidationFold]:
    """Generate fixed 48-hour target windows that remain identical across reporting gaps.

    Parameters
    ----------
    train:
        Challenge train DataFrame with tz-aware target_start.
    gap_hours:
        Reporting gap from last eligible PM hour to target start (48, 72, 96, 120).
    horizon_hours:
        Forecast horizon (default 48h).
    step_days:
        Spacing between consecutive target windows (default 14 days).
    holdout_hours:
        Number of final hours reserved as untouched chronological holdout (default 48h).
    min_history_days:
        Minimum historical days required before the first fold cutoff.

    Returns
    -------
    List of ValidationFold instances.
    """
    full_start = train.target_start.min()
    full_end = train.target_start.max()

    holdout_start = full_end - pd.Timedelta(hours=holdout_hours)
    # Target starts must allow min_history_days + max expected gap (120h)
    earliest_target = full_start + pd.Timedelta(days=min_history_days) + pd.Timedelta(hours=120)
    latest_target = holdout_start - pd.Timedelta(hours=horizon_hours)

    if earliest_target >= latest_target:
        raise ValueError("Insufficient timeline length to generate fixed target folds")

    # Generate fixed target starts backwards from latest_target to anchor on recent regimes
    target_starts: list[pd.Timestamp] = []
    curr = latest_target
    while curr >= earliest_target:
        target_starts.append(curr)
        curr = curr - pd.Timedelta(days=step_days)

    target_starts.reverse()
    folds: list[ValidationFold] = []
    for i, t_start in enumerate(target_starts):
        t_end = t_start + pd.Timedelta(hours=horizon_hours)
        cutoff = t_start - pd.Timedelta(hours=gap_hours)
        fold_id = f"fold_{i:02d}_{t_start.strftime('%Y%m%d')}"
        folds.append(ValidationFold(
            fold_id=fold_id,
            target_start=t_start,
            target_end=t_end,
            prediction_origin=t_start,
            pm_history_cutoff=cutoff,
            gap_hours=gap_hours,
            horizon_hours=horizon_hours,
        ))
    return folds


def _baseline(history: pd.Series, target: pd.DatetimeIndex, model: str) -> np.ndarray:
    history = history.sort_index()
    if history.empty or not history.notna().any():
        return np.full(len(target), np.nan)
    if model == "last":
        return np.full(len(target), float(history.dropna().iloc[-1]))
    cutoff = history.index.max()
    if model == "year_ago":
        references = pd.DatetimeIndex([target_time - pd.DateOffset(years=1) for target_time in target])
        previous = history.reindex(references).to_numpy(dtype=float)
        fallback = _baseline(history, target, "median72")
        return np.where(np.isfinite(previous), previous, fallback)
    if model in {"mean72", "median72", "ewm72", "mean72_clip300", "mean72_exclude_gt1000"}:
        window = history.loc[history.index >= cutoff - pd.Timedelta(hours=72)]
        if not window.notna().any():
            return np.full(len(target), float(history.dropna().iloc[-1]))
        if model == "mean72":
            value = window.mean()
        elif model == "median72":
            value = window.median()
        elif model == "mean72_clip300":
            value = window.clip(upper=300).mean()
        elif model == "mean72_exclude_gt1000":
            value = window.where(window <= 1000).mean()
        else:
            usable = window.dropna()
            age_hours = (cutoff - usable.index).total_seconds() / 3600
            weights = np.exp2(-age_hours / 24)
            value = np.average(usable.to_numpy(dtype=float), weights=weights)
        return np.full(len(target), float(value))
    if model == "diurnal7":
        window = history.loc[history.index >= cutoff - pd.Timedelta(hours=168)]
        profile = window.groupby(window.index.hour).mean()
        fallback = float(window.mean()) if window.notna().any() else float(history.dropna().iloc[-1])
        values = np.asarray([profile.get(t.hour, fallback) for t in target], dtype=float)
        return np.where(np.isfinite(values), values, fallback)
    elif model == "hour_week4":
        window = history.loc[history.index >= cutoff - pd.Timedelta(hours=672)]
        profile = window.groupby([window.index.day_of_week, window.index.hour]).mean()
        fallback = float(window.mean()) if window.notna().any() else float(history.dropna().iloc[-1])
        values = np.asarray([profile.get((t.day_of_week, t.hour), fallback) for t in target], dtype=float)
        return np.where(np.isfinite(values), values, fallback)
    else:
        raise ValueError(f"Unknown baseline model: {model}")


def rolling_oof(
    train: pd.DataFrame,
    *,
    gap_hours: int,
    horizon_hours: int = 48,
    step_days: int = 7,
    fixed_targets: bool = False,
) -> pd.DataFrame:
    """Score baseline models on aligned chronological windows.

    When fixed_targets=True, target windows remain completely identical regardless of gap_hours.
    """
    if gap_hours < 0 or horizon_hours < 1 or step_days * 24 < horizon_hours:
        raise ValueError("Require nonnegative gap and non-overlapping positive target windows")
    rows: list[tuple] = []
    stations = sorted(int(v) for v in train.location_id.unique())
    full_start, full_end = train.target_start.min(), train.target_start.max()
    hours = pd.date_range(full_start, full_end, freq="h")
    grid = train.set_index(["location_id", "target_start"])[["pm25"]].unstack(0).reindex(hours)

    if fixed_targets:
        # Fixed target window mode: target start is fixed; cutoff shifts backwards with gap
        first_target = full_start.ceil("D") + pd.Timedelta(hours=120 + 24)
        last_target = full_end - pd.Timedelta(hours=horizon_hours)
        target_dates = pd.date_range(first_target, last_target, freq=f"{step_days}D")
        loop_items = [(t - pd.Timedelta(hours=gap_hours), t) for t in target_dates]
    else:
        # Legacy cutoff-anchored mode
        first_origin = full_start.ceil("D") + pd.Timedelta(hours=23)
        last_origin = full_end - pd.Timedelta(hours=gap_hours + horizon_hours)
        cutoffs = pd.date_range(first_origin, last_origin, freq=f"{step_days}D")
        loop_items = [(c, c + pd.Timedelta(hours=gap_hours)) for c in cutoffs]

    for cutoff, target_start in loop_items:
        targets = pd.date_range(target_start, periods=horizon_hours, freq="h")
        issue_time = target_start
        fold_id = target_start if fixed_targets else cutoff
        for station in stations:
            s = grid[("pm25", station)]
            history = s.loc[s.index < cutoff]
            last_observed_start = history.last_valid_index()
            if last_observed_start is None:
                continue
            last_observed_end = last_observed_start + pd.Timedelta(hours=1)
            truth = s.reindex(targets)
            for model in MODELS:
                pred = _baseline(history, targets, model)
                for horizon, (t, y, p) in enumerate(zip(targets, truth.to_numpy(), pred), start=1):
                    if np.isfinite(y) and np.isfinite(p):
                        exact_gap = (t - last_observed_end).total_seconds() / 3600
                        rows.append((
                            fold_id, issue_time, cutoff, last_observed_end, exact_gap, t,
                            t + pd.Timedelta(hours=1), station, horizon, float(y),
                            max(0.0, float(p)), model
                        ))
    return pd.DataFrame(rows, columns=[
        "fold_id", "prediction_origin", "pm_history_cutoff", "last_pm_available_at",
        "pm_gap_hours", "target_start", "target_end", "location_id",
        "horizon_hours", "y", "prediction", "model"
    ])


def metric_tables(oof: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return model, station, and horizon metrics; full-target RMSE is primary."""
    if oof.empty:
        raise ValueError("No eligible OOF rows")
    scored = oof.assign(error=oof.prediction - oof.y, squared=(oof.prediction - oof.y) ** 2)

    def summarize(keys: list[str]) -> pd.DataFrame:
        result = scored.groupby(keys, dropna=False).agg(
            rows=("y", "size"),
            full_target_rmse=("squared", lambda x: float(np.sqrt(x.mean()))),
            mae=("error", lambda x: float(x.abs().mean())),
            bias=("error", "mean"),
            clean_rows=("y", lambda x: int((x < 500).sum())),
        ).reset_index()
        clean = scored.loc[scored.y < 500].groupby(keys).squared.mean().pow(0.5).rename("clean_rmse")
        extreme = scored.groupby(keys).apply(
            lambda part: float(part.loc[part.y > 1000, "squared"].sum() / part.squared.sum()) if part.squared.sum() else 0.0,
            include_groups=False,
        ).rename("extreme_squared_error_share")
        extreme_rows = scored.groupby(keys).y.apply(lambda y: int((y > 1000).sum())).rename("extreme_rows")
        return result.merge(clean.reset_index(), on=keys, how="left").merge(extreme.reset_index(), on=keys).merge(extreme_rows.reset_index(), on=keys)

    by_model = summarize(["model"])
    by_station = summarize(["model", "location_id"])
    by_horizon = summarize(["model", "horizon_hours"])
    fold_rmse = scored.groupby(["model", "fold_id"]).squared.mean().pow(0.5).rename("fold_rmse")
    folds = fold_rmse.groupby("model").agg(fold_count="count", fold_rmse_median="median", fold_rmse_sd="std")
    by_fold = summarize(["model", "fold_id"])
    return by_model.merge(folds, on="model", how="left"), by_station, by_horizon, by_fold


def evaluate_predictions(oof: pd.DataFrame) -> dict[str, Any]:
    """Calculate comprehensive competition metrics for a predictions dataframe.

    Returns dict containing:
        pooled_rmse: full-target RMSE (official primary metric)
        clean_rmse: diagnostic RMSE on y < 500
        mae: Mean Absolute Error
        bias: Mean prediction error (pred - y)
        fold_count: number of evaluated validation folds
        fold_rmse_mean: mean per-fold RMSE
        fold_rmse_median: median per-fold RMSE
        fold_rmse_std: standard deviation across fold RMSEs
        by_station: dict mapping location_id -> station RMSE
        by_horizon: dict mapping horizon bucket -> horizon RMSE
        high_pollution_rmse: RMSE on observations with y >= 100
        extreme_pollution_rmse: RMSE on observations with y >= 300
    """
    if oof.empty:
        raise ValueError("Empty OOF dataframe provided for evaluation")

    df = oof.copy()
    df["error"] = df["prediction"] - df["y"]
    df["squared_error"] = df["error"] ** 2

    pooled_rmse = float(np.sqrt(df["squared_error"].mean()))
    clean_sub = df.loc[df["y"] < 500]
    clean_rmse = float(np.sqrt(clean_sub["squared_error"].mean())) if not clean_sub.empty else np.nan
    mae = float(df["error"].abs().mean())
    bias = float(df["error"].mean())

    # Per-fold metrics
    fold_rmses = df.groupby("fold_id")["squared_error"].mean().pow(0.5)
    fold_count = len(fold_rmses)
    fold_rmse_mean = float(fold_rmses.mean())
    fold_rmse_median = float(fold_rmses.median())
    fold_rmse_std = float(fold_rmses.std()) if len(fold_rmses) > 1 else 0.0

    # Per-station metrics
    by_station = (
        df.groupby("location_id")["squared_error"]
        .mean()
        .pow(0.5)
        .round(4)
        .to_dict()
    )

    # Per-horizon buckets: 1-12, 13-24, 25-36, 37-48
    def horizon_bucket(h: int) -> str:
        if h <= 12:
            return "h01_12"
        elif h <= 24:
            return "h13_24"
        elif h <= 36:
            return "h25_36"
        return "h37_48"

    df["h_bucket"] = df["horizon_hours"].apply(horizon_bucket)
    by_horizon = (
        df.groupby("h_bucket")["squared_error"]
        .mean()
        .pow(0.5)
        .round(4)
        .to_dict()
    )

    # High-pollution error analysis
    ge_100 = df.loc[df["y"] >= 100]
    ge_300 = df.loc[df["y"] >= 300]
    high_rmse = float(np.sqrt(ge_100["squared_error"].mean())) if not ge_100.empty else np.nan
    extreme_rmse = float(np.sqrt(ge_300["squared_error"].mean())) if not ge_300.empty else np.nan

    return {
        "rows": len(df),
        "pooled_rmse": round(pooled_rmse, 4),
        "clean_rmse": round(clean_rmse, 4) if np.isfinite(clean_rmse) else None,
        "mae": round(mae, 4),
        "bias": round(bias, 4),
        "fold_count": fold_count,
        "fold_rmse_mean": round(fold_rmse_mean, 4),
        "fold_rmse_median": round(fold_rmse_median, 4),
        "fold_rmse_std": round(fold_rmse_std, 4),
        "by_station": by_station,
        "by_horizon": by_horizon,
        "high_pollution_rmse": round(high_rmse, 4) if np.isfinite(high_rmse) else None,
        "extreme_pollution_rmse": round(extreme_rmse, 4) if np.isfinite(extreme_rmse) else None,
    }
