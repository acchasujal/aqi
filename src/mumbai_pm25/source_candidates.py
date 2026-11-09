"""Experimental reconstruction of the supplied branch's seasonal candidate C.

Name-pooled archive readings are an explicit alternative to exact-source P_fix,
not an assertion that two archive sensors measure the same physical location.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

NAMES = {
    11606: "Borivali East, Mumbai - IITM",
    11611: "Malad West, Mumbai - IITM",
    3409510: "Byculla, Mumbai - BMC",
    3409511: "Shivaji Nagar, Mumbai - BMC",
}


def normalized_days(times: pd.Series) -> np.ndarray:
    if not isinstance(times.dtype, pd.DatetimeTZDtype) or times.isna().any():
        raise ValueError("Seasonal timestamps must be present and timezone-aware")
    days = times.dt.day_of_year.to_numpy(dtype=float)
    days -= (times.dt.is_leap_year & times.dt.month.gt(2)).to_numpy()
    days[(times.dt.month.eq(2) & times.dt.day.eq(29)).to_numpy()] = 59.5
    return days


def branch_seasonal(history: pd.DataFrame, targets: pd.DataFrame) -> np.ndarray:
    """Reproduce default 14-day normalized-calendar window and >=3 unique hours.

    Each timestamp first averages concurrent readings of the exact canonical
    station name, matching the supplied branch. No outlier filtering occurs.
    """
    required = {"station_name", "hour_start", "pm25"}
    if not required.issubset(history) or not {"location_id", "target_start"}.issubset(targets):
        raise ValueError("Need named archive station-hours and aligned target keys")
    if history.empty or targets.empty:
        return np.full(len(targets), np.nan)
    if history.hour_start.dt.year.ne(2024).any():
        raise ValueError("Only the frozen 2024 archive is eligible")
    if not np.isfinite(history.pm25.to_numpy(dtype=float)).all() or history.pm25.lt(0).any():
        raise ValueError("Archive PM must be finite and nonnegative")
    pooled = history.groupby(["station_name", "hour_start"], as_index=False).pm25.mean()
    pooled["day"] = normalized_days(pooled.hour_start)
    pooled["hour"] = pooled.hour_start.dt.hour
    day = np.round(normalized_days(targets.target_start))
    hour = targets.target_start.dt.hour.to_numpy()
    station = targets.location_id.to_numpy()
    result = np.full(len(targets), np.nan)
    for sid, name in NAMES.items():
        for h in range(24):
            part = pooled.loc[pooled.station_name.eq(name) & pooled.hour.eq(h)]
            if part.empty:
                continue
            mask = (station == sid) & (hour == h)
            for d in np.unique(day[mask]):
                distance = np.abs(part.day.to_numpy() - d)
                values = part.loc[np.minimum(distance, 365-distance) <= 14, "pm25"]
                if len(values) >= 3:
                    result[mask & (day == d)] = float(values.mean())
    return result


def branch_recent(train: pd.DataFrame, targets: pd.DataFrame,
                  cutoff: pd.Timestamp) -> np.ndarray:
    """72h median -> 168h median -> last value, using eligible interval ends."""
    if cutoff.tzinfo is None or cutoff != cutoff.floor("h"):
        raise ValueError("Require timezone-aware hourly PM cutoff")
    if train.duplicated(["location_id", "target_start"]).any():
        raise ValueError("Duplicate training station-hour keys")
    past = train.loc[train.target_start + pd.Timedelta(hours=1) <= cutoff]
    levels = {}
    for sid in targets.location_id.unique():
        station = past.loc[past.location_id.eq(sid)].sort_values("target_start")
        if station.empty:
            raise ValueError(f"No eligible PM history for station {sid}")
        values = station.pm25.to_numpy(dtype=float)
        if not np.isfinite(values).all() or (values < 0).any():
            raise ValueError("Eligible history must be finite and nonnegative")
        level = float(values[-1])
        for hours in (72, 168):
            window = station.loc[station.target_start.ge(cutoff-pd.Timedelta(hours=hours)), "pm25"]
            if not window.empty:
                level = float(window.median())
                break
        levels[sid] = level
    return targets.location_id.map(levels).to_numpy(dtype=float)


def branch_c(train: pd.DataFrame, targets: pd.DataFrame, seasonal: np.ndarray,
             cutoff: pd.Timestamp) -> np.ndarray:
    if np.shape(seasonal) != (len(targets),) or np.isinf(seasonal).any():
        raise ValueError("Need one finite-or-missing seasonal value per target")
    level = branch_recent(train, targets, cutoff)
    prediction = .5*level + .5*np.where(np.isfinite(seasonal), seasonal, level)
    if not np.isfinite(prediction).all() or (prediction < 0).any():
        raise ValueError("Candidate C produced invalid predictions")
    return prediction
