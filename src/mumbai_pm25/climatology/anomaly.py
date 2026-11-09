"""Recent anomaly extraction relative to kernel climatology."""
from __future__ import annotations

import numpy as np
import pandas as pd

from mumbai_pm25.climatology.kernel import KernelClimatology


def extract_recent_anomalies(
    station_history: pd.DataFrame,
    origin: pd.Timestamp,
    climatology_estimator: KernelClimatology,
    window_hours: int = 168,
) -> dict[str, float]:
    """Calculate multi-scale recent anomalies strictly prior to forecast origin.

    Parameters:
        station_history: DataFrame with columns ['timestamp', 'pm25'] sorted by timestamp.
        origin: Forecast issuance origin timestamp.
        climatology_estimator: Pre-configured KernelClimatology.
        window_hours: Maximum lookback window (default 168h = 7 days).

    Returns:
        Dict of anomaly features:
            a24, a72, a168, count_24, count_72, count_168, coverage_168, std_168, staleness_hours
    """
    # 1. Filter observations strictly at or before origin
    hist = station_history.loc[station_history["timestamp"] <= origin].copy()
    if hist.empty:
        return {
            "a24": 0.0,
            "a72": 0.0,
            "a168": 0.0,
            "count_24": 0,
            "count_72": 0,
            "count_168": 0,
            "coverage_168": 0.0,
            "std_168": 0.0,
            "staleness_hours": float(window_hours),
        }

    latest_ts = hist["timestamp"].iloc[-1]
    staleness_hours = max(0.0, (origin - latest_ts).total_seconds() / 3600.0)

    # 2. Lookback window
    window_start = origin - pd.Timedelta(hours=window_hours)
    w_df = hist.loc[hist["timestamp"] >= window_start].copy()
    if w_df.empty:
        return {
            "a24": 0.0,
            "a72": 0.0,
            "a168": 0.0,
            "count_24": 0,
            "count_72": 0,
            "count_168": 0,
            "coverage_168": 0.0,
            "std_168": 0.0,
            "staleness_hours": staleness_hours,
        }

    # 3. Calculate climatology for each observation in the lookback window
    eligible_clim = climatology_estimator._extract_eligible_history(station_history, origin)
    clim_results = climatology_estimator.estimate_batch(eligible_clim, list(w_df["timestamp"]))
    w_df["clim"] = [r["clim_prediction"] for r in clim_results]
    w_df["anomaly"] = w_df["pm25"] - w_df["clim"]

    # 4. Aggregate anomalies across windows
    t24 = origin - pd.Timedelta(hours=24)
    t72 = origin - pd.Timedelta(hours=72)

    w24 = w_df.loc[w_df["timestamp"] >= t24, "anomaly"].dropna()
    w72 = w_df.loc[w_df["timestamp"] >= t72, "anomaly"].dropna()
    w168 = w_df["anomaly"].dropna()

    a24 = float(w24.mean()) if len(w24) > 0 else 0.0
    a72 = float(w72.mean()) if len(w72) > 0 else (a24 if len(w24) > 0 else 0.0)
    a168 = float(w168.mean()) if len(w168) > 0 else (a72 if len(w72) > 0 else 0.0)

    std_168 = float(w_df["pm25"].std()) if len(w_df) > 1 else 0.0
    if not np.isfinite(std_168):
        std_168 = 0.0

    return {
        "a24": a24,
        "a72": a72,
        "a168": a168,
        "count_24": len(w24),
        "count_72": len(w72),
        "count_168": len(w168),
        "coverage_168": min(1.0, len(w168) / float(window_hours)),
        "std_168": std_168,
        "staleness_hours": staleness_hours,
    }
