"""Calendar and temporal feature engineering."""
from __future__ import annotations

import numpy as np
import pandas as pd


def build_calendar_features(
    target_start: pd.Series,
    location_id: pd.Series,
    horizon_hours: pd.Series | np.ndarray | None = None,
) -> pd.DataFrame:
    """Generate cyclical and calendar features for given target start timestamps.

    Features generated:
      - hour, weekday, month, day_of_year
      - hour_sin, hour_cos (24-hour cycle)
      - weekday_sin, weekday_cos (7-day cycle)
      - doy_sin, doy_cos (365.25-day seasonal cycle)
      - horizon_hours: 1 to 48 (or custom)
      - station_id: integer station identifier
      - station_11606, station_11611, station_3409510, station_3409511: one-hot indicators
    """
    ts = pd.to_datetime(target_start)
    locs = pd.to_numeric(location_id, errors="raise").to_numpy(dtype=int)

    h = ts.dt.hour.to_numpy(dtype=float)
    w = ts.dt.day_of_week.to_numpy(dtype=float)
    m = ts.dt.month.to_numpy(dtype=float)
    d = ts.dt.day_of_year.to_numpy(dtype=float)

    if horizon_hours is None:
        h_vals = np.ones(len(ts), dtype=float)
    elif isinstance(horizon_hours, pd.Series):
        h_vals = horizon_hours.to_numpy(dtype=float)
    else:
        h_vals = np.asarray(horizon_hours, dtype=float)

    feat: dict[str, np.ndarray] = {
        "hour": h,
        "weekday": w,
        "month": m,
        "day_of_year": d,
        "hour_sin": np.sin(2.0 * np.pi * h / 24.0),
        "hour_cos": np.cos(2.0 * np.pi * h / 24.0),
        "weekday_sin": np.sin(2.0 * np.pi * w / 7.0),
        "weekday_cos": np.cos(2.0 * np.pi * w / 7.0),
        "doy_sin": np.sin(2.0 * np.pi * d / 365.25),
        "doy_cos": np.cos(2.0 * np.pi * d / 365.25),
        "horizon_hours": h_vals,
        "station_id": locs,
    }

    # Canonical competition station one-hot indicators
    for sid in [11606, 11611, 3409510, 3409511]:
        feat[f"station_{sid}"] = (locs == sid).astype(np.int8)

    return pd.DataFrame(feat, index=target_start.index)
