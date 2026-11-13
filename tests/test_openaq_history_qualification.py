"""Offline tests for replay-month OpenAQ qualification."""
from __future__ import annotations

from apps.airwindow.scripts.openaq_audit.qualify_history import (
    discrepancies,
    monthly_coverage,
    normalize_hour,
    RequestGate,
    replay_months,
)
from apps.airwindow.scripts.openaq_audit.summarize_qualification import decide, longest_run


def sensor():
    return {"location_id": 11606, "location_name": "Borivali East", "provider": {"name": "CPCB"},
            "owner": {"name": "IITM"}, "sensor": {"id": 7,
            "parameter": {"name": "pm25", "units": "µg/m³"}}}


def hour(start, end, value=42):
    return normalize_hour({"value": value, "parameter": {"units": "µg/m³"},
                           "period": {"datetimeFrom": {"utc": start},
                                      "datetimeTo": {"utc": end}}}, 7)


def test_replay_months_final_month_is_partial():
    cases = [{"original_start_ist": "2025-05-03T09:00:00+05:30",
              "original_end_ist": "2025-05-03T10:00:00+05:30"},
             {"original_start_ist": "2025-06-01T10:00:00+05:30",
              "original_end_ist": "2025-06-01T11:00:00+05:30"}]
    months = replay_months(cases)
    assert [m[0] for m in months] == ["2025-05", "2025-06"]
    assert months[0][3] is False
    assert months[1][3] is True
    assert (months[1][2] - months[1][1]).total_seconds() == 24 * 3600


def test_hourly_coverage_uses_ist_start_and_counts_duplicate():
    month = replay_months([{"original_start_ist": "2025-05-03T09:00:00+05:30",
                            "original_end_ist": "2025-05-03T10:00:00+05:30"},
                           {"original_start_ist": "2025-06-01T09:00:00+05:30",
                            "original_end_ist": "2025-06-01T10:00:00+05:30"}])[0]
    rows = [hour("2025-04-30T18:30:00Z", "2025-04-30T19:30:00Z"),
            hour("2025-04-30T18:30:00Z", "2025-04-30T19:30:00Z"),
            hour("2025-04-30T20:30:00Z", "2025-04-30T21:30:00Z")]
    result = monthly_coverage(sensor(), rows, month, fetch_status="FETCHED", truncated=False)
    assert result["expected_hours"] == 24 * 31
    assert result["unique_hourly_starts"] == 2
    assert result["aligned_ist_coverage_percent"] == result["coverage_percent"]
    assert result["duplicate_hours"] == 1
    assert result["longest_internal_missing_run_hours"] == 1
    assert result["missing_hours"] == 24 * 31 - 2


def test_failed_or_truncated_fetch_does_not_claim_zero_coverage():
    month = replay_months([{"original_start_ist": "2025-05-03T09:00:00+05:30",
                            "original_end_ist": "2025-05-03T10:00:00+05:30"}])[0]
    failed = monthly_coverage(sensor(), [], month, fetch_status="FETCH_FAILED", truncated=False)
    truncated = monthly_coverage(sensor(), [], month, fetch_status="FETCHED", truncated=True)
    recovered = monthly_coverage(sensor(), [], month,
                                 fetch_status="FETCHED_MONTHLY_FALLBACK", truncated=False)
    assert failed["coverage_percent"] is None and failed["missing_hours"] is None
    assert truncated["coverage_percent"] is None and truncated["fetch_status"] == "TRUNCATED"
    assert recovered["coverage_percent"] == 0


def test_discrepancy_threshold_and_interval_end(tmp_path):
    train = tmp_path / "Train.csv"
    train.write_text("timestamp_ist,pm25,location_id,sensor_id\n"
                     "2025-05-01T01:00:00+05:30,42,11606,7\n"
                     "2025-05-01T02:00:00+05:30,50,11606,7\n"
                     "2025-05-01T02:00:00+05:30,900,11606,8\n", encoding="utf-8")
    rows = [hour("2025-04-30T18:30:00Z", "2025-04-30T19:30:00Z", 42.1),
            hour("2025-04-30T19:30:00Z", "2025-04-30T20:30:00Z", 50.3)]
    outliers, summary = discrepancies(train, 11606, 7, rows)
    assert summary["matched_hours"] == 2
    assert summary["over_0_2_hours"] == 1
    assert summary["alignment_mae_by_shift_hours"]["0"] < 1
    assert len(outliers) == 1
    assert outliers[0]["hour_end_ist"] == "2025-05-01T02:00:00+05:30"


def test_request_gate_spaces_calls_without_a_live_key(monkeypatch):
    clock = [0.0]
    monkeypatch.setattr("apps.airwindow.scripts.openaq_audit.qualify_history.time.monotonic",
                        lambda: clock[0])
    monkeypatch.setattr("apps.airwindow.scripts.openaq_audit.qualify_history.time.sleep",
                        lambda seconds: clock.__setitem__(0, clock[0] + seconds))
    gate = RequestGate(1.1)
    gate.wait()
    gate.wait()
    assert clock[0] == 1.1


def test_qualification_is_conservative_and_deterministic():
    rows = [{"fetch_status": "FETCHED", "start_minute_phases_ist": "[0]",
             "partial_month": "False", "aligned_ist_coverage_percent": "80"}
            for _ in range(18)]
    assert decide(sensor(), rows)[0] == "ACCEPT"
    assert decide(sensor(), [{**r, "fetch_status": "FETCH_FAILED"} for r in rows])[0] == "CONDITIONAL"
    assert decide(sensor(), [{**r, "fetch_status": "SENSOR_ENDED_BEFORE_REPLAY"}
                             for r in rows])[0] == "REJECT"
    airnow = {**sensor(), "provider": {"name": "AirNow"}}
    assert decide(airnow, rows)[0] == "CONDITIONAL"
    assert decide(sensor(), rows, {"max_absolute_difference": 2000})[0] == "CONDITIONAL"
    assert longest_run([True, True, False, True, True, True]) == 3
