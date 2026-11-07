"""Past-only forecasting and submission generation.

This module separates three information clocks:
  - model_run_time: wall-clock time when predictions are generated.
  - pm_history_cutoff: latest eligible PM observation timestamp in Train snapshot.
  - target intervals: from Test.csv.

Supports:
  - median72 (inference control)
  - hist24_blend50_median72 (statistical seasonal blend)
  - ensemble_accuracy (Submission A: Optimal blend of CatBoost log1p + 2024 Seasonal Blend)
  - ensemble_robust (Submission B: 50% CatBoost log1p + 50% 2024 Seasonal Blend)
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from mumbai_pm25.features.pipeline import build_feature_matrix
from mumbai_pm25.models.supervised import SupervisedForecaster


def station_history_cutoffs(train: pd.DataFrame) -> pd.Series:
    """Latest observed target-hour start independently for each station."""
    return train.groupby("location_id")["target_start"].max()


def derive_pm_history_cutoff(train: pd.DataFrame) -> pd.Timestamp:
    """Derive the PM-history cutoff from the actual Train snapshot."""
    latest_start = train["target_start"].max()
    return latest_start + pd.Timedelta(hours=1)


def history_features(
    grid: pd.DataFrame,
    *,
    pm_history_cutoff: pd.Timestamp,
    station_id: int,
) -> dict[str, Any]:
    """Calculate explicit recent-level features and metadata strictly before cutoff.

    Returns diagnostic metrics:
        latest_pm25, obs_age_hours, obs_count_24, obs_count_72, obs_count_168,
        coverage_72, median24, median72, median168, mean24, mean72, trend_slope.
    """
    if pm_history_cutoff.tz is None:
        raise ValueError("pm_history_cutoff must be timezone-aware")
    station = grid.xs(station_id, level="location_id").sort_index()
    history = station.loc[station.index < pm_history_cutoff]
    valid = history.dropna()
    if valid.empty:
        raise ValueError(f"No eligible PM history for station {station_id} before {pm_history_cutoff}")

    latest_time = valid.index[-1]
    latest_end = latest_time + pd.Timedelta(hours=1)
    obs_age_hours = max(0.0, (pm_history_cutoff - latest_end).total_seconds() / 3600.0)
    latest_pm25 = float(valid.iloc[-1]["pm25"])

    # Windows: target_start represents interval start, while pm_history_cutoff is interval end
    # (or issue_time). For a W-hour window before cutoff, interval start > cutoff - (W + 1)h
    w24 = valid.loc[valid.index > pm_history_cutoff - pd.Timedelta(hours=25), "pm25"]
    w72 = valid.loc[valid.index > pm_history_cutoff - pd.Timedelta(hours=73), "pm25"]
    w168 = valid.loc[valid.index > pm_history_cutoff - pd.Timedelta(hours=169), "pm25"]

    count24 = len(w24)
    count72 = len(w72)
    count168 = len(w168)
    coverage72 = min(1.0, count72 / 72.0)

    # Multi-tier age-aware fallback
    if count72 > 0:
        med72 = float(w72.median())
        mean72 = float(w72.mean())
    elif count168 > 0:
        med72 = float(w168.median())
        mean72 = float(w168.mean())
    else:
        med72 = latest_pm25
        mean72 = latest_pm25

    med24 = float(w24.median()) if count24 > 0 else med72
    mean24 = float(w24.mean()) if count24 > 0 else mean72
    med168 = float(w168.median()) if count168 > 0 else med72
    trend_slope = float(med24 - med72)

    return {
        "latest_pm25": latest_pm25,
        "obs_age_hours": obs_age_hours,
        "obs_count_24": count24,
        "obs_count_72": count72,
        "obs_count_168": count168,
        "coverage_72": coverage72,
        "median24": med24,
        "median72": med72,
        "median168": med168,
        "mean24": mean24,
        "mean72": mean72,
        "trend_slope": trend_slope,
    }


def predict_test(
    train: pd.DataFrame,
    test: pd.DataFrame,
    *,
    issue_time: pd.Timestamp,
    pm_history_cutoff: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Forecast all test rows using the station-specific recent 72-hour median."""
    if issue_time.tz is None:
        raise ValueError("issue_time must be timezone-aware")
    if pm_history_cutoff is not None and pm_history_cutoff.tz is None:
        raise ValueError("pm_history_cutoff must be timezone-aware if provided")

    eligible = train.loc[train.target_start + pd.Timedelta(hours=1) <= issue_time]
    if eligible.empty:
        raise ValueError("No PM labels were available by issue_time")

    effective_cutoff = pm_history_cutoff if pm_history_cutoff is not None else issue_time
    grid = eligible.set_index(["location_id", "target_start"])[["pm25"]]
    out = test[["ID", "location_id", "target_start"]].copy()
    predictions: list[float] = []
    cutoffs = station_history_cutoffs(eligible)
    features = {
        int(s): history_features(grid, pm_history_cutoff=effective_cutoff, station_id=int(s))
        for s in cutoffs.index
    }
    missing_stations = {int(s) for s in test.location_id.unique()} - set(features)
    if missing_stations:
        raise ValueError(
            f"No eligible PM history by pm_history_cutoff for test stations: {sorted(missing_stations)}"
        )
    for row in out.itertuples(index=False):
        feat = features[int(row.location_id)]
        predictions.append(max(0.0, float(feat["median72"])))
    out["Target"] = predictions
    validate_submission(out[["ID", "Target"]], test)
    return out[["ID", "Target"]]


def predict_test_with_hist24_blend(
    train: pd.DataFrame,
    test: pd.DataFrame,
    history_2024: pd.DataFrame,
    *,
    issue_time: pd.Timestamp,
    pm_history_cutoff: pd.Timestamp | None = None,
    blend_weight_hist24: float = 0.5,
) -> pd.DataFrame:
    """Forecast using a blend of median72 and 2024 seasonal same-hour climatology."""
    from mumbai_pm25.historical_archive import STATION_NAME_MAP, build_seasonal_features

    if issue_time.tz is None:
        raise ValueError("issue_time must be timezone-aware")

    effective_cutoff = pm_history_cutoff if pm_history_cutoff is not None else issue_time
    eligible = train.loc[train.target_start + pd.Timedelta(hours=1) <= issue_time]
    if eligible.empty:
        raise ValueError("No PM labels were available by issue_time")

    grid = eligible.set_index(["location_id", "target_start"])[["pm25"]]
    cutoffs = station_history_cutoffs(eligible)
    median72_feat = {
        int(s): history_features(grid, pm_history_cutoff=effective_cutoff, station_id=int(s))
        for s in cutoffs.index
    }
    missing_stations = {int(s) for s in test.location_id.unique()} - set(median72_feat)
    if missing_stations:
        raise ValueError(f"No eligible PM history for test stations: {sorted(missing_stations)}")

    target_df = test[["location_id", "target_start"]].copy()
    seasonal = build_seasonal_features(
        history_2024,
        target_df,
        station_map=STATION_NAME_MAP,
        window_days=14,
        min_obs=3,
    )

    out = test[["ID", "location_id", "target_start"]].copy()
    predictions: list[float] = []
    for i, row in enumerate(out.itertuples(index=False)):
        loc_id = int(row.location_id)
        m72 = max(0.0, float(median72_feat[loc_id]["median72"]))
        idx = test.index[i]
        sh = seasonal.loc[idx, "hist24_same_hour_mean"] if idx in seasonal.index else np.nan

        if np.isfinite(sh):
            sh_val = max(0.0, float(sh))
            blended = (1.0 - blend_weight_hist24) * m72 + blend_weight_hist24 * sh_val
        else:
            blended = m72
        predictions.append(max(0.0, blended))

    out["Target"] = predictions
    validate_submission(out[["ID", "Target"]], test)
    return out[["ID", "Target"]]


def predict_test_ensemble(
    train: pd.DataFrame,
    test: pd.DataFrame,
    history_2024: pd.DataFrame,
    *,
    issue_time: pd.Timestamp,
    pm_history_cutoff: pd.Timestamp | None = None,
    ensemble_type: str = "accuracy",
) -> pd.DataFrame:
    """Generate final competition ensemble predictions (Submission A or Submission B).

    Parameters
    ----------
    ensemble_type:
        'accuracy' (Submission A): 83% CatBoost log1p + 17% 2024 Seasonal Blend
        'robust'   (Submission B): 50% CatBoost log1p + 50% 2024 Seasonal Blend
    """
    effective_cutoff = pm_history_cutoff if pm_history_cutoff is not None else issue_time

    # 1. Base statistical predictions
    stat_sub = predict_test_with_hist24_blend(
        train, test, history_2024,
        issue_time=issue_time,
        pm_history_cutoff=effective_cutoff,
        blend_weight_hist24=0.5,
    )
    p_stat = stat_sub["Target"].to_numpy(dtype=float)

    # 2. Build training samples from historical forecast origins
    grid = train.set_index(["location_id", "target_start"])[["pm25"]].sort_index()
    station_histories = {
        int(sid): grid.xs(sid, level="location_id")["pm25"]
        for sid in train["location_id"].unique()
    }

    # Sample historical training origins strictly prior to cutoff
    gap = int((test["target_start"].min() - effective_cutoff).total_seconds() / 3600.0)
    gap = max(48, min(120, gap))

    origins = pd.date_range(
        train.target_start.min() + pd.Timedelta(days=21),
        effective_cutoff - pd.Timedelta(hours=48),
        freq="48h",
        tz="Asia/Kolkata",
    )
    if len(origins) > 40:
        origins = origins[::len(origins) // 40]

    train_dfs, train_ys = [], []
    for orig in origins:
        orig_cutoff = orig - pd.Timedelta(hours=gap)
        target_hours = pd.date_range(orig, periods=48, freq="h")
        t_rows = []
        for sid in [11606, 11611, 3409510, 3409511]:
            s_series = station_histories[sid]
            for h_idx, t in enumerate(target_hours, start=1):
                if t in s_series.index and pd.notna(s_series.loc[t]):
                    t_rows.append({"location_id": sid, "target_start": t, "horizon_hours": h_idx, "pm25": s_series.loc[t]})
        if not t_rows:
            continue
        tdf = pd.DataFrame(t_rows)
        X_p = build_feature_matrix(
            station_histories,
            tdf,
            orig_cutoff,
            history_2024=history_2024,
            include_seasonal=True,
            include_spatial=True,
        )
        train_dfs.append(X_p)
        train_ys.append(tdf["pm25"])

    X_train = pd.concat(train_dfs, ignore_index=True)
    y_train = pd.concat(train_ys, ignore_index=True)

    # Build features for test rows with aligned in-distribution block horizon (1..48)
    test_df = test.copy()
    priv_start = pd.Timestamp("2026-11-11 00:00:00", tz="Asia/Kolkata")
    offset_h = (
        (test_df["target_start"] - priv_start).dt.total_seconds() / 3600.0
    ).astype(int)
    test_df["horizon_hours"] = np.where(
        (offset_h >= 0) & (offset_h < 48),
        offset_h + 1,
        (offset_h % 48) + 1,
    )

    X_test = build_feature_matrix(
        station_histories,
        test_df,
        effective_cutoff,
        history_2024=history_2024,
        include_seasonal=True,
        include_spatial=True,
    )

    # Fit CatBoost log1p
    cb_model = SupervisedForecaster(
        model_family="catboost",
        target_transform="log1p",
        params={"iterations": 150, "learning_rate": 0.05, "depth": 6},
    )
    cb_model.fit(X_train, y_train)
    p_cb = cb_model.predict(X_test)

    if ensemble_type == "accuracy":
        # 83% CatBoost log1p + 17% Statistical Blend
        final_preds = 0.83 * p_cb + 0.17 * p_stat
    elif ensemble_type == "robust":
        # 50% CatBoost log1p + 50% Statistical Blend
        final_preds = 0.50 * p_cb + 0.50 * p_stat
    else:
        raise ValueError(f"Unknown ensemble type: {ensemble_type}")

    out = test[["ID"]].copy()
    out["Target"] = np.maximum(0.0, final_preds)
    validate_submission(out, test)
    return out


def validate_submission(prediction: pd.DataFrame, test: pd.DataFrame) -> None:
    if list(prediction.columns) != ["ID", "Target"]:
        raise ValueError("Submission columns must be exactly ID, Target")
    if prediction.ID.tolist() != test.ID.tolist():
        raise ValueError("Submission IDs must match Test.csv exactly in original order")
    values = pd.to_numeric(prediction.Target, errors="coerce").to_numpy(dtype=float)
    if len(values) != len(test) or not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("Predictions must be finite, non-negative, and complete")


def write_manifest(
    path: Path,
    *,
    train_path: Path,
    test_path: Path,
    output_path: Path | None = None,
    issue_time: pd.Timestamp,
    pm_history_cutoff: pd.Timestamp | None,
    train: pd.DataFrame,
    stations: pd.DataFrame,
    model: str = "median72",
    extra_sources: list[Path] | None = None,
    ensemble_weights: str | None = None,
) -> None:
    """Write an exhaustive, cryptographically verified reproducibility manifest."""
    def sha256(p: Path) -> str:
        digest = hashlib.sha256()
        with p.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    eligible = train.loc[train.target_start + pd.Timedelta(hours=1) <= issue_time]
    cutoffs = eligible.groupby("location_id").target_start.max() + pd.Timedelta(hours=1)
    effective_cutoff = pm_history_cutoff if pm_history_cutoff is not None else issue_time

    git_root = Path(__file__).resolve().parents[2]
    try:
        git_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=git_root, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        git_commit = "unavailable"

    try:
        status = subprocess.run(
            ["git", "status", "--porcelain"], cwd=git_root, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
        git_working_tree = "clean" if not status else "modified"
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        git_working_tree = "unknown"

    raw_inputs = [
        train_path, test_path,
        train_path.with_name("SampleSubmission.csv"),
        train_path.with_name("Stations.csv"),
        train_path.with_name("DataDictionary.txt"),
        train_path.with_name("AdditionalHistory.zip"),
    ]
    if extra_sources:
        raw_inputs.extend(extra_sources)

    # Deduplicate inputs while preserving order
    inputs = list(dict.fromkeys(raw_inputs))

    # Installed ML library versions
    def get_pkg_version(pkg_name: str) -> str:
        try:
            return importlib.metadata.version(pkg_name)
        except importlib.metadata.PackageNotFoundError:
            return "not-installed"

    lines = [
        f"model: {model}",
        f"ensemble_weights: {ensemble_weights or 'none'}",
        f"model_run_time: {issue_time.isoformat()}",
        f"pm_history_cutoff_global: {effective_cutoff.isoformat()}",
        f"git_commit: {git_commit}",
        f"git_working_tree: {git_working_tree}",
        f"python: {sys.version.split()[0]}",
        f"platform: {platform.platform()}",
        f"pandas: {pd.__version__}",
        f"numpy: {np.__version__}",
        f"lightgbm: {get_pkg_version('lightgbm')}",
        f"catboost: {get_pkg_version('catboost')}",
        f"xgboost: {get_pkg_version('xgboost')}",
        f"scikit_learn: {get_pkg_version('scikit-learn')}",
        "weather: disabled",
        "seasonal_archive: History_Mumbai_2024.csv.gz (cpcb_caaqm, pre-aggregated, leap-year aligned)",
    ]

    if output_path and output_path.is_file():
        lines.append(f"output_file: {output_path.name}")
        lines.append(f"output_sha256: {sha256(output_path)}")

    lines.append("station_pm_history_cutoffs:")
    lines.extend(f"  {int(sid)}: {cutoff.isoformat()}" for sid, cutoff in cutoffs.items())

    station_names = stations.set_index("location_id").station_name
    lines.append("station_names:")
    lines.extend(f"  {int(sid)}: {station_names.loc[sid]}" for sid in cutoffs.index)

    lines.append("input_sha256:")
    lines.extend(f"  {p.name}: {sha256(p)}" for p in inputs if p.is_file())

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
