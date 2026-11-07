"""Recent PM2.5 history and pollution dynamics feature engineering (Groups A & B)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def extract_station_pm_features(
    station_history: pd.Series,
    cutoff: pd.Timestamp,
) -> dict[str, float]:
    """Compute Group A and Group B features strictly prior to cutoff."""
    if cutoff.tz is None:
        raise ValueError("cutoff must be timezone-aware")

    # Filter strictly prior to cutoff
    valid = station_history.loc[station_history.index < cutoff].dropna()
    if valid.empty:
        # Default fallback values
        return {
            "latest_pm25": 40.0,
            "obs_age_hours": 999.0,
            "obs_count_24": 0.0,
            "obs_count_72": 0.0,
            "obs_count_168": 0.0,
            "coverage_72": 0.0,
            "median_6": 40.0,
            "median_12": 40.0,
            "median_24": 40.0,
            "median_48": 40.0,
            "median_72": 40.0,
            "median_168": 40.0,
            "mean_24": 40.0,
            "mean_72": 40.0,
            "mean_168": 40.0,
            "min_24": 40.0,
            "max_24": 40.0,
            "std_24": 0.0,
            "iqr_72": 0.0,
            "ewm_24": 40.0,
            "ewm_72": 40.0,
            "delta_median_24_48": 0.0,
            "ratio_median_24_168": 1.0,
            "volatility_24": 0.0,
            "is_rising_trend": 0.0,
            "linear_slope_24": 0.0,
        }

    latest_time = valid.index[-1]
    latest_end = latest_time + pd.Timedelta(hours=1)
    obs_age_hours = max(0.0, (cutoff - latest_end).total_seconds() / 3600.0)
    latest_val = float(valid.iloc[-1])

    # Windows relative to cutoff
    w6 = valid.loc[valid.index >= cutoff - pd.Timedelta(hours=6)]
    w12 = valid.loc[valid.index >= cutoff - pd.Timedelta(hours=12)]
    w24 = valid.loc[valid.index >= cutoff - pd.Timedelta(hours=24)]
    w48 = valid.loc[valid.index >= cutoff - pd.Timedelta(hours=48)]
    w72 = valid.loc[valid.index >= cutoff - pd.Timedelta(hours=72)]
    w168 = valid.loc[valid.index >= cutoff - pd.Timedelta(hours=168)]
    w24_48 = valid.loc[
        (valid.index < cutoff - pd.Timedelta(hours=24))
        & (valid.index >= cutoff - pd.Timedelta(hours=48))
    ]

    m6 = float(w6.median()) if not w6.empty else latest_val
    m12 = float(w12.median()) if not w12.empty else latest_val
    m24 = float(w24.median()) if not w24.empty else latest_val
    m48 = float(w48.median()) if not w48.empty else latest_val
    m72 = float(w72.median()) if not w72.empty else latest_val
    m168 = float(w168.median()) if not w168.empty else latest_val

    mean24 = float(w24.mean()) if not w24.empty else latest_val
    mean72 = float(w72.mean()) if not w72.empty else latest_val
    mean168 = float(w168.mean()) if not w168.empty else latest_val

    min24 = float(w24.min()) if not w24.empty else latest_val
    max24 = float(w24.max()) if not w24.empty else latest_val
    std24 = float(w24.std()) if len(w24) > 1 else 0.0

    if not w72.empty:
        q75, q25 = np.percentile(w72.to_numpy(dtype=float), [75, 25])
        iqr72 = float(q75 - q25)
    else:
        iqr72 = 0.0

    # Exponentially weighted averages
    if not w24.empty:
        ages24 = (cutoff - w24.index).total_seconds() / 3600.0
        weights24 = np.exp2(-ages24 / 12.0)
        ewm24 = float(np.average(w24.to_numpy(dtype=float), weights=weights24))
    else:
        ewm24 = latest_val

    if not w72.empty:
        ages72 = (cutoff - w72.index).total_seconds() / 3600.0
        weights72 = np.exp2(-ages72 / 24.0)
        ewm72 = float(np.average(w72.to_numpy(dtype=float), weights=weights72))
    else:
        ewm72 = latest_val

    # Dynamics
    m24_prev = float(w24_48.median()) if not w24_48.empty else m24
    delta_median_24_48 = float(m24 - m24_prev)
    ratio_median_24_168 = float(m24 / (m168 + 1.0))
    volatility_24 = float(std24 / (mean24 + 1.0))
    is_rising_trend = 1.0 if m24 > m72 else 0.0

    # Linear slope over recent 24h
    if len(w24) >= 3:
        x = (w24.index - w24.index[0]).total_seconds() / 3600.0
        y = w24.to_numpy(dtype=float)
        # Least squares slope: cov(x, y) / var(x)
        var_x = np.var(x)
        if var_x > 1e-4:
            linear_slope_24 = float(np.cov(x, y)[0, 1] / var_x)
        else:
            linear_slope_24 = 0.0
    else:
        linear_slope_24 = 0.0

    return {
        "latest_pm25": latest_val,
        "obs_age_hours": obs_age_hours,
        "obs_count_24": float(len(w24)),
        "obs_count_72": float(len(w72)),
        "obs_count_168": float(len(w168)),
        "coverage_72": float(min(1.0, len(w72) / 72.0)),
        "median_6": m6,
        "median_12": m12,
        "median_24": m24,
        "median_48": m48,
        "median_72": m72,
        "median_168": m168,
        "mean_24": mean24,
        "mean_72": mean72,
        "mean_168": mean168,
        "min_24": min24,
        "max_24": max24,
        "std_24": std24,
        "iqr_72": iqr72,
        "ewm_24": ewm24,
        "ewm_72": ewm72,
        "delta_median_24_48": delta_median_24_48,
        "ratio_median_24_168": ratio_median_24_168,
        "volatility_24": volatility_24,
        "is_rising_trend": is_rising_trend,
        "linear_slope_24": linear_slope_24,
    }


def build_pm_history_features(
    station_histories: dict[int, pd.Series],
    target_df: pd.DataFrame,
    cutoff: pd.Timestamp,
) -> pd.DataFrame:
    """Compute Group A and B features for all rows in target_df using a frozen cutoff."""
    # Pre-compute features for each unique station in target_df
    station_feats: dict[int, dict[str, float]] = {}
    for sid in target_df["location_id"].unique():
        s_hist = station_histories.get(int(sid))
        if s_hist is not None:
            station_feats[int(sid)] = extract_station_pm_features(s_hist, cutoff)
        else:
            station_feats[int(sid)] = extract_station_pm_features(pd.Series(dtype=float), cutoff)

    # Map features to target_df rows
    rows: list[dict[str, float]] = [
        station_feats[int(loc)] for loc in target_df["location_id"]
    ]

    return pd.DataFrame(rows, index=target_df.index)
