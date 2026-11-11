"""Refresh only AirWindow's forecast from the audited TASK011 final P_fix artifact.

The TASK011 inference run was completed and validated before its source deadline.
This exporter revalidates the preserved outputs and temporal row audit; it does
not rerun or alter the ML pipeline, replay, raw inputs, or model.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from apps.airwindow.build_artifacts import build_forecast
from apps.airwindow.contract_validation import validate_artifact

DEFAULT_PREDICTION = ROOT / "artifacts/submissions/task011_final_Pfix_20261110.csv"
DEFAULT_OOF = ROOT / "reports/ml_pipeline/task011/task011_84_origin_oof.csv.gz"
DEFAULT_INTEGRITY = ROOT / "reports/ml_pipeline/task011/task011_final_data_release_integrity.json"
DATA = ROOT / "apps/airwindow/public/data"
FALLBACK_NAME = "forecast_fallback_task008.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prediction", type=Path, default=DEFAULT_PREDICTION)
    parser.add_argument("--oof", type=Path, default=DEFAULT_OOF)
    parser.add_argument("--integrity", type=Path, default=DEFAULT_INTEGRITY)
    parser.add_argument("--generated-at", type=str, default=None)
    args = parser.parse_args()

    audit_path = args.prediction.with_suffix(".audit.json")
    rows_path = args.prediction.with_suffix(".rows.csv")
    task_manifest_path = args.prediction.with_suffix(".manifest.txt")
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    task_manifest = json.loads(task_manifest_path.read_text(encoding="utf-8"))
    integrity = json.loads(args.integrity.read_text(encoding="utf-8"))
    if audit["output_sha256"] != sha(args.prediction) or audit["output_sha256"] != "f450b68212463f64bab67adfb0d98e1c4cce7ee83ec118f2564d38d738e34c13":
        raise ValueError("TASK011 P_fix output does not match its frozen, reviewed hash")
    if task_manifest["output_sha256"] != audit["output_sha256"] or not audit["deterministic_rerun"]:
        raise ValueError("TASK011 audit and manifest disagree or deterministic rerun was not recorded")
    if task_manifest["model_run_time"] != audit["model_run_time"] or task_manifest["pm_history_cutoff"] != audit["pm_history_cutoff"]:
        raise ValueError("Issue/cutoff clocks differ between TASK011 records")
    for name, expected in task_manifest["input_sha256"].items():
        if integrity[name]["sha256"] != expected:
            raise ValueError(f"Frozen TASK011 input fingerprint mismatch: {name}")
    if task_manifest["station_cutoffs"] != integrity["Train.csv"]["station_cutoffs"]:
        raise ValueError("Station PM cutoffs disagree with the final Train audit")

    rows = pd.read_csv(rows_path)
    sample = pd.read_csv(ROOT / "data/processed/official_releases/20261110_final/SampleSubmission.csv")
    predictions = pd.read_csv(args.prediction)
    if rows.ID.tolist() != sample.ID.tolist() or predictions.ID.tolist() != sample.ID.tolist():
        raise ValueError("Forecast rows do not exactly match the frozen SampleSubmission order")
    if rows["released_observation_match"].sum() != audit["overlay_rows"] or int(rows["private"].sum()) != audit["private_rows"]:
        raise ValueError("Released-observation overlay/row counts do not match the run audit")
    cutoff = pd.Timestamp(task_manifest["pm_history_cutoff"])
    target_start = pd.to_datetime(rows["target_start"], utc=True).dt.tz_convert("Asia/Kolkata")
    if (pd.to_datetime(rows["pm_history_cutoff"], utc=True).dt.tz_convert("Asia/Kolkata") > cutoff).any():
        raise ValueError("A row uses a PM cutoff later than the audited cutoff")
    if (target_start.loc[target_start > pd.Timestamp(task_manifest["model_run_time"])] <= cutoff).any():
        raise ValueError("Future forecast target starts at or before the PM information cutoff")

    if args.generated_at:
        generated = pd.Timestamp(args.generated_at)
        if generated.tzinfo is None:
            raise ValueError("--generated-at must include an explicit timezone")
        generated = generated.tz_convert("Asia/Kolkata")
    else:
        generated = pd.Timestamp(datetime.now(ZoneInfo("Asia/Kolkata"))).floor("s")
    if generated < pd.Timestamp(task_manifest["model_run_time"]):
        raise ValueError("Export generation time precedes the recorded forecast issue")

    adapted_audit = dict(audit)
    adapted_audit.update({
        "pm_history_cutoff": task_manifest["pm_history_cutoff"],
        "station_last_pm_end": task_manifest["station_cutoffs"],
        "input_sha256": task_manifest["input_sha256"],
        "source_sha256": task_manifest["source_sha256"],
        "git_commit": task_manifest["git_commit"],
    })
    temp_audit = ROOT / "data/processed/airwindow_final_refresh/task011_audit_adapter.json"
    temp_audit.parent.mkdir(parents=True, exist_ok=True)
    temp_audit.write_text(json.dumps(adapted_audit, indent=2), encoding="utf-8")
    oof = pd.read_csv(args.oof)
    artifact = build_forecast(args.prediction, temp_audit, rows_path,
                              ROOT / "data/processed/official_releases/20261110_final/Stations.csv",
                              oof, generated)
    artifact["artifact_id"] = "task011-final-pfix-" + sha(args.prediction)[:16]
    artifact["model"]["version"] = "TASK011-final-P_fix"
    for station in artifact["stations"]:
        station["freshness"]["note"] = "Measured at issue from the audited 10 November Train release; no validated freshness threshold is configured."
        station["data_status"]["note"] = "Forecast hours come from the audited 10 November final P_fix run. Forecast issue and PM history cutoff are distinct. Historical validation does not calibrate this live forecast."
    validate_artifact(artifact)

    fallback = DATA / FALLBACK_NAME
    current = DATA / "forecast.json"
    if not fallback.exists():
        shutil.copyfile(current, fallback)
    previous = json.loads(fallback.read_text(encoding="utf-8"))
    if previous["model_issue_time_ist"] != "2026-11-08T15:58:00+05:30":
        raise ValueError("Preserved fallback is not the expected original TASK008 snapshot")
    current.write_text(json.dumps(artifact, separators=(",", ":"), allow_nan=False) + "\n", encoding="utf-8")

    manifest_path = DATA / "manifest.json"
    manifest_text = manifest_path.read_text(encoding="utf-8")
    manifest_text = manifest_text.removesuffix("\\n")
    manifest = json.loads(manifest_text)
    manifest.update({
        "forecast_sha256": sha(current),
        "fallback_forecast_file": FALLBACK_NAME,
        "fallback_forecast_sha256": sha(fallback),
        "forecast_issue_time_ist": artifact["model_issue_time_ist"],
        "forecast_pm_history_cutoff_ist": artifact["pm_history_cutoff_ist"],
        "forecast_generated_at_ist": artifact["generated_at_ist"],
        "forecast_source": "TASK011 final P_fix, issued 10 November 2026; preserved audited output; no rerun after source deadline",
        "forecast_prediction_sha256": sha(args.prediction),
        "forecast_prediction_audit_sha256": sha(audit_path),
        "forecast_row_audit_sha256": sha(rows_path),
        "forecast_task_manifest_sha256": sha(task_manifest_path),
        "forecast_training_data_sha256": task_manifest["input_sha256"]["Train.csv"],
        "forecast_release_integrity_sha256": sha(args.integrity),
    })
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"artifact_id": artifact["artifact_id"], "issue": artifact["model_issue_time_ist"],
                      "cutoff": artifact["pm_history_cutoff_ist"], "generated": artifact["generated_at_ist"],
                      "horizon_end": artifact["stations"][0]["forecasts"][-1]["target_end_ist"],
                      "hours_per_station": len(artifact["stations"][0]["forecasts"]),
                      "fallback_sha256": sha(fallback), "forecast_sha256": sha(current),
                      "prediction_sha256": sha(args.prediction), "validation": "PASS"}, indent=2))


if __name__ == "__main__":
    main()
