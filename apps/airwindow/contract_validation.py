"""Validation helpers for the AirWindow forecast artifact contract."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from itertools import pairwise
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

SCHEMA_PATH = Path(__file__).parent / "contracts" / "forecast.schema.json"
STATION_COORDINATES = {
    "11606": (19.232410, 72.868950), "11611": (19.197090, 72.822040),
    "3409510": (18.976700, 72.838000), "3409511": (19.060498, 72.923356),
}


def validate_artifact(artifact: dict[str, Any]) -> None:
    """Raise ValueError when an artifact violates the schema or temporal invariants."""
    schema_path = (SCHEMA_PATH.with_name("forecast.v1.1.schema.json")
                   if artifact.get("schema_version") == "1.1.0" else SCHEMA_PATH)
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(artifact), key=lambda error: list(error.absolute_path))
    if errors:
        details = "; ".join(
            f"/{'/'.join(str(part) for part in error.absolute_path)}: {error.message}"
            for error in errors[:8]
        )
        raise ValueError(f"Forecast artifact schema validation failed: {details}")

    model_issue = _parse_ist(artifact["model_issue_time_ist"])
    pm_cutoff = _parse_ist(artifact["pm_history_cutoff_ist"])
    generated_at = _parse_ist(artifact["generated_at_ist"])
    if pm_cutoff > model_issue:
        raise ValueError("pm_history_cutoff_ist must be no later than model_issue_time_ist")
    if generated_at < model_issue:
        raise ValueError("generated_at_ist must be no earlier than model_issue_time_ist")

    weather = artifact["weather"]
    if weather["used"] and _parse_ist(weather["issue_time_ist"]) > model_issue:
        raise ValueError("weather issue time must be no later than model issue time")

    for station in artifact["stations"]:
        latitude, longitude = STATION_COORDINATES[station["station_id"]]
        if abs(station["latitude"]-latitude) > 1e-6 or abs(station["longitude"]-longitude) > 1e-6:
            raise ValueError("Station coordinates must match the actual challenge monitor")
        forecasts = station["forecasts"]
        target_starts = [_parse_ist(row["target_start_ist"]) for row in forecasts]
        if target_starts != sorted(set(target_starts)):
            raise ValueError(f"Forecast timestamps must be unique and increasing for {station['station_id']}")
        if any(
            right - left != timedelta(hours=1)
            for left, right in pairwise(target_starts)
        ):
            raise ValueError("Forecast records must form a contiguous hourly timeline, including missing hours")

        freshness = station["freshness"]
        observation = station["last_observation_ist"]
        if observation is None:
            if freshness["status"] not in {"unknown", "missing_observation"}:
                raise ValueError("Freshness cannot be fresh or stale without a last observation timestamp")
            if freshness["observation_age_hours"] is not None:
                raise ValueError("Observation age must be null when the last observation is unknown")
        else:
            if artifact["schema_version"] == "1.1.0" and _parse_ist(observation) > pm_cutoff:
                raise ValueError("Last observation must not occur after PM history cutoff")
            if freshness["status"] == "missing_observation":
                raise ValueError("Freshness cannot be missing_observation when a timestamp is present")
            expected_age = (model_issue - _parse_ist(observation)).total_seconds() / 3600
            if expected_age < 0:
                raise ValueError("Last observation must not occur after model issue time")
            if freshness["observation_age_hours"] is not None and abs(
                freshness["observation_age_hours"] - expected_age
            ) > 1e-6:
                raise ValueError("observation_age_hours must be measured at model_issue_time_ist")
            threshold = freshness["stale_after_hours"]
            if freshness["status"] in {"fresh", "stale"} and threshold is None:
                raise ValueError("Freshness status requires an explicit stale_after_hours threshold")
            if threshold is not None and freshness["observation_age_hours"] is None:
                raise ValueError("Freshness threshold requires an explicit observation age")
            if threshold is not None:
                expected_status = "fresh" if expected_age <= threshold else "stale"
                if freshness["status"] != expected_status:
                    raise ValueError(f"Freshness status must be {expected_status} for the supplied age")

        available = 0
        missing_starts: list[str] = []
        for row, target_start in zip(forecasts, target_starts, strict=True):
            target_end = _parse_ist(row["target_end_ist"])
            if target_end - target_start != timedelta(hours=1):
                raise ValueError("Each forecast target interval must be exactly one hour")
            exact_horizon = (target_start - model_issue).total_seconds() / 3600
            horizon_hours = exact_horizon if artifact["schema_version"] == "1.1.0" else int(exact_horizon)
            if exact_horizon <= 0 or abs(row["forecast_horizon_hours"] - horizon_hours) > 1e-9:
                raise ValueError("forecast_horizon_hours must match target start minus model issue time")
            if row["status"] == "available":
                available += 1
                interval = row["prediction_interval"]
                if artifact["uncertainty"]["status"] == "calibrated" and interval is None:
                    raise ValueError("Calibrated uncertainty requires an interval for each available forecast")
                if interval is not None and not (
                    interval["lower"] <= row["pm25_prediction"] <= interval["upper"]
                ):
                    raise ValueError("Prediction interval must contain the point prediction")
            else:
                missing_starts.append(row["target_start_ist"])

        data_status = station["data_status"]
        if data_status["expected_forecast_hours"] != len(forecasts):
            raise ValueError("expected_forecast_hours must equal the number of forecast records")
        if data_status["available_forecast_hours"] != available:
            raise ValueError("available_forecast_hours must equal available forecast records")
        if data_status["missing_target_starts_ist"] != missing_starts:
            raise ValueError("missing_target_starts_ist must list exactly the missing forecast records")
        expected_status = "complete" if available == len(forecasts) else "partial" if available else "unavailable"
        if data_status["status"] != expected_status:
            raise ValueError(f"data_status must be {expected_status} for the forecast records")


def _parse_ist(value: str) -> datetime:
    """Parse an explicit IST timestamp after schema validation."""
    parsed = datetime.fromisoformat(value)
    if parsed.utcoffset() != timedelta(hours=5, minutes=30):
        raise ValueError(f"Expected Asia/Kolkata UTC+05:30 timestamp: {value}")
    return parsed
