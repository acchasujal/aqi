"""Provenance checks for reusable out-of-fold artifacts."""
from __future__ import annotations


def cache_manifest_matches(cached: dict, expected: dict) -> bool:
    """Accept cached OOF only when every recorded provenance field matches."""
    return cached == expected
