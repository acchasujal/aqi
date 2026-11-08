#!/usr/bin/env python3
"""Review recorded weather artifacts, source hashes, clocks and control parity."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from mumbai_pm25.weather_grib import required_fields, sha256

ROOT = Path(__file__).resolve().parents[1]


def text_sha256(path: Path) -> str:
    """Stable Git text fingerprint across Windows checkout line endings."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports", type=Path, default=ROOT / "reports/ml_pipeline/weather")
    parser.add_argument("--diagnostics", type=Path, required=True)
    args = parser.parse_args()
    reports = args.reports
    raw_before = json.loads((reports / "RAW_CHALLENGE_HASHES.json").read_text())
    raw_after = {p.name: sha256(p) for p in (ROOT / "data/raw/challenge").iterdir() if p.is_file()}
    assert raw_before == raw_after, "Raw challenge inputs changed"
    for supplied in json.loads((reports / "INPUT_PROVENANCE.json").read_text()):
        assert sha256(ROOT / supplied["raw_path"]) == supplied["sha256"]
    downloads = json.loads((reports / "NOAA_DOWNLOADED_FILE_AUDITS.json").read_text())
    assert len(downloads) == 48
    for receipt in downloads:
        assert sha256(ROOT / receipt["raw_path"]) == receipt["source_sha256"]
    manifest = pd.read_csv(reports / "WEATHER_RUN_MANIFEST.csv")
    assert len(manifest) == 169 and not manifest.duplicated(["source", "valid_time_utc"]).any()
    run, valid = (pd.to_datetime(manifest[k], utc=True) for k in ("run_utc", "valid_time_utc"))
    assert (valid == run + pd.to_timedelta(manifest.forecast_lead_hours, unit="h")).all()
    assert manifest.eligibility.eq("RESEARCH_ONLY_BLOCKED").all()
    assert manifest.publication_time_utc.isna().all()
    diagnostic = json.loads((reports / "diagnostic.json").read_text())
    available = pd.to_datetime(manifest.available_at_utc, utc=True, format="mixed")
    assert (available <= pd.Timestamp(diagnostic["issue_time"])).all()
    coverage = pd.read_csv(reports / "WEATHER_FEATURE_COVERAGE.csv")
    assert len(coverage) == 48 and coverage.finite_hours.eq(48).sum() == 44
    assert coverage.loc[coverage.finite_hours.eq(0), "feature"].eq("cams_surface_pressure_pa").all()
    registry = pd.read_csv(ROOT / "configs/feature_registry.csv")
    names = (*required_fields("cams"), *required_fields("gfs"))
    candidate_rows = registry.loc[registry.feature_name.isin(names)]
    assert len(candidate_rows) == 12 and candidate_rows.status.eq("candidate").all()
    form = {
        x["name"]: x for x in json.loads((reports / "CAMS_OFFICIAL_REQUEST_FORM.json").read_text())
    }
    for request_path in reports.glob("CAMS_REQUEST_*.json"):
        request = json.loads(request_path.read_text())
        assert set(request).issubset(form)
        for key in ("time", "type", "data_format", "leadtime_hour"):
            values = request[key] if isinstance(request[key], list) else [request[key]]
            assert set(values).issubset(form[key]["details"]["values"])
    first, second = (args.diagnostics / n for n in ("pfix_control.csv", "pfix_control_repeat.csv"))
    assert sha256(first) == sha256(second) == diagnostic["control_sha256"]
    previous = ROOT / "artifacts/submissions/task008_provisional_pfix_20261108_1558.csv"
    if previous.is_file():
        assert first.read_bytes() == previous.read_bytes().replace(b"\r\n", b"\n")
    summary = {
        "raw_challenge_hashes_unchanged": True,
        "supplied_hashes_verified": 2,
        "noaa_hourly_file_hashes_verified": 48,
        "run_manifest_rows": len(manifest),
        "complete_station_feature_series": 44,
        "missing_cams_pressure_series": 4,
        "all_candidate_statuses": True,
        "official_cams_request_fields_verified": True,
        "deterministic_pfix": True,
        "weather_promotion": False,
        "fingerprint_policy": "Implementation/report UTF-8 text normalized to LF; raw inputs use original bytes",
        "implementation_sha256": {
            str(p.relative_to(ROOT)).replace("\\", "/"): text_sha256(p)
            for p in [
                *sorted((ROOT / "src/mumbai_pm25").glob("weather_*.py")),
                ROOT / "scripts/weather_pipeline.py",
                ROOT / "scripts/fetch_single_run_weather.py",
                ROOT / "scripts/prepare_weather_diagnostics.py",
                ROOT / "scripts/audit_weather_results.py",
                ROOT / "tests/test_weather.py",
                ROOT / "configs/feature_registry.csv",
            ]
        },
        "artifact_sha256": {
            p.name: text_sha256(p)
            for p in sorted(reports.iterdir())
            if p.is_file() and p.name != "ARTIFACT_REVIEW.json"
        },
    }
    (reports / "ARTIFACT_REVIEW.json").write_text(json.dumps(summary, indent=2) + "\n")
    print("Weather artifact review passed; raw inputs unchanged; no weather promotion")


if __name__ == "__main__":
    main()
