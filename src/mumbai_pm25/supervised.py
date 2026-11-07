"""EXP-014 cutoff-safe supervised examples and bounded model candidates."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from mumbai_pm25.forecast import combine_forecasts
from mumbai_pm25.historical_archive import build_seasonal_features

IST = "Asia/Kolkata"
SEED = 42
FEATURE_COLUMNS = (
    "station_11606", "station_11611", "station_3409510", "station_3409511",
    "lead_hours", "actual_lead_hours", "hour_sin", "hour_cos", "doy_sin", "doy_cos",
    "weekday_sin", "weekday_cos", "issue_hour", "issue_month",
    "last_pm", "age_hours", "median6", "median12", "median24", "median48",
    "median72", "mean24", "mean72", "std72", "min24", "max24",
    "available24", "available72", "missing_fraction72", "trend24",
    "station_history_median", "station_history_iqr", "seasonal_pm", "w50",
)


@dataclass(frozen=True)
class Origin:
    target_start: pd.Timestamp
    pm_cutoff: pd.Timestamp
    issue_time: pd.Timestamp
    regime: str


def make_origin(target_start: pd.Timestamp, regime: str,
                *, private_issue_offset_hours: int = 109) -> Origin:
    """Create the current public/private information clocks for one target day."""
    if target_start.tz is None or target_start.hour != 0:
        raise ValueError("Target day must start at timezone-aware midnight")
    if regime not in {"public", "private"}:
        raise ValueError(f"Unknown regime: {regime}")
    gap = 1 if regime == "public" else 193
    cutoff = target_start - pd.Timedelta(hours=gap)
    issue = cutoff if regime == "public" else cutoff + pd.Timedelta(hours=private_issue_offset_hours)
    if issue >= target_start:
        raise ValueError("Forecast issue must precede first target")
    return Origin(target_start, cutoff, issue, regime)


def _stats(history: pd.Series, cutoff: pd.Timestamp) -> dict[str, float]:
    """Elapsed-hour statistics; missing grid hours stay absent, never zero."""
    eligible = history.loc[history.index < cutoff].dropna()
    if eligible.empty:
        return {}
    result: dict[str, float] = {
        "last_pm": float(eligible.iloc[-1]),
        "age_hours": float((cutoff - eligible.index[-1]).total_seconds() / 3600),
        "station_history_median": float(eligible.median()),
        "station_history_iqr": float(eligible.quantile(0.75) - eligible.quantile(0.25)),
    }
    windows = {}
    for hours in (6, 12, 24, 48, 72):
        window = eligible.loc[eligible.index >= cutoff - pd.Timedelta(hours=hours)]
        windows[hours] = window
        result[f"median{hours}"] = float(window.median()) if not window.empty else np.nan
    for hours in (24, 72):
        window = windows[hours]
        result[f"mean{hours}"] = float(window.mean()) if not window.empty else np.nan
    result["std72"] = float(windows[72].std()) if len(windows[72]) > 1 else np.nan
    result["min24"] = float(windows[24].min()) if not windows[24].empty else np.nan
    result["max24"] = float(windows[24].max()) if not windows[24].empty else np.nan
    result["available24"] = float(len(windows[24]))
    result["available72"] = float(len(windows[72]))
    result["missing_fraction72"] = 1.0 - len(windows[72]) / 72
    previous24 = eligible.loc[(eligible.index >= cutoff - pd.Timedelta(hours=48)) &
                              (eligible.index < cutoff - pd.Timedelta(hours=24))]
    result["trend24"] = (float(windows[24].median() - previous24.median())
                         if not windows[24].empty and not previous24.empty else np.nan)
    return result


def origin_features(train: pd.DataFrame, targets: pd.DataFrame, origin: Origin,
                    station_ids: tuple[int, ...]) -> pd.DataFrame:
    """Build predictors before any target label join, using only PM before cutoff."""
    if origin.pm_cutoff > origin.issue_time or origin.issue_time >= origin.target_start:
        raise ValueError("Invalid issue/cutoff/target clock ordering")
    if targets.target_start.dt.tz is None or not (targets.target_start >= origin.target_start).all():
        raise ValueError("Targets must be timezone-aware and after first target")
    if not targets.location_id.isin(station_ids).all():
        raise ValueError("Unknown target station")
    if train.duplicated(["location_id", "target_start"]).any():
        raise ValueError("Duplicate station-hour PM history")
    eligible = train.loc[train.target_start + pd.Timedelta(hours=1) <= origin.pm_cutoff]
    rows = []
    for station, target_group in targets.groupby("location_id", sort=True):
        series = eligible.loc[eligible.location_id.eq(station)].set_index("target_start").pm25.sort_index()
        stats = _stats(series, origin.pm_cutoff)
        if not stats:
            continue
        part = target_group[["location_id", "target_start"]].copy()
        for key, value in stats.items():
            part[key] = value
        rows.append(part)
    if not rows:
        return pd.DataFrame()
    result = pd.concat(rows, ignore_index=True)
    result["target_end"] = result.target_start + pd.Timedelta(hours=1)
    result["prediction_origin"] = origin.issue_time
    result["pm_history_cutoff"] = origin.pm_cutoff
    result["regime"] = origin.regime
    result["lead_hours"] = (result.target_start - origin.pm_cutoff).dt.total_seconds() / 3600
    result["actual_lead_hours"] = result.lead_hours + result.age_hours - 1
    hour = result.target_start.dt.hour.to_numpy()
    doy = result.target_start.dt.day_of_year.to_numpy()
    weekday = result.target_start.dt.day_of_week.to_numpy()
    result["hour_sin"] = np.sin(2*np.pi*hour/24)
    result["hour_cos"] = np.cos(2*np.pi*hour/24)
    result["doy_sin"] = np.sin(2*np.pi*doy/365.25)
    result["doy_cos"] = np.cos(2*np.pi*doy/365.25)
    result["weekday_sin"] = np.sin(2*np.pi*weekday/7)
    result["weekday_cos"] = np.cos(2*np.pi*weekday/7)
    result["issue_hour"] = origin.issue_time.hour
    result["issue_month"] = origin.issue_time.month
    for station in station_ids:
        result[f"station_{station}"] = result.location_id.eq(station).astype("int8")
    return result


def add_seasonal_and_baseline(rows: pd.DataFrame, archive: pd.DataFrame) -> pd.DataFrame:
    """Attach the unchanged legacy 2024 feature and shared W50 fallback."""
    if rows.empty:
        return rows.copy()
    unique = rows[["location_id", "target_start"]].drop_duplicates().reset_index(drop=True)
    seasonal = build_seasonal_features(archive, unique, calendar_mode="legacy_doy")
    unique["seasonal_pm"] = seasonal.hist24_same_hour_mean.to_numpy()
    out = rows.merge(unique, on=["location_id", "target_start"], validate="many_to_one")
    recent = out.median72.fillna(out.station_history_median)
    out["w50"] = [combine_forecasts(float(r), float(s) if np.isfinite(s) else None)
                  for r, s in zip(recent, out.seasonal_pm)]
    if not np.isfinite(out.w50).all():
        raise ValueError("Non-finite W50 features")
    return out


def build_examples(train: pd.DataFrame, archive: pd.DataFrame,
                   target_days: pd.DatetimeIndex, station_ids: tuple[int, ...]) -> pd.DataFrame:
    """Construct supervised examples; join labels only after features exist."""
    targets = train[["location_id", "target_start"]]
    parts = []
    for day in target_days:
        window = targets.loc[(targets.target_start >= day) &
                             (targets.target_start < day + pd.Timedelta(hours=48))]
        if window.empty:
            continue
        for regime in ("public", "private"):
            part = origin_features(train, window, make_origin(day, regime), station_ids)
            if not part.empty:
                parts.append(part)
    if not parts:
        raise ValueError("No training examples have eligible history")
    raw_features = pd.concat(parts, ignore_index=True)
    in_band = ((raw_features.regime.eq("public") & raw_features.actual_lead_hours.between(1, 48)) |
               (raw_features.regime.eq("private") & raw_features.actual_lead_hours.between(193, 240)))
    features = add_seasonal_and_baseline(raw_features.loc[in_band].copy(), archive)
    labels = train[["location_id", "target_start", "pm25"]].rename(columns={"pm25": "y"})
    examples = features.merge(labels, on=["location_id", "target_start"], validate="many_to_one")
    if not (examples.target_end > examples.prediction_origin).all():
        raise ValueError("A supervised target was already observed at its forecast issue")
    if not np.isfinite(examples.y).all() or (examples.y < 0).any():
        raise ValueError("Training labels must remain original finite nonnegative values")
    return examples


def candidate_model(name: str):
    """Return a bounded deterministic candidate; optional imports stay local."""
    if name in {"lightgbm", "lightgbm_residual"}:
        from lightgbm import LGBMRegressor
        return LGBMRegressor(n_estimators=120, learning_rate=0.05, num_leaves=7,
                             max_depth=4, min_child_samples=100, reg_lambda=20,
                             n_jobs=2, random_state=SEED, verbosity=-1)
    if name in {"catboost", "catboost_huber"}:
        from catboost import CatBoostRegressor
        loss = "RMSE" if name == "catboost" else "Huber:delta=50"
        return CatBoostRegressor(iterations=120, depth=4, learning_rate=0.05,
                                 l2_leaf_reg=20, loss_function=loss, thread_count=2,
                                 random_seed=SEED, verbose=False, allow_writing_files=False)
    if name == "hist_gradient_boosting":
        from sklearn.ensemble import HistGradientBoostingRegressor
        return HistGradientBoostingRegressor(max_iter=120, learning_rate=0.05,
                                             max_leaf_nodes=7, min_samples_leaf=100,
                                             l2_regularization=20, random_state=SEED)
    raise ValueError(f"Unknown candidate model: {name}")


def fit_predict(name: str, training: pd.DataFrame, validation: pd.DataFrame) -> np.ndarray:
    """Fit on original labels or W50 residuals and return valid predictions."""
    if training.empty or validation.empty:
        raise ValueError("Training and prediction examples must be nonempty")
    if (training.target_end > validation.pm_history_cutoff.min()).any():
        raise ValueError("A training label was unavailable at validation PM cutoff")
    model = candidate_model(name)
    target = training.y.to_numpy(dtype=float)
    if name.endswith("_residual"):
        target = target - training.w50.to_numpy(dtype=float)
    model.fit(training[list(FEATURE_COLUMNS)], target)
    result = model.predict(validation[list(FEATURE_COLUMNS)])
    if name.endswith("_residual"):
        result = validation.w50.to_numpy(dtype=float) + result
    result = np.maximum(np.asarray(result, dtype=float), 0.0)
    if not np.isfinite(result).all():
        raise ValueError(f"{name} produced non-finite predictions")
    return result
