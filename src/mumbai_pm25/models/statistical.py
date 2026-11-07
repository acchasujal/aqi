"""Statistical forecasting baselines module for Mumbai PM2.5 forecasting.

Implements robust, timestamp-indexed statistical forecasting methods:
 1. last: Last valid observation
 2. median24: 24-hour rolling median
 3. median72: 72-hour rolling median (inference control)
 4. median168: 168-hour (7-day) rolling median
 5. mean24: 24-hour rolling mean
 6. mean72: 72-hour rolling mean
 7. mean168: 168-hour rolling mean
 8. ewm72: 72-hour exponentially weighted moving average (half-life = 24h)
 9. diurnal7: Station-specific hour-of-day profile (last 7 days)
10. hour_week4: Station-specific hour-of-week profile (last 28 days)
11. seasonal_2024: 2024 seasonal climatology (leap-year aligned)
12. seasonal_blend50_median72: 50:50 blend of 2024 seasonal and median72
13. trend_adjusted_median: Trend-adjusted recent median (M24 + 0.5 * slope(M24 - M72))

All temporal windows are timestamp-based. Missing observations remain NaN and
are never treated as zeros. Full history metadata (observation count, age,
coverage ratio) is returned alongside statistical features.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class HistoryStats:
    """Diagnostic statistics for a station's recent PM history."""
    obs_count: int
    latest_obs: float | None
    latest_obs_time: pd.Timestamp | None
    age_hours: float | None
    coverage_ratio: float
    mean: float | None
    median: float | None
    std: float | None
    min: float | None
    max: float | None


def compute_station_history_stats(
    station_history: pd.Series,
    cutoff: pd.Timestamp,
    *,
    window_hours: int = 72,
) -> HistoryStats:
    """Calculate explicit history diagnostics strictly prior to cutoff."""
    if cutoff.tz is None:
        raise ValueError("cutoff must be timezone-aware")

    # Observations whose target_start < cutoff
    valid = station_history.loc[station_history.index < cutoff].dropna()
    if valid.empty:
        return HistoryStats(
            obs_count=0,
            latest_obs=None,
            latest_obs_time=None,
            age_hours=None,
            coverage_ratio=0.0,
            mean=None,
            median=None,
            std=None,
            min=None,
            max=None,
        )

    last_time = valid.index[-1]
    # Interval end of last observation is start + 1h
    last_end = last_time + pd.Timedelta(hours=1)
    age_hours = max(0.0, (cutoff - last_end).total_seconds() / 3600.0)
    latest_val = float(valid.iloc[-1])

    window_start = cutoff - pd.Timedelta(hours=window_hours)
    in_window = valid.loc[valid.index >= window_start]
    count = len(in_window)
    coverage = min(1.0, count / max(1, window_hours))

    if count > 0:
        vals = in_window.to_numpy(dtype=float)
        mean_val = float(np.mean(vals))
        median_val = float(np.median(vals))
        std_val = float(np.std(vals)) if count > 1 else 0.0
        min_val = float(np.min(vals))
        max_val = float(np.max(vals))
    else:
        # Fall back to latest available value
        mean_val = latest_val
        median_val = latest_val
        std_val = None
        min_val = latest_val
        max_val = latest_val

    return HistoryStats(
        obs_count=count,
        latest_obs=latest_val,
        latest_obs_time=last_time,
        age_hours=age_hours,
        coverage_ratio=coverage,
        mean=mean_val,
        median=median_val,
        std=std_val,
        min=min_val,
        max=max_val,
    )


class StatisticalForecaster:
    """Standardized forecasting interface for all statistical baseline methods."""

    def __init__(
        self,
        method: str = "median72",
        *,
        history_2024: pd.DataFrame | None = None,
        seasonal_weight: float = 0.5,
    ) -> None:
        self.method = method
        self.history_2024 = history_2024
        self.seasonal_weight = seasonal_weight
        self.station_histories_: dict[int, pd.Series] = {}

    def fit(self, train: pd.DataFrame, **kwargs: Any) -> StatisticalForecaster:
        """Store station history timelines indexed by target_start."""
        grid = train.set_index(["location_id", "target_start"])[["pm25"]].sort_index()
        self.station_histories_ = {
            int(sid): grid.xs(sid, level="location_id")["pm25"]
            for sid in train["location_id"].unique()
        }
        return self

    def predict_station_block(
        self,
        station_id: int,
        target_hours: pd.DatetimeIndex,
        pm_history_cutoff: pd.Timestamp,
    ) -> np.ndarray:
        """Forecast a block of future target hours for a single station."""
        history = self.station_histories_.get(station_id)
        if history is None or history.empty:
            return np.full(len(target_hours), np.nan)

        # Labels strictly prior to PM cutoff
        eligible = history.loc[history.index < pm_history_cutoff].dropna()
        if eligible.empty:
            return np.full(len(target_hours), np.nan)

        latest_val = float(eligible.iloc[-1])

        if self.method == "last":
            return np.full(len(target_hours), max(0.0, latest_val))

        if self.method in {"median24", "median72", "median168"}:
            w_hours = int(self.method.replace("median", ""))
            window = eligible.loc[eligible.index >= pm_history_cutoff - pd.Timedelta(hours=w_hours)]
            val = float(window.median()) if not window.empty else latest_val
            return np.full(len(target_hours), max(0.0, val))

        if self.method in {"mean24", "mean72", "mean168"}:
            w_hours = int(self.method.replace("mean", ""))
            window = eligible.loc[eligible.index >= pm_history_cutoff - pd.Timedelta(hours=w_hours)]
            val = float(window.mean()) if not window.empty else latest_val
            return np.full(len(target_hours), max(0.0, val))

        if self.method == "ewm72":
            window = eligible.loc[eligible.index >= pm_history_cutoff - pd.Timedelta(hours=72)]
            if window.empty:
                val = latest_val
            else:
                age_hours = (pm_history_cutoff - window.index).total_seconds() / 3600.0
                weights = np.exp2(-age_hours / 24.0)
                val = float(np.average(window.to_numpy(dtype=float), weights=weights))
            return np.full(len(target_hours), max(0.0, val))

        if self.method == "diurnal7":
            window = eligible.loc[eligible.index >= pm_history_cutoff - pd.Timedelta(hours=168)]
            if window.empty:
                return np.full(len(target_hours), max(0.0, latest_val))
            profile = window.groupby(window.index.hour).median()
            fallback = float(window.median())
            preds = np.array([profile.get(t.hour, fallback) for t in target_hours], dtype=float)
            return np.maximum(0.0, np.where(np.isfinite(preds), preds, fallback))

        if self.method == "hour_week4":
            window = eligible.loc[eligible.index >= pm_history_cutoff - pd.Timedelta(hours=672)]
            if window.empty:
                return np.full(len(target_hours), max(0.0, latest_val))
            profile = window.groupby([window.index.day_of_week, window.index.hour]).median()
            fallback = float(window.median())
            preds = np.array([profile.get((t.day_of_week, t.hour), fallback) for t in target_hours], dtype=float)
            return np.maximum(0.0, np.where(np.isfinite(preds), preds, fallback))

        if self.method == "trend_adjusted_median":
            # Compare median24 vs median72 to capture recent direction of change
            w24 = eligible.loc[eligible.index >= pm_history_cutoff - pd.Timedelta(hours=24)]
            w72 = eligible.loc[eligible.index >= pm_history_cutoff - pd.Timedelta(hours=72)]
            m24 = float(w24.median()) if not w24.empty else latest_val
            m72 = float(w72.median()) if not w72.empty else latest_val
            # Damped trend delta: 0.3 * (m24 - m72), capped to [-25, 25] to prevent runaway
            trend_delta = np.clip(0.3 * (m24 - m72), -25.0, 25.0)
            val = max(0.0, m24 + trend_delta)
            return np.full(len(target_hours), val)

        if self.method in {"seasonal_2024", "seasonal_blend50_median72"}:
            if self.history_2024 is None or self.history_2024.empty:
                # Fall back to median72
                w72 = eligible.loc[eligible.index >= pm_history_cutoff - pd.Timedelta(hours=72)]
                val = float(w72.median()) if not w72.empty else latest_val
                return np.full(len(target_hours), max(0.0, val))

            from mumbai_pm25.historical_archive import build_seasonal_features

            target_df = pd.DataFrame({
                "location_id": [station_id] * len(target_hours),
                "target_start": target_hours,
            })
            seasonal = build_seasonal_features(self.history_2024, target_df)
            s_vals = seasonal["hist24_same_hour_mean"].to_numpy(dtype=float)

            w72 = eligible.loc[eligible.index >= pm_history_cutoff - pd.Timedelta(hours=72)]
            m72 = float(w72.median()) if not w72.empty else latest_val

            if self.method == "seasonal_2024":
                preds = np.where(np.isfinite(s_vals), s_vals, m72)
            else:
                # Blend with seasonal_weight (default 0.5)
                w_s = self.seasonal_weight
                blended = np.where(
                    np.isfinite(s_vals),
                    (1.0 - w_s) * m72 + w_s * s_vals,
                    m72,
                )
                preds = blended
            return np.maximum(0.0, preds)

        raise ValueError(f"Unknown statistical forecasting method: {self.method}")
