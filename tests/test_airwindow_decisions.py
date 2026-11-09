"""Adversarial decision tests; synthetic values stay in tests only."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from apps.airwindow.contract_validation import validate_artifact
from apps.airwindow.decision_engine import (
    Hour,
    classify_decision,
    compare_schedule,
    enumerate_windows,
    observed_mean,
)
from apps.airwindow.replay_validation import validate_replay

IST = timezone(timedelta(hours=5, minutes=30))


def hours(values: list[float | None], observations: list[float | None] | None = None) -> list[Hour]:
    start = datetime(2025, 5, 3, 8, tzinfo=IST)
    observed = observations if observations is not None else [None]*len(values)
    return [Hour(start+timedelta(hours=i), start+timedelta(hours=i+1), value, observed[i])
            for i, value in enumerate(values)]


def test_contiguous_windows_duration_bounds_means_peaks_and_original():
    values = hours([20, 30, 10, 15, 40])
    first = values[0].start
    original, selected, candidates = compare_schedule(values, original_start=first, duration=2,
            earliest_start=first, latest_end=first+timedelta(hours=5))
    assert original.mean_prediction == 25
    assert original.max_prediction == 30
    assert original.peak_start == first+timedelta(hours=1)
    assert selected.mean_prediction == 12.5
    assert len(candidates) == 4
    assert selected.end <= first+timedelta(hours=5)
    assert observed_mean(selected, values) is None
    with pytest.raises(ValueError, match="No complete"):
        compare_schedule(values, original_start=first, duration=3, earliest_start=first,
                          latest_end=first+timedelta(hours=2))


def test_missing_forecasts_never_bridge_and_original_is_not_omitted():
    values = hours([20, None, 10, 15])
    start = values[0].start
    windows = enumerate_windows(values, duration=2, earliest_start=start, latest_end=start+timedelta(hours=4))
    assert len(windows) == 1 and windows[0].start == start+timedelta(hours=2)
    with pytest.raises(ValueError, match="Original schedule"):
        compare_schedule(values, original_start=start, duration=2, earliest_start=start, latest_end=start+timedelta(hours=4))
    with pytest.raises(ValueError, match="Duplicate"):
        enumerate_windows(values+[values[0]], duration=1, earliest_start=start, latest_end=start+timedelta(hours=4))


def test_ranking_is_invariant_to_subsequent_actual_observations():
    original = hours([30, 20, 10, 15], [1, 2, 90000, 80000])
    changed = hours([30, 20, 10, 15], [90000, 80000, 1, 2])
    params = {"original_start": original[0].start, "duration": 2,
              "earliest_start": original[0].start, "latest_end": original[-1].end}
    one = compare_schedule(original, **params)
    two = compare_schedule(changed, **params)
    assert one == two
    assert observed_mean(one[1], original) != observed_mean(two[1], changed)


def test_states_abstain_without_independently_validated_evidence():
    assert classify_decision(-10, None)["state"] == "INSUFFICIENT EVIDENCE"
    assert classify_decision(0, None)["state"] == "NO CLEAR WINNER"
    evidence = {"origins": 20, "paired_outcome_origins": 15, "median_absolute_difference_error": 4}
    assert classify_decision(-1, evidence)["state"] == "NO CLEAR WINNER"
    result = classify_decision(-10, evidence)
    assert result["state"] == "TENTATIVE IMPROVEMENT"
    assert result["probability"] is None and result["interval"] is None
    assert classify_decision(-10, {**evidence, "comparable": False})["state"] == "INSUFFICIENT EVIDENCE"
    assert classify_decision(-10, {**evidence, "paired_outcome_origins": 1})["state"] == "INSUFFICIENT EVIDENCE"
    future_gate = {**evidence, "calibration": {"status": "independently_validated", "approved_method_id": "synthetic-test-only", "comparison_passed": True}}
    assert classify_decision(-10, future_gate)["state"] == "ROBUST IMPROVEMENT"


def test_hour_alignment_and_nonfinite_values_rejected():
    hour = hours([10])[0]
    with pytest.raises(ValueError, match="finite"):
        Hour(hour.start, hour.end, float("nan"))
    with pytest.raises(ValueError, match="exact hour"):
        Hour(hour.start+timedelta(minutes=1), hour.end+timedelta(minutes=1), 10)
    with pytest.raises(ValueError, match="one-hour"):
        Hour(hour.start, hour.end+timedelta(hours=1), 10)


def test_real_artifacts_validate_and_fractional_issue_leads_are_exact():
    import json

    root = Path(__file__).resolve().parents[1] / "apps/airwindow/public/data"
    artifact = json.loads((root / "forecast.json").read_text())
    validate_artifact(artifact)
    issue = datetime.fromisoformat(artifact["model_issue_time_ist"])
    for station in artifact["stations"]:
        for row in station["forecasts"]:
            assert datetime.fromisoformat(row["target_start_ist"]) > issue
            assert row["prediction_interval"] is None
    invalid = deepcopy(artifact)
    invalid["stations"][0]["forecasts"][0]["forecast_horizon_hours"] += 0.5
    with pytest.raises(ValueError, match="forecast_horizon_hours"):
        validate_artifact(invalid)
    invalid = deepcopy(artifact)
    invalid["stations"][0]["latitude"] += 0.1
    with pytest.raises(ValueError, match="coordinates"):
        validate_artifact(invalid)
    invalid = deepcopy(artifact)
    invalid["stations"][0]["last_observation_ist"] = artifact["model_issue_time_ist"]
    with pytest.raises(ValueError, match="PM history cutoff"):
        validate_artifact(invalid)
    replay = json.loads((root / "replay.json").read_text())
    validate_replay(replay)
    assert replay["summary"]["cases"] == len(replay["cases"])
    assert replay["summary"]["recommended_cases"] == 0
    assert all(case["decision_status"] != "ROBUST IMPROVEMENT" for case in replay["cases"])
    invalid_replay = deepcopy(replay)
    invalid_replay["cases"][0]["selected_start_ist"] = invalid_replay["cases"][0]["original_start_ist"]
    if replay["cases"][0]["selected_start_ist"] == replay["cases"][0]["original_start_ist"]:
        invalid_replay["cases"][0]["predicted_difference"] = -999
    with pytest.raises(ValueError, match="selection differs|comparison differs"):
        validate_replay(invalid_replay)


def test_every_real_replay_choice_ignores_changed_outcomes_and_private_actuals_are_rejected():
    import json

    path = Path(__file__).resolve().parents[1] / "apps/airwindow/public/data/replay.json"
    replay = json.loads(path.read_text())
    for case in replay["cases"]:
        changed_hours = [Hour(datetime.fromisoformat(row["target_start_ist"]),
                              datetime.fromisoformat(row["target_end_ist"]), row["prediction"],
                              999999.0 if index % 2 else 0.0)
                         for index, row in enumerate(case["hours"])]
        _, selected, _ = compare_schedule(changed_hours,
                    original_start=datetime.fromisoformat(case["original_start_ist"]),
                    duration=case["duration_hours"], earliest_start=datetime.fromisoformat(case["feasible_start_ist"]),
                    latest_end=datetime.fromisoformat(case["feasible_end_ist"]))
        assert selected.start.isoformat() == case["selected_start_ist"]
    invalid = deepcopy(replay)
    hour = invalid["cases"][0]["hours"][0]
    hour["target_start_ist"] = "2026-11-11T08:00:00+05:30"
    hour["target_end_ist"] = "2026-11-11T09:00:00+05:30"
    hour["observed"] = 42.0
    with pytest.raises(ValueError, match="released history"):
        validate_replay(invalid)
