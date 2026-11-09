"""Regression gates for combining main's historical APIs with reviewed P_fix."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from mumbai_pm25.data import load_data
from mumbai_pm25.forecast import (
    predict_station_baseline,
    predict_test_with_hist24_blend,
    recent_median72,
)
from mumbai_pm25.historical_archive import build_seasonal_features, load_2024_history

ROOT = Path(__file__).resolve().parents[1]


def test_exact_policy_and_legacy_pool_remain_separate():
    days = pd.date_range("2024-11-10 10:00", periods=3, freq="D", tz="Asia/Kolkata")
    archive = pd.DataFrame([
        {"series_id": sid, "station_name": name, "hour_start": day, "pm25": value}
        for sid, name, value in (
            ("xkdr:site_5102", "Malad West, Mumbai - IITM", 10.0),
            ("xkdr:site_5402", "Malad West, Mumbai - IITM", 30.0),
            ("xkdr:site_5807", "Mindspace-Malad West, Mumbai - MPCB", 900.0),
        ) for day in days
    ])
    target = pd.DataFrame({"location_id": [11611],
                           "target_start": [pd.Timestamp("2026-11-11 10:00", tz="Asia/Kolkata")]})
    exact = build_seasonal_features(archive, target)
    legacy = build_seasonal_features(archive, target, calendar_mode="legacy_doy")
    assert exact.hist24_same_hour_mean.iloc[0] == 20.0
    assert legacy.hist24_same_hour_mean.iloc[0] == (10+30+900)/3
    assert "site_5807" not in exact.hist24_source_ids.iloc[0]


def test_partial_hour_cutoff_excludes_unfinished_interval_in_both_baselines():
    index = pd.date_range("2026-01-01", periods=24*6, freq="h", tz="Asia/Kolkata")
    history = pd.Series(np.arange(len(index), dtype=float), index=index)
    cutoff = pd.Timestamp("2026-01-05 00:30", tz="Asia/Kolkata")
    target = pd.date_range("2026-01-10", periods=48, freq="h", tz="Asia/Kolkata")
    changed = history.copy()
    changed.loc[changed.index+pd.Timedelta(hours=1) > cutoff] = 999999.0
    eligible = history.loc[history.index+pd.Timedelta(hours=1) <= cutoff]
    expected = eligible.loc[eligible.index > cutoff-pd.Timedelta(hours=73)].median()
    assert recent_median72(changed, cutoff) == expected
    predictions = predict_station_baseline(changed, target, pm_history_cutoff=cutoff,
                                           model="median72")
    np.testing.assert_array_equal(predictions, np.full(48, expected))


def test_merged_pfix_reproduces_archived_airwindow_predictions():
    train, test, _, _ = load_data(ROOT / "data/raw/challenge")
    archive = load_2024_history(ROOT / "data/raw/challenge/AdditionalHistory.zip")
    selected = test.loc[test.target_start.isin([
        pd.Timestamp("2026-11-11 00:00", tz="Asia/Kolkata"),
        pd.Timestamp("2026-11-12 00:00", tz="Asia/Kolkata"),
    ])]
    artifact = json.loads((ROOT / "apps/airwindow/public/data/forecast.json").read_text())
    reference = {(int(s["station_id"]), pd.Timestamp(h["target_start_ist"])): h["pm25_prediction"]
                 for s in artifact["stations"] for h in s["forecasts"]}
    prediction = predict_test_with_hist24_blend(
        train, selected, archive,
        issue_time=pd.Timestamp(artifact["model_issue_time_ist"]),
        pm_history_cutoff=pd.Timestamp(artifact["pm_history_cutoff_ist"]),
    )
    expected = [reference[(int(r.location_id), r.target_start)]
                for r in selected.itertuples()]
    np.testing.assert_allclose(prediction.Target, expected, rtol=0, atol=1e-12)
