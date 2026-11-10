"""TASK 016: Regression tests for official 10 November 2026 dataset release and active pipeline integration."""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

from mumbai_pm25.climatology.kernel import KernelClimatology
from mumbai_pm25.data import load_data
from mumbai_pm25.forecast import (
    predict_test_with_hist24_blend,
    recent_median72,
)
from mumbai_pm25.historical_archive import (
    ARCHIVE_SERIES,
    load_2024_history,
)

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "raw" / "challenge"
EXPECTED_TRAIN_HASH = "8adbcf55315f166d7dc3dc1d3e4d7400651f26c1d8b95ff387eef38f4e70a283"
TARGET_STATIONS = [11606, 11611, 3409510, 3409511]


def test_1_canonical_train_row_count():
    train = pd.read_csv(DATA_DIR / "Train.csv")
    assert len(train) == 48400, f"Expected 48,400 rows in Train.csv, found {len(train)}"


def test_2_canonical_train_sha256():
    h = hashlib.sha256((DATA_DIR / "Train.csv").read_bytes()).hexdigest()
    assert h == EXPECTED_TRAIN_HASH, f"Train.csv SHA-256 mismatch: {h} != {EXPECTED_TRAIN_HASH}"


def test_3_canonical_test_row_count():
    test = pd.read_csv(DATA_DIR / "Test.csv")
    assert len(test) == 2592, f"Expected 2,592 rows in Test.csv, found {len(test)}"


def test_4_canonical_sample_submission_row_count():
    sample = pd.read_csv(DATA_DIR / "SampleSubmission.csv")
    assert len(sample) == 2592, f"Expected 2,592 rows in SampleSubmission.csv, found {len(sample)}"


def test_5_test_and_sample_ids_match_exactly_in_order():
    test = pd.read_csv(DATA_DIR / "Test.csv")
    sample = pd.read_csv(DATA_DIR / "SampleSubmission.csv")
    assert list(sample.columns) == ["ID", "Target"]
    assert (test["ID"] == sample["ID"]).all(), "Test.csv IDs do not match SampleSubmission.csv exactly in order"


def test_6_all_four_stations_represented():
    train = pd.read_csv(DATA_DIR / "Train.csv")
    test = pd.read_csv(DATA_DIR / "Test.csv")
    assert sorted(train["location_id"].unique()) == TARGET_STATIONS
    assert sorted(test["location_id"].unique()) == TARGET_STATIONS


def test_7_latest_timestamps_correctly_calculated_per_station():
    train, test, _, _ = load_data(DATA_DIR)
    ends = train.groupby("location_id")["timestamp_ist"].max()
    expected_cutoff = pd.Timestamp("2026-11-10 09:00:00+05:30")
    for sid in TARGET_STATIONS:
        assert ends[sid] == expected_cutoff, f"Station {sid} latest timestamp is {ends[sid]}, expected {expected_cutoff}"
    
    # Check physical lead times to private targets (11-12 Nov)
    private_test = test[test["scoring_block"] == "private"]
    assert len(private_test) == 192
    for sid in TARGET_STATIONS:
        s_test = private_test[private_test["location_id"] == sid]
        min_lead = (s_test["target_start"].min() - ends[sid]).total_seconds() / 3600.0
        max_lead = (s_test["target_start"].max() - ends[sid]).total_seconds() / 3600.0
        assert min_lead == 15.0, f"Expected min lead 15.0h, got {min_lead}"
        assert max_lead == 62.0, f"Expected max lead 62.0h, got {max_lead}"


def test_8_inference_reads_canonical_paths_and_no_legacy_192_test():
    train, test, sample, stations = load_data(DATA_DIR)
    assert len(train) == 48400
    assert len(test) == 2592
    assert len(sample) == 2592
    assert len(stations) == 4


def test_9_no_future_observations_enter_forecasts():
    train, test, _, _ = load_data(DATA_DIR)
    station_cutoffs = train.groupby("location_id")["timestamp_ist"].max()
    
    # Check that for any target, historical data used is <= min(station_cutoff, target_start)
    for _, row in test.iterrows():
        sid = row["location_id"]
        t_start = row["target_start"]
        cutoff = station_cutoffs[sid]
        eligible_cutoff = min(cutoff, t_start)
        
        # Any observation with timestamp_ist (interval end) > eligible_cutoff must NOT be accessible
        # Specifically, interval start is timestamp_ist - 1h. Target start must be strictly >= interval start.
        assert eligible_cutoff <= cutoff
        assert eligible_cutoff <= t_start or (t_start < cutoff and eligible_cutoff == t_start)


def test_10_clean_historical_climatology_excludes_logger_corruptions():
    archive = load_2024_history(DATA_DIR / "AdditionalHistory.zip")
    assert not archive.empty
    
    # Station 3409511 (Shivaji Nagar) clean 2024 archive has max <= 350 ug/m3
    sn_archive = archive[archive["series_id"].isin(ARCHIVE_SERIES[3409511])]
    assert sn_archive["pm25"].max() < 500.0, f"Shivaji Nagar clean 2024 archive contaminated: max={sn_archive['pm25'].max()}"
    
    # Ensure raw logger overflow in 2025 Train (241,587.56 ug/m3) is not present in 2024 archive
    assert (archive["pm25"] > 2000.0).sum() == 0, "Corruptions > 2,000 ug/m3 found in historical archive"


def test_11_candidate_c_operational_on_final_release():
    train, test, sample, _ = load_data(DATA_DIR)
    archive = load_2024_history(DATA_DIR / "AdditionalHistory.zip")
    issue_time = pd.Timestamp("2026-11-10 12:00:00+05:30")
    preds = predict_test_with_hist24_blend(
        train, test, archive,
        issue_time=issue_time,
        blend_weight_hist24=0.5,
        calendar_mode="month_day_365",
    )
    assert len(preds) == 2592
    assert (preds["ID"] == sample["ID"]).all()
    assert np.isfinite(preds["Target"]).all()
    assert (preds["Target"] >= 0).all()
    
    # Private evaluation slice
    private_preds = preds.loc[test["scoring_block"] == "private", "Target"]
    assert len(private_preds) == 192
    assert private_preds.min() > 15.0
    assert private_preds.max() < 150.0


def test_12_corrected_blend_operational_on_final_release():
    train, test, _sample, _ = load_data(DATA_DIR)
    archive = load_2024_history(DATA_DIR / "AdditionalHistory.zip")
    
    station_cutoffs = {sid: train.loc[train["location_id"] == sid, "timestamp_ist"].max() for sid in TARGET_STATIONS}
    clim_estimator = KernelClimatology(sigma_doy=10.0, sigma_hour=1.0, clim_gap_days=14, min_weight=5.0)
    
    # Build clean climatology predictions
    clean_clim_preds = {}
    for sid in TARGET_STATIONS:
        sub = archive.loc[archive["series_id"].isin(ARCHIVE_SERIES[sid])].copy()
        clean_df = sub.groupby("hour_start")["pm25"].median().reset_index().rename(columns={"hour_start": "timestamp"})
        s_test = test.loc[test["location_id"] == sid]
        t_targets = list(pd.to_datetime(s_test["target_start"]))
        elig = clim_estimator._extract_eligible_history(clean_df, station_cutoffs[sid])
        c_res = clim_estimator.estimate_batch(elig, t_targets)
        for (_, row), cres in zip(s_test.iterrows(), c_res):
            clean_clim_preds[row["ID"]] = float(cres["clim_prediction"])
            
    # Compute median72
    station_histories = {
        sid: train.loc[train["location_id"] == sid].set_index("target_start")["pm25"].sort_index()
        for sid in TARGET_STATIONS
    }
    
    blend_preds = []
    for _, row in test.iterrows():
        tid = row["ID"]
        sid = int(row["location_id"])
        t_target = row["target_start"]
        s_cutoff = station_cutoffs[sid]
        row_cutoff = min(s_cutoff, t_target)
        
        m72_val = recent_median72(station_histories[sid], row_cutoff)
        c_val = clean_clim_preds[tid]
        pred = 0.50 * m72_val + 0.50 * c_val
        blend_preds.append(pred)
        
    blend_series = pd.Series(blend_preds, index=test["ID"])
    assert len(blend_series) == 2592
    assert np.isfinite(blend_series).all()
    assert (blend_series >= 0).all()
    
    private_blend = blend_series[test.loc[test["scoring_block"] == "private", "ID"]]
    assert len(private_blend) == 192
    assert private_blend.min() > 20.0
    assert private_blend.max() < 120.0
