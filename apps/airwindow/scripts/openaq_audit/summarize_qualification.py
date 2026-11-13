"""Turn complete monthly OpenAQ evidence into conservative research qualifications."""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import median
from typing import Any

from .qualify_history import DEFAULT_OUTPUT, PRIORITY_SENSOR_IDS, STAGE1
from .run_audit import write_csv


def decide(sensor: dict[str, Any], rows: list[dict[str, Any]],
           discrepancy_summary: dict[str, Any] | None = None) -> tuple[str, str]:
    statuses = {r["fetch_status"] for r in rows}
    if statuses == {"SENSOR_ENDED_BEFORE_REPLAY"}:
        return "REJECT", "Sensor ended before May 2025 replay period"
    if statuses & {"FETCH_FAILED", "TRUNCATED"}:
        return "CONDITIONAL", "API fetch incomplete; monthly coverage unknown"
    unit = (sensor["sensor"].get("parameter") or {}).get("units", "")
    if unit.lower().replace("μ", "µ") not in {"µg/m³", "µg/m3", "ug/m³", "ug/m3"}:
        return "REJECT", "PM2.5 unit incompatible or unverified"
    phases = {minute for r in rows for minute in json.loads(r["start_minute_phases_ist"] or "[]")}
    if phases and phases != {0}:
        return "CONDITIONAL", "Hourly starts are not aligned to IST whole hours"
    full = [r for r in rows if r["partial_month"] == "False"]
    coverage = [float(r["aligned_ist_coverage_percent"]) for r in full
                if r["aligned_ist_coverage_percent"]]
    good = sum(v >= 75 for v in coverage)
    poor = sum(v < 50 for v in coverage)
    provider = (sensor.get("provider") or {}).get("name")
    if provider == "AirNow":
        return ("CONDITIONAL", "Distinct-provider lead, but owner/site unverified and replay-wide "
                "coverage sparse") if good else ("REJECT", "No adequate full replay month")
    if (discrepancy_summary and discrepancy_summary.get("max_absolute_difference") is not None
            and discrepancy_summary["max_absolute_difference"] > 1000):
        return "CONDITIONAL", "Large flagged Train/OpenAQ revisions need source-version review"
    lifetime_min = (sensor["sensor"].get("summary") or {}).get("min")
    if lifetime_min is not None and lifetime_min < 0:
        return "CONDITIONAL", "Negative lifetime sensor values require explicit flag review"
    if len(coverage) >= 18 and good >= 15 and poor == 0:
        return "ACCEPT", "Research-only: >=75% aligned coverage in >=15/18 full months, " \
                         "none below 50%; preserve missingness"
    if good >= 3 or (coverage and median(coverage) >= 50):
        return "CONDITIONAL", "Useful months exist, but replay-wide continuity is insufficient"
    return "REJECT", "Insufficient replay-month PM2.5 coverage"


def summarize(output: Path = DEFAULT_OUTPUT) -> list[dict[str, Any]]:
    manifest = json.loads((output / "RUN_MANIFEST.json").read_text(encoding="utf-8"))
    catalog = json.loads((STAGE1 / "PM25_SENSOR_CATALOG.json").read_text(encoding="utf-8"))["results"]
    with (output / "MONTHLY_SENSOR_COVERAGE.csv").open(newline="", encoding="utf-8") as handle:
        monthly = list(csv.DictReader(handle))
    if len(catalog) != manifest["catalog_sensors"] or len(monthly) != len(catalog) * 19:
        raise ValueError("Monthly coverage is incomplete for the Stage 1 sensor catalog")
    by_sensor: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in monthly:
        by_sensor[int(row["sensor_id"])].append(row)
    result = []
    discrepancy_by_sensor = {int(d["sensor_id"]): d for d in manifest["discrepancy_summaries"]}
    for sensor in sorted(catalog, key=lambda item: int(item["sensor"]["id"])):
        sid = int(sensor["sensor"]["id"])
        rows = by_sensor[sid]
        decision, reason = decide(sensor, rows, discrepancy_by_sensor.get(sid))
        full = [r for r in rows if r["partial_month"] == "False"]
        values = [float(r["aligned_ist_coverage_percent"]) for r in full
                  if r["aligned_ist_coverage_percent"]]
        observed_months = [r["month_ist"] for r in rows if int(r["unique_hourly_starts"]) > 0]
        zero_run = longest_run([int(r["unique_hourly_starts"]) == 0 for r in full])
        after_may = [float(r["aligned_ist_coverage_percent"]) for r in full
                     if r["month_ist"] != "2025-05" and r["aligned_ist_coverage_percent"]]
        coord = sensor.get("coordinates") or {}
        result.append({"location_id": sensor["location_id"],
                       "location_name": sensor["location_name"], "sensor_id": sid,
                       "provider": (sensor.get("provider") or {}).get("name"),
                       "owner": (sensor.get("owner") or {}).get("name"),
                       "latitude": coord.get("latitude"), "longitude": coord.get("longitude"),
                       "unit": (sensor["sensor"].get("parameter") or {}).get("units"),
                       "first_sensor_utc": (sensor["sensor"].get("datetimeFirst") or {}).get("utc"),
                       "last_sensor_utc": (sensor["sensor"].get("datetimeLast") or {}).get("utc"),
                       "months_full": len(full), "months_at_75_percent": sum(v >= 75 for v in values),
                       "months_below_50_percent": sum(v < 50 for v in values),
                       "first_observed_replay_month": min(observed_months) if observed_months else None,
                       "last_observed_replay_month": max(observed_months) if observed_months else None,
                       "longest_zero_month_run": zero_run,
                       "median_monthly_aligned_coverage_percent": round(median(values), 3)
                       if values else None,
                       "minimum_monthly_aligned_coverage_percent": min(values) if values else None,
                       "may_2025_coverage_percent": next((r["aligned_ist_coverage_percent"]
                           for r in rows if r["month_ist"] == "2025-05"), None),
                       "remaining_full_month_median_percent": round(median(after_may), 3)
                       if after_may else None,
                       "oct_2026_coverage_percent": next((r["aligned_ist_coverage_percent"]
                           for r in rows if r["month_ist"] == "2026-10"), None),
                       "duplicate_hours_total": sum(int(r["duplicate_hours"]) for r in rows),
                       "longest_internal_gap_hours": max(float(r["longest_internal_missing_run_hours"])
                                                          for r in rows),
                       "fetch_statuses": sorted({r["fetch_status"] for r in rows}),
                       "decision": decision, "reason": reason})
    write_csv(output / "STATION_QUALIFICATION.csv", result, list(result[0]))
    priority = [r for r in result if int(r["sensor_id"]) in PRIORITY_SENSOR_IDS]
    counts = {label: sum(r["decision"] == label for r in result)
              for label in ("ACCEPT", "CONDITIONAL", "REJECT")}
    lines = ["# OpenAQ Mumbai Stage 1.5 decision", "",
             f"**Coverage:** {len(result)} PM2.5 sensor series × 19 replay calendar months "
             "(18 complete months, November 2026 partial).",
             f"**Research qualification:** {counts['ACCEPT']} ACCEPT, "
             f"{counts['CONDITIONAL']} CONDITIONAL, {counts['REJECT']} REJECT.", "",
             "ACCEPT means suitable for **internal historical research with explicit missingness**. "
             "It does not approve redistribution, an independent validation claim or production "
             "forecast integration. The screening rule requires at least 15 of 18 full months "
             "at 75% aligned hourly coverage, none below 50%, a compatible unit and no incomplete "
             "API fetch. Provider/site and negative lifetime data can keep a series conditional.", "",
             "Coverage here uses complete **IST calendar months** and OpenAQ interval starts. "
             "The Stage 1 May spot check used UTC date bounds, so its percentages differ "
             "slightly and should not be substituted for these monthly values.", "",
             "## Priority sensors", "", "| Location | ID | Provider | May 2025 | "
             "Later full-month median | Oct 2026 | Months ≥75% | Decision |",
             "|---|---:|---|---:|---:|---:|---:|---|"]
    def display(value: Any) -> str:
        return "unknown" if value is None else str(value)

    lines.extend(f"| {r['location_name']} | {r['sensor_id']} | {r['provider']} | "
                 f"{display(r['may_2025_coverage_percent'])}% | "
                 f"{display(r['remaining_full_month_median_percent'])}% | "
                 f"{display(r['oct_2026_coverage_percent'])}% | "
                 f"{r['months_at_75_percent']}/18 | {r['decision']} |" for r in priority)
    airnow = next((r for r in priority if int(r["sensor_id"]) == 23320), None)
    if airnow:
        lines.extend(["", f"AirNow Mumbai first has observations in the sampled replay span "
                      f"in **{airnow['first_observed_replay_month']}**; its catalog lifetime start "
                      "does not establish continuous coverage. It cannot fill earlier replay months."])
    lines.extend(["", "## Accepted internal-research series", "",
                  "| Location | Sensor ID | Full months ≥75% | Median aligned coverage |",
                  "|---|---:|---:|---:|"])
    lines.extend(f"| {r['location_name']} | {r['sensor_id']} | "
                 f"{r['months_at_75_percent']}/18 | "
                 f"{r['median_monthly_aligned_coverage_percent']}% |"
                 for r in result if r["decision"] == "ACCEPT")
    priority_gaps = sorted((r for r in monthly if int(r["sensor_id"]) in PRIORITY_SENSOR_IDS
                            and r["partial_month"] == "False"),
                           key=lambda r: float(r["longest_internal_missing_run_hours"]), reverse=True)
    lines.extend(["", "## Largest priority-sensor reporting interruptions", "",
                  "| Sensor ID | Month | Hourly coverage | Longest internal missing run |",
                  "|---:|---|---:|---:|"])
    lines.extend(f"| {r['sensor_id']} | {r['month_ist']} | {r['coverage_percent']}% | "
                 f"{r['longest_internal_missing_run_hours']} h |" for r in priority_gaps[:8])
    lines.extend(["", "Whole months with no observations are recorded as 0% coverage "
                  "in the CSV; their internal-gap field is zero because no two reports bracket "
                  "the interruption. The missing-hours count captures those months.", ""])
    lines.extend(["", "## Same-sensor discrepancy findings", "",
                  "OpenAQ hourly period ends were compared with local Train interval-end "
                  "timestamps for the four existing station/sensor IDs. All differences above "
                  "0.2 µg/m³ remain in `DISCREPANCY_ANALYSIS.csv`; no value was deleted.", "",
                  "| Station ID | Matched hours | >0.2 hours | Frequency | Maximum difference | "
                  "Median abs. error, shifts −1 / 0 / +1 h |",
                  "|---:|---:|---:|---:|---:|---|"])
    for d in manifest["discrepancy_summaries"]:
        shifts = d.get("alignment_median_abs_error_by_shift_hours", {})
        lines.append(f"| {d['station_id']} | {d['matched_hours']} | {d['over_0_2_hours']} | "
                     f"{d['over_0_2_percent']}% | {round(d['max_absolute_difference'], 3)} | "
                     f"{shifts.get('-1')} / {shifts.get('0')} / {shifts.get('1')} |")
    with (output / "DISCREPANCY_ANALYSIS.csv").open(newline="", encoding="utf-8") as handle:
        differences = list(csv.DictReader(handle))
    flagged = sum(r["openaq_flagged"] == "True" for r in differences)
    huge = sum(float(r["absolute_difference"]) > 1000 for r in differences)
    lines.extend(["", f"Of {len(differences)} differences above 0.2 µg/m³, "
                  f"{flagged} OpenAQ hourly rows carry flags and {huge} exceed 1,000 µg/m³. "
                  "The largest local Train readings retain their original `flag_high_1000` "
                  "values. Current OpenAQ quarter-hour responses for Borivali East on 9 and 26 "
                  "August 2025 contain flagged null measurements where Train has enormous "
                  "hourly means; a source revision/filter is plausible, but the original "
                  "quarter-hour snapshot is unavailable. Smaller unflagged disagreements, "
                  "including some midnight hours, are not fully explained by rounding. "
                  "The unchanged interval-end alignment is substantially better than ±1 hour "
                  "for all four stations.", ""])
    lines.extend(["Two checked raw-response examples make the source-version issue concrete:", "",
                  "- Borivali East sensor `12236418`, 9 August 2025 13:00–14:00 IST: "
                  "Train is 75,203.525 µg/m³ with `flag_high_1000=True`; current OpenAQ "
                  "hourly is 817.00 µg/m³ and flagged. The current quarter-hours show "
                  "817.07 followed by three flagged null values.",
                  "- Shivaji Nagar sensor `12238576`, 4 December 2025 05:00–06:00 IST: "
                  "Train is 42,206.7725 µg/m³ with `flag_high_1000=True`; current OpenAQ "
                  "hourly is 89.00 µg/m³ and flagged. The current quarter-hours show "
                  "89.00 followed by three flagged null values.", "",
                  "These examples support later flagging/filtering as a plausible explanation; "
                  "the original quarter-hour values used for Train are not available here, "
                  "so the precise revision history is unresolved. Both products use PM2.5 "
                  "µg/m³ and the same explicit hour-end alignment.", ""])
    lines.extend(["", "All 57 sensor decisions and their reasons are in "
                  "`STATION_QUALIFICATION.csv`; monthly evidence is in "
                  "`MONTHLY_SENSOR_COVERAGE.csv`. The 22 pre-replay sensors are rejected "
                  "using their OpenAQ sensor last-report timestamps; API failures remain "
                  "conditional, never zero coverage.", "",
                  "## Stage 2 recommendation", "",
                  "Proceed only with a research-only, source-labelled prototype for accepted "
                  "sensor-months after upstream reuse terms and interval methodology are resolved. "
                  "Keep current AirWindow station forecasts and replay artifacts unchanged. "
                  "OpenAQ CPCB copies cannot independently verify CPCB-derived forecasts. "
                  "Prospective verification needs immutable pre-target forecast vintages and "
                  "publication-time observation evidence.", "",
                  "See `PROVIDER_AND_LICENSING.md`, "
                  "`FORECAST_VERIFICATION_FEASIBILITY.md` and `DISCREPANCY_ANALYSIS.csv`.", "",
                  "## Existing integration-test artifact", "",
                  "`tests/test_main_integration.py::test_refreshed_app_forecast_matches_audited_task011_rows` "
                  "expects four TASK011 submission-side files (`.csv`, `.rows.csv`, "
                  "`.audit.json`, `.manifest.txt`) under ignored `artifacts/submissions/`. "
                  "They are absent in this checkout; the tracked "
                  "`reports/ml_pipeline/task011/task011_final_row_audit.csv` is a different "
                  "artifact and is not substituted. The test remains unchanged and fails "
                  "until the genuine TASK011 files are restored or the test is separately "
                  "redesigned around committed provenance.", ""])
    (output / "STAGE1_5_DECISION.md").write_text("\n".join(lines), encoding="utf-8")
    return result


def longest_run(flags: list[bool]) -> int:
    current = longest = 0
    for flag in flags:
        current = current + 1 if flag else 0
        longest = max(longest, current)
    return longest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    rows = summarize(args.output)
    print(f"Qualified {len(rows)} separate sensor series")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
