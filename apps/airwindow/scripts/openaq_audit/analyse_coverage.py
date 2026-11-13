"""Per-sensor coverage on an explicit UTC window; never imputes missing values."""
from __future__ import annotations

from collections import Counter
from datetime import timedelta
from statistics import median
from typing import Any
from zoneinfo import ZoneInfo

from .common import utc_time


def analyse(sensor: dict[str, Any], measurements: list[dict[str, Any]], *,
            date_from: str, date_to: str, truncated: bool = False) -> dict[str, Any]:
    start, end = utc_time(date_from), utc_time(date_to)
    if start is None or end is None or end <= start:
        raise ValueError("Coverage window must have increasing timezone-aware bounds")
    sensor_id = int(sensor["sensor"]["id"])
    parameter = sensor["sensor"].get("parameter") or {}
    unit = parameter.get("units")
    expected = int((end - start).total_seconds() // 3600)
    hourly = [r for r in measurements if r["kind"] == "hourly" and r["sensor_id"] == sensor_id]
    raw = [r for r in measurements if r["kind"] == "raw" and r["sensor_id"] == sensor_id]
    times = sorted(utc_time(r["timestamp_utc"]) for r in hourly)
    raw_times = sorted(utc_time(r["timestamp_utc"]) for r in raw)
    valid_times = [t for t in times if start <= t < end]
    counts = Counter(valid_times)
    unique = sorted(counts)
    gaps = [(b - a).total_seconds() / 3600 for a, b in zip(unique, unique[1:])]
    intervals = [(b - a).total_seconds() / 3600 for a, b in zip(times, times[1:])]
    raw_intervals = [(b - a).total_seconds() / 60 for a, b in zip(raw_times, raw_times[1:])]
    values = [float(r["value"]) for r in hourly if isinstance(r.get("value"), (int, float))]
    units = {str((r.get("raw") or {}).get("parameter", {}).get("units", unit)) for r in hourly}
    covered_hours = {t.replace(minute=0, second=0, microsecond=0) for t in unique}
    return {"location_id": sensor["location_id"], "location_name": sensor["location_name"],
            "sensor_id": sensor_id, "provider": (sensor.get("provider") or {}).get("name")
            if isinstance(sensor.get("provider"), dict) else sensor.get("provider"),
            "unit": unit, "units_seen": sorted(units), "raw_observations": len(raw),
            "hourly_observations": len(hourly), "first_observation_utc": times[0].isoformat() if times else None,
            "last_observation_utc": times[-1].isoformat() if times else None,
            "first_observation_ist": times[0].astimezone(ZoneInfo("Asia/Kolkata")).isoformat()
            if times else None,
            "last_observation_ist": times[-1].astimezone(ZoneInfo("Asia/Kolkata")).isoformat()
            if times else None,
            "expected_hours": expected, "covered_hours": len(covered_hours),
            "coverage_percent": round(100 * len(covered_hours) / expected, 3) if expected else None,
            "missing_percent": round(100 * (expected - len(covered_hours)) / expected, 3)
            if expected else None,
            "missing_hours": expected - len(covered_hours),
            "duplicate_hourly_timestamps": sum(n - 1 for n in counts.values()),
            "duplicate_raw_timestamps": len(raw_times) - len(set(raw_times)),
            "longest_reporting_gap_hours": max(gaps) if gaps else None,
            "median_interval_hours": median(intervals) if intervals else None,
            "median_raw_interval_minutes": median(raw_intervals) if raw_intervals else None,
            "min_value": min(values) if values else None,
            "max_value": max(values) if values else None,
            "usable_days": len({t.date() for t in unique}),
            "stale_at_window_end": bool(times and end - times[-1] > timedelta(days=7)),
            "truncated": truncated,
            "quality_flags": quality_flags(unit, units, values, truncated, len(covered_hours),
                                           expected, sensor["sensor"].get("summary") or {})}


def quality_flags(unit: Any, units: set[str], values: list[float], truncated: bool,
                  covered: int, expected: int, sensor_summary: dict[str, Any]) -> list[str]:
    flags = []
    if str(unit).lower().replace("μ", "µ") not in {"µg/m³", "µg/m3", "ug/m3", "ug/m³"}:
        flags.append("unit_incompatible_or_unverified")
    if len(units) > 1:
        flags.append("inconsistent_units")
    if truncated:
        flags.append("request_truncated_coverage_unreliable")
    if expected and covered / expected < 0.75:
        flags.append("coverage_below_75_percent")
    if any(v < 0 or v > 1000 for v in values):
        flags.append("unusual_value_review_without_deletion")
    if sensor_summary.get("min") is not None and sensor_summary["min"] < 0:
        flags.append("negative_lifetime_sensor_summary_review")
    return flags
