#!/usr/bin/env python3
"""Export provisional weather diagnostics and unchanged P_fix; never select a model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from mumbai_pm25.data import load_data
from mumbai_pm25.forecast import predict_test_with_hist24_blend
from mumbai_pm25.historical_archive import load_2024_history
from mumbai_pm25.weather_features import (
    align_block,
    export_pfix_fallback,
    extract_station_rows,
    utc,
)
from mumbai_pm25.weather_grib import required_fields, sha256

ROOT = Path(__file__).resolve().parents[1]


def compact_manifest(frame: pd.DataFrame) -> pd.DataFrame:
    """One source/file/valid-hour record with nested variable and spatial metadata."""
    records = []
    for _, group in frame.groupby(["source_sha256", "valid_time_utc"], sort=True):
        metadata_columns = [
            "source",
            "source_id",
            "source_sha256",
            "raw_path",
            "processed_path",
            "run_utc",
            "valid_time_utc",
            "forecast_lead_hours",
            "retrieved_at_utc",
            "available_at_utc",
            "availability_basis",
            "eligibility",
            "experiment_id",
            "manifest_schema_version",
            "model_identifier",
            "publisher",
            "licence",
            "terms_checked_date",
            "dataset_url",
            "publication_time_utc",
            "grid",
        ]
        record = group.iloc[0][metadata_columns].to_dict()
        record["variables"] = group.drop_duplicates("feature")[
            [
                "feature",
                "native_unit",
                "resolved_unit",
                "converted_unit",
                "unit_reference",
                "grib_identifiers",
            ]
        ].to_json(orient="records")
        spatial = []
        for station in group.drop_duplicates("location_id").itertuples(index=False):
            corners = json.loads(station.interpolation)["corners"]
            spatial.append(
                {
                    "location_id": station.location_id,
                    "latitude": station.station_latitude,
                    "longitude": station.station_longitude,
                    "corners": [{k: v for k, v in c.items() if k != "value"} for c in corners],
                }
            )
        record["station_interpolation"] = json.dumps(spatial, sort_keys=True)
        records.append(record)
    return pd.DataFrame(records)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cams-decoded", type=Path, required=True)
    parser.add_argument("--gfs-decoded", type=Path, required=True)
    parser.add_argument("--issue-time", required=True)
    parser.add_argument("--cams-available-at", required=True)
    parser.add_argument("--gfs-available-at", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Choose a new output directory; preserve prior diagnostics")
    args.output.mkdir(parents=True)
    train, test, _, stations = load_data(ROOT / "data/raw/challenge")
    cutoff = train.timestamp_ist.max()
    history = load_2024_history(ROOT / "data/raw/challenge/AdditionalHistory.zip")
    first = predict_test_with_hist24_blend(
        train, test, history, issue_time=utc(args.issue_time), pm_history_cutoff=cutoff
    )
    second = predict_test_with_hist24_blend(
        train, test, history, issue_time=utc(args.issue_time), pm_history_cutoff=cutoff
    )
    pd.testing.assert_frame_equal(first, second, check_exact=True)
    export_pfix_fallback(first, test, args.output / "pfix_control.csv")
    export_pfix_fallback(second, test, args.output / "pfix_control_repeat.csv")
    assert sha256(args.output / "pfix_control.csv") == sha256(
        args.output / "pfix_control_repeat.csv"
    )
    targets = test.loc[
        (test.target_start >= pd.Timestamp("2026-11-11", tz="Asia/Kolkata"))
        & (test.target_start < pd.Timestamp("2026-11-13", tz="Asia/Kolkata"))
    ]
    coverage, manifests, aligned_sources = [], [], []
    for source, path, available in [
        ("cams", args.cams_decoded, args.cams_available_at),
        ("gfs", args.gfs_decoded, args.gfs_available_at),
    ]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if source == "cams":
            for message in payload["messages"]:
                message["raw_path"] = "data/external/weather/incoming/" + payload["filename"]
        station_rows = extract_station_rows(
            payload["messages"], source, stations, source_hash=payload.get("sha256", "per_message")
        )
        station_rows.to_csv(args.output / f"{source}_station_features.csv", index=False)
        present = tuple(n for n in required_fields(source) if n in station_rows.feature.unique())
        aligned = align_block(
            targets,
            station_rows,
            issue_time=args.issue_time,
            pm_history_cutoff=cutoff.isoformat(),
            available_at=available,
            availability_evidence="Local preservation/retrieval upper bound; "
            "not original publication time; provisional diagnostic only",
            features=present,
        )
        aligned.to_csv(args.output / f"{source}_private_diagnostic.csv", index=False)
        aligned_sources.append(aligned)
        for station in stations.itertuples(index=False):
            for feature in required_fields(source):
                count = (
                    int(aligned.loc[aligned.location_id.eq(station.location_id), feature].count())
                    if feature in aligned
                    else 0
                )
                coverage.append(
                    {
                        "source": source,
                        "location_id": station.location_id,
                        "feature": feature,
                        "expected_hours": 48,
                        "finite_hours": count,
                        "status": "complete" if count == 48 else "BLOCKED_MISSING",
                    }
                )
        station_rows["available_at_utc"] = available
        station_rows["availability_basis"] = "local retrieval/preservation upper bound"
        station_rows["eligibility"] = "RESEARCH_ONLY_BLOCKED"
        station_rows["experiment_id"] = "EXP-025-WEATHER"
        station_rows["manifest_schema_version"] = "1.0"
        station_rows["source_id"] = "cams_global" if source == "cams" else "noaa_gfs_0p25"
        station_rows["model_identifier"] = "CAMS IFS-COMPO" if source == "cams" else "NOAA GFS"
        station_rows["publisher"] = "ECMWF/Copernicus" if source == "cams" else "NOAA/NCEP"
        station_rows["licence"] = "ADS CC-BY" if source == "cams" else "NWS public domain"
        station_rows["terms_checked_date"] = "2026-11-08"
        station_rows["dataset_url"] = (
            "https://doi.org/10.24381/04a0b097"
            if source == "cams"
            else "https://www.nco.ncep.noaa.gov/pmb/products/gfs/"
        )
        station_rows["publication_time_utc"] = None
        station_rows["processed_path"] = (args.output / f"{source}_station_features.csv").as_posix()
        manifests.append(station_rows)
    # Current-period level comparison only: no labels, no fitted calibration, no RMSE.
    cams_aligned = aligned_sources[0]
    diagnostic = cams_aligned[["ID", "location_id", "target_start", "cams_pm25_ug_m3"]].merge(
        first, on="ID", validate="one_to_one"
    )
    diagnostic["cams_minus_pfix"] = diagnostic.cams_pm25_ug_m3 - diagnostic.Target
    diagnostic.to_csv(args.output / "cams_vs_pfix_provisional.csv", index=False)
    pd.DataFrame(coverage).to_csv(args.output / "WEATHER_FEATURE_COVERAGE.csv", index=False)
    compact_manifest(pd.concat(manifests)).to_csv(
        args.output / "WEATHER_RUN_MANIFEST.csv", index=False
    )
    report = {
        "schema_version": "1.0",
        "issue_time": args.issue_time,
        "pm_history_cutoff": cutoff.isoformat(),
        "model": "P_fix",
        "weather_correction": False,
        "historical_weather_validation": "BLOCKED_NO_ISSUE_POLICY",
        "deterministic": True,
        "rows": len(first),
        "control_sha256": sha256(args.output / "pfix_control.csv"),
        "private_diagnostic_rows": len(diagnostic),
        "private_cams_mean": float(diagnostic.cams_pm25_ug_m3.mean()),
        "private_pfix_mean": float(diagnostic.Target.mean()),
        "forecast_means_are_not_validation": True,
        "input_hashes": {
            p.name: sha256(p) for p in (ROOT / "data/raw/challenge").iterdir() if p.is_file()
        },
    }
    if not np.isfinite(diagnostic.cams_pm25_ug_m3).all():
        raise ValueError("Incomplete CAMS PM2.5 diagnostic")
    (args.output / "diagnostic.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
