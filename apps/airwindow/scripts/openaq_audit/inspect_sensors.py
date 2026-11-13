"""Inspect PM2.5 sensors at each discovered location."""
from __future__ import annotations

from typing import Any

from .client import OpenAQClient
from .common import pm25_sensors


def inspect(client: OpenAQClient, locations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    catalog = []
    for location in locations:
        location_id = int(location["id"])
        sensors, truncated = client.pages(f"/locations/{location_id}/sensors", {}, max_pages=5)
        if truncated:
            raise RuntimeError(f"Sensor listing truncated for location {location_id}")
        for sensor in pm25_sensors({"sensors": sensors}):
            catalog.append({"location_id": location_id, "location_name": location.get("name"),
                            "provider": location.get("provider"), "owner": location.get("owner"),
                            "coordinates": location.get("coordinates"),
                            "country": location.get("country"), "locality": location.get("locality"),
                            "location_instruments": location.get("instruments"),
                            "location_datetime_first": location.get("datetimeFirst"),
                            "location_datetime_last": location.get("datetimeLast"),
                            "sensor": sensor})
    return sorted(catalog, key=lambda item: (item["location_id"], item["sensor"]["id"]))
