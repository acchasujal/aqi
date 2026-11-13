"""Discover Mumbai locations without assuming their PM2.5 capability."""
from __future__ import annotations

from typing import Any

from .client import OpenAQClient

MUMBAI_BBOX = (72.75, 18.85, 73.05, 19.35)


def discover(client: OpenAQClient, *, bbox: tuple[float, float, float, float] = MUMBAI_BBOX,
             max_pages: int = 5) -> tuple[list[dict[str, Any]], bool]:
    rows, truncated = client.pages("/locations", {"bbox": ",".join(map(str, bbox)), "iso": "IN"},
                                   max_pages=max_pages, page_size=100)
    return sorted(rows, key=lambda row: row["id"]), truncated
