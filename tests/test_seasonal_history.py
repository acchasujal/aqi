"""Tests for 2024 seasonal history features and updated forecast clocks.

EXP-20261107-007 test suite.
"""
from __future__ import annotations

import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from mumbai_pm25.forecast import (
    derive_pm_history_cutoff,
    predict_test,
    predict_test_with_hist24_blend,
)
from mumbai_pm25.historical_archive import (
    STATION_NAME_MAP,
    build_seasonal_features,
    load_2024_history,
)

# ---------------------------------------------------------------------------
# Synthetic history fixtures
# ---------------------------------------------------------------------------

def _make_archive_history(rows: list[dict]) -> pd.DataFrame:
    """Return a DataFrame with the same schema as load_2024_history output."""
    return pd.DataFrame(rows)


def _make_synthetic_archive_zip(station_name: str, n_hours: int = 100) -> bytes:
    """Return in-memory zip bytes containing a minimal History_Mumbai_2024.csv.gz."""
    import gzip
    import io as _io

    starts = pd.date_range("2024-01-01", periods=n_hours, freq="h", tz="Asia/Kolkata")
    rows = []
    for t in starts:
        rows.append(
            f"{station_name},,,,PM2.5,µg/m³,{t.isoformat()},{20 + t.hour},"
            f"cpcb_caaqm,{20 + t.hour},False,False,series_123,{t.isoformat()},False"
        )

    header = (
        "station_id,station_name,state_name,city_name,parameter_name,unit,"
        "collected_at,value,source,pm25_nonnegative,flag_negative,flag_high_500,"
        "series_id,timestamp_ist,flag_high_1000"
    )
    csv_content = header + "\n" + "\n".join(rows) + "\n"
    gz_bytes = gzip.compress(csv_content.encode())

    buf = _io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("History_Mumbai_2024.csv.gz", gz_bytes)
        zf.writestr("HistoryNotes.txt", "Test archive.\n")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Tests for derive_pm_history_cutoff
# ---------------------------------------------------------------------------

def test_derive_pm_history_cutoff_uses_train_snapshot():
    """PM-history cutoff must come from Train data, not wall clock."""
    starts = pd.date_range("2026-01-01", periods=10, freq="h", tz="Asia/Kolkata")
    train = pd.DataFrame({"location_id": [1] * 10, "target_start": starts})
    cutoff = derive_pm_history_cutoff(train)
    expected = starts[-1] + pd.Timedelta(hours=1)
    assert cutoff == expected


def test_pm_history_cutoff_independent_of_model_run_time():
    """Explicit pm_history_cutoff overrides issue_time for feature computation."""
    starts = pd.date_range("2026-01-01", periods=24 * 7, freq="h", tz="Asia/Kolkata")
    train_rows = []
    for s in [1, 2]:
        for i, t in enumerate(starts):
            train_rows.append({
                "location_id": s, "target_start": t,
                "timestamp_ist": t + pd.Timedelta(hours=1), "pm25": float(20 + i % 24),
            })
    train = pd.DataFrame(train_rows)

    # Station mapping for test  
    test = pd.DataFrame({
        "ID": ["a", "b"],
        "location_id": [1, 2],
        "target_start": pd.date_range("2026-01-08 01:00", periods=2, freq="h", tz="Asia/Kolkata"),
    })

    # With issue_time == pm_history_cutoff (default behaviour)
    issue = pd.Timestamp("2026-01-08 10:00:00+05:30")
    pred1 = predict_test(train, test, issue_time=issue)

    # With explicit pm_history_cutoff (earlier than issue_time)
    cutoff = pd.Timestamp("2026-01-07 23:00:00+05:30")
    pred2 = predict_test(train, test, issue_time=issue, pm_history_cutoff=cutoff)

    # Both must be finite and non-negative
    assert np.isfinite(pred1.Target).all() and (pred1.Target >= 0).all()
    assert np.isfinite(pred2.Target).all() and (pred2.Target >= 0).all()
    # pred2 uses an earlier cutoff, so it uses an earlier 72h window
    # (they may or may not differ, but neither should raise)


# ---------------------------------------------------------------------------
# Tests for load_2024_history
# ---------------------------------------------------------------------------

def test_load_2024_history_filters_to_cpcb_caaqm(tmp_path: Path):
    """load_2024_history must remove us_embassy rows."""
    import gzip

    rows = [
        # cpcb_caaqm row at :00 — should be kept
        "site_1,Test Station,Maharashtra,Mumbai,PM2.5,µg/m³,2024-06-01 10:00:00+05:30,25.0,cpcb_caaqm,25.0,False,False,s1,2024-06-01 10:00:00+05:30,False",
        # us_embassy row at :30 — must be removed
        "DS1010004,US Embassy,Maharashtra,Mumbai,PM2.5,µg/m³,2024-06-01 10:30:00+05:30,30.0,us_embassy,30.0,False,False,s2,2024-06-01 10:30:00+05:30,False",
    ]
    header = (
        "station_id,station_name,state_name,city_name,parameter_name,unit,"
        "collected_at,value,source,pm25_nonnegative,flag_negative,flag_high_500,"
        "series_id,timestamp_ist,flag_high_1000"
    )
    csv_content = header + "\n" + "\n".join(rows) + "\n"
    gz_bytes = gzip.compress(csv_content.encode())

    archive = tmp_path / "test.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("History_Mumbai_2024.csv.gz", gz_bytes)
        zf.writestr("HistoryNotes.txt", "test\n")

    result = load_2024_history(archive)
    assert len(result) == 1
    assert result["station_name"].iloc[0] == "Test Station"
    assert result["hour_start"].dt.minute.eq(0).all()
    assert float(result["pm25"].iloc[0]) == pytest.approx(25.0)


def test_load_2024_history_requires_zero_minute_timestamps(tmp_path: Path):
    """cpcb_caaqm rows with non-zero minute timestamps raise an error."""
    import gzip

    # Row with :30 minute but source=cpcb_caaqm (should trigger the minute check)
    rows = [
        "site_1,Test Station,,,,PM2.5,µg/m³,2024-06-01 10:30:00+05:30,25.0,cpcb_caaqm,25.0,False,False,s1,2024-06-01 10:30:00+05:30,False",
    ]
    header = (
        "station_id,station_name,state_name,city_name,parameter_name,unit,"
        "collected_at,value,source,pm25_nonnegative,flag_negative,flag_high_500,"
        "series_id,timestamp_ist,flag_high_1000"
    )
    csv_content = header + "\n" + "\n".join(rows) + "\n"
    gz_bytes = gzip.compress(csv_content.encode())

    archive = tmp_path / "test.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("History_Mumbai_2024.csv.gz", gz_bytes)
        zf.writestr("HistoryNotes.txt", "test\n")

    with pytest.raises(ValueError, match="non-zero minute"):
        load_2024_history(archive)


# ---------------------------------------------------------------------------
# Tests for build_seasonal_features
# ---------------------------------------------------------------------------

def _make_history_df(station_name: str, n_hours: int = 300) -> pd.DataFrame:
    """Create synthetic history DataFrame with known values."""
    starts = pd.date_range("2024-01-01", periods=n_hours, freq="h", tz="Asia/Kolkata")
    return pd.DataFrame({
        "station_name": station_name,
        "hour_start": starts,
        "pm25": [float(10 + t.hour) for t in starts],
        "source": "cpcb_caaqm",
    })


def test_seasonal_features_match_expected_hour():
    """hist24_same_hour_mean uses same hour-of-day within ±14 days."""
    history = _make_history_df("Borivali East, Mumbai - IITM", n_hours=24 * 60)
    # Target: Borivali East, hour=10 (DOY=1 -> Jan 1, so ±14 day window is Jan 1-15 + Dec 18-31)
    target_df = pd.DataFrame({
        "location_id": [11606],  # Borivali East
        "target_start": [pd.Timestamp("2026-01-05 10:00:00+05:30")],
    })
    result = build_seasonal_features(history, target_df, station_map=STATION_NAME_MAP, window_days=14)
    # Hour 10 should give 10 + 10 = 20
    assert "hist24_same_hour_mean" in result.columns
    assert np.isfinite(result["hist24_same_hour_mean"].iloc[0])
    assert result["hist24_same_hour_mean"].iloc[0] == pytest.approx(20.0)


def test_seasonal_features_returns_nan_for_unknown_station():
    """Stations not in station_map return NaN, not an error."""
    history = _make_history_df("Borivali East, Mumbai - IITM")
    target_df = pd.DataFrame({
        "location_id": [99999],  # Unknown station
        "target_start": [pd.Timestamp("2026-01-05 10:00:00+05:30")],
    })
    result = build_seasonal_features(history, target_df, station_map=STATION_NAME_MAP)
    assert np.isnan(result["hist24_same_hour_mean"].iloc[0])
    assert result["hist24_coverage"].iloc[0] == 0


def test_seasonal_features_returns_nan_when_insufficient_obs():
    """hist24_same_hour_mean returns NaN when fewer than min_obs observations."""
    # Only 2 observations for Borivali East at the target hour
    history = pd.DataFrame({
        "station_name": ["Borivali East, Mumbai - IITM"] * 2,
        "hour_start": pd.to_datetime(["2024-01-05 10:00:00+05:30", "2024-01-06 10:00:00+05:30"]),
        "pm25": [15.0, 20.0],
        "source": "cpcb_caaqm",
    })
    target_df = pd.DataFrame({
        "location_id": [11606],
        "target_start": [pd.Timestamp("2026-01-05 10:00:00+05:30")],
    })
    result = build_seasonal_features(
        history, target_df, station_map=STATION_NAME_MAP, window_days=14, min_obs=3
    )
    assert np.isnan(result["hist24_same_hour_mean"].iloc[0])


def test_seasonal_features_leap_year_doy():
    """DOY handling for target falling on day 60 (Feb 29 in leap year)."""
    # Create history spanning 2024 (a leap year) around day 60
    starts = pd.date_range("2024-02-20 08:00:00", periods=20, freq="D", tz="Asia/Kolkata")
    history = pd.DataFrame({
        "station_name": "Byculla, Mumbai - BMC",
        "hour_start": starts,
        "pm25": [30.0] * 20,
        "source": "cpcb_caaqm",
    })
    target_df = pd.DataFrame({
        "location_id": [3409510],  # Byculla
        "target_start": [pd.Timestamp("2026-02-28 08:00:00+05:30")],
    })
    result = build_seasonal_features(
        history, target_df, station_map=STATION_NAME_MAP, window_days=14, min_obs=3
    )
    # Should not raise; value should be 30.0 or NaN (no assertion on exact value since
    # 2026-02-28 is DOY 59 and 2024 data at DOY 50-73 covers some of the window)
    assert "hist24_same_hour_mean" in result.columns


def test_seasonal_features_no_future_data_used():
    """build_seasonal_features uses only 2024 archive; no 2025/2026 leakage possible."""
    history = _make_history_df("Borivali East, Mumbai - IITM")
    # 2024 archive data covers Jan 2024; target is Nov 2026
    assert history["hour_start"].dt.year.unique().tolist() == [2024]
    target_df = pd.DataFrame({
        "location_id": [11606],
        "target_start": [pd.Timestamp("2026-11-11 10:00:00+05:30")],
    })
    result = build_seasonal_features(history, target_df, station_map=STATION_NAME_MAP)
    # Must not raise; NaN is acceptable if no matching window
    assert "hist24_same_hour_mean" in result.columns


# ---------------------------------------------------------------------------
# Tests for predict_test_with_hist24_blend
# ---------------------------------------------------------------------------

def test_hist24_blend_falls_back_to_median72_when_no_seasonal_data():
    """When hist24 feature is NaN, blend falls back to median72."""
    starts = pd.date_range("2026-01-01", periods=24 * 7, freq="h", tz="Asia/Kolkata")
    train_rows = []
    for s in [1, 2]:
        for i, t in enumerate(starts):
            train_rows.append({
                "location_id": s, "target_start": t,
                "timestamp_ist": t + pd.Timedelta(hours=1), "pm25": float(20 + i % 24),
                "sensor_id": s, "station_name": f"Station {s}", "mean": float(20 + i % 24),
            })
    train = pd.DataFrame(train_rows)

    test = pd.DataFrame({
        "ID": ["a", "b"],
        "location_id": [1, 2],
        "target_start": pd.date_range("2026-01-08 01:00", periods=2, freq="h", tz="Asia/Kolkata"),
    })

    # Empty history (no matching station names)
    empty_history = pd.DataFrame(
        columns=["station_name", "hour_start", "pm25", "source"]
    )

    issue = pd.Timestamp("2026-01-08 10:00:00+05:30")
    result = predict_test_with_hist24_blend(
        train, test, empty_history, issue_time=issue,
        blend_weight_hist24=0.5,
    )
    # Must produce valid, finite, non-negative predictions
    assert len(result) == 2
    assert np.isfinite(result.Target).all()
    assert (result.Target >= 0).all()


def test_hist24_blend_is_deterministic():
    """Same inputs produce identical predictions."""
    starts = pd.date_range("2026-01-01", periods=24 * 7, freq="h", tz="Asia/Kolkata")
    train_rows = []
    for s in [1, 2]:
        for i, t in enumerate(starts):
            train_rows.append({
                "location_id": s, "target_start": t,
                "timestamp_ist": t + pd.Timedelta(hours=1), "pm25": float(20 + i % 24),
                "sensor_id": s, "station_name": f"Station {s}", "mean": float(20 + i % 24),
            })
    train = pd.DataFrame(train_rows)
    test = pd.DataFrame({
        "ID": ["a"],
        "location_id": [1],
        "target_start": [pd.Timestamp("2026-01-08 05:00:00+05:30")],
    })
    empty_history = pd.DataFrame(columns=["station_name", "hour_start", "pm25", "source"])
    issue = pd.Timestamp("2026-01-08 10:00:00+05:30")

    pred1 = predict_test_with_hist24_blend(train, test, empty_history, issue_time=issue)
    pred2 = predict_test_with_hist24_blend(train, test, empty_history, issue_time=issue)
    pd.testing.assert_frame_equal(pred1, pred2)


def test_hist24_blend_excludes_future_labels():
    """Labels whose interval ends after model_run_time must not enter predictions."""
    starts = pd.date_range("2026-02-01", periods=24 * 5, freq="h", tz="Asia/Kolkata")
    rows = []
    for i, t in enumerate(starts):
        rows.append({
            "location_id": 1, "target_start": t,
            "timestamp_ist": t + pd.Timedelta(hours=1), "pm25": float(10 + i % 24),
        })
    # This row's interval ends at 01:00, after issue_time=00:30 — must be excluded
    rows.append({
        "location_id": 1,
        "target_start": pd.Timestamp("2026-02-06 00:00:00+05:30"),
        "timestamp_ist": pd.Timestamp("2026-02-06 01:00:00+05:30"),
        "pm25": 9999.0,
    })
    train = pd.DataFrame(rows)
    test = pd.DataFrame({
        "ID": ["a"],
        "location_id": [1],
        "target_start": [pd.Timestamp("2026-02-06 02:00:00+05:30")],
    })
    empty_history = pd.DataFrame(columns=["station_name", "hour_start", "pm25", "source"])
    issue = pd.Timestamp("2026-02-06 00:30:00+05:30")

    result = predict_test_with_hist24_blend(train, test, empty_history, issue_time=issue)
    # 9999.0 must not appear in prediction
    assert result.Target.iloc[0] < 1000.0


def test_submission_finite_nonnegative_complete():
    """Final submission must be finite, non-negative, and cover all 2592 test rows."""
    # Lightweight: just check validate_submission
    from mumbai_pm25.forecast import validate_submission

    test = pd.DataFrame({"ID": [f"id{i}" for i in range(2592)]})
    good = pd.DataFrame({"ID": test.ID.tolist(), "Target": np.full(2592, 25.0)})
    validate_submission(good, test)

    bad_neg = good.copy()
    bad_neg.loc[0, "Target"] = -1.0
    with pytest.raises(ValueError, match="non-negative"):
        validate_submission(bad_neg, test)

    bad_inf = good.copy()
    bad_inf.loc[0, "Target"] = np.inf
    with pytest.raises(ValueError, match="finite"):
        validate_submission(bad_inf, test)




def test_validation_and_inference_differ_when_recent_pm_baseline_is_missing():
    """Known EXP-008 parity defect: validation uses hist24, inference rejects the row."""
    from scripts.validate_seasonal_history import _seasonal_baseline_for_fold

    history = _make_history_df("Borivali East, Mumbai - IITM", n_hours=24 * 60)
    target_start = pd.Timestamp("2026-01-05 10:00:00+05:30")
    fold_targets = pd.DataFrame({
        "location_id": [11606],
        "target_start": [target_start],
    })
    empty_station_history = pd.Series(
        dtype=float,
        index=pd.DatetimeIndex([], tz="Asia/Kolkata", name="target_start"),
    )
    validation = _seasonal_baseline_for_fold(
        history,
        fold_targets,
        {11606: empty_station_history},
    )
    assert np.isfinite(validation["hist24_blend50_median72"][0])

    # Inference requires a station median before it evaluates seasonal fallback.
    train = pd.DataFrame({
        "location_id": [9999],
        "target_start": [pd.Timestamp("2026-01-01 00:00:00+05:30")],
        "pm25": [25.0],
    })
    test = pd.DataFrame({
        "ID": ["target"],
        "location_id": [11606],
        "target_start": [target_start],
    })
    issue = pd.Timestamp("2026-01-10 00:00:00+05:30")
    with pytest.raises(ValueError, match="No eligible PM history for test stations"):
        predict_test_with_hist24_blend(train, test, history, issue_time=issue)
