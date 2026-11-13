"""Authenticated OpenAQ v3 client with bounded pagination and disk cache."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

import requests

LOG = logging.getLogger(__name__)
BASE_URL = "https://api.openaq.org/v3"


class OpenAQClient:
    def __init__(self, api_key: str | None = None, *, cache_dir: Path | None = None,
                 session: requests.Session | None = None, max_retries: int = 3):
        self.api_key = api_key or os.environ.get("OPENAQ_API_KEY")
        if not self.api_key:
            raise RuntimeError("OPENAQ_API_KEY is unset. Register at https://explore.openaq.org/register "
                               "and set it as an environment variable before running the live audit.")
        self.session = session or requests.Session()
        self.cache_dir = cache_dir
        self.max_retries = max_retries

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if not path.startswith("/") or ".." in path or not path.startswith(("/locations", "/sensors")):
            raise ValueError("Only OpenAQ locations and sensors endpoints are allowed")
        params = {k: v for k, v in (params or {}).items() if v is not None}
        cache_key = hashlib.sha256(json.dumps([path, params], sort_keys=True).encode()).hexdigest()
        cache_file = self.cache_dir / f"{cache_key}.json" if self.cache_dir else None
        if cache_file and cache_file.exists():
            return json.loads(cache_file.read_text(encoding="utf-8"))
        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.get(BASE_URL + path, params=params,
                                            headers={"X-API-Key": self.api_key}, timeout=30)
            except requests.RequestException as exc:
                if attempt == self.max_retries:
                    raise RuntimeError(f"OpenAQ request failed for {path}: {exc}") from exc
                time.sleep(min(2 ** attempt, 8))
                continue
            if response.status_code == 401:
                raise RuntimeError("OpenAQ rejected OPENAQ_API_KEY (HTTP 401). Check the key.")
            if response.status_code == 429 or 500 <= response.status_code < 600:
                if attempt < self.max_retries:
                    retry = response.headers.get("Retry-After", "")
                    delay = float(retry) if retry.isdigit() else min(2 ** attempt, 8)
                    LOG.warning("OpenAQ HTTP %s on %s; retrying in %.1fs", response.status_code, path, delay)
                    time.sleep(delay)
                    continue
            try:
                response.raise_for_status()
                payload = response.json()
            except (requests.RequestException, ValueError) as exc:
                raise RuntimeError(f"OpenAQ request failed for {path}: HTTP {response.status_code}") from exc
            if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
                raise ValueError(f"Unexpected OpenAQ response schema for {path}")
            if cache_file:
                cache_file.parent.mkdir(parents=True, exist_ok=True)
                cache_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            return payload
        raise AssertionError("Unreachable retry state")

    def pages(self, path: str, params: dict[str, Any], *, max_pages: int,
              page_size: int = 100) -> tuple[list[dict[str, Any]], bool]:
        if max_pages < 1 or not 1 <= page_size <= 1000:
            raise ValueError("Pagination limits must be positive; page size at most 1000")
        results: list[dict[str, Any]] = []
        for page in range(1, max_pages + 1):
            payload = self.get(path, {**params, "page": page, "limit": page_size})
            batch = payload["results"]
            results.extend(batch)
            found = (payload.get("meta") or {}).get("found")
            if len(batch) < page_size or (isinstance(found, int) and len(results) >= found):
                return results, False
        return results, True
