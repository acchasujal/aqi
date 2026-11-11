"""Regression gates for combining main's historical APIs with reviewed P_fix."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from mumbai_pm25.forecast import (
    predict_station_baseline,
    recent_median72,
)
from mumbai_pm25.historical_archive import build_seasonal_features

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


def test_refreshed_app_forecast_matches_audited_task011_rows():
    artifact_path = ROOT / "apps/airwindow/public/data/forecast.json"
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    prediction_path = ROOT / "artifacts/submissions/task011_final_Pfix_20261110.csv"
    rows_path = prediction_path.with_suffix(".rows.csv")
    audit_path = prediction_path.with_suffix(".audit.json")
    task_manifest_path = prediction_path.with_suffix(".manifest.txt")
    rows = pd.read_csv(rows_path)
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    task_manifest = json.loads(task_manifest_path.read_text(encoding="utf-8"))
    assert audit["output_sha256"] == hashlib.sha256(prediction_path.read_bytes()).hexdigest()
    assert task_manifest["output_sha256"] == audit["output_sha256"]
    assert artifact["model"]["training_data_sha256"] == task_manifest["input_sha256"]["Train.csv"]
    assert artifact["model_issue_time_ist"] == task_manifest["model_run_time"]
    assert artifact["pm_history_cutoff_ist"] == task_manifest["pm_history_cutoff"]
    rows = rows.loc[pd.to_datetime(rows["target_start"], utc=True).dt.tz_convert("Asia/Kolkata")
                    > pd.Timestamp(artifact["model_issue_time_ist"])]
    expected = {(int(row.location_id), pd.Timestamp(row.target_start)): float(row.Target)
                for row in rows.itertuples(index=False)}
    actual = {(int(station["station_id"]), pd.Timestamp(hour["target_start_ist"])): hour["pm25_prediction"]
              for station in artifact["stations"] for hour in station["forecasts"]}
    assert actual.keys() == expected.keys()
    for key, target in expected.items():
        np.testing.assert_allclose(actual[key], target, rtol=0, atol=1e-12)
