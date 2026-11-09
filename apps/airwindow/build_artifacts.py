"""Export AirWindow's live forecast and separate retrospective decision replay.

Consumes immutable ML predictions. Does not fit, change or duplicate the model.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from apps.airwindow.contract_validation import validate_artifact
from apps.airwindow.decision_engine import (
    Hour,
    Window,
    classify_decision,
    compare_schedule,
    observed_mean,
)
from apps.airwindow.replay_validation import validate_replay

SEED = 20261108
UNIT = "\u00b5g/m\u00b3"
STATION_NAMES = {"11606": "Borivali East", "11611": "Malad West", "3409510": "Byculla", "3409511": "Shivaji Nagar"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def scalar(value: Any) -> float | None:
    return float(value) if pd.notna(value) and np.isfinite(float(value)) else None


def metric(part: pd.DataFrame) -> dict[str, Any]:
    outcomes = part.loc[part.observed_difference.notna()]
    changed = outcomes.loc[outcomes.predicted_difference.lt(0)]
    return {"cases": len(part), "origins": int(part.fold_id.nunique()),
            "paired_outcome_origins": int(outcomes.fold_id.nunique()),
            "paired_outcome_cases": len(outcomes), "missing_outcome_cases": len(part)-len(outcomes),
            "selected_alternative_cases": len(changed), "recommended_cases": 0,
            "lower_observed_fraction": float(changed.observed_difference.lt(0).mean()) if len(changed) else None,
            "median_realised_difference": scalar(changed.observed_difference.median()),
            "hindsight_gap_median": scalar(outcomes.hindsight_gap.median()),
            "complete_hindsight_cases": int(outcomes.hindsight_gap.notna().sum()),
            "missing_hindsight_cases": int(outcomes.hindsight_gap.isna().sum()),
            "median_absolute_difference_error": scalar((outcomes.predicted_difference-outcomes.observed_difference).abs().median())}


def window_json(window: Window, hours: list[Hour], rank: int | None = None) -> dict[str, Any]:
    return {"start_ist": window.start.isoformat(), "end_ist": window.end.isoformat(),
            "mean_prediction": window.mean_prediction, "max_prediction": window.max_prediction,
            "peak_start_ist": window.peak_start.isoformat(), "hourly_predictions": list(window.hourly_predictions),
            "mean_observed": observed_mean(window, hours), "rank": rank}


def build_forecast(prediction: Path, audit_path: Path, rows_path: Path,
                   stations_path: Path, oof: pd.DataFrame,
                   generated_at: pd.Timestamp) -> dict[str, Any]:
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if audit["output_sha256"] != sha(prediction):
        raise ValueError("Forecast CSV does not match its ML audit hash")
    forecast = pd.read_csv(prediction)
    rows = pd.read_csv(rows_path)
    if forecast.ID.tolist() != rows.ID.tolist() or not np.allclose(forecast.Target, rows.Target, rtol=0, atol=1e-9):
        raise ValueError("Forecast and temporal row audit differ")
    issue = pd.Timestamp(audit["model_run_time"])
    rows["target_start"] = pd.to_datetime(rows.target_start, utc=True).dt.tz_convert("Asia/Kolkata")
    rows["target_end"] = pd.to_datetime(rows.target_end, utc=True).dt.tz_convert("Asia/Kolkata")
    rows = rows.loc[rows.target_start.gt(issue)].copy()
    if rows.empty or generated_at < issue:
        raise ValueError("Need future forecasts and generation time no earlier than issue")
    stations = pd.read_csv(stations_path).set_index("location_id")
    result = []
    for station_id, short_name in STATION_NAMES.items():
        sid = int(station_id)
        station = stations.loc[sid]
        part = rows.loc[rows.location_id.eq(sid)].sort_values("target_start")
        last = pd.Timestamp(audit["station_last_pm_end"][station_id])
        validation = []
        hist = oof.loc[oof.location_id.eq(sid) & oof.y.notna()]
        for lead, values in hist.groupby("forecast_lead_hours"):
            errors = values.P_fix-values.y
            folds = values.assign(sq=errors**2).groupby("fold_id").sq.mean().pow(.5)
            validation.append({"horizon_hours": int(lead), "status": "measured",
                               "primary_metric": "full_target_rmse", "rmse": float(np.sqrt(np.mean(errors**2))),
                               "n_targets": len(values), "folds": int(values.fold_id.nunique()),
                               "fold_rmse_std": scalar(folds.std())})
        hours = [{"target_start_ist": row.target_start.isoformat(), "target_end_ist": row.target_end.isoformat(),
                  "pm25_prediction": scalar(row.Target), "unit": UNIT,
                  "forecast_horizon_hours": (row.target_start-issue).total_seconds()/3600,
                  "status": "available" if scalar(row.Target) is not None else "missing", "prediction_interval": None}
                 for row in part.itertuples(index=False)]
        available = sum(row["status"] == "available" for row in hours)
        result.append({"station_id": station_id, "station_name": short_name,
                       "latitude": float(station.latitude), "longitude": float(station.longitude),
                       "last_observation_ist": last.isoformat(),
                       "freshness": {"status": "unknown", "observation_age_hours": (issue-last).total_seconds()/3600,
                                     "stale_after_hours": None, "note": "Age is measured at forecast issue; no validated freshness threshold is configured. Current snapshot is provisional."},
                       "data_status": {"status": "complete" if available == len(hours) else "partial" if available else "unavailable",
                                       "expected_forecast_hours": len(hours), "available_forecast_hours": available,
                                       "missing_target_starts_ist": [row["target_start_ist"] for row in hours if row["status"] == "missing"],
                                       "note": "Future target hours only. Historical validation uses a 193-240h PM-gap proxy and is not a matching live issue-lead calibration."},
                       "validation": validation, "forecasts": hours})
    artifact = {"schema_version": "1.1.0", "artifact_id": "task008-pfix-"+sha(prediction)[:16],
                "generated_at_ist": generated_at.isoformat(), "model_issue_time_ist": issue.isoformat(),
                "pm_history_cutoff_ist": audit["pm_history_cutoff"],
                "model": {"id": "P_fix", "version": "TASK008-provisional-source-"+audit["source_sha256"]["src/mumbai_pm25/forecast.py"][:12],
                          "git_commit": audit["git_commit"], "training_data_sha256": audit["input_sha256"]["Train.csv"]},
                "weather": {"used": False, "provider": None, "model": None, "issue_time_ist": None},
                "uncertainty": {"status": "not_calibrated", "method": None, "calibration_folds": None,
                                "nominal_coverage": None, "empirical_coverage": None}, "stations": result}
    validate_artifact(artifact)
    return artifact


def replay_cases(all_rows: pd.DataFrame, matched_origins: set[str]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """All predeclared school scenarios; forecasts rank before outcome availability."""
    rows = all_rows.loc[all_rows.fold_id.astype(str).isin(matched_origins)].copy()
    for field in ("fold_id", "prediction_origin", "pm_history_cutoff", "last_pm_end", "target_start", "target_end"):
        rows[field] = pd.to_datetime(rows[field], utc=True).dt.tz_convert("Asia/Kolkata")
    cases, coverage = [], {"scenario_cases_considered": 0, "missing_original_or_feasible_forecast": 0}
    for (fold, sid), part in rows.groupby(["fold_id", "location_id"], sort=True):
        for day in (0, 1):
            date = fold + pd.Timedelta(days=day)
            start, end, original_start = date+pd.Timedelta(hours=8), date+pd.Timedelta(hours=18), date+pd.Timedelta(hours=9)
            period = part.loc[part.target_start.ge(start) & part.target_start.lt(end)]
            hours = [Hour(row.target_start.to_pydatetime(), row.target_end.to_pydatetime(), scalar(row.P_fix), scalar(row.y))
                     for row in period.itertuples(index=False)]
            if not len(period):
                coverage["scenario_cases_considered"] += 3
                coverage["missing_original_or_feasible_forecast"] += 3
                continue
            metadata = period.iloc[0]
            for duration in (1, 2, 3):
                coverage["scenario_cases_considered"] += 1
                try:
                    original, selected, windows = compare_schedule(hours, original_start=original_start.to_pydatetime(),
                            duration=duration, earliest_start=start.to_pydatetime(), latest_end=end.to_pydatetime())
                except ValueError as error:
                    if "incomplete" not in str(error) and "No complete" not in str(error):
                        raise
                    coverage["missing_original_or_feasible_forecast"] += 1
                    continue
                original_observed, selected_observed = observed_mean(original, hours), observed_mean(selected, hours)
                actual_windows = [observed_mean(window, hours) for window in windows]
                actual_windows = [value for value in actual_windows if value is not None]
                difference = selected.mean_prediction-original.mean_prediction
                outcome = None if original_observed is None or selected_observed is None else selected_observed-original_observed
                case = {"case_id": f"{sid}-{fold:%Y%m%d}-d{day+1}-h{duration}", "station_id": str(sid),
                        "station_name": STATION_NAMES[str(sid)], "duration_hours": duration,
                        "fold_id": fold.isoformat(), "split": metadata["split"],
                        "issue_time_ist": metadata.prediction_origin.isoformat(),
                        "pm_history_cutoff_ist": metadata.pm_history_cutoff.isoformat(), "last_pm_end_ist": metadata.last_pm_end.isoformat(),
                        "original_start_ist": original.start.isoformat(), "original_end_ist": original.end.isoformat(),
                        "feasible_start_ist": start.isoformat(), "feasible_end_ist": end.isoformat(),
                        "selected_start_ist": selected.start.isoformat(), "selected_end_ist": selected.end.isoformat(),
                        "lead_min_hours": (start-metadata.prediction_origin).total_seconds()/3600,
                        "lead_max_hours": (end-pd.Timedelta(hours=1)-metadata.prediction_origin).total_seconds()/3600,
                        "pm_lead_min_hours": (start-metadata.last_pm_end).total_seconds()/3600,
                        "pm_lead_max_hours": (end-pd.Timedelta(hours=1)-metadata.last_pm_end).total_seconds()/3600,
                        "predicted_difference": difference, "observed_difference": outcome,
                        "hindsight_gap": None if selected_observed is None or len(actual_windows) != len(windows) else max(0., selected_observed-min(actual_windows)),
                        "hindsight_complete": len(actual_windows) == len(windows),
                        "observed_feasible_windows": len(actual_windows), "forecast_feasible_windows": len(windows),
                        "decision_status": "INSUFFICIENT EVIDENCE", "decision_reason": "Uncalibrated historical comparison.",
                        "hours": [{"target_start_ist": hour.start.isoformat(), "target_end_ist": hour.end.isoformat(),
                                   "prediction": hour.prediction, "observed": hour.observed} for hour in hours],
                        "windows": [window_json(window, hours, rank+1) for rank, window in enumerate(windows)],
                        "original": window_json(original, hours, next((i+1 for i, window in enumerate(windows) if window.start == original.start), None)),
                        "selected": window_json(selected, hours, next((i+1 for i, window in enumerate(windows) if window.start == selected.start), None))}
                cases.append(case)
    return cases, coverage


def origin_bootstrap(cases: pd.DataFrame, repetitions: int = 1000) -> dict[str, Any]:
    """Exploratory sampling variability, never a calibrated forecast interval."""
    known = cases.loc[cases.observed_difference.notna() & cases.predicted_difference.lt(0)].copy()
    if known.empty:
        return {"status": "not_available", "origins": 0}
    known["won"] = known.observed_difference.lt(0).astype(int)
    by_origin = known.groupby("fold_id", sort=True).agg(wins=("won", "sum"), cases=("won", "size"), difference=("observed_difference", "sum"))
    values = by_origin.to_numpy(dtype=float)
    length = min(4, len(values))
    rng = np.random.default_rng(SEED)
    starts = rng.integers(0, len(values)-length+1, size=(repetitions, int(np.ceil(len(values)/length))))
    indices = (starts[..., None]+np.arange(length)).reshape(repetitions, -1)[:, :len(values)]
    totals = values[indices].sum(axis=1)
    return {"status": "exploratory_not_calibrated", "origins": len(values), "resamples": repetitions,
            "contiguous_origin_block_length": length, "seed": SEED,
            "win_fraction_resampling_sd": float(np.std(totals[:, 0]/totals[:, 1])),
            "mean_difference_resampling_sd": float(np.std(totals[:, 2]/totals[:, 1])),
            "note": "Whole paired-origin cases resampled in contiguous blocks; no independent-hour bootstrap; not an uncertainty interval for live decisions."}


def build_replay(all_rows: pd.DataFrame, matched: pd.DataFrame, oof_path: Path,
                 latest_observation: str, generated_at: pd.Timestamp) -> tuple[dict[str, Any], dict[str, Any]]:
    cases, coverage = replay_cases(all_rows, set(matched.fold_id.astype(str)))
    frame = pd.DataFrame(cases)
    profiles, grouped = [], []
    for (station, duration, split), part in frame.groupby(["station_id", "duration_hours", "split"], sort=True):
        stats = metric(part)
        hist = matched.loc[matched.location_id.eq(int(station)) & matched["split"].eq(split)]
        grouped.append({"station_id": station, "duration_hours": int(duration), "split": split,
                        "lead_min_hours": float(part.lead_min_hours.min()), "lead_max_hours": float(part.lead_max_hours.max()),
                        "pm_lead_min_hours": float(part.pm_lead_min_hours.min()), "pm_lead_max_hours": float(part.pm_lead_max_hours.max()),
                        "rmse": float(np.sqrt(np.mean((hist.P_fix-hist.y)**2))), "validation_rows": len(hist), **stats})
    # Development errors only can inform later confirmation's descriptive state.
    # Stratify by station, duration and target-day issue-lead range; never pool stations.
    development = frame.loc[frame["split"].eq("development")].copy()
    for (station, duration, lead), part in development.groupby(["station_id", "duration_hours", "lead_min_hours"], sort=True):
        stats = metric(part)
        profile = {"station_id": station, "duration_hours": int(duration), "split": "development",
                   "lead_min_hours": float(lead), "lead_max_hours": float(part.lead_max_hours.max()),
                   "pm_lead_min_hours": float(part.pm_lead_min_hours.min()), "pm_lead_max_hours": float(part.pm_lead_max_hours.max()),
                   "calibration_status": "not_calibrated", "comparable": True, **stats}
        profiles.append(profile)
    for case in cases:
        profile = next((p for p in profiles if p["station_id"] == case["station_id"] and p["duration_hours"] == case["duration_hours"]
                        and p["lead_min_hours"] == case["lead_min_hours"]), None)
        # Development case states must not use their own outcomes; keep them unassessed.
        state = classify_decision(case["predicted_difference"], profile if case["split"] == "confirmation" else None)
        case["decision_status"], case["decision_reason"] = state["state"], state["reason"]
    artifact = {"schema_version": "1.0.0", "artifact_id": "task008-pfix-replay-"+sha(oof_path)[:16],
                "generated_at_ist": generated_at.isoformat(), "model": {"id": "P_fix", "version": "TASK008-provisional", "git_commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()},
                "provenance": {"oof_sha256": sha(oof_path), "prediction_lineage": "Genuine fixed-origin chronological OOF generated retrospectively on 8 November 2026; issue times are simulated historical origins, not archived real-time forecast vintages.",
                               "availability_assumption": "PM interval end is a proxy for availability; first-publication times are unverified. P_fix archive series policy uses supplied 2024 history.",
                               "independent_calibration": False, "latest_available_observation_end_ist": latest_observation,
                               "historical_confirmation_limit": "Later chronological origins were previously inspected by analysts; this is not independent calibration.",
                               "live_lead_comparability": "OOF issue equals PM cutoff (193-240h issue lead). Current live issue is later than PM cutoff; matching PM-information age does not establish matching issue-lead calibration."},
                "calibration": {"status": "not_calibrated", "reason": "No independently validated decision probability/interval method; descriptive paired errors only.", "probability": None, "interval": None},
                "scenario": {"original_hour_ist": 9, "feasible_start_hour_ist": 8, "feasible_end_hour_ist": 18,
                             "durations_hours": [1, 2, 3], "target_days": [1, 2],
                             "definition": "All matched OOF origins, stations and both target days. Rank every complete forecast window before inspecting actual outcomes; retain cases with missing outcomes.", **coverage},
                "summary": metric(frame), "by_station_duration": grouped, "reliability_profiles": profiles, "cases": cases}
    validate_replay(artifact)
    diagnostics = {"method": "Paired original/selected differences; station-duration-lead conditioned; development-only descriptive error benchmark applied to later confirmation; no calibrated probabilities.",
                   "development": origin_bootstrap(frame.loc[frame["split"].eq("development")]),
                   "confirmation": origin_bootstrap(frame.loc[frame["split"].eq("confirmation")]),
                   "confirmation_metrics": metric(frame.loc[frame["split"].eq("confirmation")]),
                   "development_metrics": metric(frame.loc[frame["split"].eq("development")])}
    return artifact, diagnostics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prediction", type=Path, default=ROOT / "artifacts/submissions/task008_provisional_pfix_20261108_1558.csv")
    parser.add_argument("--run-dir", type=Path, default=ROOT / "reports/ml_pipeline/task008/run01")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).parent / "public/data")
    parser.add_argument("--generated-at", default=None)
    args = parser.parse_args()
    generated = pd.Timestamp(args.generated_at) if args.generated_at else pd.Timestamp.now(tz="Asia/Kolkata").floor("s")
    matched = pd.read_csv(args.run_dir / "matched_oof.csv.gz")
    all_path = args.run_dir / "all_block_rows.csv.gz"
    if not all_path.exists():
        raise FileNotFoundError("Run scripts/run_task008.py to recreate all_block_rows.csv.gz; matched labelled rows alone cannot rank without outcome-availability bias")
    all_rows = pd.read_csv(all_path)
    audit_path, rows_path = args.prediction.with_suffix(".audit.json"), args.prediction.with_suffix(".rows.csv")
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    forecast = build_forecast(args.prediction, audit_path, rows_path, ROOT / "data/raw/challenge/Stations.csv", matched, generated)
    replay, diagnostics = build_replay(all_rows, matched, all_path, audit["pm_history_cutoff"], generated)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in (("forecast.json", forecast), ("replay.json", replay)):
        (args.output_dir / name).write_text(json.dumps(payload, separators=(",", ":"), allow_nan=False)+"\n", encoding="utf-8")
    evidence = Path(__file__).parent / "evidence"
    evidence.mkdir(exist_ok=True)
    (evidence / "replay_diagnostics.json").write_text(json.dumps(diagnostics, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    manifest = {"generated_at_ist": generated.isoformat(), "export_git_commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip(),
                "prediction_sha256": sha(args.prediction), "prediction_audit_sha256": sha(audit_path), "all_block_oof_sha256": sha(all_path),
                "matched_oof_sha256": sha(args.run_dir / "matched_oof.csv.gz"), "forecast_sha256": sha(args.output_dir / "forecast.json"),
                "replay_sha256": sha(args.output_dir / "replay.json"), "calibration": "NOT CALIBRATED", "model_issue_time_ist": forecast["model_issue_time_ist"],
                "forecast_source_code": audit["source_sha256"], "training_data_sha256": audit["input_sha256"]["Train.csv"],
                "forecast_hours_per_station": len(forecast["stations"][0]["forecasts"]), "replay_summary": replay["summary"],
                "replay_scenario": replay["scenario"]}
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
