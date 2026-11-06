"""Historical archive loader and 2024 seasonal climatology features.

Acceptance gate (EXP-20261107-007):
- Only History_Mumbai_2024.csv.gz is used as a seasonal prior source.
- Filtered to source == 'cpcb_caaqm' (removes :30-minute US embassy timestamps).
- Station identity is established by name matching only; sensor cross-reference
  across XKDR site IDs and OpenAQ location IDs is unverified (documented
  in EXP-20261107-007 and HistoryNotes.txt).
- PM2.5 values in the archive are pre-capped at 1000 µg/m³; this is a known
  semantic difference from competition Train which contains values up to ~241 k.
- HistoryNotes.txt explicitly states "Averaging intervals have not been fully
  aligned to current OpenAQ hour-ending targets"; we treat cpcb_caaqm rows
  whose timestamps fall at minute=0 as hour-start-aligned observations and
  document this assumption.
- NOT used as a direct substitution for current-year PM history.
- Used only as a seasonal/climatological prior (day-of-year ± window, hour-of-day).
- The 2024 archive is competition-supplied data, available from submission start.
"""
from __future__ import annotations

import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

# Competition target-station name fragments and their location_ids.
# Mapping is by name fragment (case-insensitive) only; sensor IDs are NOT matched
# because XKDR site IDs are not interchangeable with OpenAQ location IDs.
STATION_NAME_MAP: dict[int, str] = {
    11606: "Borivali East",
    11611: "Malad West",
    3409510: "Byculla",
    3409511: "Shivaji Nagar",
}

# Archive member expected
_HISTORY_2024_MEMBER = "History_Mumbai_2024.csv.gz"
_REQUIRED_COLS = {
    "station_name", "timestamp_ist", "value", "source",
    "flag_high_1000", "pm25_nonnegative",
}


def load_2024_history(archive_path: Path) -> pd.DataFrame:
    """Load and validate the 2024 PM2.5 history from the archive.

    Returns a cleaned DataFrame with columns:
        station_name: original archive station name
        hour_start: tz-aware timestamp (Asia/Kolkata) = hour start
        value: PM2.5 µg/m³ (pre-capped at 1000 in source; documented)
        source: 'cpcb_caaqm' (us_embassy filtered out)

    Raises FileNotFoundError or ValueError on schema failures.
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
        # Some rows may carry no offset after gz decompression; handle gracefully
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
            f"cpcb_caaqm rows have non-zero minute timestamps: {minute_vals}. "
            "Review interval semantics before using as features."
        )

    # Use pm25_nonnegative (pre-cleaned) but keep the original value column for
    # reference. Use 'value' as it was filtered by the archive preparer to exclude
    # negative and missing entries.
    df = df[["station_name", "hour_start", "value", "source"]].copy()
    df = df.rename(columns={"value": "pm25"})
    df["pm25"] = pd.to_numeric(df["pm25"], errors="coerce")

    # Validate value range
    if df["pm25"].isna().any():
        raise ValueError("Unexpected NaN in pm25 after cpcb_caaqm filter")
    if (df["pm25"] < 0).any():
        raise ValueError("Negative pm25 in archive after cpcb_caaqm filter")

    # Sort for reproducibility
    df = df.sort_values(["station_name", "hour_start"]).reset_index(drop=True)
    return df


def build_seasonal_features(
    history: pd.DataFrame,
    target_df: pd.DataFrame,
    *,
    station_map: dict[int, str] | None = None,
    window_days: int = 14,
    min_obs: int = 3,
) -> pd.DataFrame:
    """Build 2024 seasonal climatology features for each row in target_df.

    Parameters
    ----------
    history:
        Output of load_2024_history(): columns station_name, hour_start, pm25.
    target_df:
        DataFrame with columns ``location_id`` and ``target_start`` (IST-aware).
    station_map:
        Maps competition location_id -> archive station name fragment.
        Defaults to STATION_NAME_MAP.
    window_days:
        Half-width in calendar days for the ±day-of-year window.
        Default 14 (±14 days = 29-day centred window).
    min_obs:
        Minimum number of non-null observations required; returns NaN otherwise.

    Returns
    -------
    DataFrame indexed like target_df with columns:
        hist24_same_hour_mean: mean pm25 in 2024 for same hour-of-day ±window_days
        hist24_month_hour_mean: mean pm25 in 2024 for same calendar month + hour-of-day
        hist24_coverage: number of observations used for hist24_same_hour_mean
    """
    if station_map is None:
        station_map = STATION_NAME_MAP

    # Pre-compute 2024 day-of-year and hour-of-day on the history
    history = history.copy()
    if history.empty:
        # Return NaN features for all targets
        result = pd.DataFrame({
            "hist24_same_hour_mean": np.nan,
            "hist24_month_hour_mean": np.nan,
            "hist24_coverage": 0,
        }, index=target_df.index)
        return result
    # Ensure hour_start is datetime
    if not pd.api.types.is_datetime64_any_dtype(history["hour_start"]):
        history["hour_start"] = pd.to_datetime(history["hour_start"])
    history["doy"] = history["hour_start"].dt.day_of_year
    history["hod"] = history["hour_start"].dt.hour
    history["month"] = history["hour_start"].dt.month

    # Build a lookup dict: archive_station_name -> sub-DataFrame
    station_cache: dict[str, pd.DataFrame] = {}
    for sname, sub in history.groupby("station_name"):
        station_cache[str(sname)] = sub

    result_rows: list[dict] = []
    for row in target_df.itertuples(index=True):
        loc_id = int(row.location_id)
        t_start: pd.Timestamp = row.target_start
        idx = row.Index

        name_fragment = station_map.get(loc_id)
        if name_fragment is None:
            result_rows.append({
                "idx": idx,
                "hist24_same_hour_mean": np.nan,
                "hist24_month_hour_mean": np.nan,
                "hist24_coverage": 0,
            })
            continue

        # Find matching archive station(s)
        matching = [k for k in station_cache if name_fragment.lower() in k.lower()]
        if not matching:
            result_rows.append({
                "idx": idx,
                "hist24_same_hour_mean": np.nan,
                "hist24_month_hour_mean": np.nan,
                "hist24_coverage": 0,
            })
            continue

        # Combine all matching stations (may be multiple — e.g., Malad West has IITM + MPCB)
        sub = pd.concat([station_cache[k] for k in matching], ignore_index=True)

        target_hod = t_start.hour
        target_doy = t_start.day_of_year
        target_month = t_start.month

        # Day-of-year window (handle year wrap: DOY 1-365/366)
        # Map to a range of doy values within ±window_days
        # Use modular arithmetic on 365-day year (non-leap aware)
        doy_min = target_doy - window_days
        doy_max = target_doy + window_days

        if doy_min < 1 and doy_max > 365:
            # Window spans the whole year — use all doys for this hour
            same_hod = sub.loc[sub["hod"] == target_hod]
        elif doy_min < 1:
            # Wraps into previous year
            mask = (
                (sub["hod"] == target_hod)
                & ((sub["doy"] >= doy_min + 365) | (sub["doy"] <= doy_max))
            )
            same_hod = sub.loc[mask]
        elif doy_max > 365:
            # Wraps into next year
            mask = (
                (sub["hod"] == target_hod)
                & ((sub["doy"] >= doy_min) | (sub["doy"] <= doy_max - 365))
            )
            same_hod = sub.loc[mask]
        else:
            mask = (
                (sub["hod"] == target_hod)
                & (sub["doy"] >= doy_min)
                & (sub["doy"] <= doy_max)
            )
            same_hod = sub.loc[mask]

        obs_vals = same_hod["pm25"].dropna()
        n_obs = len(obs_vals)
        if n_obs >= min_obs:
            same_hour_mean = float(obs_vals.mean())
        else:
            same_hour_mean = np.nan

        # Month + hour profile
        month_hod = sub.loc[(sub["month"] == target_month) & (sub["hod"] == target_hod), "pm25"].dropna()
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
    """Pre-compute per-station 2024 seasonal profiles keyed by competition location_id.

    Returns dict mapping location_id -> DataFrame with columns:
        doy, hod, mean_pm25, median_pm25, count
    """
    if station_map is None:
        station_map = STATION_NAME_MAP

    history = history.copy()
    history["doy"] = history["hour_start"].dt.day_of_year
    history["hod"] = history["hour_start"].dt.hour
    history["month"] = history["hour_start"].dt.month

    profiles: dict[int, pd.DataFrame] = {}
    for loc_id, name_fragment in station_map.items():
        matching = history.loc[
            history["station_name"].str.contains(name_fragment, case=False, na=False)
        ].copy()
        if matching.empty:
            profiles[loc_id] = pd.DataFrame(
                columns=["doy", "hod", "month", "mean_pm25", "median_pm25", "count"]
            )
            continue
        profile = (
            matching.groupby(["doy", "hod", "month"])["pm25"]
            .agg(mean_pm25="mean", median_pm25="median", count="count")
            .reset_index()
        )
        profiles[loc_id] = profile
    return profiles
