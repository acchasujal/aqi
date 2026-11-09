"""Explicit station-specific PM cutoff and forecast-lead calculations."""
from __future__ import annotations

import pandas as pd


def station_last_pm_end(train: pd.DataFrame, cutoff: pd.Timestamp) -> pd.Series:
    """Last observed PM interval end per station available by cutoff."""
    if cutoff.tz is None:
        raise ValueError("PM cutoff must be timezone-aware")
    ends = train.target_start + pd.Timedelta(hours=1)
    eligible = train.loc[(ends <= cutoff) & train.pm25.notna()]
    if eligible.empty:
        return pd.Series(dtype="datetime64[ns, Asia/Kolkata]")
    return eligible.groupby("location_id").target_start.max() + pd.Timedelta(hours=1)


def target_leads(targets: pd.DataFrame, station_ends: pd.Series) -> pd.DataFrame:
    """Attach latest eligible station PM end and elapsed lead to target rows."""
    if not targets.target_start.dt.tz:
        raise ValueError("Target timestamps must be timezone-aware")
    out = targets.copy()
    out["last_pm_end"] = out.location_id.map(station_ends)
    if out.last_pm_end.isna().any():
        raise ValueError("A target station lacks eligible PM history")
    out["forecast_lead_hours"] = (out.target_start - out.last_pm_end).dt.total_seconds() / 3600
    return out


def target_window(test: pd.DataFrame, start: pd.Timestamp, hours: int = 48) -> pd.DataFrame:
    """Select a fixed target interval by explicit IST hour starts."""
    if start.tz is None or hours < 1:
        raise ValueError("Require timezone-aware start and positive hours")
    end = start + pd.Timedelta(hours=hours)
    return test.loc[(test.target_start >= start) & (test.target_start < end)].copy()
