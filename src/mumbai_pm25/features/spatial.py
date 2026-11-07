"""Cross-station spatial feature engineering (Group E)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def extract_citywide_spatial_features(
    station_histories: dict[int, pd.Series],
    target_df: pd.DataFrame,
    cutoff: pd.Timestamp,
) -> pd.DataFrame:
    """Compute citywide cross-station spatial features strictly prior to cutoff.

    Parameters
    ----------
    station_histories:
        Mapping of location_id -> historical PM2.5 Series.
    target_df:
        DataFrame with 'location_id' column.
    cutoff:
        Frozen PM history cutoff timestamp.

    Returns
    -------
    DataFrame with columns:
        city_median_pm25
        city_mean_pm25
        city_std_pm25
        city_dispersion
        station_diff_from_city
        station_ratio_to_city
        other_stations_mean_pm25
    """
    station_latest: dict[int, float] = {}
    station_ages: dict[int, float] = {}

    for sid, series in station_histories.items():
        valid = series.loc[series.index < cutoff].dropna()
        if not valid.empty:
            station_latest[sid] = float(valid.iloc[-1])
            last_end = valid.index[-1] + pd.Timedelta(hours=1)
            station_ages[sid] = max(0.0, (cutoff - last_end).total_seconds() / 3600.0)
        else:
            station_latest[sid] = 40.0
            station_ages[sid] = 999.0

    all_vals = list(station_latest.values())
    city_med = float(np.median(all_vals)) if all_vals else 40.0
    city_mean = float(np.mean(all_vals)) if all_vals else 40.0
    city_std = float(np.std(all_vals)) if len(all_vals) > 1 else 0.0
    city_disp = float(city_std / (city_mean + 1.0))

    rows: list[dict[str, float]] = []
    for loc in target_df["location_id"]:
        loc_id = int(loc)
        st_val = station_latest.get(loc_id, city_med)

        # Other stations mean
        others = [v for s, v in station_latest.items() if s != loc_id]
        other_mean = float(np.mean(others)) if others else st_val

        rows.append({
            "city_median_pm25": city_med,
            "city_mean_pm25": city_mean,
            "city_std_pm25": city_std,
            "city_dispersion": city_disp,
            "station_diff_from_city": float(st_val - city_med),
            "station_ratio_to_city": float(st_val / (city_med + 1.0)),
            "other_stations_mean_pm25": other_mean,
        })

    return pd.DataFrame(rows, index=target_df.index)
