"""Past-only baseline forecasting and submission checks."""
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


def history_features(grid: pd.DataFrame, *, pm_history_cutoff: pd.Timestamp, station_id: int) -> dict[str, float]:
    """Create deterministic recent-level features from observations strictly before cutoff."""
    if pm_history_cutoff.tz is None:
        raise ValueError("pm_history_cutoff must be timezone-aware")
    station = grid.xs(station_id, level="location_id").sort_index()
    history = station.loc[station.index < pm_history_cutoff]
    if history.empty or history.pm25.notna().sum() == 0:
        raise ValueError(f"No eligible PM history for station {station_id} before {pm_history_cutoff}")
    # Train timestamps mark interval starts here. Include intervals whose end
    # falls in the 72 hours preceding cutoff, including fractional-hour issues.
    recent = history.loc[history.index > pm_history_cutoff - pd.Timedelta(hours=73), "pm25"]
    observed = recent.dropna()
    level = float(observed.median()) if not observed.empty else float(history.pm25.median())
    if not np.isfinite(level):
        raise ValueError(f"No finite PM history for station {station_id}")
    return {"median72": level}


def predict_test(train: pd.DataFrame, test: pd.DataFrame, *, issue_time: pd.Timestamp) -> pd.DataFrame:
    """Forecast all rows using the station-specific recent 72-hour median."""
    if issue_time.tz is None:
        raise ValueError("issue_time must be timezone-aware")
    # The hourly label is available only after its interval ends (start + 1h).
    eligible = train.loc[train.target_start + pd.Timedelta(hours=1) <= issue_time]
    if eligible.empty:
        raise ValueError("No PM labels were available by issue_time")
    grid = eligible.set_index(["location_id", "target_start"])[["pm25"]]
    out = test[["ID", "location_id", "target_start"]].copy()
    predictions: list[float] = []
    cutoffs = station_history_cutoffs(eligible)
    features = {int(s): history_features(grid, pm_history_cutoff=issue_time, station_id=int(s)) for s in cutoffs.index}
    missing_stations = {int(s) for s in test.location_id.unique()} - set(features)
    if missing_stations:
        raise ValueError(f"No eligible PM history by issue_time for test stations: {sorted(missing_stations)}")
    for row in out.itertuples(index=False):
        feat = features[int(row.location_id)]
        predictions.append(max(0.0, float(feat["median72"])))
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


def write_manifest(path: Path, *, train_path: Path, test_path: Path, issue_time: pd.Timestamp,
                   train: pd.DataFrame, stations: pd.DataFrame, model: str = "median72") -> None:
    """Write a compact reproducibility manifest beside generated predictions."""
    def sha256(p: Path) -> str:
        digest = hashlib.sha256()
        with p.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    eligible = train.loc[train.target_start + pd.Timedelta(hours=1) <= issue_time]
    cutoffs = eligible.groupby("location_id").target_start.max() + pd.Timedelta(hours=1)
    git_root = Path(__file__).resolve().parents[2]
    git_commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=git_root, check=True,
                                capture_output=True, text=True).stdout.strip()
    inputs = [train_path, test_path, train_path.with_name("SampleSubmission.csv"),
              train_path.with_name("Stations.csv"), train_path.with_name("DataDictionary.txt")]
    lines = [f"model: {model}", f"issue_time: {issue_time.isoformat()}",
             f"git_commit: {git_commit}", f"python: {sys.version.split()[0]}",
             f"platform: {platform.platform()}", f"pandas: {pd.__version__}",
             f"numpy: {np.__version__}", "weather: disabled", "history_window_hours: 72",
             "station_pm_history_cutoffs:"]
    lines.extend(f"  {int(sid)}: {cutoff.isoformat()}" for sid, cutoff in cutoffs.items())
    station_names = stations.set_index("location_id").station_name
    lines.append("station_names:")
    lines.extend(f"  {int(sid)}: {station_names.loc[sid]}" for sid in cutoffs.index)
    lines.append("input_sha256:")
    lines.extend(f"  {p.name}: {sha256(p)}" for p in inputs)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
