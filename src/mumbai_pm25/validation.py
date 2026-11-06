"""Chronological rolling-origin comparisons using non-overlapping 48-hour targets."""
from __future__ import annotations

import numpy as np
import pandas as pd

MODELS = ("last", "mean72", "median72", "ewm72", "diurnal7", "hour_week4",
          "mean72_clip300", "mean72_exclude_gt1000", "year_ago")


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
    return np.asarray([profile.get(t.hour, np.nan) for t in target], dtype=float)


def rolling_oof(train: pd.DataFrame, *, gap_hours: int, horizon_hours: int = 48,
                step_days: int = 7) -> pd.DataFrame:
    """Score baseline models on aligned, separated chronological windows."""
    if gap_hours < 0 or horizon_hours < 1 or step_days * 24 < horizon_hours:
        raise ValueError("Require nonnegative gap and non-overlapping positive target windows")
    rows: list[tuple] = []
    stations = sorted(int(v) for v in train.location_id.unique())
    full_start, full_end = train.target_start.min(), train.target_start.max()
    hours = pd.date_range(full_start, full_end, freq="h")
    grid = train.set_index(["location_id", "target_start"])[["pm25"]].unstack(0).reindex(hours)
    first_origin = full_start.ceil("D") + pd.Timedelta(hours=23)
    last_origin = full_end - pd.Timedelta(hours=gap_hours + horizon_hours)
    for cutoff in pd.date_range(first_origin, last_origin, freq=f"{step_days}D"):
        target_start = cutoff + pd.Timedelta(hours=gap_hours)
        targets = pd.date_range(target_start, periods=horizon_hours, freq="h")
        issue_time = target_start
        for station in stations:
            s = grid[("pm25", station)]
            # Labels become available at interval end, so a 23:00 cutoff
            # includes a target_start of 22:00 but excludes target_start 23:00.
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
                        rows.append((cutoff, issue_time, cutoff, last_observed_end, exact_gap, t,
                                     t + pd.Timedelta(hours=1), station, horizon, float(y), max(0.0, float(p)), model))
    return pd.DataFrame(rows, columns=["fold_id", "prediction_origin", "pm_history_cutoff", "last_pm_available_at",
                                      "pm_gap_hours", "target_start", "target_end", "location_id",
                                      "horizon_hours", "y", "prediction", "model"])


def metric_tables(oof: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return model, station, and horizon metrics; full-target RMSE is primary."""
    if oof.empty:
        raise ValueError("No eligible OOF rows")
    scored = oof.assign(error=oof.prediction - oof.y, squared=(oof.prediction - oof.y) ** 2)
    def summarize(keys: list[str]) -> pd.DataFrame:
        result = scored.groupby(keys, dropna=False).agg(
            rows=("y", "size"), full_target_rmse=("squared", lambda x: float(np.sqrt(x.mean()))),
            mae=("error", lambda x: float(x.abs().mean())), bias=("error", "mean"),
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
