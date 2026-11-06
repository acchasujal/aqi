"""Validated challenge data loading and timestamp alignment."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

TRAIN_COLUMNS = {"timestamp_ist", "pm25", "location_id", "sensor_id", "station_name"}
TEST_COLUMNS = {"ID", "location_id", "target_start_ist", "target_end_ist"}


def _read_csv(path: Path, required: set[str]) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"Required challenge file not found: {path}")
    frame = pd.read_csv(path)
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{path.name} is missing columns: {sorted(missing)}")
    return frame


def _parse_ist(values: pd.Series, *, field_name: str) -> pd.Series:
    """Require explicit competition IST offsets and return Asia/Kolkata values."""
    offsets = values.astype("string").str[-6:]
    if offsets.isna().any() or set(offsets) != {"+05:30"}:
        raise ValueError(f"{field_name} values must carry the explicit +05:30 IST offset")
    return pd.to_datetime(values, utc=True).dt.tz_convert("Asia/Kolkata")


def load_data(data_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load core inputs, aligning training labels to the target-hour start."""
    train = _read_csv(data_dir / "Train.csv", TRAIN_COLUMNS)
    test = _read_csv(data_dir / "Test.csv", TEST_COLUMNS)
    sample = _read_csv(data_dir / "SampleSubmission.csv", {"ID", "Target"})
    stations = _read_csv(data_dir / "Stations.csv", {"location_id", "station_name", "selected_sensor", "timezone"})
    if list(sample.columns) != ["ID", "Target"]:
        raise ValueError("SampleSubmission.csv columns must be exactly ID, Target")
    train = train.copy()
    test = test.copy()
    train["timestamp_ist"] = _parse_ist(train["timestamp_ist"], field_name="Train.timestamp_ist")
    train["target_start"] = train["timestamp_ist"] - pd.Timedelta(hours=1)
    test["target_start"] = _parse_ist(test["target_start_ist"], field_name="Test.target_start_ist")
    test["target_end"] = _parse_ist(test["target_end_ist"], field_name="Test.target_end_ist")
    if train.duplicated(["location_id", "target_start"]).any():
        raise ValueError("Train contains duplicate station/hour labels")
    if test.ID.duplicated().any() or test.duplicated(["location_id", "target_start"]).any():
        raise ValueError("Test must contain unique IDs and station/hour targets")
    if len(test) != 2592 or len(stations) != 4:
        raise ValueError(f"Unexpected challenge grid: expected 2,592 test rows and 4 stations; found {len(test)} and {len(stations)}")
    if train["pm25"].isna().any() or not pd.to_numeric(train["pm25"], errors="coerce").notna().all():
        raise ValueError("Train PM2.5 labels must be present and numeric")
    values = pd.to_numeric(train["pm25"], errors="raise").to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("Train PM2.5 labels must be finite and non-negative")
    if stations.location_id.duplicated().any() or stations.selected_sensor.duplicated().any():
        raise ValueError("Stations.csv must contain unique location_id and selected_sensor values")
    if set(stations.timezone) != {"Asia/Kolkata"}:
        raise ValueError("All competition stations must use Asia/Kolkata")
    mapping = stations.set_index("location_id")["selected_sensor"]
    if not test["location_id"].isin(mapping.index).all() or not train["location_id"].isin(mapping.index).all():
        raise ValueError("Train or test includes station absent from Stations.csv")
    if not test["sensor_id"].eq(test["location_id"].map(mapping)).all():
        raise ValueError("Test sensor/station mapping disagrees with Stations.csv")
    if not train["sensor_id"].eq(train["location_id"].map(mapping)).all():
        raise ValueError("Train sensor/station mapping disagrees with Stations.csv")
    station_names = stations.set_index("location_id")["station_name"]
    if not train["station_name"].eq(train["location_id"].map(station_names)).all():
        raise ValueError("Train station names disagree with Stations.csv")
    if not test["target_end"].sub(test["target_start"]).eq(pd.Timedelta(hours=1)).all():
        raise ValueError("Test rows must describe one-hour intervals")
    return train, test, sample, stations


def complete_hourly_grid(train: pd.DataFrame) -> pd.DataFrame:
    """Return station-indexed complete hourly timeline; absent observations stay NaN."""
    if "target_start" not in train:
        raise ValueError("Call load_data first; aligned target_start is required")
    stations = sorted(train["location_id"].unique())
    full_hours = pd.date_range(train.target_start.min(), train.target_start.max(), freq="h")
    grid = pd.MultiIndex.from_product([stations, full_hours], names=["location_id", "target_start"])
    return train.set_index(["location_id", "target_start"])[["pm25"]].reindex(grid)
