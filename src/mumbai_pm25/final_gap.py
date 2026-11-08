"""TASK008 fixed-origin feature construction and matched 48-hour evaluation.

PM labels are assumed available at interval end, an explicit proxy rather than
verified first-publication time. Every block freezes history at one cutoff.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from mumbai_pm25.data import complete_hourly_grid
from mumbai_pm25.forecast import predict_station_baseline
from mumbai_pm25.historical_archive import build_seasonal_features

SEED = 20261108
STATIONS = (11606, 11611, 3409510, 3409511)
FEATURES = (
    "median24", "median72", "median168", "mean24", "mean72", "std72", "last_pm",
    "age_hours", "missing72", "lag1", "lag2", "lag3", "lag6", "lag24", "ewm72",
    "profile7", "normal28", "normal_now", "archive_target", "archive_now",
    "hour_sin", "hour_cos", "week_sin", "week_cos", "year_sin", "year_cos",
    "forecast_lead_hours", "target_day", "station_11606", "station_11611",
    "station_3409510", "station_3409511",
)
BASE_MODELS = (
    "median24", "median72", "median168", "ewm72", "diur7", "diurnal7_raw",
    "hour_week4", "recent_shrink72", "recent_shrink168", "P_fix",
    "archive_decay72", "archive_decay168", "archive_piecewise", "archive_constant50",
    "current_decay168", "current_constant50",
)


@dataclass(frozen=True)
class ForecastBlock:
    target_start: pd.Timestamp
    pm_cutoff: pd.Timestamp
    issue_time: pd.Timestamp
    split: str = "development"
    hours: int = 48

    def __post_init__(self) -> None:
        clocks = (self.target_start, self.pm_cutoff, self.issue_time)
        if any(t.tzinfo is None or t != t.floor("h") for t in clocks):
            raise ValueError("Block clocks must be timezone-aware and aligned to an hour")
        if not self.pm_cutoff <= self.issue_time < self.target_start or self.hours != 48:
            raise ValueError("Require cutoff <= issue < target and a complete 48h block")

    @property
    def target_end(self) -> pd.Timestamp:
        return self.target_start + pd.Timedelta(hours=self.hours)


def make_blocks(train: pd.DataFrame, gap_hours: int) -> list[ForecastBlock]:
    """Predeclare weekly non-overlapping targets, then later confirmation targets.

    The schedule is independent of label magnitudes. Historical confirmation
    has been broadly inspected in earlier tasks and is not an untouched holdout.
    """
    if gap_hours < 1:
        raise ValueError("gap_hours must be positive")
    first = train.target_start.min().ceil("D") + pd.Timedelta(days=35, hours=gap_hours)
    first = first.ceil("D")
    end = train.target_start.max() + pd.Timedelta(hours=1)
    blocks = []
    for target in pd.date_range(first, end - pd.Timedelta(hours=48), freq="7D"):
        cutoff = target - pd.Timedelta(hours=gap_hours)
        split = "development" if target < pd.Timestamp("2026-09-01", tz="Asia/Kolkata") else "confirmation"
        blocks.append(ForecastBlock(target, cutoff, cutoff, split))
    return blocks


def eligible_training_rows(rows: pd.DataFrame, cutoff: pd.Timestamp) -> pd.DataFrame:
    """Require the ENTIRE training target block to end by fitting cutoff."""
    return rows.loc[rows.block_target_end.le(cutoff) & rows.y.notna() & rows.median72.notna()]


def block_features(train: pd.DataFrame, archive: pd.DataFrame, block: ForecastBlock,
                   station_ids: tuple[int, ...] = STATIONS) -> pd.DataFrame:
    """Build predictors without reading any target values or future PM values."""
    required = {"location_id", "target_start", "pm25"}
    if not required.issubset(train) or train.target_start.dt.tz is None:
        raise ValueError("Need aligned timezone-aware station-hour training data")
    if train.duplicated(["location_id", "target_start"]).any():
        raise ValueError("Duplicate PM station-hour keys")
    # Discard future rows BEFORE building the hourly grid, including its bounds.
    past = train.loc[train.target_start + pd.Timedelta(hours=1) <= block.pm_cutoff]
    targets = pd.date_range(block.target_start, periods=block.hours, freq="h")
    target_grid = pd.MultiIndex.from_product([station_ids, targets], names=["location_id", "target_start"])
    result = target_grid.to_frame(index=False)
    result["prediction_origin"] = block.issue_time
    result["pm_history_cutoff"] = block.pm_cutoff
    result["fold_id"] = block.target_start
    result["split"] = block.split
    result["target_end"] = result.target_start + pd.Timedelta(hours=1)
    result["block_target_end"] = block.target_end
    result["target_day"] = ((result.target_start - block.target_start).dt.total_seconds()/86400).astype(int) + 1
    result["forecast_lead_hours"] = (result.target_start - block.issue_time).dt.total_seconds()/3600
    if past.empty:
        grid = pd.DataFrame(columns=["pm25"])
    else:
        grid = complete_hourly_grid(past)
    for station, part in result.groupby("location_id", sort=False):
        idx = part.index
        if past.empty or station not in past.location_id.unique():
            continue
        series = grid.xs(station, level="location_id").pm25
        # Explicitly extend the grid through the cutoff for exact-hour lags.
        series = series.reindex(pd.date_range(series.index.min(), block.pm_cutoff - pd.Timedelta(hours=1), freq="h"))
        observed = series.dropna()
        if observed.empty:
            continue
        last_end = observed.index[-1] + pd.Timedelta(hours=1)
        result.loc[idx, "last_pm_end"] = last_end
        result.loc[idx, "last_pm"] = float(observed.iloc[-1])
        result.loc[idx, "age_hours"] = (block.pm_cutoff - last_end).total_seconds()/3600
        for lag in (1, 2, 3, 6, 24):
            result.loc[idx, f"lag{lag}"] = series.get(block.pm_cutoff - pd.Timedelta(hours=lag), np.nan)
        for hours in (24, 72, 168):
            recent = series.loc[series.index >= block.pm_cutoff - pd.Timedelta(hours=hours)].dropna()
            result.loc[idx, f"median{hours}"] = float(recent.median()) if len(recent) else float(observed.median())
            if hours in (24, 72):
                result.loc[idx, f"mean{hours}"] = float(recent.mean()) if len(recent) else float(observed.median())
            if hours == 72:
                result.loc[idx, "std72"] = float(recent.std()) if len(recent) > 1 else np.nan
                result.loc[idx, "missing72"] = 1 - len(recent)/72
                weights = np.exp2(-(block.pm_cutoff - recent.index).total_seconds()/3600/24)
                result.loc[idx, "ewm72"] = float(np.average(recent, weights=weights)) if len(recent) else float(observed.median())
        result.loc[idx, "median72"] = predict_station_baseline(series, targets, pm_history_cutoff=block.pm_cutoff, model="median72")
        result.loc[idx, "diur7"] = predict_station_baseline(series, targets, pm_history_cutoff=block.pm_cutoff, model="diur7")
        week = series.loc[series.index >= block.pm_cutoff - pd.Timedelta(hours=168)]
        profile = week.groupby(week.index.hour).mean()
        result.loc[idx, "profile7"] = [profile.get(t.hour, np.nan) for t in targets]
        result.loc[idx, "profile_now"] = float(profile.mean())
        month = series.loc[series.index >= block.pm_cutoff - pd.Timedelta(hours=672)]
        normal = month.groupby(month.index.hour).mean()
        result.loc[idx, "normal28"] = [normal.get(t.hour, np.nan) for t in targets]
        result.loc[idx, "normal_now"] = float(normal.mean())
        weekly = month.groupby([month.index.day_of_week, month.index.hour]).agg(["mean", "count"])
        result.loc[idx, "hour_week4"] = [
            weekly.loc[(t.day_of_week, t.hour), "mean"]
            if (t.day_of_week, t.hour) in weekly.index and weekly.loc[(t.day_of_week, t.hour), "count"] >= 3 else np.nan
            for t in targets]
    for col in ("median24", "median72", "median168", "diur7", "ewm72", "profile7", "profile_now", "normal28", "normal_now", "hour_week4", "last_pm_end"):
        if col not in result:
            result[col] = np.nan if col != "last_pm_end" else pd.NaT
    result["actual_pm_lead_hours"] = (result.target_start - pd.to_datetime(result.last_pm_end, utc=True).dt.tz_convert("Asia/Kolkata")).dt.total_seconds()/3600
    seasonal = build_seasonal_features(archive, result)
    result["archive_target"] = seasonal.hist24_same_hour_mean.to_numpy()
    result["archive_coverage"] = seasonal.hist24_coverage.to_numpy()
    reference = pd.MultiIndex.from_product([station_ids, pd.date_range(block.pm_cutoff - pd.Timedelta(hours=72), periods=72, freq="h")], names=["location_id", "target_start"]).to_frame(index=False)
    reference["archive"] = build_seasonal_features(archive, reference).hist24_same_hour_mean.to_numpy()
    result["archive_now"] = result.location_id.map(reference.groupby("location_id").archive.mean())
    for name, values, period in (("hour", result.target_start.dt.hour, 24), ("week", result.target_start.dt.day_of_week, 7), ("year", result.target_start.dt.day_of_year, 365.25)):
        result[f"{name}_sin"] = np.sin(2*np.pi*values/period)
        result[f"{name}_cos"] = np.cos(2*np.pi*values/period)
    for station in STATIONS:
        result[f"station_{station}"] = result.location_id.eq(station).astype(float)
    return result


def baseline_predictions(rows: pd.DataFrame) -> pd.DataFrame:
    """Small predeclared grid; all fallback rules also apply at inference."""
    out = rows.copy()
    level = out.median72
    out["diurnal7_raw"] = out.profile7.fillna(level)
    out["hour_week4"] = out.hour_week4.fillna(out.diurnal7_raw)
    for half in (72, 168):
        alpha = np.exp2(-out.forecast_lead_hours/half)
        out[f"recent_shrink{half}"] = level + alpha*(out.profile7 - out.profile_now).fillna(0)
    out["P_fix"] = .5*level + .5*out.archive_target.fillna(level)
    alphas = {"decay72": np.exp2(-out.forecast_lead_hours/72),
              "decay168": np.exp2(-out.forecast_lead_hours/168),
              "piecewise": np.where(out.forecast_lead_hours <= 72, .75,
                                    np.where(out.forecast_lead_hours <= 168, .5, .25)),
              "constant50": .5}
    for name, alpha in alphas.items():
        anomaly = level - out.archive_now
        out[f"archive_{name}"] = (out.archive_target + alpha*anomaly).fillna(level)
    for name in ("decay168", "constant50"):
        out[f"current_{name}"] = (out.normal28 + alphas[name]*(level - out.normal_now)).fillna(level)
    out[list(BASE_MODELS)] = out[list(BASE_MODELS)].clip(lower=0)
    return out


def labelled_blocks(train: pd.DataFrame, archive: pd.DataFrame,
                    blocks: list[ForecastBlock]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Preserve missing targets in coverage; score every available labelled row."""
    parts, coverage = [], []
    for block in blocks:
        features = baseline_predictions(block_features(train, archive, block))
        labelled = features.merge(train[["location_id", "target_start", "pm25"]],
                                  on=["location_id", "target_start"], how="left", validate="one_to_one")
        labelled = labelled.rename(columns={"pm25": "y"})
        coverage.append({"fold_id": block.target_start, "split": block.split,
                         "expected_rows": len(features), "labelled_rows": int(labelled.y.notna().sum()),
                         "unsupported_history_rows": int((labelled.y.notna() & labelled.median72.isna()).sum())})
        parts.append(labelled)
    return pd.concat(parts, ignore_index=True), pd.DataFrame(coverage)


def score_predictions(rows: pd.DataFrame, models: list[str],
                      group_keys: tuple[str, ...] = ()) -> pd.DataFrame:
    """Missing forecasts cannot improve scores by shrinking eligible rows."""
    result = []
    eligible = rows.loc[rows.y.notna()]
    groups = eligible.groupby(list(group_keys), dropna=False) if group_keys else [((), eligible)]
    for key, part in groups:
        key = key if isinstance(key, tuple) else (key,)
        for model in models:
            pred = part[model].to_numpy(dtype=float)
            y = part.y.to_numpy(dtype=float)
            missing = ~np.isfinite(pred)
            valid = not missing.any()
            error = pred-y
            sq = error**2
            clean = y < 500
            result.append({**dict(zip(group_keys, key)), "model": model, "rows": len(y),
                           "origins": part.fold_id.nunique(), "missing_predictions": int(missing.sum()),
                           "coverage": float((~missing).mean()),
                           "full_target_rmse": float(np.sqrt(sq.mean())) if valid else np.nan,
                           "mae": float(np.abs(error).mean()) if valid else np.nan,
                           "bias": float(error.mean()) if valid else np.nan,
                           "clean_rmse": float(np.sqrt(sq[clean].mean())) if valid and clean.any() else np.nan,
                           "extreme_rows": int((y > 1000).sum()),
                           "extreme_squared_error_share": float(sq[y > 1000].sum()/sq.sum()) if valid and sq.sum() else np.nan})
    return pd.DataFrame(result)


def paired_bootstrap(rows: pd.DataFrame, model: str, comparator: str = "P_fix",
                     repetitions: int = 2000) -> dict[str, object]:
    """Moving blocks of four adjacent origins preserve short-range dependence."""
    frame = rows.loc[rows.y.notna()].copy()
    if not np.isfinite(frame[[model, comparator]].to_numpy(dtype=float)).all():
        return {"model": model, "status": "incomplete_predictions"}
    frame["candidate_sse"] = (frame[model]-frame.y)**2
    frame["baseline_sse"] = (frame[comparator]-frame.y)**2
    blocks = frame.groupby("fold_id", sort=True).agg(candidate=("candidate_sse", "sum"), baseline=("baseline_sse", "sum"), n=("y", "size"))
    values = blocks.to_numpy(dtype=float)
    rng = np.random.default_rng(SEED)
    n = len(values)
    if n == 0:
        raise ValueError("No paired origins")
    length = min(4, n)
    starts = rng.integers(0, n-length+1, size=(repetitions, int(np.ceil(n/length))))
    indices = (starts[..., None]+np.arange(length)).reshape(repetitions, -1)[:, :n]
    sums = values[indices].sum(axis=1)
    deltas = np.sqrt(sums[:, 0]/sums[:, 2])-np.sqrt(sums[:, 1]/sums[:, 2])
    totals = values.sum(axis=0)
    return {"model": model, "comparator": comparator, "origins": n, "block_origins": length,
            "rmse_delta": float(np.sqrt(totals[0]/totals[2])-np.sqrt(totals[1]/totals[2])),
            "lower95": float(np.quantile(deltas, .025)), "upper95": float(np.quantile(deltas, .975)),
            "origin_wins": int((values[:, 0] < values[:, 1]).sum()), "seed": SEED}
