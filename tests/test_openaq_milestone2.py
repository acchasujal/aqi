"""Offline tests for the research publication boundary."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from apps.airwindow.scripts.openaq_audit.milestone2 import (
    agreement,
    build,
    classify_difference,
    parse_utc,
    valid_hour,
)
from apps.airwindow.scripts.openaq_audit.refresh_research import main as refresh_main


def test_timezones_and_interval_end_are_explicit() -> None:
    assert parse_utc("2025-05-01T05:30:00+05:30") == datetime(2025, 5, 1, tzinfo=timezone.utc)
    assert parse_utc("2025-11-02T01:30:00-04:00") == datetime(
        2025, 11, 2, 5, 30, tzinfo=timezone.utc
    )
    with pytest.raises(ValueError, match="Timezone missing"):
        parse_utc("2025-05-01T05:30:00")
    row = {
        "sensor_id": 7,
        "start_utc": "2025-05-01T00:00:00Z",
        "end_utc": "2025-05-01T01:00:00Z",
        "unit": "µg/m³",
        "value": 12.5,
    }
    assert valid_hour(row, 7)[2] == 12.5
    with pytest.raises(ValueError, match="Sensor identity"):
        valid_hour(row, 8)
    with pytest.raises(ValueError, match="not one hour"):
        valid_hour({**row, "end_utc": "2025-05-01T02:00:00Z"}, 7)
    with pytest.raises(ValueError, match="unit"):
        valid_hour({**row, "unit": "ppm"}, 7)
    assert valid_hour({**row, "value": float("nan")}, 7)[2] is None
    assert valid_hour({**row, "value": -1.5}, 7)[2] == -1.5


def test_discrepancy_classification_preserves_uncertainty() -> None:
    source = {"has_flags": False, "raw": {"coverage": {"observedCount": 4, "expectedCount": 4}}}
    assert classify_difference({}, source)[0] == "UNRESOLVED"
    assert classify_difference({}, {**source, "has_flags": True})[0] == "POTENTIAL_SOURCE_REVISION"
    assert (
        classify_difference(
            {}, {**source, "raw": {"coverage": {"observedCount": 1, "expectedCount": 4}}}
        )[0]
        == "PARTIAL_AGGREGATION_UNRESOLVED"
    )


def test_agreement_includes_all_matched_rows() -> None:
    rows = [{"train_pm25": 1.0, "openaq_pm25": 1.1}, {"train_pm25": 2.0, "openaq_pm25": 2.5}]
    result = agreement(rows)
    assert result["matched_hours"] == 2
    assert result["within_0_2"] == 1
    assert result["mean_absolute_difference"] == pytest.approx(0.3)
    assert agreement([]) == {"matched_hours": 0}


def test_failed_snapshot_cannot_replace_last_successful_public_artifact(tmp_path) -> None:
    source = tmp_path / "stage15"
    source.mkdir()
    (source / "RUN_MANIFEST.json").write_text(
        json.dumps({"failures": ["API unavailable"], "truncated_sensors": []}), encoding="utf-8"
    )
    public = tmp_path / "public.json"
    public.write_text('{"last_good":true}', encoding="utf-8")
    with pytest.raises(ValueError, match="incomplete"):
        build(source, tmp_path / "output", public)
    assert public.read_text(encoding="utf-8") == '{"last_good":true}'


def test_live_refresh_requires_environment_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENAQ_API_KEY", raising=False)
    monkeypatch.setattr("sys.argv", ["refresh_research", "--run-id", "offline-test"])
    with pytest.raises(SystemExit) as error:
        refresh_main()
    assert error.value.code == 2


def test_published_artifact_is_aggregate_only_and_reconciles() -> None:
    root = Path(__file__).resolve().parents[1]
    content = (root / "apps/airwindow/public/data/external_observation_research.json").read_text(
        encoding="utf-8"
    )
    artifact = json.loads(content)
    assert artifact["counts"]["locations"] == 43
    assert artifact["counts"]["sensors"] == len(artifact["sensors"]) == 57
    assert len(artifact["quality"]) == 57
    assert artifact["counts"]["sensor_months"] == len(artifact["monthly"]) == 1083
    assert artifact["counts"]["discrepancies_over_0_2"] == sum(
        artifact["discrepancy_status_counts"].values()
    )
    assert artifact["operational_station_ids"] == [11606, 11611, 3409510, 3409511]
    assert "value_ug_m3" not in content
    assert "train_pm25" not in content
    assert "openaq_pm25" not in content
    assert "OPENAQ_API_KEY" not in content
