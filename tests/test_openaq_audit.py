"""Offline contract tests for bounded OpenAQ audit tooling."""
from __future__ import annotations

from datetime import timezone

import pytest

from apps.airwindow.scripts.openaq_audit.analyse_coverage import analyse
from apps.airwindow.scripts.openaq_audit.client import OpenAQClient
from apps.airwindow.scripts.openaq_audit.common import extract_measurement, pm25_sensors, utc_time
from apps.airwindow.scripts.openaq_audit.reconcile_stations import compare_train_overlap, reconcile


class Response:
    status_code = 200
    headers = {}

    def __init__(self, results, found):
        self.results = results
        self.found = found

    def json(self):
        return {"results": self.results, "meta": {"found": self.found}}

    def raise_for_status(self):
        return None


class Session:
    def __init__(self):
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        page = kwargs["params"]["page"]
        return Response([{"id": page}], 2)


class RateLimitedSession:
    def __init__(self):
        self.calls = 0

    def get(self, *_args, **_kwargs):
        self.calls += 1
        if self.calls == 1:
            response = Response([], 0)
            response.status_code = 429
            response.headers = {"Retry-After": "1"}
            return response
        return Response([{"id": 1}], 1)


def test_pagination_uses_bounded_pages_and_key_not_in_url():
    session = Session()
    client = OpenAQClient("secret", session=session)
    rows, truncated = client.pages("/locations", {}, max_pages=2, page_size=1)
    assert rows == [{"id": 1}, {"id": 2}]
    assert not truncated
    assert len(session.calls) == 2
    assert all("secret" not in url for url, _ in session.calls)
    assert session.calls[0][1]["headers"] == {"X-API-Key": "secret"}


def test_missing_key_is_actionable(monkeypatch):
    monkeypatch.delenv("OPENAQ_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENAQ_API_KEY is unset"):
        OpenAQClient()


def test_rate_limit_retry_and_cache(monkeypatch, tmp_path):
    monkeypatch.setattr("apps.airwindow.scripts.openaq_audit.client.time.sleep", lambda _: None)
    session = RateLimitedSession()
    client = OpenAQClient("secret", session=session, cache_dir=tmp_path)
    assert client.get("/locations", {"limit": 1})["results"] == [{"id": 1}]
    assert client.get("/locations", {"limit": 1})["results"] == [{"id": 1}]
    assert session.calls == 2


def test_pm25_sensor_filter_and_timezone_normalization():
    sensors = [{"id": 1, "parameter": {"name": "pm25"}},
               {"id": 2, "parameter": {"name": "pm10"}}]
    assert pm25_sensors({"sensors": sensors}) == sensors[:1]
    assert utc_time("2026-11-10T05:30:00+05:30").hour == 0
    assert utc_time("2026-11-10T05:30:00+05:30").tzinfo == timezone.utc
    with pytest.raises(ValueError, match="no timezone"):
        utc_time("2026-11-10T05:30:00")


def test_measurement_parsing_and_missing_timestamp():
    row = {"value": 42.5, "period": {"datetimeFrom": {"utc": "2026-11-10T00:00:00Z"},
                                    "datetimeTo": {"utc": "2026-11-10T01:00:00Z"}}}
    parsed = extract_measurement(row, 123, "hourly")
    assert parsed["timestamp_utc"] == "2026-11-10T00:00:00+00:00"
    assert parsed["raw"] == row
    with pytest.raises(ValueError, match="lacks a timestamp"):
        extract_measurement({"value": 1}, 123, "raw")


def test_coverage_counts_missing_and_duplicate_hours_without_imputation():
    sensor = {"location_id": 1, "location_name": "A", "sensor": {"id": 123,
              "parameter": {"units": "µg/m³"}}}
    records = [{"sensor_id": 123, "kind": "hourly", "timestamp_utc": t, "value": value,
                "raw": {"parameter": {"units": "µg/m³"}}}
               for t, value in [("2026-11-10T00:00:00Z", 10),
                                ("2026-11-10T00:00:00Z", 11),
                                ("2026-11-10T02:00:00Z", 900)]]
    result = analyse(sensor, records, date_from="2026-11-10T00:00:00Z",
                     date_to="2026-11-10T04:00:00Z")
    assert result["hourly_observations"] == 3
    assert result["covered_hours"] == 2
    assert result["missing_hours"] == 2
    assert result["duplicate_hourly_timestamps"] == 1
    assert result["coverage_percent"] == 50
    assert result["longest_reporting_gap_hours"] == 2


def test_reconciliation_never_confirms_by_name_or_id_alone():
    station = {"station_id": 11606, "station_name": "Borivali East", "sensor_id": 7,
               "latitude": 19.2, "longitude": 72.8}
    location = {"id": 11606, "name": "Borivali East", "coordinates":
                {"latitude": 19.2, "longitude": 72.8}}
    rows = reconcile([station], [location], [{"sensor": {"id": 7}}])
    assert rows[0]["classification"] == "Possible match requiring manual verification"
    assert rows[0]["openaq_sensor_id"] == 7


def test_overlap_uses_interval_end_and_sensor_id(tmp_path):
    train = tmp_path / "Train.csv"
    train.write_text("timestamp_ist,pm25,location_id,sensor_id\n"
                     "2026-11-10T06:30:00+05:30,42,11606,7\n"
                     "2026-11-10T06:30:00+05:30,999,11606,8\n", encoding="utf-8")
    records = [{"kind": "hourly", "value": 42, "raw": {"period": {"datetimeTo":
                {"utc": "2026-11-10T01:00:00Z"}}}}]
    result = compare_train_overlap(train, {"station_id": 11606, "sensor_id": 7}, records)
    assert result == {"overlap_hours": 1, "mean_absolute_difference": 0, "exact_fraction": 1,
                      "within_0_2_fraction": 1, "max_absolute_difference": 0}
