"""Optional supervised model candidates for station/calendar structure."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesRegressor


def calendar_features(target_start: pd.Series, location_id: pd.Series,
                      station_ids: list[int]) -> pd.DataFrame:
    """Create stable calendar cycles and station one-hot features only."""
    if target_start.isna().any() or location_id.isna().any():
        raise ValueError("Calendar features require complete timestamps and station IDs")
    timestamp = pd.to_datetime(target_start)
    station = pd.to_numeric(location_id, errors="raise").to_numpy(dtype=int)
    known = {int(sid) for sid in station_ids}
    unknown = {int(sid) for sid in np.unique(station)} - known
    if unknown:
        raise ValueError(f"Unknown station IDs in calendar features: {sorted(unknown)}")
    hour = timestamp.dt.hour.to_numpy(dtype=float)
    weekday = timestamp.dt.day_of_week.to_numpy(dtype=float)
    day_of_year = timestamp.dt.day_of_year.to_numpy(dtype=float)
    features: dict[str, np.ndarray] = {
        "hour_sin": np.sin(2 * np.pi * hour / 24),
        "hour_cos": np.cos(2 * np.pi * hour / 24),
        "weekday_sin": np.sin(2 * np.pi * weekday / 7),
        "weekday_cos": np.cos(2 * np.pi * weekday / 7),
        "year_day_sin": np.sin(2 * np.pi * day_of_year / 365.25),
        "year_day_cos": np.cos(2 * np.pi * day_of_year / 365.25),
    }
    for station_id in sorted(known):
        features[f"station_{station_id}"] = (station == station_id).astype(np.int8)
    return pd.DataFrame(features, index=target_start.index)


def fit_extra_trees(train_rows: pd.DataFrame, predict_rows: pd.DataFrame, *,
                    station_ids: list[int], seed: int = 42) -> np.ndarray:
    """Fit a deterministic, regularized ExtraTrees model on available labels."""
    if train_rows.empty:
        raise ValueError("ExtraTrees requires at least one eligible training label")
    if (train_rows.target_start + pd.Timedelta(hours=1) > train_rows.pm_history_cutoff).any():
        raise ValueError("ExtraTrees training labels exceed the declared PM-history cutoff")
    x_train = calendar_features(train_rows.target_start, train_rows.location_id, station_ids)
    x_predict = calendar_features(predict_rows.target_start, predict_rows.location_id, station_ids)
    y_train = pd.to_numeric(train_rows.pm25, errors="raise").to_numpy(dtype=float)
    if not np.isfinite(y_train).all() or (y_train < 0).any():
        raise ValueError("ExtraTrees training labels must be finite and non-negative")
    model = ExtraTreesRegressor(n_estimators=64, min_samples_leaf=40, max_features=0.8,
                                n_jobs=1, random_state=seed)
    model.fit(x_train, y_train)
    prediction = np.maximum(model.predict(x_predict), 0.0)
    if not np.isfinite(prediction).all():
        raise ValueError("ExtraTrees returned non-finite predictions")
    return prediction


def rolling_extra_trees(train: pd.DataFrame, *, gap_hours: int, horizon_hours: int = 48,
                        step_days: int = 28, seed: int = 42,
                        baseline_oof: pd.DataFrame | None = None) -> pd.DataFrame:
    """Evaluate calendar ExtraTrees on the same target rows as baseline folds."""
    from mumbai_pm25.validation import rolling_oof

    if baseline_oof is None:
        baseline_oof = rolling_oof(train, gap_hours=gap_hours, horizon_hours=horizon_hours,
                                   step_days=step_days)
    target_rows = baseline_oof.drop_duplicates(["fold_id", "location_id", "target_start"]).copy()
    station_ids = sorted(int(sid) for sid in train.location_id.unique())
    outputs = []
    for fold_id, targets in target_rows.groupby("fold_id", sort=True):
        cutoff = targets.pm_history_cutoff.iloc[0]
        eligible = train.loc[train.target_start + pd.Timedelta(hours=1) <= cutoff].copy()
        eligible["pm_history_cutoff"] = cutoff
        predictions = fit_extra_trees(eligible, targets, station_ids=station_ids, seed=seed)
        result = targets.drop(columns=["y", "prediction", "model"]).copy()
        result["y"] = targets.y.to_numpy()
        result["prediction"] = predictions
        result["model"] = "extra_trees_calendar"
        outputs.append(result)
    if not outputs:
        raise ValueError("No eligible rolling folds for ExtraTrees")
    return pd.concat(outputs, ignore_index=True)
