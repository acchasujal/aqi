"""Validate retrospective replay separately from live forecasts."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from apps.airwindow.decision_engine import Hour, compare_schedule, observed_mean


def validate_replay(artifact: dict[str, Any]) -> None:
    schema = json.loads((Path(__file__).parent / "contracts/replay.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(artifact), key=lambda error: str(error.path))
    if errors:
        raise ValueError("Replay schema: " + "; ".join(error.message for error in errors[:5]))
    if artifact["calibration"]["status"] != "not_calibrated" or artifact["provenance"]["independent_calibration"]:
        raise ValueError("This replay release cannot claim independently calibrated evidence")
    if artifact["calibration"]["probability"] is not None or artifact["calibration"]["interval"] is not None:
        raise ValueError("Uncalibrated replay must not contain probabilities or intervals")
    latest = datetime.fromisoformat(artifact["provenance"]["latest_available_observation_end_ist"])
    ids = set()
    for case in artifact["cases"]:
        if case["case_id"] in ids:
            raise ValueError("Duplicate replay case")
        ids.add(case["case_id"])
        issue = datetime.fromisoformat(case["issue_time_ist"])
        cutoff = datetime.fromisoformat(case["pm_history_cutoff_ist"])
        last = datetime.fromisoformat(case["last_pm_end_ist"])
        if not last <= cutoff <= issue:
            raise ValueError("Replay has unavailable PM information")
        hours = [Hour(datetime.fromisoformat(row["target_start_ist"]),
                      datetime.fromisoformat(row["target_end_ist"]), row["prediction"], row["observed"])
                 for row in case["hours"]]
        if any(hour.start <= issue or (hour.observed is not None and hour.end > latest) for hour in hours):
            raise ValueError("Replay targets must follow issue and observed outcomes must be released history")
        original, selected, _ = compare_schedule(hours, original_start=datetime.fromisoformat(case["original_start_ist"]),
                    duration=case["duration_hours"], earliest_start=datetime.fromisoformat(case["feasible_start_ist"]),
                    latest_end=datetime.fromisoformat(case["feasible_end_ist"]))
        if selected.start.isoformat() != case["selected_start_ist"]:
            raise ValueError("Replay selection differs from forecast-only ranking")
        if abs(selected.mean_prediction-original.mean_prediction-case["predicted_difference"]) > 1e-8:
            raise ValueError("Replay predicted comparison differs")
        observed_original, observed_selected = observed_mean(original, hours), observed_mean(selected, hours)
        expected = None if observed_original is None or observed_selected is None else observed_selected-observed_original
        if (expected is None) != (case["observed_difference"] is None):
            raise ValueError("Missing replay outcome was invented")
        if expected is not None and abs(expected-case["observed_difference"]) > 1e-8:
            raise ValueError("Replay outcome differs from actual hourly values")
        if case["station_id"] not in {"11606", "11611", "3409510", "3409511"}:
            raise ValueError("Unknown replay station")
        for window in (case["original"], case["selected"]):
            start = datetime.fromisoformat(window["start_ist"])
            end = datetime.fromisoformat(window["end_ist"])
            if end-start != timedelta(hours=case["duration_hours"]):
                raise ValueError("Replay window duration mismatch")
