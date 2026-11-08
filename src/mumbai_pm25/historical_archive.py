"""Identity-preserving loader and calendar-aware 2024 PM2.5 profiles."""
from __future__ import annotations

import zipfile
from collections.abc import Sequence
from pathlib import Path

import numpy as np
import pandas as pd

ARCHIVE_SERIES: dict[int, tuple[str, ...]] = {
    11606: ("xkdr:site_5113", "xkdr:site_5400"),  # Borivali East candidates
    11611: ("xkdr:site_5102", "xkdr:site_5402", "xkdr:site_5807"),  # Malad candidates
    3409510: ("xkdr:site_5960",),
    3409511: ("xkdr:site_5961",),
}

# Candidate fallback mapping. Predictive source selection does not establish
# physical sensor equivalence. Keep Mindspace site_5807 outside the Malad mapping.
P_FIX_SERIES: dict[int, tuple[str, ...]] = {
    11606: ("xkdr:site_5400",),
    11611: ("xkdr:site_5102", "xkdr:site_5402"),
    3409510: ("xkdr:site_5960",),
    3409511: ("xkdr:site_5961",),
}

HISTORY_MEMBER = "History_Mumbai_2024.csv.gz"
REQUIRED_COLUMNS = {
    "station_id", "series_id", "station_name", "collected_at", "timestamp_ist",
    "value", "unit", "source", "flag_negative", "flag_high_500", "flag_high_1000",
}


def load_2024_history(archive_path: Path) -> pd.DataFrame:
    """Load eligible CPCB rows while retaining raw provenance columns.

    ``collected_at`` and ``timestamp_ist`` are preserved verbatim. The parsed
    ``hour_start`` is only an alignment hypothesis; archive interval semantics
    have not been verified against the competition station measurements.
    """
    if not archive_path.is_file():
        raise FileNotFoundError(f"Archive not found: {archive_path}")
    with zipfile.ZipFile(archive_path) as archive:
        if HISTORY_MEMBER not in archive.namelist():
            raise ValueError(f"Expected {HISTORY_MEMBER!r} in archive")
        with archive.open(HISTORY_MEMBER) as stream:
            raw = pd.read_csv(stream, compression="gzip")
    missing = REQUIRED_COLUMNS - set(raw.columns)
    if missing:
        raise ValueError(f"Archive member is missing columns: {sorted(missing)}")

    rows = raw.loc[raw.source.eq("cpcb_caaqm")].copy()
    if rows.empty:
        raise ValueError("No cpcb_caaqm rows in the 2024 history member")
    rows["hour_start"] = pd.to_datetime(rows.timestamp_ist, utc=True).dt.tz_convert(
        "Asia/Kolkata"
    )
    if not rows.hour_start.dt.minute.eq(0).all():
        bad = sorted(rows.loc[rows.hour_start.dt.minute.ne(0), "hour_start"].dt.minute.unique())
        raise ValueError(f"CPCB archive timestamps have non-zero minute values: {bad}")
    rows["pm25"] = pd.to_numeric(rows.value, errors="coerce")
    valid = np.isfinite(rows.pm25.to_numpy(dtype=float)) & rows.pm25.ge(0).to_numpy()
    rows = rows.loc[valid].copy()
    if rows.empty:
        raise ValueError("No finite non-negative CPCB PM2.5 rows remain")
    if rows.duplicated(["series_id", "hour_start"]).any():
        raise ValueError("Archive has duplicate series_id/hour_start keys")
    if rows.hour_start.dt.year.ne(2024).any():
        raise ValueError("Expected only 2024 timestamps in History_Mumbai_2024")
    return rows.sort_values(["series_id", "hour_start"]).reset_index(drop=True)


def _calendar_anchor(timestamp: pd.Timestamp) -> pd.Timestamp:
    """Map month/day to 2024; Feb 29 maps to Feb 29, other dates by month/day."""
    try:
        return pd.Timestamp(year=2024, month=timestamp.month, day=timestamp.day)
    except ValueError as exc:
        raise ValueError(f"Cannot map calendar date {timestamp:%m-%d} into 2024") from exc


def build_seasonal_features(
    history: pd.DataFrame,
    target_df: pd.DataFrame,
    *,
    series_map: dict[int, str | Sequence[str]] | None = None,
    window_days: int = 14,
    min_obs: int = 3,
    offset_hours: int = 0,
) -> pd.DataFrame:
    """Build exact-series same-hour climatology on a calendar-date window.

    Window endpoints use 2024 calendar dates, including its leap day and year
    boundary. A target on 29 February is matched to 29 February 2024. The
    returned coverage is the number of source observations, not an imputed
    count; an insufficient profile remains NaN.
    """
    if window_days < 0 or min_obs < 1 or offset_hours not in (-1, 0, 1):
        raise ValueError("Require window_days >= 0, min_obs >= 1, and offset_hours in -1/0/1")
    if not {"location_id", "target_start"}.issubset(target_df.columns):
        raise ValueError("target_df needs location_id and target_start columns")
    if series_map is None:
        series_map = P_FIX_SERIES
    if "series_id" not in history or "hour_start" not in history or "pm25" not in history:
        raise ValueError("history needs exact series_id, parsed hour_start, and pm25 columns")

    # Daily sums/counts keep multiple-series combinations explicit and weighted
    # by the actual count of observations, without substring matching.
    history = history.loc[history.series_id.isin({
        sid for values in series_map.values()
        for sid in ((values,) if isinstance(values, str) else values)
    })].copy()
    if history.empty:
        empty = pd.DataFrame({
            "hist24_same_hour_mean": np.nan,
            "hist24_coverage": 0,
            "hist24_expected_coverage": (2 * window_days + 1),
            "hist24_coverage_fraction": 0.0,
            "hist24_source_ids": "",
            "hist24_month_hour_mean": np.nan,
            "hist24_offset_hours": offset_hours,
        }, index=target_df.index)
        return empty
    history["calendar_date"] = history.hour_start.dt.date
    history["hour"] = history.hour_start.dt.hour
    by_source = {
        source_id: group.groupby(["calendar_date", "hour"]).pm25.agg(["sum", "count"])
        for source_id, group in history.groupby("series_id", sort=False)
    }

    features: list[dict[str, float | int | str]] = []
    for idx, row in target_df.iterrows():
        loc_id = int(row.location_id)
        source_value = series_map.get(loc_id, ())
        source_ids = (source_value,) if isinstance(source_value, str) else tuple(source_value)
        timestamp = pd.Timestamp(row.target_start) + pd.Timedelta(hours=offset_hours)
        if timestamp.tzinfo is None:
            raise ValueError("target_start values must be timezone-aware")
        anchor = _calendar_anchor(timestamp)
        calendar_start = pd.Timestamp("2024-01-01")
        anchor_index = int((anchor - calendar_start).days)
        dates = [
            (calendar_start + pd.Timedelta(days=(anchor_index + delta) % 366)).date()
            for delta in range(-window_days, window_days + 1)
        ]
        sums: list[float] = []
        counts: list[int] = []
        source_coverage: dict[str, int] = {}
        source_means: dict[str, float] = {}
        source_sums: dict[str, float] = {}
        for source_id in source_ids:
            table = by_source.get(source_id)
            if table is None:
                source_coverage[source_id] = 0
                source_means[source_id] = np.nan
                source_sums[source_id] = 0.0
                continue
            keys = [(date, timestamp.hour) for date in dates]
            selected = table.reindex(pd.MultiIndex.from_tuples(keys, names=["calendar_date", "hour"]))
            n = int(selected["count"].fillna(0).sum())
            source_coverage[source_id] = n
            sums.append(float(selected["sum"].fillna(0).sum()))
            source_sums[source_id] = sums[-1]
            counts.append(n)
            source_means[source_id] = (
                float(sums[-1] / n) if n >= min_obs else np.nan
            )
        coverage = int(sum(counts))
        mean = float(sum(sums) / coverage) if coverage >= min_obs else np.nan
        # Keep per-source counts as audit metadata; these columns are never model predictors.
        item: dict[str, float | int | str] = {
            "hist24_same_hour_mean": mean,
            "hist24_coverage": coverage,
            "hist24_expected_coverage": len(dates) * len(source_ids),
            "hist24_coverage_fraction": (
                coverage / (len(dates) * len(source_ids)) if source_ids else 0.0
            ),
            "hist24_source_ids": ",".join(source_ids),
            "hist24_month_hour_mean": np.nan,
            "hist24_offset_hours": offset_hours,
        }
        for source_id, n in source_coverage.items():
            item[f"hist24_series::{source_id}::mean"] = source_means[source_id]
            item[f"hist24_series::{source_id}::coverage"] = n
            item[f"hist24_series::{source_id}::sum"] = source_sums[source_id]
        features.append(item)
    return pd.DataFrame(features, index=target_df.index)


def source_coverage_report(history: pd.DataFrame) -> pd.DataFrame:
    """Summarize exact archive series provenance and temporal coverage."""
    report = history.groupby(["series_id", "station_id", "station_name", "source"],
                             dropna=False).agg(
        rows=("pm25", "size"),
        first_hour=("hour_start", "min"),
        last_hour=("hour_start", "max"),
        non_missing=("pm25", "count"),
        median_pm25=("pm25", "median"),
        maximum_pm25=("pm25", "max"),
    ).reset_index()
    return report.sort_values(["station_name", "series_id"]).reset_index(drop=True)
