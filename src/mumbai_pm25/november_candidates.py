"""Small deterministic EXP-012 history-only candidate calculations."""
from __future__ import annotations

import numpy as np
import pandas as pd


def recent_median(history: pd.Series, cutoff: pd.Timestamp, hours: int) -> float | None:
    """Median of eligible elapsed-hour observations, falling back to all eligible history."""
    if cutoff.tz is None or history.index.tz is None:
        raise ValueError("History and cutoff must be timezone-aware")
    if hours < 1:
        raise ValueError("hours must be positive")
    eligible = history.loc[history.index < cutoff].dropna()
    if eligible.empty:
        return None
    window = eligible.loc[eligible.index >= cutoff - pd.Timedelta(hours=hours)]
    value = window.median() if not window.empty else eligible.median()
    if not np.isfinite(value) or value < 0:
        raise ValueError("Recent PM median must be finite and non-negative")
    return float(value)


def bounded_trend48(history: pd.Series, cutoff: pd.Timestamp,
                    targets: pd.DatetimeIndex, *, strength: float = 0.25,
                    max_change: float = 20.0, decay_hours: float = 72.0) -> np.ndarray:
    """Recent 48h level plus a bounded earlier-window trend decaying with lead."""
    if not 0 <= strength <= 1 or max_change < 0 or decay_hours <= 0:
        raise ValueError("Invalid trend parameters")
    recent = recent_median(history, cutoff, 48)
    if recent is None:
        raise ValueError("No eligible station PM history")
    earlier = history.loc[(history.index >= cutoff - pd.Timedelta(hours=96)) &
                          (history.index < cutoff - pd.Timedelta(hours=48))].dropna()
    delta = np.clip(recent - float(earlier.median()), -max_change, max_change) if not earlier.empty else 0.0
    lead_hours = (targets - cutoff).total_seconds() / 3600
    if (lead_hours < 0).any():
        raise ValueError("Targets must not precede PM cutoff")
    return np.maximum(0.0, recent + strength * delta * np.exp(-lead_hours / decay_hours))
