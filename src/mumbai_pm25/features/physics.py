"""Micro-meteorological atmospheric dispersion, coastal breeze, and spatial geometry features."""

from __future__ import annotations

import numpy as np
import pandas as pd

TARGET_STATIONS = [11606, 11611, 3409510, 3409511]

STATION_COORDS: dict[int, tuple[float, float]] = {
    11606: (19.23241, 72.86895),     # Borivali East - IITM
    11611: (19.19709, 72.82204),     # Malad West - IITM
    3409510: (18.97670, 72.83800),   # Byculla - BMC
    3409511: (19.060498, 72.923356), # Shivaji Nagar - BMC
}

# Mumbai coastline runs ~15° NNE-SSW.
# Normal pointing onshore from Arabian Sea is ~285° (WNW -> ESE).
COASTLINE_NORMAL_RAD = np.deg2rad(285.0)

# Regional emission corridors:
# Deonar dumping ground is ~75° (ENE) of Shivaji Nagar.
# Thane Creek / Mahul petrochemical corridor is ~110° (ESE).
DEONAR_RAD = np.deg2rad(75.0)
THANE_CREEK_RAD = np.deg2rad(110.0)


def compute_station_geometry() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Calculate pairwise distances (km) and unit direction vectors (dx, dy) across stations."""
    n = len(TARGET_STATIONS)
    dist_km = np.zeros((n, n), dtype=np.float64)
    dir_east = np.zeros((n, n), dtype=np.float64)
    dir_north = np.zeros((n, n), dtype=np.float64)

    for i, loc_i in enumerate(TARGET_STATIONS):
        lat_i, lon_i = STATION_COORDS[loc_i]
        for j, loc_j in enumerate(TARGET_STATIONS):
            if i == j:
                continue
            lat_j, lon_j = STATION_COORDS[loc_j]
            dy_km = (lat_i - lat_j) * 111.0
            dx_km = (lon_i - lon_j) * 111.0 * np.cos(np.deg2rad(0.5 * (lat_i + lat_j)))
            d = float(np.hypot(dx_km, dy_km))
            dist_km[i, j] = max(d, 0.5)
            dir_east[i, j] = dx_km / max(d, 1e-3)
            dir_north[i, j] = dy_km / max(d, 1e-3)

    return dist_km, dir_east, dir_north


_DIST_KM, _DIR_EAST, _DIR_NORTH = compute_station_geometry()


def compute_atmospheric_physics_features(df: pd.DataFrame) -> pd.DataFrame:
    """Enrich feature matrix with first-principles atmospheric dispersion physics.

    If weather/PBLH columns are missing, deterministic micro-meteorological diurnal proxies
    are synthesized from solar hour and month to maintain pipeline robustness.
    """
    out = df.copy()

    # Determine hour and day of year
    if "hour" in out.columns:
        hours = out["hour"].to_numpy(dtype=float)
    elif "target_start" in out.columns:
        hours = pd.to_datetime(out["target_start"]).dt.hour.to_numpy(dtype=float)
    else:
        hours = np.zeros(len(out), dtype=float)

    # 1. Boundary Layer Height (PBLH) & Wind Speed
    has_pblh = "boundary_layer_height" in out.columns and out["boundary_layer_height"].notna().any()
    has_wspd = "wind_speed_10m" in out.columns and out["wind_speed_10m"].notna().any()

    if has_pblh:
        pblh = np.maximum(out["boundary_layer_height"].fillna(300.0).to_numpy(dtype=float), 20.0)
    else:
        # Physical diurnal PBLH proxy: nocturnal collapse to ~150m, afternoon solar expansion to ~1000m
        solar_phase = np.sin(np.pi * np.clip((hours - 6.0) / 12.0, 0.0, 1.0))
        pblh = 150.0 + 850.0 * (solar_phase ** 1.5)

    if has_wspd:
        wspd = np.maximum(out["wind_speed_10m"].fillna(2.5).to_numpy(dtype=float), 0.1)
    else:
        # Afternoon sea breeze peak (~3.5 m/s), nocturnal calm (~1.5 m/s)
        wspd = 1.8 + 1.7 * np.maximum(0.0, np.sin(np.pi * (hours - 8.0) / 12.0))

    # Ventilation Coefficient: VC = PBLH * Wind Speed (mixing volume index)
    vc = pblh * wspd
    out["pblh"] = pblh
    out["log_pblh"] = np.log(pblh)
    out["vc"] = vc
    out["log1p_vc"] = np.log1p(vc)

    # 2. Wind Direction & Coastal Land-Sea Breeze
    has_wdir = "wind_direction_10m" in out.columns and out["wind_direction_10m"].notna().any()
    if has_wdir:
        wdir_deg = out["wind_direction_10m"].fillna(270.0).to_numpy(dtype=float)
        wdir_rad = np.deg2rad(wdir_deg)
    else:
        # Typical diurnal wind direction: morning land-breeze (~80° ENE), afternoon sea-breeze (~280° WNW)
        is_day = (hours >= 11) & (hours <= 19)
        wdir_rad = np.where(is_day, np.deg2rad(280.0), np.deg2rad(80.0))

    out["u10"] = -wspd * np.sin(wdir_rad)
    out["v10"] = -wspd * np.cos(wdir_rad)
    out["wind_dir_sin"] = np.sin(wdir_rad)
    out["wind_dir_cos"] = np.cos(wdir_rad)

    # Onshore breeze along 285° Arabian Sea normal (>0: sea breeze, <0: nocturnal land breeze)
    out["onshore_breeze"] = wspd * np.cos(wdir_rad - COASTLINE_NORMAL_RAD)

    # 3. Regional Emission Corridor Transport Proxies
    out["deonar_wind_cos"] = np.cos(wdir_rad - DEONAR_RAD)
    out["deonar_transport_proxy"] = wspd * np.maximum(0.0, out["deonar_wind_cos"])
    out["thane_creek_wind_cos"] = np.cos(wdir_rad - THANE_CREEK_RAD)
    out["thane_creek_transport_proxy"] = wspd * np.maximum(0.0, out["thane_creek_wind_cos"])

    # 4. Thermal Inversion & Stagnation Proxies
    has_temp = "temperature_2m" in out.columns and out["temperature_2m"].notna().any()
    has_dew = "dew_point_2m" in out.columns and out["dew_point_2m"].notna().any()

    if has_temp and has_dew:
        t_2m = out["temperature_2m"].to_numpy(dtype=float)
        dp_2m = out["dew_point_2m"].to_numpy(dtype=float)
        out["dewpoint_depression"] = t_2m - dp_2m
    else:
        # Synthetic diurnal dewpoint depression
        out["dewpoint_depression"] = 4.0 + 3.0 * np.sin(2.0 * np.pi * (hours - 10.0) / 24.0)

    # Stagnation index: low VC combined with low onshore breeze
    out["stagnation_index"] = 1.0 / (1.0 + np.maximum(0.0, out["log1p_vc"]))

    return out


def extract_interstation_advection(
    pm_current: dict[int, float],
    wind_speed: float,
    wind_dir_rad: float,
) -> dict[int, float]:
    """Compute directional advection flux arriving at station i from upstream stations."""
    # Unit wind vector pointing TOWARDS
    w_x = -wind_speed * np.sin(wind_dir_rad)
    w_y = -wind_speed * np.cos(wind_dir_rad)

    advection_flux: dict[int, float] = {}

    for i, loc_i in enumerate(TARGET_STATIONS):
        flux_i = 0.0
        weight_sum = 0.0
        for j, loc_j in enumerate(TARGET_STATIONS):
            if i == j or loc_j not in pm_current:
                continue
            # Direction vector from j to i
            e_x = _DIR_EAST[i, j]
            e_y = _DIR_NORTH[i, j]
            d_ij = _DIST_KM[i, j]

            # Alignment between wind vector and vector j -> i
            alignment = (w_x * e_x + w_y * e_y) / max(wind_speed, 0.1)

            # Only positive alignment transports from upstream j to downstream i
            if alignment > 0:
                spatial_weight = alignment / (d_ij ** 1.2)
                flux_i += spatial_weight * pm_current[loc_j]
                weight_sum += spatial_weight

        advection_flux[loc_i] = (flux_i / weight_sum) if weight_sum > 0 else pm_current.get(loc_i, 40.0)

    return advection_flux
