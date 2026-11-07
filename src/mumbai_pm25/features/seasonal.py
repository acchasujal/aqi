"""Historical 2024 seasonal feature extraction (Group D)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from mumbai_pm25.historical_archive import build_seasonal_features


def extract_seasonal_features(
    history_2024: pd.DataFrame | None,
    target_df: pd.DataFrame,
    recent_medians: dict[int, float] | None = None,
) -> pd.DataFrame:
    """Extract 2024 seasonal climatological features for target DataFrame rows.

    Parameters
    ----------
    history_2024:
        Cleaned 2024 archive DataFrame (from load_2024_history).
    target_df:
        DataFrame with columns 'location_id' and 'target_start'.
    recent_medians:
        Optional mapping of location_id -> recent median72 for computing ratio features.

    Returns
    -------
    DataFrame with columns:
        hist24_same_hour_mean
        hist24_month_hour_mean
        hist24_coverage
        hist24_has_prior
        hist24_ratio_to_recent
    """
    if history_2024 is None or history_2024.empty:
        df = pd.DataFrame({
            "hist24_same_hour_mean": np.full(len(target_df), np.nan),
            "hist24_month_hour_mean": np.full(len(target_df), np.nan),
            "hist24_coverage": np.zeros(len(target_df), dtype=float),
            "hist24_has_prior": np.zeros(len(target_df), dtype=float),
            "hist24_ratio_to_recent": np.ones(len(target_df), dtype=float),
        }, index=target_df.index)
        return df

    seasonal = build_seasonal_features(history_2024, target_df)
    sh_mean = seasonal["hist24_same_hour_mean"].to_numpy(dtype=float)
    has_prior = np.isfinite(sh_mean).astype(float)

    # Ratio to recent median
    if recent_medians is not None:
        rec_vals = np.array([recent_medians.get(int(loc), 40.0) for loc in target_df["location_id"]], dtype=float)
        ratio = np.where(np.isfinite(sh_mean), sh_mean / (rec_vals + 1.0), 1.0)
    else:
        ratio = np.ones(len(target_df), dtype=float)

    seasonal["hist24_has_prior"] = has_prior
    seasonal["hist24_ratio_to_recent"] = ratio
    return seasonal
