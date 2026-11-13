"""Conservative station reconciliation: proximity is a lead, not proof."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import pandas as pd

from .common import metres_between
from .common import utc_time


def load_airwindow_stations(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [{"station_id": int(r["location_id"]), "station_name": r["station_name"],
                 "sensor_id": int(r["selected_sensor"]), "latitude": float(r["latitude"]),
                 "longitude": float(r["longitude"])} for r in csv.DictReader(handle)]


def reconcile(stations: list[dict[str, Any]], locations: list[dict[str, Any]],
              sensors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    sensor_ids = {int(s["sensor"]["id"]) for s in sensors}
    for station in stations:
        candidates = []
        for loc in locations:
            coords = loc.get("coordinates")
            if not coords or coords.get("latitude") is None or coords.get("longitude") is None:
                continue
            distance = metres_between(station, coords)
            if distance <= 2000 or int(loc["id"]) == station["station_id"]:
                candidates.append((distance, loc))
        if not candidates:
            rows.append({"station_id": station["station_id"], "station_name": station["station_name"],
                         "local_sensor_id": station["sensor_id"], "openaq_location_id": "",
                         "openaq_sensor_id": "", "distance_m": "", "classification": "Unmatched station",
                         "evidence": "No candidate within 2 km in bounded location catalog"})
        for distance, loc in sorted(candidates, key=lambda p: p[0]):
            matched_sensor = station["sensor_id"] if station["sensor_id"] in sensor_ids else ""
            rows.append({"station_id": station["station_id"], "station_name": station["station_name"],
                         "local_sensor_id": station["sensor_id"], "openaq_location_id": loc["id"],
                         "openaq_sensor_id": matched_sensor if loc["id"] == station["station_id"] else "",
                         "distance_m": round(distance, 1),
                         "classification": "Possible match requiring manual verification",
                         "evidence": "Proximity/identifier lead only; source and overlapping values not verified"})
    return rows


def compare_train_overlap(train_path: Path, station: dict[str, Any],
                          records: list[dict[str, Any]]) -> dict[str, Any]:
    """Compare OpenAQ period ends to local Train interval-end timestamps."""
    frame = pd.read_csv(train_path, usecols=["timestamp_ist", "pm25", "location_id", "sensor_id"])
    frame = frame.loc[(frame.location_id == station["station_id"])
                      & (frame.sensor_id == station["sensor_id"]) & frame.pm25.notna()]
    frame["end_utc"] = pd.to_datetime(frame.timestamp_ist, utc=True)
    local = frame.groupby("end_utc").pm25.mean()
    pairs = []
    for row in records:
        if row["kind"] != "hourly":
            continue
        period = row["raw"].get("period") or {}
        end = utc_time(period.get("datetimeTo"))
        if end is None or row["value"] is None:
            continue
        key = pd.Timestamp(end)
        if key in local.index:
            pairs.append(abs(float(local.loc[key]) - float(row["value"])))
    return {"overlap_hours": len(pairs), "mean_absolute_difference":
            round(sum(pairs) / len(pairs), 6) if pairs else None,
            "exact_fraction": round(sum(d < 1e-6 for d in pairs) / len(pairs), 4) if pairs else None,
            "within_0_2_fraction": round(sum(d <= 0.2 for d in pairs) / len(pairs), 4)
            if pairs else None, "max_absolute_difference": max(pairs) if pairs else None}
