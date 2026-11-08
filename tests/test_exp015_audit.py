"""Focused checks for exploratory EXP-015 seasonal sensitivities."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from mumbai_pm25.historical_archive import build_seasonal_features
from scripts.audit_exp015 import seasonal_sensitivity_from_w50


def test_w50_sensitivity_preserves_blend_and_fallback() -> None:
    baseline = np.array([30.0, 20.0, 25.0, 40.0])
    original = np.array([40.0, np.nan, 20.0, 30.0])
    alternative = np.array([50.0, 60.0, np.nan, 30.0])
    assert seasonal_sensitivity_from_w50(baseline, original, original) == pytest.approx(baseline)
    assert seasonal_sensitivity_from_w50(baseline, original, alternative) == pytest.approx(
        [35.0, 40.0, 30.0, 40.0]
    )
    with pytest.raises(ValueError, match="identical shapes"):
        seasonal_sensitivity_from_w50(baseline, original[:-1], alternative)


def test_mindspace_exclusion_and_hour_shift_are_explicit_and_deterministic() -> None:
    hours = pd.date_range("2024-11-01 08:00", periods=4, freq="D", tz="Asia/Kolkata")
    history = pd.DataFrame({
        "station_name": ["Malad West, Mumbai - IITM"] * 4 +
                        ["Mindspace-Malad West, Mumbai - MPCB"] * 4,
        "hour_start": list(hours) * 2,
        "pm25": [10.0] * 4 + [100.0] * 4,
    })
    target = pd.DataFrame({"location_id": [11611],
                           "target_start": [pd.Timestamp("2026-11-02 08:00+05:30")]})
    original = build_seasonal_features(history, target, window_days=2)
    filtered = history.loc[~history.station_name.str.contains("Mindspace-Malad")]
    corrected = build_seasonal_features(filtered, target, window_days=2)
    assert original.hist24_same_hour_mean.iloc[0] == pytest.approx(55.0)
    assert corrected.hist24_same_hour_mean.iloc[0] == pytest.approx(10.0)
    assert original.hist24_coverage.iloc[0] == 6
    assert build_seasonal_features(filtered, target, window_days=2).equals(corrected)
    shifted = history.copy()
    shifted["hour_start"] += pd.Timedelta(hours=1)
    assert np.isnan(build_seasonal_features(shifted, target, window_days=2)
                    .hist24_same_hour_mean.iloc[0])
    assert str(shifted.hour_start.dt.tz) == "Asia/Kolkata"
