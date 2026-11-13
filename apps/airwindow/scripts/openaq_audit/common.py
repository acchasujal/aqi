"""Shared normalization and time utilities for the OpenAQ audit."""
from __future__ import annotations

from datetime import datetime, timezone
from math import asin, cos, radians, sin, sqrt
from typing import Any


def utc_time(value: Any) -> datetime | None:
    if isinstance(value, dict):
        value = value.get("utc") or value.get("local")
    if not value:
        return None
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"Timestamp has no timezone: {value}")
    return parsed.astimezone(timezone.utc)


def pm25_sensors(location: dict[str, Any]) -> list[dict[str, Any]]:
    return [sensor for sensor in location.get("sensors") or []
            if str((sensor.get("parameter") or {}).get("name", "")).lower()
            in {"pm25", "pm2.5"}]


def metres_between(a: dict[str, float], b: dict[str, float]) -> float:
    lat1, lon1 = radians(float(a["latitude"])), radians(float(a["longitude"]))
    lat2, lon2 = radians(float(b["latitude"])), radians(float(b["longitude"]))
    h = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return 2 * 6_371_000 * asin(sqrt(h))


def extract_measurement(row: dict[str, Any], sensor_id: int, kind: str) -> dict[str, Any]:
    period = row.get("period") or {}
    dt = utc_time((period.get("datetimeFrom") or {}).get("utc")
                  or (row.get("datetime") or {}).get("utc")
                  or row.get("date") or row.get("datetimeFrom"))
    if dt is None:
        raise ValueError(f"Sensor {sensor_id} {kind} record lacks a timestamp")
    value = row.get("value")
    return {"sensor_id": sensor_id, "kind": kind, "timestamp_utc": dt.isoformat(),
            "value": value, "raw": row}
