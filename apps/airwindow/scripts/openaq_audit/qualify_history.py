"""Stage 1.5: bounded replay-month coverage and same-sensor discrepancy audit."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import median
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd
import requests

from .client import OpenAQClient
from .common import utc_time
from .run_audit import ROOT

LOG = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")
DEFAULT_OUTPUT = ROOT / "reports/creative_submission/openaq_stage1_5"
STAGE1 = ROOT / "reports/creative_submission/openaq_stage1"
REPLAY = ROOT / "apps/airwindow/public/data/replay.json"
TRAIN = ROOT / "data/raw/challenge/Train.csv"
PRIORITY_SENSOR_IDS = {12236418, 12236426, 12238567, 12238576,
                       12236435, 12235914, 12236385, 23320}


class RequestGate:
    """Limit request starts across workers to fewer than 60 per minute."""

    def __init__(self, min_interval_seconds: float = 1.1):
        self.interval = min_interval_seconds
        self.lock = threading.Lock()
        self.next_at = 0.0

    def wait(self) -> None:
        with self.lock:
            now = time.monotonic()
            delay = max(0.0, self.next_at - now)
            self.next_at = max(now, self.next_at) + self.interval
        if delay:
            time.sleep(delay)


class PacedSession:
    def __init__(self, gate: RequestGate):
        self.gate = gate
        self.session = requests.Session()

    def get(self, *args: Any, **kwargs: Any) -> requests.Response:
        self.gate.wait()
        return self.session.get(*args, **kwargs)


def replay_months(cases: list[dict[str, Any]]) -> list[tuple[str, datetime, datetime, bool]]:
    """Complete replay months, except the final month ends after its last replay day."""
    starts = [datetime.fromisoformat(c["original_start_ist"]).astimezone(IST) for c in cases]
    ends = [datetime.fromisoformat(c["original_end_ist"]).astimezone(IST) for c in cases]
    if not starts:
        raise ValueError("Replay has no cases")
    first = datetime(min(starts).year, min(starts).month, 1, tzinfo=IST)
    last_end = max(ends)
    result = []
    current = first
    while current <= last_end:
        next_month = datetime(current.year + (current.month == 12),
                              1 if current.month == 12 else current.month + 1, 1, tzinfo=IST)
        end = min(next_month, datetime.combine(last_end.date() + timedelta(days=1),
                                                datetime.min.time(), IST))
        result.append((current.strftime("%Y-%m"), current, end, end < next_month))
        current = next_month
    return result


def normalize_hour(row: dict[str, Any], sensor_id: int) -> dict[str, Any]:
    period = row.get("period") or {}
    start, end = utc_time(period.get("datetimeFrom")), utc_time(period.get("datetimeTo"))
    if start is None or end is None or end - start != timedelta(hours=1):
        raise ValueError(f"Sensor {sensor_id} has missing/non-hourly period")
    return {"sensor_id": sensor_id, "start_utc": start.isoformat(), "end_utc": end.isoformat(),
            "value": row.get("value"), "unit": (row.get("parameter") or {}).get("units"),
            "has_flags": (row.get("flagInfo") or {}).get("hasFlags"), "raw": row}


def monthly_coverage(sensor: dict[str, Any], hours: list[dict[str, Any]],
                     month: tuple[str, datetime, datetime, bool], *,
                     fetch_status: str, truncated: bool) -> dict[str, Any]:
    label, start, end, partial = month
    expected = int((end - start).total_seconds() / 3600)
    rows = [r for r in hours if start <= utc_time(r["start_utc"]).astimezone(IST) < end]
    times = sorted(utc_time(r["start_utc"]) for r in rows)
    unique = sorted(set(times))
    aligned = [t for t in unique if t.astimezone(IST).minute == 0
               and t.astimezone(IST).second == 0]
    gaps = [(b - a).total_seconds() / 3600 - 1 for a, b in zip(unique, unique[1:])]
    unit = (sensor["sensor"].get("parameter") or {}).get("units")
    observed_units = sorted({r.get("unit") for r in rows if r.get("unit")})
    status = "TRUNCATED" if truncated else fetch_status
    complete = fetch_status in {"FETCHED", "FETCHED_MONTHLY_FALLBACK",
                                "SENSOR_ENDED_BEFORE_REPLAY"} and not truncated
    return {"month_ist": label, "partial_month": partial,
            "location_id": sensor["location_id"], "location_name": sensor["location_name"],
            "sensor_id": sensor["sensor"]["id"],
            "provider": (sensor.get("provider") or {}).get("name"),
            "owner": (sensor.get("owner") or {}).get("name"),
            "expected_hours": expected, "observed_rows": len(rows),
            "unique_hourly_starts": len(unique), "missing_hours": expected - len(unique)
            if complete else None,
            "coverage_percent": round(100 * len(unique) / expected, 3) if complete else None,
            "aligned_ist_hours": len(aligned),
            "aligned_ist_coverage_percent": round(100 * len(aligned) / expected, 3)
            if complete else None,
            "start_minute_phases_ist": sorted({t.astimezone(IST).minute for t in unique}),
            "duplicate_hours": len(times) - len(unique),
            "longest_internal_missing_run_hours": max(gaps) if gaps else 0,
            "first_ist": unique[0].astimezone(IST).isoformat() if unique else None,
            "last_ist": unique[-1].astimezone(IST).isoformat() if unique else None,
            "median_interval_hours": median([(b - a).total_seconds() / 3600
                                               for a, b in zip(unique, unique[1:])])
            if len(unique) > 1 else None,
            "sensor_unit": unit, "observed_units": observed_units,
            "flagged_hours": sum(bool(r["has_flags"]) for r in rows),
            "fetch_status": status,
            "reporting_latency_hours": None}  # OpenAQ lacks first-publication timestamps.


def discrepancies(train_path: Path, station_id: int, sensor_id: int,
                  hours: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Compare matching interval ends only; preserve every >0.2 difference."""
    train = pd.read_csv(train_path, usecols=["timestamp_ist", "pm25", "location_id", "sensor_id"])
    train = train.loc[train.location_id.eq(station_id) & train.sensor_id.eq(sensor_id)
                      & train.pm25.notna()].copy()
    train["end_utc"] = pd.to_datetime(train.timestamp_ist, utc=True)
    train_by_end = train.groupby("end_utc").pm25.mean()
    matched = []
    shift_errors: dict[int, list[float]] = {-1: [], 0: [], 1: []}
    for row in hours:
        if row["value"] is None:
            continue
        end = pd.Timestamp(row["end_utc"])
        for shift in shift_errors:
            shifted_end = end + pd.Timedelta(hours=shift)
            if shifted_end in train_by_end.index:
                shift_errors[shift].append(abs(float(row["value"]) -
                                               float(train_by_end.loc[shifted_end])))
        if end in train_by_end.index:
            local = float(train_by_end.loc[end])
            diff = float(row["value"]) - local
            matched.append({"station_id": station_id, "sensor_id": sensor_id,
                            "hour_start_ist": utc_time(row["start_utc"]).astimezone(IST).isoformat(),
                            "hour_end_ist": end.tz_convert(IST).isoformat(),
                            "train_pm25": local, "openaq_pm25": float(row["value"]),
                            "signed_difference": round(diff, 6),
                            "absolute_difference": round(abs(diff), 6),
                            "openaq_unit": row["unit"], "openaq_flagged": row["has_flags"]})
    outliers = [r for r in matched if r["absolute_difference"] > 0.2]
    magnitudes = [r["absolute_difference"] for r in matched]
    summary = {"station_id": station_id, "sensor_id": sensor_id, "matched_hours": len(matched),
               "over_0_2_hours": len(outliers),
               "over_0_2_percent": round(100 * len(outliers) / len(matched), 3)
               if matched else None,
               "median_absolute_difference": median(magnitudes) if magnitudes else None,
               "max_absolute_difference": max(magnitudes) if magnitudes else None,
               "alignment_mae_by_shift_hours": {str(k): round(sum(v) / len(v), 6)
                                                if v else None for k, v in shift_errors.items()},
               "alignment_median_abs_error_by_shift_hours":
               {str(k): round(median(v), 6) if v else None for k, v in shift_errors.items()},
               "alignment_n_by_shift_hours": {str(k): len(v) for k, v in shift_errors.items()}}
    return outliers, summary


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v
                             for k, v in row.items()})


def run(*, output: Path, max_pages: int = 25, max_sensors: int = 57,
        workers: int = 4) -> dict[str, Any]:
    retrieval_started_at_utc = datetime.now(timezone.utc).isoformat()
    replay = json.loads(REPLAY.read_text(encoding="utf-8"))
    months = replay_months(replay["cases"])
    catalog = json.loads((STAGE1 / "PM25_SENSOR_CATALOG.json").read_text(encoding="utf-8"))
    sensors = catalog["results"]
    if catalog.get("status") != "LIVE_BOUNDED_DISCOVERY":
        raise ValueError("Stage 1 sensor catalog is not from live API discovery")
    sensors.sort(key=lambda s: (s["sensor"]["id"] not in PRIORITY_SENSOR_IDS,
                                s["location_id"], s["sensor"]["id"]))
    output.mkdir(parents=True, exist_ok=True)
    gate = RequestGate()
    query_from = (months[0][1].astimezone(timezone.utc) - timedelta(days=1)).isoformat()
    query_to = (months[-1][2].astimezone(timezone.utc) + timedelta(days=1)).isoformat()
    previous_manifest_path = output / "RUN_MANIFEST.json"
    previous = (json.loads(previous_manifest_path.read_text(encoding="utf-8"))
                if previous_manifest_path.exists() else {})
    reuse_hourly = (previous.get("query_from_utc") == query_from and
                    previous.get("query_to_utc") == query_to and
                    previous.get("catalog_sensors") == len(sensors))
    coverage_rows: list[dict[str, Any]] = []
    discrepancy_rows: list[dict[str, Any]] = []
    discrepancy_summaries = []
    failures = []
    sensor_retrieval: list[dict[str, Any]] = []
    monthly_fallback_sensors = list(previous.get("monthly_fallback_sensors", [])) if reuse_hourly else []
    selected = sensors[:max_sensors]
    def fetch_one(sensor: dict[str, Any]) -> tuple[list[dict[str, Any]], bool, str, str | None]:
        sid = int(sensor["sensor"]["id"])
        last = utc_time(sensor["sensor"].get("datetimeLast"))
        if last and last < months[0][1].astimezone(timezone.utc):
            return [], False, "SENSOR_ENDED_BEFORE_REPLAY", None
        record_path = output / "raw" / "hourly" / f"sensor_{sid}.json"
        if reuse_hourly and record_path.exists():
            cached = json.loads(record_path.read_text(encoding="utf-8"))
            if isinstance(cached, list) and all(r.get("sensor_id") == sid for r in cached):
                return cached, False, "FETCHED", None
        LOG.info("Fetching hourly sensor %s", sid)
        client = OpenAQClient(cache_dir=output / "raw" / "api_cache",
                              session=PacedSession(gate), max_retries=4)
        try:
            raw, truncated = client.pages(f"/sensors/{sid}/hours",
                {"datetime_from": query_from, "datetime_to": query_to},
                max_pages=max_pages, page_size=1000)
            return [normalize_hour(r, sid) for r in raw], truncated, "FETCHED", None
        except RuntimeError as exc:
            if "HTTP 408" in str(exc):
                LOG.warning("Sensor %s full-range query timed out; retrying bounded months", sid)
                try:
                    gathered = []
                    any_truncated = False
                    for _, start, end, _ in months:
                        rows, part_truncated = client.pages(f"/sensors/{sid}/hours",
                            {"datetime_from": (start.astimezone(timezone.utc) -
                                               timedelta(hours=1)).isoformat(),
                             "datetime_to": (end.astimezone(timezone.utc) +
                                             timedelta(hours=1)).isoformat()},
                            max_pages=2, page_size=1000)
                        gathered.extend(normalize_hour(r, sid) for r in rows
                                        if start <= utc_time((r.get("period") or {}).get("datetimeFrom"))
                                        .astimezone(IST) < end)
                        any_truncated |= part_truncated
                    return gathered, any_truncated, "FETCHED_MONTHLY_FALLBACK", None
                except (RuntimeError, ValueError, AttributeError) as month_exc:
                    LOG.error("Sensor %s monthly fallback failed: %s", sid, month_exc)
                    return [], False, "FETCH_FAILED", str(month_exc)
            LOG.error("Sensor %s failed: %s", sid, exc)
            return [], False, "FETCH_FAILED", str(exc)
        except ValueError as exc:
            LOG.error("Sensor %s failed: %s", sid, exc)
            return [], False, "FETCH_FAILED", str(exc)

    if workers < 1 or workers > 8:
        raise ValueError("--workers must be between 1 and 8")
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fetch_one, sensor): sensor for sensor in selected}
        for future in as_completed(futures):
            sensor = futures[future]
            sid = int(sensor["sensor"]["id"])
            records, truncated, status, error = future.result()
            if error:
                failures.append({"sensor_id": sid, "error": error})
            if status == "FETCHED_MONTHLY_FALLBACK":
                monthly_fallback_sensors.append(sid)
            LOG.info("Finished sensor %s: %s, %s hours", sid, status, len(records))
            if status in {"FETCHED", "FETCHED_MONTHLY_FALLBACK"}:
                record_path = output / "raw" / "hourly" / f"sensor_{sid}.json"
                record_path.parent.mkdir(parents=True, exist_ok=True)
                record_path.write_text(json.dumps(records), encoding="utf-8")
            sensor_retrieval.append({"location_id": int(sensor["location_id"]),
                                     "sensor_id": sid,
                                     "provider": (sensor.get("provider") or {}).get("name"),
                                     "status": status, "retrieved_hourly_rows": len(records),
                                     "raw_hourly_sha256": hashlib.sha256(record_path.read_bytes()).hexdigest()
                                     if status in {"FETCHED", "FETCHED_MONTHLY_FALLBACK"} else None})
            coverage_rows.extend(monthly_coverage(sensor, records, month,
                                 fetch_status=status, truncated=truncated) for month in months)
            if sid in {12236418, 12236426, 12238567, 12238576} and status in {
                    "FETCHED", "FETCHED_MONTHLY_FALLBACK"}:
                outliers, summary = discrepancies(TRAIN, int(sensor["location_id"]), sid, records)
                discrepancy_rows.extend(outliers)
                discrepancy_summaries.append(summary)
    coverage_rows.sort(key=lambda r: (r["sensor_id"], r["month_ist"]))
    discrepancy_rows.sort(key=lambda r: (r["sensor_id"], r["hour_end_ist"]))
    discrepancy_summaries.sort(key=lambda r: r["sensor_id"])
    failures.sort(key=lambda r: r["sensor_id"])
    monthly_fallback_sensors = sorted(set(monthly_fallback_sensors))
    sensor_retrieval.sort(key=lambda r: r["sensor_id"])
    coverage_columns = list(coverage_rows[0]) if coverage_rows else []
    diff_columns = ["station_id", "sensor_id", "hour_start_ist", "hour_end_ist", "train_pm25",
                    "openaq_pm25", "signed_difference", "absolute_difference", "openaq_unit",
                    "openaq_flagged"]
    write_csv(output / "MONTHLY_SENSOR_COVERAGE.csv", coverage_rows, coverage_columns)
    write_csv(output / "DISCREPANCY_ANALYSIS.csv", discrepancy_rows, diff_columns)
    manifest = {"source_catalog_status": catalog["status"], "replay_months": [m[0] for m in months],
                "api_version": "v3", "retrieval_started_at_utc": retrieval_started_at_utc,
                "retrieval_completed_at_utc": datetime.now(timezone.utc).isoformat(),
                "request": {"endpoint": "/sensors/{sensor_id}/hours", "page_size": 1000,
                            "max_pages": max_pages, "workers": workers},
                "input_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                                 for path in (REPLAY, STAGE1 / "PM25_SENSOR_CATALOG.json", TRAIN)},
                "query_from_utc": query_from, "query_to_utc": query_to,
                "requested_sensors": len(selected), "catalog_sensors": len(sensors),
                "max_pages_per_sensor": max_pages, "failures": failures,
                "sensor_retrieval": sensor_retrieval,
                "monthly_fallback_sensors": monthly_fallback_sensors,
                "discrepancy_summaries": discrepancy_summaries,
                "coverage_rows": len(coverage_rows),
                "truncated_sensors": sorted({r["sensor_id"] for r in coverage_rows
                                             if r["fetch_status"] == "TRUNCATED"})}
    (output / "RUN_MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--max-pages", type=int, default=25)
    parser.add_argument("--max-sensors", type=int, default=57)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    manifest = run(output=args.output, max_pages=args.max_pages, max_sensors=args.max_sensors,
                   workers=args.workers)
    LOG.info("Finished %s sensor-month rows; %s failures; %s truncated sensors",
             manifest["coverage_rows"], len(manifest["failures"]), len(manifest["truncated_sensors"]))
    return 1 if manifest["failures"] or manifest["truncated_sensors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
