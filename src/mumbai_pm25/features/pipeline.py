"""Unified feature engineering pipeline for Mumbai PM2.5 forecasting."""
from __future__ import annotations

import pandas as pd

from mumbai_pm25.features.calendar import build_calendar_features
from mumbai_pm25.features.pm_history import build_pm_history_features
from mumbai_pm25.features.seasonal import extract_seasonal_features
from mumbai_pm25.features.spatial import extract_citywide_spatial_features


class FeaturePipeline:
    """Orchestrates leak-free feature extraction from frozen historical snapshots."""

    def __init__(
        self,
        *,
        history_2024: pd.DataFrame | None = None,
        include_seasonal: bool = True,
        include_spatial: bool = True,
    ) -> None:
        self.history_2024 = history_2024
        self.include_seasonal = include_seasonal
        self.include_spatial = include_spatial

    def transform(
        self,
        station_histories: dict[int, pd.Series],
        target_df: pd.DataFrame,
        cutoff: pd.Timestamp,
    ) -> pd.DataFrame:
        """Construct full tabular feature matrix for target_df given frozen cutoff."""
        if cutoff.tz is None:
            raise ValueError("cutoff must be timezone-aware")

        # 1. Temporal & Calendar features (Group C)
        horizon = target_df.get("horizon_hours", None)
        f_cal = build_calendar_features(
            target_df["target_start"],
            target_df["location_id"],
            horizon_hours=horizon,
        )

        # 2. PM History Levels & Dynamics (Groups A & B)
        f_pm = build_pm_history_features(
            station_histories,
            target_df,
            cutoff,
        )

        parts = [f_cal, f_pm]

        # 3. Seasonal Climatology (Group D)
        if self.include_seasonal and self.history_2024 is not None:
            recent_meds = {sid: f_pm.loc[target_df["location_id"] == sid, "median_72"].iloc[0]
                           for sid in target_df["location_id"].unique()
                           if not f_pm.loc[target_df["location_id"] == sid].empty}
            f_seas = extract_seasonal_features(
                self.history_2024,
                target_df,
                recent_medians=recent_meds,
            )
            parts.append(f_seas)

        # 4. Spatial & Citywide Context (Group E)
        if self.include_spatial:
            f_spat = extract_citywide_spatial_features(
                station_histories,
                target_df,
                cutoff,
            )
            parts.append(f_spat)

        return pd.concat(parts, axis=1)


def build_feature_matrix(
    station_histories: dict[int, pd.Series],
    target_df: pd.DataFrame,
    cutoff: pd.Timestamp,
    *,
    history_2024: pd.DataFrame | None = None,
    include_seasonal: bool = True,
    include_spatial: bool = True,
) -> pd.DataFrame:
    """Convenience functional interface for feature matrix generation."""
    pipeline = FeaturePipeline(
        history_2024=history_2024,
        include_seasonal=include_seasonal,
        include_spatial=include_spatial,
    )
    return pipeline.transform(station_histories, target_df, cutoff)
