"""Download bounded raw and pre-aggregated hourly measurements separately."""
from __future__ import annotations

from typing import Any

from .client import OpenAQClient
from .common import extract_measurement


def download(client: OpenAQClient, sensor_id: int, *, date_from: str, date_to: str,
             max_pages: int = 10) -> tuple[list[dict[str, Any]], bool]:
    params = {"datetime_from": date_from, "datetime_to": date_to}
    all_rows = []
    any_truncated = False
    for kind, endpoint in (("raw", "measurements"), ("hourly", "hours")):
        rows, truncated = client.pages(f"/sensors/{sensor_id}/{endpoint}", params,
                                       max_pages=max_pages, page_size=1000)
        all_rows.extend(extract_measurement(row, sensor_id, kind) for row in rows)
        any_truncated |= truncated
    return all_rows, any_truncated
