"""Run bounded OpenAQ Mumbai discovery and write explicit evidence/status reports.

Example: py -3 -m apps.airwindow.scripts.openaq_audit.run_audit --date-from
2026-10-01T00:00:00Z --date-to 2026-11-11T00:00:00Z
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .analyse_coverage import analyse
from .client import OpenAQClient
from .discover_locations import MUMBAI_BBOX, discover
from .download_measurements import download
from .inspect_sensors import inspect
from .reconcile_stations import compare_train_overlap, load_airwindow_stations, reconcile
from .common import utc_time

ROOT = Path(__file__).resolve().parents[4]
DEFAULT_OUTPUT = ROOT / "reports/creative_submission/openaq_stage1"
STATIONS = ROOT / "data/raw/challenge/Stations.csv"
PRIORITY_NAMES = ("bandra kurla", "powai", "worli", "deonar")
LOG = logging.getLogger(__name__)
COVERAGE_COLUMNS = ["location_id", "location_name", "sensor_id", "provider", "unit",
                    "units_seen", "raw_observations", "hourly_observations", "first_observation_utc",
                    "last_observation_utc", "first_observation_ist", "last_observation_ist",
                    "expected_hours", "covered_hours", "coverage_percent",
                    "missing_hours", "missing_percent", "duplicate_hourly_timestamps",
                    "duplicate_raw_timestamps", "longest_reporting_gap_hours",
                    "median_interval_hours", "median_raw_interval_minutes", "min_value", "max_value", "usable_days",
                    "stale_at_window_end", "truncated", "quality_flags"]
RECON_COLUMNS = ["station_id", "station_name", "local_sensor_id", "openaq_location_id",
                 "openaq_sensor_id", "distance_m", "classification", "evidence",
                 "provider", "owner", "overlap_hours", "mean_absolute_difference", "exact_fraction",
                 "within_0_2_fraction", "max_absolute_difference"]


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict))
                             else value for key, value in row.items()})


def render_reports(output: Path, *, status: str, locations: list[dict[str, Any]],
                   sensors: list[dict[str, Any]], coverage: list[dict[str, Any]],
                   matches: list[dict[str, Any]], date_from: str, date_to: str,
                   caveats: list[str]) -> None:
    output.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).isoformat()
    for filename, rows in (("MUMBAI_LOCATION_CATALOG.json", locations),
                           ("PM25_SENSOR_CATALOG.json", sensors)):
        (output / filename).write_text(json.dumps({"status": status, "generated_at_utc": stamp,
             "date_from_utc": date_from, "date_to_utc": date_to, "results": rows}, indent=2),
             encoding="utf-8")
    write_csv(output / "HOURLY_COVERAGE_REPORT.csv", coverage, COVERAGE_COLUMNS)
    write_csv(output / "STATION_RECONCILIATION.csv", matches, RECON_COLUMNS)
    usable = [r for r in coverage if r["coverage_percent"] is not None
              and r["coverage_percent"] >= 75 and not r["truncated"]
              and "unit_incompatible_or_unverified" not in r["quality_flags"]]
    usable_mumbai = sum("mumbai" in r["location_name"].lower() and
                        "navi mumbai" not in r["location_name"].lower() for r in usable)
    zero_hourly = sum(r["hourly_observations"] == 0 for r in coverage)
    duplicate_hours = sum(r["duplicate_hourly_timestamps"] for r in coverage)
    stale_count = sum(r["stale_at_window_end"] for r in coverage)
    confirmed = [r for r in matches if r["classification"] ==
                 "Confirmed same physical station and source"]
    cpcb_count = sum((s.get("provider") or {}).get("name") == "CPCB"
                     for s in sensors if isinstance(s.get("provider"), dict))
    lines = ["# OpenAQ Mumbai data quality report", "", f"Status: **{status}**. Generated {stamp}.",
             "", f"Requested UTC interval: {date_from} to {date_to} (end exclusive).",
             "", f"Discovered locations: {len(locations)}; PM2.5 sensors: {len(sensors)}; "
             f"75%+ coverage candidates in sampled interval: {len(usable)}.", "",
             "Coverage is measured only in the requested interval. A truncated request cannot "
             "establish complete coverage. Values outside the interval are retained in raw data.", "",
             "## Limitations", ""] + [f"- {item}" for item in caveats]
    for row in coverage:
        lines.extend(["", f"## Sensor {row['sensor_id']} — {row['location_name']}", "",
            f"Hourly records: {row['hourly_observations']}; coverage: {row['coverage_percent']}%; "
            f"hourly duplicates: {row['duplicate_hourly_timestamps']}; raw duplicates: "
            f"{row['duplicate_raw_timestamps']}; median raw interval: "
            f"{row['median_raw_interval_minutes']} min; longest internal gap: "
            f"{row['longest_reporting_gap_hours']} h; usable days: {row['usable_days']}; "
            f"unit: {row['unit']}; value range: {row['min_value']}–{row['max_value']}.",
            f"Flags: {', '.join(row['quality_flags']) or 'none in sampled interval'}."])
    lines.extend(["", "OpenAQ does not expose a verified first-publication timestamp in these "
                  "responses, so measurement reporting latency cannot be calculated reliably."])
    (output / "DATA_QUALITY_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    recommendations = []
    confirmed_sensor_ids = {int(r["openaq_sensor_id"]) for r in confirmed
                            if r["openaq_sensor_id"]}
    for row in coverage:
        verdict = ("ACCEPT" if row in usable and not row["stale_at_window_end"]
                   and not row["quality_flags"] else "CONDITIONAL"
                   if row in usable or row["coverage_percent"] >= 50 else "REJECT")
        note = ("same CPCB source as AirWindow; no independent verification"
                if int(row["sensor_id"]) in confirmed_sensor_ids else
                "requires source agreement check")
        recommendations.append(f"| {row['location_name']} | {row['sensor_id']} | {verdict} | "
                               f"{row['coverage_percent']}% sampled hourly coverage; "
                               f"{', '.join(row['quality_flags']) or note} |")
    if not recommendations:
        recommendations = ["| None verified | — | UNASSESSED | Live measurements unavailable |"]
    station_lines = ["| AirWindow station ID | OpenAQ location ID | OpenAQ PM2.5 sensor ID | "
                     "Provider | Aligned hours | Within 0.2 µg/m³ | Mean abs. difference | Classification |",
                     "|---:|---:|---:|---|---:|---:|---:|---|"]
    for row in matches:
        if row["openaq_location_id"] == row["station_id"] or not row["openaq_location_id"]:
            station_lines.append(f"| {row['station_id']} | {row['openaq_location_id'] or '—'} | "
                                 f"{row['openaq_sensor_id'] or '—'} | {row.get('provider') or '—'} | "
                                 f"{row.get('overlap_hours', '—')} | "
                                 f"{row.get('within_0_2_fraction', '—')} | "
                                 f"{row.get('mean_absolute_difference', '—')} | "
                                 f"{row['classification']} |")
    if confirmed:
        station_lines.extend(["", "The comparisons align OpenAQ hourly period ends with "
            "Train `timestamp_ist` interval ends. Most values agree within 0.2 µg/m³, "
            "but rare larger differences remain unexplained; see the CSV maximum absolute "
            "difference column. Matching provider and series IDs establish shared provenance, "
            "not independent forecast validation."])
    priority_rows = [r for r in coverage if r in usable and
                     int(r["sensor_id"]) not in confirmed_sensor_ids and
                     (any(name in r["location_name"].lower() for name in PRIORITY_NAMES)
                      or r["provider"] == "AirNow")]
    priority_lines = ["| Location | Sensor ID | Provider | Sampled hourly coverage |",
                      "|---|---:|---|---:|"]
    priority_lines.extend(f"| {r['location_name']} | {r['sensor_id']} | {r['provider']} | "
                          f"{r['coverage_percent']}% |" for r in priority_rows)
    first_seen = min((r["first_observation_ist"] for r in coverage
                      if r["first_observation_ist"]), default="unavailable")
    last_seen = max((r["last_observation_ist"] for r in coverage
                     if r["last_observation_ist"]), default="unavailable")
    main = ["# AirWindow OpenAQ Mumbai stage 1 audit", "", f"**Status: {status}.** Generated {stamp}.", "",
            "## Evidence and answers", "", f"- Mumbai locations discovered: **{len(locations)}** in bounded bbox "
            f"{MUMBAI_BBOX}; PM2.5 sensors: **{len(sensors)}**.",
            f"- Sufficient sampled hourly coverage (>=75%): **{len(usable)}** sensors in the "
            f"bbox, including **{usable_mumbai}** at locations named Mumbai. This is a screening "
            "threshold, not an integration approval.",
            f"- Existing AirWindow matches confirmed with aligned local observations: "
            f"**{len(confirmed)}**; see STATION_RECONCILIATION.csv.",
            "- Additional promising stations: see discovery shortlist below; no production "
            "stations are added by this audit.",
            f"- Actual measured range in the sampled window (IST): {first_seen} to {last_seen}.",
            "- Missing data, observation regularity, and stale sensors: see HOURLY_COVERAGE_REPORT.csv "
            "and DATA_QUALITY_REPORT.md.",
            f"- Of {len(coverage)} sensors, {zero_hourly} have no hourly data in the sampled "
            f"interval; {duplicate_hours} duplicate hourly timestamps and {stale_count} stale "
            "nonempty sensors were found. Raw measurement frequency is reported per sensor.",
            f"- PM2.5 sensors at locations listing CPCB as provider: **{cpcb_count}** of "
            f"{len(sensors)}. This is provider metadata, not a count of independent sources. "
            "OpenAQ redistribution is not independent validation.",
            "- Forecast verification readiness: **not established**; require station/source and "
            "hourly interval compatibility checks.", "", "## Existing station reconciliation", "",
            *station_lines, "", "## Additional locations to investigate", "",
            *priority_lines, "", "These are discovery leads only; CPCB redistribution adds "
            "station coverage but does not provide an independent observation source. AirNow "
            "requires separate physical-site and quality verification.", "",
            "## Station recommendations", "",
            "| Location | PM2.5 sensor ID | Decision | Evidence |", "|---|---:|---|---|",
            *recommendations, "", "## Use recommendations", "",
            "| Use | Decision |", "|---|---|",
            "| Historical observation enrichment | CONDITIONAL — requires compatible, sufficiently "
            "complete PM2.5 sensor history |",
            "| Existing forecast verification | CONDITIONAL — first resolve station/source overlap "
            "and independence |",
            "| Additional station support | REJECT for production in stage 1; needs model and UI "
            "validation in a separate task |",
            "| Future external-observation interface | CONDITIONAL — requires provenance, freshness "
            "and terms review |", "", "## Limits", "", *[f"- {item}" for item in caveats], "",
            "## Source documentation", "",
            "- [OpenAQ API v3](https://docs.openaq.org/api)",
            "- [API key](https://docs.openaq.org/using-the-api/api-key)",
            "- [Rate limits](https://docs.openaq.org/using-the-api/rate-limits)",
            "- [Terms and attribution](https://docs.openaq.org/about/terms)",
            "- [Hourly sensor measurements](https://docs.openaq.org/api/operations/"
            "sensor_hourly_measurements_get_v3_sensors__sensors_id__hours_get)", ""]
    replay_report = output / "historical_2025_05" / "HOURLY_COVERAGE_REPORT.csv"
    if replay_report.exists():
        with replay_report.open(newline="", encoding="utf-8") as handle:
            replay_rows = list(csv.DictReader(handle))
        replay_lines = ["", "## Replay-period spot check", "",
                        "A separate bounded May 2025 query covers the earliest replay period. "
                        "It sampled only the four existing AirWindow PM2.5 sensors:", "",
                        "| Station | Sensor | May 2025 hourly coverage |",
                        "|---|---:|---:|"]
        replay_lines.extend(f"| {r['location_name']} | {r['sensor_id']} | "
                            f"{r['coverage_percent']}% |" for r in replay_rows)
        replay_lines.extend(["", "See `historical_2025_05/` for the complete bounded "
                             "query outputs. Other replay months have not been audited.", ""])
        main[main.index("## Source documentation"):main.index("## Source documentation")] = replay_lines
    (output / "OPENAQ_MUMBAI_AUDIT.md").write_text("\n".join(main), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date-from", default="2026-10-01T00:00:00Z")
    parser.add_argument("--date-to", default="2026-11-11T00:00:00Z")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--max-location-pages", type=int, default=5)
    parser.add_argument("--max-measurement-pages", type=int, default=10)
    parser.add_argument("--max-sensors", type=int, default=60)
    parser.add_argument("--offline-status", action="store_true",
                        help="Write explicit unverified reports without API requests")
    args = parser.parse_args()
    if utc_time(args.date_to) <= utc_time(args.date_from):
        parser.error("--date-to must follow --date-from")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    locations: list[dict[str, Any]] = []
    sensors: list[dict[str, Any]] = []
    coverage: list[dict[str, Any]] = []
    matches: list[dict[str, Any]] = []
    caveats = ["AirWindow source IDs in Stations.csv are local leads until authenticated OpenAQ "
               "responses verify them.",
               "OpenAQ location coordinates may be rounded; coordinate proximity alone cannot "
               "prove physical or source identity.",
               "The requested 2026-10 to 2026-11 window does not cover all replay cases from "
               "2025-05 onward; rerun for additional bounded historical intervals.",
               "OpenAQ's terms require OpenAQ and underlying-source attribution; review provider "
               "terms before any downstream publication or integration.",
               "OpenAQ precomputed hourly periods may start at :30 UTC; comparisons use their "
               "explicit period end against AirWindow's interval-end timestamps."]
    if args.offline_status:
        status = "BLOCKED_NO_API_KEY — no live locations or measurements verified"
        caveats.append("Authenticated API calls were not made; all counts are unknown, not zero.")
    else:
        client = OpenAQClient(cache_dir=args.output / "raw" / "api_cache")
        locations, loc_truncated = discover(client, max_pages=args.max_location_pages)
        sensors = inspect(client, locations)
        if loc_truncated:
            caveats.append("Location catalog hit page cap; discovery counts are lower bounds.")
        caveats.append(f"Request caps: {args.max_location_pages} location pages, "
                       f"{args.max_measurement_pages} pages per sensor endpoint, "
                       f"{args.max_sensors} sensors. All counts refer to bbox {MUMBAI_BBOX}, "
                       "not an administrative Mumbai boundary.")
        local = load_airwindow_stations(STATIONS)
        local_sensor_ids = {s["sensor_id"] for s in local}
        local_location_ids = {s["station_id"] for s in local}
        sensors.sort(key=lambda s: (0 if s["sensor"]["id"] in local_sensor_ids else
                                    1 if s["location_id"] in local_location_ids else
                                    2 if any(name in s["location_name"].lower()
                                             for name in PRIORITY_NAMES) else 3,
                                    s["location_id"], s["sensor"]["id"]))
        if len(sensors) > args.max_sensors:
            caveats.append(f"Only first {args.max_sensors} PM2.5 sensors downloaded; "
                           "remaining sensors are cataloged but unassessed.")
        args.output.joinpath("raw", "measurements").mkdir(parents=True, exist_ok=True)
        downloaded: dict[int, list[dict[str, Any]]] = {}
        for item in sensors[:args.max_sensors]:
            sensor_id = int(item["sensor"]["id"])
            LOG.info("Inspecting PM2.5 sensor %s", sensor_id)
            records, truncated = download(client, sensor_id, date_from=args.date_from,
                                          date_to=args.date_to,
                                          max_pages=args.max_measurement_pages)
            downloaded[sensor_id] = records
            args.output.joinpath("raw", "measurements", f"sensor_{sensor_id}.json").write_text(
                json.dumps({"sensor_id": sensor_id, "records": records}, indent=2), encoding="utf-8")
            coverage.append(analyse(item, records, date_from=args.date_from,
                                    date_to=args.date_to, truncated=truncated))
        matches = reconcile(local, locations, sensors)
        locations_by_id = {int(location["id"]): location for location in locations}
        for match in matches:
            if not match["openaq_location_id"]:
                continue
            location = locations_by_id[int(match["openaq_location_id"])]
            match["provider"] = (location.get("provider") or {}).get("name")
            match["owner"] = (location.get("owner") or {}).get("name")
            station = next(s for s in local if s["station_id"] == match["station_id"])
            sensor_id = station["sensor_id"]
            if match["openaq_location_id"] != station["station_id"] or sensor_id not in downloaded:
                continue
            comparison = compare_train_overlap(ROOT / "data/raw/challenge/Train.csv", station,
                                               downloaded[sensor_id])
            match.update(comparison)
            if (match["distance_m"] <= 100 and match["provider"] == "CPCB"
                    and comparison["overlap_hours"] >= 24
                    and comparison["mean_absolute_difference"] <= 0.1
                    and comparison["within_0_2_fraction"] >= 0.95):
                match["classification"] = "Confirmed same physical station and source"
                match["evidence"] = "Exact OpenAQ location/sensor IDs and coordinates, CPCB provider, " \
                                    "and >=95% values within 0.2 ug/m3 at >=24 aligned ends; " \
                                    "occasional larger differences remain unexplained"
        status = "LIVE_BOUNDED_DISCOVERY"
    render_reports(args.output, status=status, locations=locations, sensors=sensors,
                   coverage=coverage, matches=matches, date_from=args.date_from,
                   date_to=args.date_to, caveats=caveats)
    LOG.info("Wrote audit reports to %s (%s)", args.output, status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
