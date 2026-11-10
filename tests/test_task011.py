"""Focused TASK011 blend and exact released-label overlay checks."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from run_task011 import blend_diur7, overlay_exact_labels


def test_diur7_blend_is_exact_and_missing_profile_falls_back_to_pfix():
    actual = blend_diur7(np.array([20.0, 40.0, 60.0]), np.array([100.0, np.nan, 20.0]))
    np.testing.assert_array_equal(actual, np.array([40.0, 40.0, 50.0]))
    with pytest.raises(ValueError, match="weight"):
        blend_diur7(np.array([1.0]), np.array([2.0]), 1.1)


def test_overlay_uses_station_and_target_interval_end_and_preserves_private_values():
    train = pd.DataFrame({
        "location_id": [11, 11],
        "timestamp_ist": ["2026-11-10T08:00:00+05:30", "2026-11-10T09:00:00+05:30"],
        "pm25": [31.0, 32.0],
    })
    test = pd.DataFrame({
        "location_id": [11, 12, 11],
        "target_end_ist": ["2026-11-10T08:00:00+05:30", "2026-11-10T08:00:00+05:30",
                            "2026-11-11T01:00:00+05:30"],
    })
    values, matched = overlay_exact_labels(train, test, np.array([1.0, 2.0, 3.0]))
    np.testing.assert_array_equal(matched, [True, False, False])
    np.testing.assert_array_equal(values, [31.0, 2.0, 3.0])


def test_overlay_rejects_conflicting_duplicate_station_interval_map():
    train = pd.DataFrame({"location_id": [11, 11],
                          "timestamp_ist": ["2026-11-10T08:00:00Z"]*2,
                          "pm25": [31.0, 32.0]})
    test = pd.DataFrame({"location_id": [11], "target_end_ist": ["2026-11-10T08:00:00Z"]})
    with pytest.raises(ValueError, match="duplicate"):
        overlay_exact_labels(train, test, np.array([1.0]))
