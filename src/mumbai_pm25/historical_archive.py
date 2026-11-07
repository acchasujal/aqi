"""Historical archive loader and 2024 seasonal climatology features.

Acceptance gate (EXP-20261107-007, updated in competition-grade ML pipeline):
- Only History_Mumbai_2024.csv.gz is used as a seasonal prior source.
- Filtered to source == 'cpcb_caaqm' (removes :30-minute US embassy timestamps).
- Exact station mapping:
  * 11606: Borivali East, Mumbai - IITM (site_5113, site_5400)
  * 11611: Malad West, Mumbai - IITM (site_5102, site_5402)
    NOTE: Mindspace-Malad West, Mumbai - MPCB (site_5807) is EXCLUDED.
  * 3409510: Byculla, Mumbai - BMC (site_5960)
  * 3409511: Shivaji Nagar, Mumbai - BMC (site_5961)
- Multiple concurrent series per station are pre-aggregated per timestamp before
  calculating seasonal statistics. Coverage represents unique observed hours.
- Leap-year calendar alignment: 2024 was a leap year; normalized day-of-year
  ensures calendar dates (e.g. November 11) match identically between 2024 and 2026.
"""
from __future__ import annotations

import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

# Canonical competition target-station mapping to exact 2024 archive station names.
CANONICAL_STATION_MAP: dict[int, str] = {
    11606: "Borivali East, Mumbai - IITM",
    11611: "Malad West, Mumbai - IITM",
    3409510: "Byculla, Mumbai - BMC",
    3409511: "Shivaji Nagar, Mumbai - BMC",
}

# Backward-compatible name fragments.
STATION_NAME_MAP: dict[int, str] = {
    11606: "Borivali East",
    11611: "Malad West",
    3409510: "Byculla",
    3409511: "Shivaji Nagar",
}

_HISTORY_2024_MEMBER = "History_Mumbai_2024.csv.gz"
_REQUIRED_COLS = {
    "station_name", "timestamp_ist", "value", "source",
    "flag_high_1000", "pm25_nonnegative",
}


def normalized_doy(ts: pd.Timestamp) -> float:
    """Normalize day-of-year so that leap years (e.g. 2024) and non-leap years (2026) align.

    In leap years:
        Jan 1 - Feb 28: DOY 1 - 59
        Feb 29: 59.5
        March 1 - Dec 31: DOY 60 - 365 (shifted by -1)
    In non-leap years:
        Jan 1 - Dec 31: DOY 1 - 365
    """
    d = ts.day_of_year
    if ts.is_leap_year:
        if ts.month == 2 and ts.day == 29:
            return 59.5
        elif ts.month > 2:
            return float(d - 1)
    return float(d)


def circular_doy_distance(doy1: float | np.ndarray, doy2: float) -> float | np.ndarray:
    """Shortest distance in days between two day-of-year values on a circular 365-day calendar."""
    diff = np.abs(doy1 - doy2)
    return np.minimum(diff, 365.0 - diff)


def load_2024_history(
    archive_path: Path,
    *,
    aggregation: str = "mean",
) -> pd.DataFrame:
    """Load and validate 2024 PM2.5 history from the archive.

    Pre-aggregates multiple concurrent series (e.g. dual sensors at IITM stations)
    per station and timestamp to produce exactly one clean observation per station-hour.

    Returns a cleaned DataFrame with columns:
        station_name: archive station name
        hour_start: tz-aware timestamp (Asia/Kolkata) = hour start
        pm25: PM2.5 µg/m³
        source: 'cpcb_caaqm'
    """
    if not archive_path.is_file():
        raise FileNotFoundError(f"Archive not found: {archive_path}")
    with zipfile.ZipFile(archive_path) as z:
        members = z.namelist()
        if _HISTORY_2024_MEMBER not in members:
            raise ValueError(
                f"Expected {_HISTORY_2024_MEMBER!r} in archive; found: {members}"
            )
        with z.open(_HISTORY_2024_MEMBER) as f:
            df = pd.read_csv(f, compression="gzip")

    missing = _REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(
            f"History_Mumbai_2024.csv.gz is missing columns: {sorted(missing)}"
        )

    # Filter to cpcb_caaqm only (removes us_embassy :30-minute rows)
    df = df.loc[df["source"] == "cpcb_caaqm"].copy()
    if df.empty:
        raise ValueError("No cpcb_caaqm rows found in History_Mumbai_2024.csv.gz")

    # Parse timestamps; require IST offset
    offsets = df["timestamp_ist"].astype("string").str[-6:]
    if not (offsets == "+05:30").all():
        df["hour_start"] = pd.to_datetime(df["timestamp_ist"], utc=False)
        if df["hour_start"].dt.tz is None:
            df["hour_start"] = df["hour_start"].dt.tz_localize("Asia/Kolkata")
        else:
            df["hour_start"] = df["hour_start"].dt.tz_convert("Asia/Kolkata")
    else:
        df["hour_start"] = pd.to_datetime(df["timestamp_ist"], utc=True).dt.tz_convert(
            "Asia/Kolkata"
        )

    # Verify minute values are 0 for cpcb_caaqm (hour-start aligned)
    minute_vals = df["hour_start"].dt.minute.unique().tolist()
    if any(m != 0 for m in minute_vals):
        raise ValueError(
            f"cpcb_caaqm rows have non-zero minute timestamps: {minute_vals}."
        )

    df["pm25"] = pd.to_numeric(df["value"], errors="coerce")

    if df["pm25"].isna().any():
        raise ValueError("Unexpected NaN in pm25 after cpcb_caaqm filter")
    if (df["pm25"] < 0).any():
        raise ValueError("Negative pm25 in archive after cpcb_caaqm filter")

    # Pre-aggregate concurrent readings at the same timestamp (e.g. site_5113 and site_5400)
    # This prevents multi-sensor locations from artificially doubling coverage or biasing means
    if aggregation == "median":
        agg_func = "median"
    else:
        agg_func = "mean"

    aggregated = (
        df.groupby(["station_name", "hour_start"], as_index=False)
        .agg({"pm25": agg_func, "source": "first"})
    )

    aggregated = aggregated.sort_values(["station_name", "hour_start"]).reset_index(drop=True)
    return aggregated


def _match_archive_station(loc_id: int, available_stations: list[str]) -> str | None:
    """Find the exact canonical archive station matching the competition location_id."""
    canonical = CANONICAL_STATION_MAP.get(loc_id)
    if canonical and canonical in available_stations:
        return canonical

    # If canonical exact name is not directly present, fall back to safe disambiguation
    fragment = STATION_NAME_MAP.get(loc_id)
    if not fragment:
        return None

    for s in available_stations:
        # Prevent Mindspace-Malad West MPCB from matching Malad West IITM
        if loc_id == 11611 and "mindspace" in s.lower():
            continue
        if fragment.lower() in s.lower():
            return s
    return None


def build_seasonal_features(
    history: pd.DataFrame,
    target_df: pd.DataFrame,
    *,
    station_map: dict[int, str] | None = None,
    window_days: int = 14,
    min_obs: int = 3,
) -> pd.DataFrame:
    """Build 2024 seasonal climatology features for each row in target_df.

    Uses normalized day-of-year for leap-year alignment between 2024 and 2026,
    and circular day-of-year distance for year-boundary handling.

    Parameters
    ----------
    history:
        Output of load_2024_history(): columns station_name, hour_start, pm25.
    target_df:
        DataFrame with columns ``location_id`` and ``target_start`` (IST-aware).
    station_map:
        Optional custom mapping location_id -> station name or fragment.
    window_days:
        Half-width in calendar days for the circular day-of-year window.
    min_obs:
        Minimum number of unique observation hours required; returns NaN otherwise.

    Returns
    -------
    DataFrame indexed like target_df with columns:
        hist24_same_hour_mean: mean pm25 in 2024 for same hour-of-day ±window_days
        hist24_month_hour_mean: mean pm25 in 2024 for same calendar month + hour-of-day
        hist24_coverage: number of unique observation hours contributing to hist24_same_hour_mean
    """
    if history.empty:
        return pd.DataFrame({
            "hist24_same_hour_mean": np.nan,
            "hist24_month_hour_mean": np.nan,
            "hist24_coverage": 0,
        }, index=target_df.index)

    history = history.copy()
    if not pd.api.types.is_datetime64_any_dtype(history["hour_start"]):
        history["hour_start"] = pd.to_datetime(history["hour_start"])

    # Compute normalized day of year for leap year alignment
    history["norm_doy"] = history["hour_start"].apply(normalized_doy)
    history["hod"] = history["hour_start"].dt.hour
    history["month"] = history["hour_start"].dt.month

    # Group by station name for fast lookups
    station_cache: dict[str, pd.DataFrame] = {
        str(sname): sub for sname, sub in history.groupby("station_name")
    }
    available_stations = list(station_cache.keys())

    result_rows: list[dict] = []
    for row in target_df.itertuples(index=True):
        loc_id = int(row.location_id)
        t_start: pd.Timestamp = row.target_start
        idx = row.Index

        matched_station = _match_archive_station(loc_id, available_stations)
        if matched_station is None:
            result_rows.append({
                "idx": idx,
                "hist24_same_hour_mean": np.nan,
                "hist24_month_hour_mean": np.nan,
                "hist24_coverage": 0,
            })
            continue

        sub = station_cache[matched_station]
        target_hod = t_start.hour
        target_norm_doy = normalized_doy(t_start)
        target_month = t_start.month

        # Circular day-of-year distance on 365-day calendar
        dists = circular_doy_distance(sub["norm_doy"].to_numpy(), target_norm_doy)
        same_hod_mask = (sub["hod"].to_numpy() == target_hod) & (dists <= window_days)
        same_hod = sub.iloc[same_hod_mask]

        obs_vals = same_hod["pm25"].dropna()
        n_obs = len(obs_vals)
        if n_obs >= min_obs:
            same_hour_mean = float(obs_vals.mean())
        else:
            same_hour_mean = np.nan

        # Month + hour profile
        month_hod_mask = (sub["month"].to_numpy() == target_month) & (sub["hod"].to_numpy() == target_hod)
        month_hod = sub.iloc[month_hod_mask]["pm25"].dropna()
        if len(month_hod) >= min_obs:
            month_hour_mean = float(month_hod.mean())
        else:
            month_hour_mean = np.nan

        result_rows.append({
            "idx": idx,
            "hist24_same_hour_mean": same_hour_mean,
            "hist24_month_hour_mean": month_hour_mean,
            "hist24_coverage": n_obs,
        })

    result = pd.DataFrame(result_rows).set_index("idx")
    result.index.name = target_df.index.name
    return result


def compute_station_seasonal_profiles(
    history: pd.DataFrame,
    station_map: dict[int, str] | None = None,
) -> dict[int, pd.DataFrame]:
    """Pre-compute per-station 2024 seasonal profiles keyed by competition location_id."""
    history = history.copy()
    history["norm_doy"] = history["hour_start"].apply(normalized_doy)
    history["hod"] = history["hour_start"].dt.hour
    history["month"] = history["hour_start"].dt.month

    available_stations = history["station_name"].unique().tolist()
    profiles: dict[int, pd.DataFrame] = {}

    for loc_id in CANONICAL_STATION_MAP:
        matched = _match_archive_station(loc_id, available_stations)
        if matched is None:
            profiles[loc_id] = pd.DataFrame(
                columns=["norm_doy", "hod", "month", "mean_pm25", "median_pm25", "count"]
            )
            continue
        sub = history.loc[history["station_name"] == matched]
        profile = (
            sub.groupby(["norm_doy", "hod", "month"])["pm25"]
            .agg(mean_pm25="mean", median_pm25="median", count="count")
            .reset_index()
        )
        profiles[loc_id] = profile
    return profiles
