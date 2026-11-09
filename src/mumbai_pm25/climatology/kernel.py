"""Kernel climatology estimator for hourly PM2.5 forecasting.

Implements Model A from the Climatology-First Architecture:
  - Gaussian kernel smoothing over circular day-of-year and circular hour-of-day.
  - Strict causality: observations strictly prior to (origin - clim_gap_days).
  - Normalised calendar phase matching leap years (2024) to common years (2025, 2026).
  - Diagnostic outputs: prediction, weight sum, observation count, unique day count.
  - Configurable fallback when local seasonal evidence is sparse.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Literal

import numpy as np
import pandas as pd


def normalized_doy(ts: pd.Timestamp) -> float:
    """Normalize day-of-year to a 365-day circular phase across leap and non-leap years.

    In leap years (e.g. 2024):
      - Jan 1 - Feb 28: DOY 1 - 59
      - Feb 29: 59.5 (or midpoint)
      - March 1 - Dec 31: DOY 60 - 365 (shifted by -1)
    In common years (2025, 2026):
      - Jan 1 - Dec 31: DOY 1 - 365
    """
    d = ts.day_of_year
    if ts.is_leap_year:
        if ts.month == 2 and ts.day == 29:
            return 59.5
        elif ts.month > 2:
            return float(d - 1)
    return float(d)


def circular_doy_distance(d1: float | np.ndarray, d2: float | np.ndarray) -> float | np.ndarray:
    """Shortest distance in days between two day-of-year values on a circular 365-day year."""
    diff = np.abs(d1 - d2)
    return np.minimum(diff, 365.0 - diff)


def circular_hour_distance(h1: float | np.ndarray, h2: float | np.ndarray) -> float | np.ndarray:
    """Shortest distance in hours between two hours of the day on a circular 24-hour clock."""
    diff = np.abs(h1 - h2)
    return np.minimum(diff, 24.0 - diff)


class KernelClimatology:
    """Gaussian kernel climatology model for hourly station PM2.5."""

    def __init__(
        self,
        sigma_doy: float = 10.0,
        sigma_hour: float = 1.0,
        clim_gap_days: int = 14,
        min_weight: float = 5.0,
        source_mode: Literal["p_fix", "equal_weight", "timestamp_median", "timestamp_mean", "train_only"] = "p_fix",
    ) -> None:
        if sigma_doy <= 0:
            raise ValueError(f"sigma_doy must be positive, got {sigma_doy}")
        if sigma_hour <= 0:
            raise ValueError(f"sigma_hour must be positive, got {sigma_hour}")
        if clim_gap_days < 0:
            raise ValueError(f"clim_gap_days must be non-negative, got {clim_gap_days}")
        if min_weight <= 0:
            raise ValueError(f"min_weight must be positive, got {min_weight}")

        self.sigma_doy = float(sigma_doy)
        self.sigma_hour = float(sigma_hour)
        self.clim_gap_days = int(clim_gap_days)
        self.min_weight = float(min_weight)
        self.source_mode = source_mode

    def _extract_eligible_history(
        self,
        station_history: pd.DataFrame,
        origin: pd.Timestamp,
    ) -> pd.DataFrame:
        """Filter historical observations strictly prior to (origin - clim_gap_days)."""
        cutoff = origin - pd.Timedelta(days=self.clim_gap_days)
        eligible = station_history.loc[station_history["timestamp"] <= cutoff].copy()
        if eligible.empty:
            return eligible

        # Precompute circular calendar coordinates
        if "doy_norm" not in eligible.columns:
            eligible["doy_norm"] = eligible["timestamp"].apply(normalized_doy)
        if "hour" not in eligible.columns:
            eligible["hour"] = eligible["timestamp"].dt.hour
        return eligible

    def estimate(
        self,
        eligible_history: pd.DataFrame,
        target_timestamp: pd.Timestamp,
    ) -> dict[str, Any]:
        """Estimate kernel climatology for a single target timestamp given eligible history."""
        if eligible_history.empty:
            return {
                "clim_prediction": np.nan,
                "clim_weight_sum": 0.0,
                "clim_observation_count": 0,
                "clim_unique_day_count": 0,
                "clim_source_type": "none",
                "clim_source_coverage": 0.0,
            }

        target_doy = normalized_doy(target_timestamp)
        target_hour = target_timestamp.hour

        hist_doy = eligible_history["doy_norm"].values
        hist_hour = eligible_history["hour"].values
        hist_val = eligible_history["pm25"].values

        dd = circular_doy_distance(hist_doy, target_doy)
        dh = circular_hour_distance(hist_hour, target_hour)

        # Vectorized Gaussian kernel computation
        w_doy = np.exp(-0.5 * (dd / self.sigma_doy) ** 2)
        w_hour = np.exp(-0.5 * (dh / self.sigma_hour) ** 2)
        weights = w_doy * w_hour

        weight_sum = float(np.sum(weights))
        active_mask = weights > 1e-4
        obs_count = int(np.sum(active_mask))
        unique_days = int(eligible_history.loc[active_mask, "timestamp"].dt.date.nunique()) if obs_count > 0 else 0

        # Primary estimation
        if weight_sum >= self.min_weight:
            clim_pred = float(np.sum(weights * hist_val) / weight_sum)
            source_type = "seasonal_kernel"
        else:
            # Fallback to hour-of-day kernel across all available history
            w_fallback = w_hour
            fallback_weight_sum = float(np.sum(w_fallback))
            if fallback_weight_sum > 0:
                clim_pred = float(np.sum(w_fallback * hist_val) / fallback_weight_sum)
                source_type = "hour_fallback"
            else:
                clim_pred = float(np.median(hist_val))
                source_type = "median_fallback"

        return {
            "clim_prediction": max(0.0, clim_pred),
            "clim_weight_sum": weight_sum,
            "clim_observation_count": obs_count,
            "clim_unique_day_count": unique_days,
            "clim_source_type": source_type,
            "clim_source_coverage": min(1.0, weight_sum / (self.min_weight * 2.0)),
        }

    def estimate_batch(
        self,
        eligible_history: pd.DataFrame,
        target_timestamps: Sequence[pd.Timestamp] | pd.DatetimeIndex | list[pd.Timestamp],
        compute_diagnostics: bool = False,
    ) -> list[dict[str, Any]]:
        """Vectorized estimation of climatology for multiple target timestamps."""
        if eligible_history.empty or len(target_timestamps) == 0:
            return [
                {
                    "clim_prediction": np.nan,
                    "clim_weight_sum": 0.0,
                    "clim_observation_count": 0,
                    "clim_unique_day_count": 0,
                    "clim_source_type": "none",
                    "clim_source_coverage": 0.0,
                }
                for _ in target_timestamps
            ]

        t_list = list(target_timestamps)
        t_doy = np.array([normalized_doy(ts) for ts in t_list], dtype=float)[:, None]
        t_hour = np.array([ts.hour for ts in t_list], dtype=float)[:, None]

        h_doy = eligible_history["doy_norm"].values[None, :]
        h_hour = eligible_history["hour"].values[None, :]
        h_val = eligible_history["pm25"].values

        dd = circular_doy_distance(h_doy, t_doy)
        dh = circular_hour_distance(h_hour, t_hour)

        w_doy = np.exp(-0.5 * (dd / self.sigma_doy) ** 2)
        w_hour = np.exp(-0.5 * (dh / self.sigma_hour) ** 2)
        weights = w_doy * w_hour

        weight_sums = weights.sum(axis=1)
        raw_preds = (weights @ h_val) / np.maximum(weight_sums, 1e-9)

        dates_arr = eligible_history["timestamp"].dt.date.values if compute_diagnostics else None

        results = []
        for i in range(len(t_list)):
            w_sum = float(weight_sums[i])
            if w_sum >= self.min_weight:
                clim_pred = float(raw_preds[i])
                source_type = "seasonal_kernel"
            else:
                w_fallback = w_hour[i]
                fb_sum = float(np.sum(w_fallback))
                if fb_sum > 0:
                    clim_pred = float(np.sum(w_fallback * h_val) / fb_sum)
                    source_type = "hour_fallback"
                else:
                    clim_pred = float(np.median(h_val))
                    source_type = "median_fallback"

            if compute_diagnostics and dates_arr is not None:
                act_mask = weights[i] > 1e-4
                obs_cnt = int(np.sum(act_mask))
                unique_days = len(set(dates_arr[act_mask])) if obs_cnt > 0 else 0
            else:
                obs_cnt = 0
                unique_days = 0

            results.append({
                "clim_prediction": max(0.0, clim_pred),
                "clim_weight_sum": w_sum,
                "clim_observation_count": obs_cnt,
                "clim_unique_day_count": unique_days,
                "clim_source_type": source_type,
                "clim_source_coverage": min(1.0, w_sum / (self.min_weight * 2.0)),
            })
        return results

    def predict_target_window(
        self,
        station_history: pd.DataFrame,
        origin: pd.Timestamp,
        target_timestamps: pd.Series | list[pd.Timestamp] | pd.DatetimeIndex,
    ) -> pd.DataFrame:
        """Vectorized/batched prediction of climatology over a list of target timestamps."""
        eligible = self._extract_eligible_history(station_history, origin)
        results = self.estimate_batch(eligible, list(target_timestamps))
        for res, ts in zip(results, target_timestamps):
            res["target_timestamp"] = ts
        return pd.DataFrame(results)
