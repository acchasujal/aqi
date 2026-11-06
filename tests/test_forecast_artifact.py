"""Tests for the AirWindow artifact contract using synthetic test-only data."""

from copy import deepcopy
import csv
from pathlib import Path

import pytest

from apps.airwindow.contract_validation import validate_artifact


STATIONS = [
    ("11606", "Borivali East", 19.232410, 72.868950),
    ("11611", "Malad West", 19.197090, 72.822040),
    ("3409510", "Byculla", 18.976700, 72.838000),
    ("3409511", "Shivaji Nagar", 19.060498, 72.923356),
]


def synthetic_artifact() -> dict:
    """Return a synthetic fixture; this is never written to public forecast data."""
    records = []
    for station_id, name, latitude, longitude in STATIONS:
        records.append(
            {
                "station_id": station_id,
                "station_name": name,
                "latitude": latitude,
                "longitude": longitude,
                "last_observation_ist": None,
                "freshness": {
                    "status": "unknown",
                    "observation_age_hours": None,
                    "stale_after_hours": None,
                    "note": "Freshness threshold has not been configured.",
                },
                "data_status": {
                    "status": "complete",
                    "expected_forecast_hours": 1,
                    "available_forecast_hours": 1,
                    "missing_target_starts_ist": [],
                    "note": "Synthetic schema test record only.",
                },
                "validation": [
                    {
                        "horizon_hours": 2,
                        "status": "not_available",
                        "primary_metric": "full_target_rmse",
                        "rmse": None,
                        "n_targets": None,
                        "folds": None,
                        "fold_rmse_std": None,
                    }
                ],
                "forecasts": [
                    {
                        "target_start_ist": "2026-11-06T11:00:00+05:30",
                        "target_end_ist": "2026-11-06T12:00:00+05:30",
                        "pm25_prediction": 35.5,
                        "unit": "µg/m³",
                        "forecast_horizon_hours": 2,
                        "status": "available",
                        "prediction_interval": None,
                    }
                ],
            }
        )
    return {
        "schema_version": "1.0.0",
        "artifact_id": "synthetic-test-only",
        "generated_at_ist": "2026-11-06T10:00:00+05:30",
        "model_issue_time_ist": "2026-11-06T09:00:00+05:30",
        "pm_history_cutoff_ist": "2026-11-02T23:00:00+05:30",
        "model": {
            "id": "synthetic-test-model",
            "version": "test-only",
            "git_commit": None,
            "training_data_sha256": None,
        },
        "weather": {"used": False, "provider": None, "model": None, "issue_time_ist": None},
        "uncertainty": {
            "status": "not_calibrated",
            "method": None,
            "calibration_folds": None,
            "nominal_coverage": None,
            "empirical_coverage": None,
        },
        "stations": records,
    }


def test_synthetic_contract_fixture_is_valid():
    validate_artifact(synthetic_artifact())


def test_weather_requires_available_issue_metadata():
    artifact = synthetic_artifact()
    artifact["weather"] = {"used": True, "provider": None, "model": None, "issue_time_ist": None}
    with pytest.raises(ValueError, match="schema validation failed"):
        validate_artifact(artifact)


def test_valid_weather_issue_metadata_is_accepted():
    artifact = synthetic_artifact()
    artifact["weather"] = {
        "used": True,
        "provider": "test-only-provider",
        "model": "test-only-run",
        "issue_time_ist": "2026-11-06T08:00:00+05:30",
    }
    validate_artifact(artifact)


def test_unavailable_validation_metrics_must_remain_null():
    artifact = synthetic_artifact()
    artifact["stations"][0]["validation"][0]["rmse"] = 17.2
    with pytest.raises(ValueError, match="schema validation failed"):
        validate_artifact(artifact)


def test_uncalibrated_uncertainty_rejects_interval():
    artifact = synthetic_artifact()
    artifact["stations"][0]["forecasts"][0]["prediction_interval"] = {"lower": 30.0, "upper": 40.0}
    with pytest.raises(ValueError, match="schema validation failed"):
        validate_artifact(artifact)


def test_future_weather_issue_time_is_rejected():
    artifact = synthetic_artifact()
    artifact["weather"] = {
        "used": True,
        "provider": "example-provider",
        "model": "example-run",
        "issue_time_ist": "2026-11-06T10:00:00+05:30",
    }
    with pytest.raises(ValueError, match="weather issue time"):
        validate_artifact(artifact)


def test_missing_forecast_is_explicit_and_never_zero_filled():
    artifact = synthetic_artifact()
    station = artifact["stations"][0]
    station["forecasts"][0]["status"] = "missing"
    station["forecasts"][0]["pm25_prediction"] = None
    station["data_status"] = {
        "status": "unavailable",
        "expected_forecast_hours": 1,
        "available_forecast_hours": 0,
        "missing_target_starts_ist": ["2026-11-06T11:00:00+05:30"],
        "note": "Forecast not available.",
    }
    validate_artifact(artifact)
    station["forecasts"][0]["pm25_prediction"] = 0.0
    with pytest.raises(ValueError, match="schema validation failed"):
        validate_artifact(artifact)


def test_point_prediction_interval_and_target_hour_consistency():
    artifact = synthetic_artifact()
    artifact["uncertainty"] = {
        "status": "calibrated",
        "method": "test-only conformal example",
        "calibration_folds": 3,
        "nominal_coverage": 0.9,
        "empirical_coverage": 0.9,
    }
    for station in artifact["stations"]:
        station["forecasts"][0]["prediction_interval"] = {"lower": 30.0, "upper": 40.0}
    validate_artifact(artifact)
    invalid = deepcopy(artifact)
    invalid["stations"][0]["forecasts"][0]["target_end_ist"] = "2026-11-06T13:00:00+05:30"
    with pytest.raises(ValueError, match="exactly one hour"):
        validate_artifact(invalid)


def test_prediction_interval_must_contain_point_estimate():
    artifact = synthetic_artifact()
    artifact["uncertainty"] = {
        "status": "calibrated",
        "method": "test-only conformal example",
        "calibration_folds": 3,
        "nominal_coverage": 0.9,
        "empirical_coverage": 0.9,
    }
    for station in artifact["stations"]:
        station["forecasts"][0]["prediction_interval"] = {"lower": 40.0, "upper": 50.0}
    with pytest.raises(ValueError, match="must contain the point prediction"):
        validate_artifact(artifact)


def test_pm_history_cutoff_cannot_follow_model_issue_time():
    artifact = synthetic_artifact()
    artifact["pm_history_cutoff_ist"] = "2026-11-06T10:00:00+05:30"
    with pytest.raises(ValueError, match="pm_history_cutoff_ist must be no later"):
        validate_artifact(artifact)


def test_artifact_generation_cannot_precede_model_issue_time():
    artifact = synthetic_artifact()
    artifact["generated_at_ist"] = "2026-11-06T08:00:00+05:30"
    with pytest.raises(ValueError, match="generated_at_ist must be no earlier"):
        validate_artifact(artifact)


def test_freshness_threshold_requires_measured_age():
    artifact = synthetic_artifact()
    station = artifact["stations"][0]
    station["last_observation_ist"] = "2026-11-06T08:00:00+05:30"
    station["freshness"] = {
        "status": "unknown",
        "observation_age_hours": None,
        "stale_after_hours": 6,
        "note": "Synthetic test value only.",
    }
    with pytest.raises(ValueError, match="requires an explicit observation age"):
        validate_artifact(artifact)


def test_freshness_age_and_threshold_are_explicitly_consistent():
    artifact = synthetic_artifact()
    for station in artifact["stations"]:
        station["last_observation_ist"] = "2026-11-06T08:00:00+05:30"
        station["freshness"] = {
            "status": "fresh",
            "observation_age_hours": 1.0,
            "stale_after_hours": 6,
            "note": "Synthetic test value only.",
        }
    validate_artifact(artifact)
    artifact["stations"][0]["freshness"]["status"] = "stale"
    with pytest.raises(ValueError, match="Freshness status must be fresh"):
        validate_artifact(artifact)


def test_station_ids_and_coordinates_match_challenge_metadata():
    stations_path = Path(__file__).resolve().parents[1] / "data" / "raw" / "challenge" / "Stations.csv"
    with stations_path.open(encoding="utf-8-sig", newline="") as handle:
        source = {row["location_id"]: row for row in csv.DictReader(handle)}
    artifact = synthetic_artifact()
    assert {station["station_id"] for station in artifact["stations"]} == set(source)
    for station in artifact["stations"]:
        reference = source[station["station_id"]]
        assert station["latitude"] == float(reference["latitude"])
        assert station["longitude"] == float(reference["longitude"])


def test_hourly_forecast_sequence_must_include_explicit_missing_hours():
    artifact = synthetic_artifact()
    station = artifact["stations"][0]
    first = station["forecasts"][0]
    second = deepcopy(first)
    second.update(
        {
            "target_start_ist": "2026-11-06T13:00:00+05:30",
            "target_end_ist": "2026-11-06T14:00:00+05:30",
            "forecast_horizon_hours": 4,
        }
    )
    station["forecasts"].append(second)
    station["data_status"]["expected_forecast_hours"] = 2
    station["data_status"]["available_forecast_hours"] = 2
    with pytest.raises(ValueError, match="contiguous hourly timeline"):
        validate_artifact(artifact)
