"""Past-only baseline forecasting and submission checks.

This module explicitly separates three information clocks:
  - model_run_time: wall-clock time when the prediction file is generated.
  - pm_history_cutoff: the latest eligible PM observation timestamp (interval END).
    Derived from actual Train snapshot contents, not the wall clock.
  - target interval: specific target_start and target_end for each Test row.

The pm_history_cutoff defaults to the latest available interval-end in the
Train snapshot, but can be overridden explicitly for reproducibility and for
simulating specific competition submission snapshots.
"""
from __future__ import annotations

import hashlib
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def station_history_cutoffs(train: pd.DataFrame) -> pd.Series:
    """Latest observed target-hour start independently for each station."""
    return train.groupby("location_id")["target_start"].max()


def derive_pm_history_cutoff(train: pd.DataFrame) -> pd.Timestamp:
    """Derive the PM-history cutoff from the actual Train snapshot.

    The cutoff is the latest interval END across all stations (target_start + 1h).
    This reflects what is available in the released Train file, NOT the wall clock.

    Returns
    -------
    A timezone-aware timestamp (Asia/Kolkata).
    """
    latest_start = train["target_start"].max()
    return latest_start + pd.Timedelta(hours=1)


def history_features(
    grid: pd.DataFrame,
    *,
    pm_history_cutoff: pd.Timestamp,
    station_id: int,
) -> dict[str, float]:
    """Create deterministic recent-level features from observations strictly before cutoff.

    Parameters
    ----------
    grid:
        Station-hour indexed DataFrame with pm25 column.
        Index levels: (location_id, target_start).
    pm_history_cutoff:
        The cutoff timestamp (interval END, i.e., target_start + 1h of latest eligible row).
        Only observations whose target_start + 1h <= pm_history_cutoff are eligible.
    station_id:
        Competition location_id.
    """
    if pm_history_cutoff.tz is None:
        raise ValueError("pm_history_cutoff must be timezone-aware")
    station = grid.xs(station_id, level="location_id").sort_index()
    # target_start < pm_history_cutoff means the interval [start, start+1h) has ended
    # before the cutoff (interval end = start+1h <= cutoff => start < cutoff)
    history = station.loc[station.index + pd.Timedelta(hours=1) <= pm_history_cutoff]
    if history.empty or history.pm25.notna().sum() == 0:
        raise ValueError(
            f"No eligible PM history for station {station_id} before {pm_history_cutoff}"
        )
    level = _baseline_level(history["pm25"], pm_history_cutoff, "median72")
    if not np.isfinite(level):
        raise ValueError(f"No finite PM history for station {station_id}")
    return {"median72": level}


def recent_median72(history: pd.Series, cutoff: pd.Timestamp) -> float | None:
    """Median in the 72 elapsed hours ending at an interval-end cutoff."""
    if cutoff.tz is None:
        raise ValueError("PM cutoff must be timezone-aware")
    if history.index.tz is None:
        raise ValueError("PM history index must be timezone-aware")
    eligible = history.loc[history.index + pd.Timedelta(hours=1) <= cutoff].dropna()
    if eligible.empty:
        return None
    recent = eligible.loc[eligible.index > cutoff - pd.Timedelta(hours=73)]
    value = recent.median() if not recent.empty else eligible.median()
    if not np.isfinite(value):
        raise ValueError("Non-finite recent PM estimate")
    return float(value)


def combine_forecasts(recent_pm: float | None, seasonal_pm: float | None,
                      seasonal_weight: float = 0.5) -> float:
    """Blend available estimates; fail explicitly when neither exists."""
    if not 0 <= seasonal_weight <= 1:
        raise ValueError("seasonal_weight must be in [0, 1]")
    values = [recent_pm, seasonal_pm]
    for value in values:
        if value is not None and (not np.isfinite(value) or value < 0):
            raise ValueError("Forecast components must be finite and non-negative")
    if recent_pm is None and seasonal_pm is None:
        raise ValueError("Neither recent PM nor seasonal history is available")
    if recent_pm is None:
        return float(seasonal_pm)
    if seasonal_pm is None:
        return float(recent_pm)
    return float((1 - seasonal_weight) * recent_pm + seasonal_weight * seasonal_pm)


def predict_station_baseline(
    history: pd.Series,
    target_starts: pd.DatetimeIndex,
    *,
    pm_history_cutoff: pd.Timestamp,
    model: str,
) -> np.ndarray:
    """Shared fixed-origin baseline used by validation and inference.

    ``history`` is indexed by target-hour start. Only complete labels ending by
    ``pm_history_cutoff`` are used. The diur7 profile reproduces Task 005's
    history-only cleaning (drop values >=1000, cap remaining history at 300).
    """
    if pm_history_cutoff.tz is None:
        raise ValueError("pm_history_cutoff must be timezone-aware")
    history = history.sort_index()
    eligible = history.loc[history.index + pd.Timedelta(hours=1) <= pm_history_cutoff]
    if eligible.empty or not eligible.notna().any():
        return np.full(len(target_starts), np.nan)
    if model == "median72":
        return np.full(len(target_starts), _baseline_level(eligible, pm_history_cutoff, model))
    if model != "diur7":
        raise ValueError(f"Unsupported shared baseline {model!r}")

    clean = eligible.where(eligible < 1000).clip(upper=300)
    recent = clean.loc[clean.index > pm_history_cutoff - pd.Timedelta(hours=73)]
    if int(recent.notna().sum()) < 24:
        # Match Task 005's minimum coverage gate; unsupported station/origin
        # pairs remain unavailable for the candidate instead of being imputed.
        return np.full(len(target_starts), np.nan)
    window = clean.loc[clean.index > pm_history_cutoff - pd.Timedelta(hours=169)]
    profile = window.groupby(window.index.hour).mean()
    values = np.asarray([profile.get(target.hour, np.nan) for target in target_starts], dtype=float)
    return values


def _baseline_level(history: pd.Series, cutoff: pd.Timestamp, model: str) -> float:
    if model != "median72":
        raise ValueError(f"Unsupported baseline level {model!r}")
    value = recent_median72(history, cutoff)
    return float("nan") if value is None else value


def predict_test(
    train: pd.DataFrame,
    test: pd.DataFrame,
    *,
    issue_time: pd.Timestamp,
    pm_history_cutoff: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Forecast all test rows using the station-specific recent 72-hour median.

    Parameters
    ----------
    train:
        Full training data (from load_data).
    test:
        Test data (from load_data).
    issue_time:
        Model run time — the wall-clock time when predictions are generated.
        Must be timezone-aware. Used to filter eligible training labels:
        a label is eligible if its interval has ended by issue_time
        (target_start + 1h <= issue_time).
    pm_history_cutoff:
        Optional explicit PM-history cutoff (interval END of latest eligible row).
        When None, defaults to issue_time (the original behaviour).
        Separating this from issue_time is important when the released Train
        snapshot is delayed relative to actual model run time.
    """
    if issue_time.tz is None:
        raise ValueError("issue_time must be timezone-aware")
    if pm_history_cutoff is not None and pm_history_cutoff.tz is None:
        raise ValueError("pm_history_cutoff must be timezone-aware if provided")

    # Labels are available only after their interval ends (target_start + 1h <= issue_time)
    eligible = train.loc[train.target_start + pd.Timedelta(hours=1) <= issue_time]
    if eligible.empty:
        raise ValueError("No PM labels were available by issue_time")

    # Use pm_history_cutoff to gate feature computation; default to issue_time
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
            f"No eligible PM history by pm_history_cutoff for test stations: "
            f"{sorted(missing_stations)}"
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
    calendar_mode: str | None = None,
    series_map: dict[int, str | tuple[str, ...]] | None = None,
) -> pd.DataFrame:
    """Forecast using a 50:50 blend of median72 and 2024 seasonal same-hour feature.

    Falls back to median72 if hist24 is unavailable for a station.

    Parameters
    ----------
    history_2024:
        Output of historical_archive.load_2024_history().
    blend_weight_hist24:
        Weight given to hist24_same_hour (1 - weight goes to median72).
    """
    from mumbai_pm25.historical_archive import build_seasonal_features

    if issue_time.tz is None:
        raise ValueError("issue_time must be timezone-aware")

    effective_cutoff = pm_history_cutoff if pm_history_cutoff is not None else issue_time

    eligible = train.loc[train.target_start + pd.Timedelta(hours=1) <= issue_time]
    station_history = {
        int(station): pd.Series(
            group.pm25.to_numpy(dtype=float),
            index=pd.DatetimeIndex(pd.to_datetime(group.target_start, utc=True)).tz_convert(
                "Asia/Kolkata"
            ),
        ).sort_index()
        for station, group in eligible.groupby("location_id")
    }
    median72_feat = {
        station: recent_median72(series, effective_cutoff)
        for station, series in station_history.items()
    }

    # Compute seasonal features for all test rows
    target_df = test[["location_id", "target_start"]].copy()
    seasonal = build_seasonal_features(
        history_2024,
        target_df,
        series_map=series_map,
        window_days=14,
        min_obs=3,
        calendar_mode=calendar_mode,
    )

    out = test[["ID", "location_id", "target_start"]].copy()
    predictions: list[float] = []
    for i, row in enumerate(out.itertuples(index=False)):
        loc_id = int(row.location_id)
        m72 = median72_feat.get(loc_id)
        idx = test.index[i]
        sh = seasonal.loc[idx, "hist24_same_hour_mean"] if idx in seasonal.index else np.nan
        seasonal_value = float(sh) if np.isfinite(sh) else None
        predictions.append(combine_forecasts(m72, seasonal_value, blend_weight_hist24))

    out["Target"] = predictions
    validate_submission(out[["ID", "Target"]], test)
    return out[["ID", "Target"]]


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
    issue_time: pd.Timestamp,
    pm_history_cutoff: pd.Timestamp | None,
    train: pd.DataFrame,
    stations: pd.DataFrame,
    model: str = "median72",
    extra_sources: list[Path] | None = None,
    calendar_mode: str | None = None,
) -> None:
    """Write a compact reproducibility manifest beside generated predictions."""
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

    inputs = [
        train_path, test_path,
        train_path.with_name("SampleSubmission.csv"),
        train_path.with_name("Stations.csv"),
        train_path.with_name("DataDictionary.txt"),
        train_path.with_name("AdditionalHistory.zip"),
    ]
    if extra_sources:
        inputs.extend(extra_sources)

    lines = [
        f"model: {model}",
        f"model_run_time: {issue_time.isoformat()}",
        f"pm_history_cutoff_global: {effective_cutoff.isoformat()}",
        f"git_commit: {git_commit}",
        f"python: {sys.version.split()[0]}",
        f"platform: {platform.platform()}",
        f"pandas: {pd.__version__}",
        f"numpy: {np.__version__}",
        "weather: disabled",
        "history_window_hours: 72",
        ("seasonal_archive: History_Mumbai_2024.csv.gz (cpcb_caaqm, exact series_id lookup)"
         if calendar_mode is None else
         "seasonal_archive: History_Mumbai_2024.csv.gz (legacy name pooling; reproduction only)"),
        f"seasonal_calendar_mode: {calendar_mode or 'month_day_2024'}",
        "station_pm_history_cutoffs:",
    ]
    lines.extend(
        f"  {int(sid)}: {cutoff.isoformat()}" for sid, cutoff in cutoffs.items()
    )
    station_names = stations.set_index("location_id").station_name
    lines.append("station_names:")
    lines.extend(
        f"  {int(sid)}: {station_names.loc[sid]}" for sid in cutoffs.index
    )
    lines.append("input_sha256:")
    lines.extend(f"  {p.name}: {sha256(p)}" for p in inputs if p.is_file())
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
