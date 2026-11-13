"""Build a versioned, research-only OpenAQ dataset from the Stage 1.5 snapshot.

Raw and row-level normalized observations stay in ignored local runs. Only
aggregate metadata and quality metrics are suitable for the static frontend.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any
from zoneinfo import ZoneInfo

from .qualify_history import DEFAULT_OUTPUT as STAGE15, STAGE1
from .run_audit import ROOT, write_csv

IST = ZoneInfo("Asia/Kolkata")
OUT = ROOT / "reports/creative_submission/milestone_2"
PUBLIC = ROOT / "apps/airwindow/public/data/external_observation_research.json"
STATIONS = {11606: 12236418, 11611: 12236426, 3409510: 12238567, 3409511: 12238576}
UNIT = {"µg/m³", "μg/m³", "ug/m3", "ug/m³", "µg/m3"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def parse_utc(value: str) -> datetime:
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise ValueError(f"Timezone missing: {value}")
    return stamp.astimezone(timezone.utc)


def valid_hour(
    row: dict[str, Any], expected_sensor: int
) -> tuple[datetime, datetime, float | None]:
    if row.get("sensor_id") != expected_sensor:
        raise ValueError("Sensor identity changed in cached hourly response")
    start, end = parse_utc(row["start_utc"]), parse_utc(row["end_utc"])
    if end - start != timedelta(hours=1):
        raise ValueError("OpenAQ hourly period is not one hour")
    if row.get("unit") not in UNIT:
        raise ValueError(f"Unverified PM2.5 unit for sensor {expected_sensor}")
    value = row.get("value")
    if value is not None:
        value = float(value)
        if not math.isfinite(value):
            value = None
    return start, end, value


def classify_difference(row: dict[str, str], source: dict[str, Any]) -> tuple[str, str]:
    """Treat source flags and partial aggregation as hypotheses, never proof."""
    raw = source.get("raw") or {}
    coverage = raw.get("coverage") or {}
    if source.get("has_flags"):
        return (
            "POTENTIAL_SOURCE_REVISION",
            "Current OpenAQ hour is flagged; original source version unavailable",
        )
    count = coverage.get("observedCount")
    expected = coverage.get("expectedCount")
    if isinstance(count, int) and isinstance(expected, int) and count < expected:
        return (
            "PARTIAL_AGGREGATION_UNRESOLVED",
            f"Current OpenAQ hour has {count}/{expected} reported samples",
        )
    return "UNRESOLVED", "Same sensor and interval end; no established cause"


def agreement(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Full matched-hour agreement; correlation is descriptive, not independence."""
    errors = [abs(r["openaq_pm25"] - r["train_pm25"]) for r in rows]
    left = [r["train_pm25"] for r in rows]
    right = [r["openaq_pm25"] for r in rows]
    if not rows:
        return {"matched_hours": 0}
    lm, rm = mean(left), mean(right)
    numerator = sum((a - lm) * (b - rm) for a, b in zip(left, right))
    spread = math.sqrt(sum((a - lm) ** 2 for a in left) * sum((b - rm) ** 2 for b in right))
    return {
        "matched_hours": len(rows),
        "mean_absolute_difference": round(mean(errors), 6),
        "median_absolute_difference": round(median(errors), 6),
        "max_absolute_difference": round(max(errors), 6),
        "within_0_1": sum(round(v, 6) <= 0.1 for v in errors),
        "within_0_2": sum(round(v, 6) <= 0.2 for v in errors),
        "within_1_0": sum(round(v, 6) <= 1 for v in errors),
        "pearson_correlation": round(numerator / spread, 6) if spread else None,
    }


def _research_payload(
    inventory: list[dict[str, Any]],
    monthly: list[dict[str, str]],
    quality: list[dict[str, Any]],
    discrepancy: list[dict[str, Any]],
    agreement_rows: list[dict[str, Any]],
    instrument_by_sensor: dict[int, list[str]],
    discovered_locations: int,
    run_id: str,
    generated: str,
    source_retrieval: str,
) -> dict[str, Any]:
    current = {int(row["sensor_id"]): row for row in inventory}
    months = [r for r in monthly if r["partial_month"] == "False"]
    return {
        "schema_version": "1.0",
        "run_id": run_id,
        "generated_at_utc": generated,
        "source_retrieval_time_status": source_retrieval,
        "period_ist": {
            "from": monthly[0]["month_ist"],
            "through": monthly[-1]["month_ist"],
            "full_months": len({r["month_ist"] for r in months}),
        },
        "source": "OpenAQ API v3; provider identities retained",
        "counts": {
            "locations": discovered_locations,
            "locations_with_pm25": len({r["location_id"] for r in inventory}),
            "sensors": len(inventory),
            "sensor_months": len(monthly),
            "research_accept": sum(r["decision"] == "ACCEPT" for r in inventory),
            "research_conditional": sum(r["decision"] == "CONDITIONAL" for r in inventory),
            "research_reject": sum(r["decision"] == "REJECT" for r in inventory),
            "cpcb_sensors": sum(r["provider"] == "CPCB" for r in inventory),
            "discrepancies_over_0_2": len(discrepancy),
        },
        "sensors": [
            {
                "location_id": int(r["location_id"]),
                "sensor_id": int(r["sensor_id"]),
                "name": r["location_name"],
                "provider": r["provider"],
                "owner": r["owner"],
                "latitude": float(r["latitude"]) if r["latitude"] else None,
                "longitude": float(r["longitude"]) if r["longitude"] else None,
                "unit": r["unit"],
                "instruments": instrument_by_sensor.get(int(r["sensor_id"]), []),
                "decision": r["decision"],
                "reason": r["reason"],
                "months_at_75_percent": int(r["months_at_75_percent"]),
                "first_observed_replay_month": r["first_observed_replay_month"] or None,
                "last_observed_replay_month": r["last_observed_replay_month"] or None,
            }
            for r in inventory
        ],
        "monthly": [
            {
                "sensor_id": int(r["sensor_id"]),
                "month_ist": r["month_ist"],
                "expected_hours": int(r["expected_hours"]),
                "covered_hours": int(r["aligned_ist_hours"]),
                "coverage_percent": float(r["aligned_ist_coverage_percent"])
                if r["aligned_ist_coverage_percent"]
                else None,
                "status": r["fetch_status"],
                "partial_month": r["partial_month"] == "True",
            }
            for r in monthly
        ],
        "quality": quality,
        "agreement": agreement_rows,
        "discrepancy_status_counts": dict(Counter(r["classification"] for r in discrepancy)),
        "reconciliation": [
            {
                "station_id": station,
                "sensor_id": sensor,
                "provider": current[sensor]["provider"],
                "same_underlying_source": True,
                "discrepancies_over_0_2": sum(int(r["sensor_id"]) == sensor for r in discrepancy),
            }
            for station, sensor in STATIONS.items()
        ],
        "verification": {
            "status": "INSUFFICIENT_CONTEMPORANEOUS_VINTAGES",
            "reason": "Replay forecasts were generated retrospectively; CPCB via OpenAQ is not an independent source.",
        },
        "licensing": "CPCB upstream redistribution rights unresolved; no raw observations published",
        "operational_station_ids": list(STATIONS),
    }


def build(
    stage15: Path = STAGE15, output: Path = OUT, public: Path = PUBLIC, *, run_id: str | None = None
) -> dict[str, Any]:
    """Validate inputs before replacing the last successful derived public artifact."""
    manifest = json.loads((stage15 / "RUN_MANIFEST.json").read_text(encoding="utf-8"))
    if manifest["failures"] or manifest["truncated_sensors"]:
        raise ValueError(
            "Stage 1.5 snapshot is incomplete; retaining last successful research artifact"
        )
    for name, expected in manifest.get("input_sha256", {}).items():
        path = ROOT / name
        if not path.exists() or sha(path) != expected:
            raise ValueError(f"Source snapshot input changed: {name}; run a new live audit")
    inventory = csv_rows(stage15 / "STATION_QUALIFICATION.csv")
    monthly = csv_rows(stage15 / "MONTHLY_SENSOR_COVERAGE.csv")
    differences = csv_rows(stage15 / "DISCREPANCY_ANALYSIS.csv")
    expected_months = len(manifest["replay_months"])
    expected_differences = sum(d["over_0_2_hours"] for d in manifest["discrepancy_summaries"])
    if (
        len(inventory) != manifest["catalog_sensors"]
        or len(monthly) != len(inventory) * expected_months
        or len(differences) != expected_differences
    ):
        raise ValueError("Stage 1.5 files are inconsistent; retaining last successful artifact")
    catalog = json.loads((STAGE1 / "PM25_SENSOR_CATALOG.json").read_text(encoding="utf-8"))
    if len(catalog["results"]) != len(inventory):
        raise ValueError("Sensor catalog count differs from qualifications")
    instrument_by_sensor = {
        int(item["sensor"]["id"]): sorted(
            {
                instrument["name"]
                for instrument in (item.get("location_instruments") or [])
                if instrument.get("name")
            }
        )
        for item in catalog["results"]
    }
    stamp = datetime.now(timezone.utc).isoformat()
    run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = output / "runs" / run_id
    if run_dir.exists():
        raise FileExistsError(f"Immutable research run already exists: {run_dir}")
    # Compute and validate entirely before writing any public artifact.
    diff_by_sensor_end = {
        (int(d["sensor_id"]), parse_utc(d["hour_end_ist"])): d for d in differences
    }
    if len(diff_by_sensor_end) != len(differences):
        raise ValueError("Duplicate discrepancy keys")
    source_by_key: dict[tuple[int, datetime], dict[str, Any]] = {}
    duplicate_source_keys: set[tuple[int, datetime]] = set()
    quality: list[dict[str, Any]] = []
    normalized: list[dict[str, Any]] = []
    for sensor in inventory:
        sid = int(sensor["sensor_id"])
        path = stage15 / "raw/hourly" / f"sensor_{sid}.json"
        if not path.exists():
            if "SENSOR_ENDED_BEFORE_REPLAY" in sensor["fetch_statuses"]:
                quality.append(
                    {
                        "sensor_id": sid,
                        "location_id": int(sensor["location_id"]),
                        "observed_rows": 0,
                        "invalid_or_missing": 0,
                        "negative_values": 0,
                        "flagged_hours": 0,
                        "duplicate_hour_end": 0,
                        "usable_days_at_18_hours": 0,
                        "longest_internal_gap_hours": 0,
                        "first_utc": None,
                        "last_utc": None,
                        "unit": sensor["unit"],
                        "provider": sensor["provider"],
                        "status": "SENSOR_ENDED_BEFORE_REPLAY",
                    }
                )
                continue
            raise FileNotFoundError(f"Missing retained source hours for sensor {sid}: {path}")
        source_rows = json.loads(path.read_text(encoding="utf-8"))
        times: list[datetime] = []
        usable_day_hours: Counter[str] = Counter()
        negatives = invalids = flagged = duplicates = 0
        for source in source_rows:
            start, end, value = valid_hour(source, sid)
            key = sid, end
            if key in source_by_key:
                duplicates += 1
                duplicate_source_keys.add(key)
            else:
                source_by_key[key] = source
            times.append(start)
            if value is None:
                invalids += 1
            if value is not None and value < 0:
                negatives += 1
            if value is not None and value >= 0:
                usable_day_hours[start.astimezone(IST).date().isoformat()] += 1
            flagged += bool(source.get("has_flags"))
            normalized.append(
                {
                    "sensor_id": sid,
                    "location_id": sensor["location_id"],
                    "provider": sensor["provider"],
                    "start_utc": start.isoformat(),
                    "end_utc": end.isoformat(),
                    "value_ug_m3": value,
                    "original_unit": source["unit"],
                    "flagged": source.get("has_flags"),
                    "aggregation": "OpenAQ /sensors/{id}/hours; no local reaggregation",
                }
            )
        sorted_times = sorted(set(times))
        quality.append(
            {
                "sensor_id": sid,
                "location_id": int(sensor["location_id"]),
                "observed_rows": len(source_rows),
                "invalid_or_missing": invalids,
                "negative_values": negatives,
                "flagged_hours": flagged,
                "duplicate_hour_end": duplicates,
                "usable_days_at_18_hours": sum(n >= 18 for n in usable_day_hours.values()),
                "longest_internal_gap_hours": max(
                    (
                        (b - a).total_seconds() / 3600 - 1
                        for a, b in zip(sorted_times, sorted_times[1:])
                    ),
                    default=0,
                ),
                "first_utc": min(times).isoformat() if times else None,
                "last_utc": max(times).isoformat() if times else None,
                "unit": sensor["unit"],
                "provider": sensor["provider"],
                "status": "FETCHED",
            }
        )
    if any(sensor_id in STATIONS.values() for sensor_id, _ in duplicate_source_keys):
        raise ValueError("Existing-station OpenAQ hours contain duplicate source keys")
    investigations = []
    for key, difference in diff_by_sensor_end.items():
        source = source_by_key.get(key)
        if source is None:
            raise ValueError(f"Discrepancy source record missing: {key}")
        classification, evidence = classify_difference(difference, source)
        raw = source.get("raw") or {}
        coverage = raw.get("coverage") or {}
        investigations.append(
            {
                **difference,
                "classification": classification,
                "evidence": evidence,
                "openaq_observed_samples": coverage.get("observedCount"),
                "openaq_expected_samples": coverage.get("expectedCount"),
                "openaq_aggregation_avg": (raw.get("summary") or {}).get("avg"),
                "source_period_start_utc": source["start_utc"],
                "source_period_end_utc": source["end_utc"],
            }
        )
    counts = Counter(r["classification"] for r in investigations)
    matched: list[dict[str, Any]] = []
    seen_train_keys: set[tuple[int, datetime]] = set()
    with (ROOT / "data/raw/challenge/Train.csv").open(newline="", encoding="utf-8") as handle:
        for train in csv.DictReader(handle):
            station = int(train["location_id"])
            if station not in STATIONS or int(train["sensor_id"]) != STATIONS[station]:
                continue
            end = parse_utc(train["timestamp_ist"])
            if (station, end) in seen_train_keys:
                raise ValueError("Train contains duplicate station-hour keys")
            seen_train_keys.add((station, end))
            source = source_by_key.get((STATIONS[station], end))
            if source is None:
                continue
            _, _, value = valid_hour(source, STATIONS[station])
            if value is None:
                continue
            matched.append(
                {
                    "station_id": station,
                    "sensor_id": STATIONS[station],
                    "hour_end_ist": train["timestamp_ist"],
                    "train_pm25": float(train["pm25"]),
                    "openaq_pm25": value,
                    "openaq_flagged": bool(source.get("has_flags")),
                }
            )
    agreement_rows = [
        {
            "station_id": station,
            "sensor_id": sensor,
            **agreement([r for r in matched if r["station_id"] == station]),
        }
        for station, sensor in STATIONS.items()
    ]
    locations = json.loads((STAGE1 / "MUMBAI_LOCATION_CATALOG.json").read_text(encoding="utf-8"))
    source_retrieval = (
        manifest.get("retrieval_completed_at_utc")
        or "Not recorded by the Stage 1.5 source snapshot"
    )
    payload = _research_payload(
        inventory,
        monthly,
        quality,
        investigations,
        agreement_rows,
        instrument_by_sensor,
        len(locations["results"]),
        run_id,
        stamp,
        source_retrieval,
    )
    if payload["operational_station_ids"] != list(STATIONS) or len(payload["sensors"]) != len(
        inventory
    ):
        raise ValueError("Public artifact validation failed")
    run_dir.mkdir(parents=True)
    with gzip.open(
        run_dir / "normalized_hours.csv.gz", "wt", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(normalized[0]))
        writer.writeheader()
        writer.writerows(normalized)
    with gzip.open(
        run_dir / "discrepancy_investigation.csv.gz", "wt", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(investigations[0]))
        writer.writeheader()
        writer.writerows(investigations)
    with gzip.open(
        run_dir / "matched_observations.csv.gz", "wt", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(matched[0]))
        writer.writeheader()
        writer.writerows(matched)
    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "SENSOR_INVENTORY.csv", inventory, list(inventory[0]))
    metadata_rows = [
        {
            "location_id": row["location_id"],
            "location_name": row["location_name"],
            "sensor_id": row["sensor_id"],
            "provider": row["provider"],
            "owner": row["owner"],
            "latitude": row["latitude"],
            "longitude": row["longitude"],
            "instruments": instrument_by_sensor.get(int(row["sensor_id"]), []),
        }
        for row in inventory
    ]
    write_csv(output / "LOCATION_PROVIDER_METADATA.csv", metadata_rows, list(metadata_rows[0]))
    write_csv(output / "SENSOR_QUALITY.csv", quality, list(quality[0]))
    write_csv(output / "AGREEMENT_SUMMARY.csv", agreement_rows, list(agreement_rows[0]))
    write_csv(
        output / "DISCREPANCY_CLASSIFICATIONS.csv",
        [
            {
                "sensor_id": r["sensor_id"],
                "hour_end_ist": r["hour_end_ist"],
                "classification": r["classification"],
                "evidence": r["evidence"],
            }
            for r in investigations
        ],
        ["sensor_id", "hour_end_ist", "classification", "evidence"],
    )
    checksums = {p.name: sha(p) for p in run_dir.iterdir()}
    research_manifest = {
        "run_id": run_id,
        "generated_at_utc": stamp,
        "source_retrieval_time_status": source_retrieval,
        "api_version": "v3",
        "source_snapshot": str(stage15.relative_to(ROOT)),
        "stage15_manifest_sha256": sha(stage15 / "RUN_MANIFEST.json"),
        "catalog_sha256": sha(STAGE1 / "PM25_SENSOR_CATALOG.json"),
        "source_location_ids": sorted({int(r["location_id"]) for r in inventory}),
        "source_sensor_ids": sorted(int(r["sensor_id"]) for r in inventory),
        "requested_sensor_months": len(inventory) * expected_months,
        "retrieved_sensor_months": len(monthly),
        "retrieved_hourly_rows": len(normalized),
        "failures": manifest["failures"],
        "truncated": manifest["truncated_sensors"],
        "private_file_sha256": checksums,
        "validation": {
            "sensor_count": len(inventory),
            "difference_count": len(differences),
            "normalized_hours": len(normalized),
            "status": "PASS",
        },
        "software_version": "milestone2-v1",
    }
    (run_dir / "RUN_MANIFEST.json").write_text(
        json.dumps(research_manifest, indent=2), encoding="utf-8"
    )
    public.parent.mkdir(parents=True, exist_ok=True)
    candidate = public.with_suffix(".json.candidate")
    candidate.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    # A failed build never replaces the last known-good public artifact.
    loaded = json.loads(candidate.read_text(encoding="utf-8"))
    if loaded["counts"]["discrepancies_over_0_2"] != len(differences):
        candidate.unlink()
        raise ValueError("Static research artifact failed integrity check")
    for attempt in range(5):
        try:
            candidate.replace(public)
            break
        except PermissionError:
            if attempt == 4:
                candidate.unlink(missing_ok=True)
                raise RuntimeError(
                    "Static research artifact is locked; last successful file retained"
                )
            time.sleep(0.5 * (attempt + 1))
    research_manifest["public_sha256"] = sha(public)
    (output / "RUN_MANIFEST.json").write_text(
        json.dumps(research_manifest, indent=2), encoding="utf-8"
    )
    (output / "DISCREPANCY_REPORT.md").write_text(
        "# Discrepancy investigation\n\n"
        f"{len(differences)} of {sum(d['matched_hours'] for d in manifest['discrepancy_summaries']):,} exact-hour "
        "Train/OpenAQ pairs differ by more than 0.2 µg/m³. All are retained in the private "
        "row-level investigation.\n\n"
        + "\n".join(f"- {kind}: {n}" for kind, n in sorted(counts.items()))
        + "\n\n"
        + "\n".join(
            f"- Station {r['station_id']}: {r['matched_hours']} matches, "
            f"MAE {r['mean_absolute_difference']} µg/m³, "
            f"{r['within_0_2']} within 0.2 µg/m³"
            for r in agreement_rows
        )
        + "\n\n"
        "A flag or incomplete current-hour aggregation suggests a mechanism, but cannot prove "
        "the historical source revision. No discrepancy is marked resolved. The Stage 1.5 "
        "manifest retains the exact-hour and ±1-hour diagnostics.\n",
        encoding="utf-8",
    )
    research_manifest["derived_file_sha256"] = {
        name: sha(output / name)
        for name in (
            "SENSOR_INVENTORY.csv",
            "LOCATION_PROVIDER_METADATA.csv",
            "SENSOR_QUALITY.csv",
            "AGREEMENT_SUMMARY.csv",
            "DISCREPANCY_CLASSIFICATIONS.csv",
            "DISCREPANCY_REPORT.md",
        )
    }
    (output / "RUN_MANIFEST.json").write_text(
        json.dumps(research_manifest, indent=2), encoding="utf-8"
    )
    return research_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage15", type=Path, default=STAGE15)
    parser.add_argument("--output", type=Path, default=OUT)
    parser.add_argument("--public", type=Path, default=PUBLIC)
    parser.add_argument("--run-id")
    args = parser.parse_args()
    result = build(args.stage15, args.output, args.public, run_id=args.run_id)
    print(
        f"Research run {result['run_id']}: {result['validation']['normalized_hours']} local hours; "
        "static aggregate validated"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
