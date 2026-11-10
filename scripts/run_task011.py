"""Reproduce final-gap baselines and create the two guarded TASK011 submissions."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from prepare_task008_submission import CORE, digest

from mumbai_pm25.data import load_data
from mumbai_pm25.final_gap import ForecastBlock, score_predictions
from mumbai_pm25.forecast import (
    derive_pm_history_cutoff,
    predict_station_baseline,
    predict_test_with_hist24_blend,
    validate_submission,
)
from mumbai_pm25.historical_archive import load_2024_history
from mumbai_pm25.oof_cache import cache_manifest_matches

STATIONS = (11606, 11611, 3409510, 3409511)
IST = ZoneInfo("Asia/Kolkata")
RELEASE = pd.Timestamp("2026-11-10 12:27", tz="Asia/Kolkata")
EXPECTED_TRAIN_HASH = "8adbcf55315f166d7dc3dc1d3e4d7400651f26c1d8b95ff387eef38f4e70a283"


def freeze(train_path: Path, raw_dir: Path, snapshot: Path) -> dict[str, str]:
    snapshot.mkdir(parents=True, exist_ok=True)
    for name in CORE:
        source = train_path if name == "Train.csv" else raw_dir / name
        target = snapshot / name
        if target.exists():
            if digest(target) != digest(source):
                raise FileExistsError(f"Preserve differing frozen input: {target}")
        else:
            shutil.copyfile(source, target)
    hashes = {name: digest(snapshot / name) for name in CORE}
    if hashes["Train.csv"] != EXPECTED_TRAIN_HASH:
        raise ValueError("Official final Train hash mismatch")
    return hashes


def blend_diur7(pfix: np.ndarray, diur7: np.ndarray, weight: float = 0.25) -> np.ndarray:
    """Use P_fix when the profile is unsupported; otherwise apply the fixed blend."""
    pfix, diur7 = np.asarray(pfix, dtype=float), np.asarray(diur7, dtype=float)
    if pfix.shape != diur7.shape or not np.isfinite(pfix).all() or (pfix < 0).any():
        raise ValueError("P_fix and diur7 must align and P_fix must be finite/non-negative")
    if not 0 <= weight <= 1:
        raise ValueError("weight must be in [0, 1]")
    return np.where(np.isfinite(diur7), (1-weight)*pfix + weight*diur7, pfix)


def overlay_exact_labels(train: pd.DataFrame, test: pd.DataFrame,
                         prediction: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Replace predictions only for exact station + target-interval-end matches."""
    values = np.asarray(prediction, dtype=float).copy()
    if len(values) != len(test):
        raise ValueError("prediction and Test row counts differ")
    if train.duplicated(["location_id", "timestamp_ist"]).any():
        raise ValueError("duplicate station/interval-end keys in Train")
    ends = pd.to_datetime(train.timestamp_ist, utc=True)
    keys = pd.MultiIndex.from_arrays(
        [test.location_id.to_numpy(), pd.to_datetime(test.target_end_ist, utc=True)],
        names=["location_id", "timestamp_ist"],
    )
    observed = train.assign(timestamp_ist=ends).set_index(["location_id", "timestamp_ist"]).pm25.reindex(keys)
    matched = observed.notna().to_numpy()
    values[matched] = observed.to_numpy(float)[matched]
    return values, matched


def metric_table(rows: pd.DataFrame, models: list[str]) -> pd.DataFrame:
    result = score_predictions(rows, models)
    result["clean_rmse_y_lt_250"] = [
        float(np.sqrt(np.mean((part[m].to_numpy(float)[part.y.to_numpy(float) < 250] -
                               part.y.to_numpy(float)[part.y.to_numpy(float) < 250]) ** 2)))
        for m in models for _, part in [(m, rows.loc[rows.y.notna()])]
    ]
    result["rmse_y_ge_250"] = [
        float(np.sqrt(np.mean((rows.loc[rows.y.ge(250), m] - rows.loc[rows.y.ge(250), "y"]) ** 2)))
        if rows.y.ge(250).any() else np.nan for m in result.model
    ]
    result["extreme_sse_share_y_ge_250"] = [
        float(np.square(rows.loc[rows.y.ge(250), m] - rows.loc[rows.y.ge(250), "y"]).sum() /
              np.square(rows.loc[rows.y.notna(), m] - rows.loc[rows.y.notna(), "y"]).sum())
        if np.square(rows.loc[rows.y.notna(), m] - rows.loc[rows.y.notna(), "y"]).sum() else 0.0
        for m in result.model
    ]
    return result


def run(data_dir: Path, supplied_submission: Path, report_dir: Path,
        output_dir: Path, raw_dir: Path, train_path: Path) -> None:
    hashes = freeze(train_path, raw_dir, data_dir)
    train, test, sample, _ = load_data(data_dir)
    cutoff = derive_pm_history_cutoff(train)
    issue = pd.Timestamp(datetime.now(IST))
    if issue.date() != pd.Timestamp("2026-11-10").date() or issue > pd.Timestamp("2026-11-10 23:59:59", tz=IST):
        raise ValueError("Run must occur before the 10 Nov IST deadline")
    train_file = pd.read_csv(data_dir / "Train.csv")
    if len(train_file) != 48400 or train_file.duplicated(["location_id", "timestamp_ist"]).any():
        raise ValueError("Train row count/uniqueness failed")
    if train_file.isna().any().any() or not train_file["mean"].equals(train_file["pm25"]):
        raise ValueError("Train missingness or mean==pm25 audit failed")
    station_ends = train.groupby("location_id").timestamp_ist.max()
    if len(station_ends) != 4 or not station_ends.eq(pd.Timestamp("2026-11-10 09:00", tz=IST)).all():
        raise ValueError("Unexpected station-specific cutoff")
    archive = load_2024_history(data_dir / "AdditionalHistory.zip")
    pfix = predict_test_with_hist24_blend(train, test, archive, issue_time=issue,
                                         pm_history_cutoff=cutoff)
    targets = pd.to_datetime(test.target_start_ist, utc=True).dt.tz_convert(IST)
    diur = np.full(len(test), np.nan)
    for station in STATIONS:
        ix = np.flatnonzero(test.location_id.to_numpy() == station)
        history = train.loc[train.location_id.eq(station)].set_index("target_start").pm25.sort_index()
        diur[ix] = predict_station_baseline(history, pd.DatetimeIndex(targets.iloc[ix]),
                                            pm_history_cutoff=cutoff, model="diur7")
    private = targets.ge(pd.Timestamp("2026-11-11", tz=IST)) & targets.lt(pd.Timestamp("2026-11-13", tz=IST))
    baseline = pfix.Target.to_numpy(float)
    blend = blend_diur7(baseline, diur, .25)
    # Exact release overlay: test target END equals the Train interval END.
    test_end = pd.to_datetime(test.target_end_ist, utc=True)
    pfix_final, matched = overlay_exact_labels(train_file, test, baseline)
    blend_final, blend_matched = overlay_exact_labels(train_file, test, blend)
    if not np.array_equal(matched, blend_matched):
        raise ValueError("Overlay keys differ between candidates")
    released = train_file.assign(timestamp_ist=pd.to_datetime(train_file.timestamp_ist, utc=True))
    lookup = released.set_index(["location_id", "timestamp_ist"]).pm25
    keys = pd.MultiIndex.from_arrays([test.location_id, test_end], names=["location_id", "timestamp_ist"])
    observed = lookup.reindex(keys)
    public_active = targets.ge(pd.Timestamp("2026-11-08", tz=IST)) & test_end.le(pd.Timestamp("2026-11-10 09:00", tz=IST).tz_convert("UTC"))
    active_match = matched & public_active.to_numpy()
    if int(matched.sum()) != 1284 or int(active_match.sum()) != 201 or (matched & private.to_numpy()).any():
        raise ValueError(f"Released-label overlay mismatch: matched={matched.sum()} active={active_match.sum()}")
    sample_ids = sample.ID.tolist()
    provided = pd.read_csv(supplied_submission)
    if list(provided.columns) != ["ID", "Target"] or provided.ID.tolist() != sample_ids:
        raise ValueError("Supplied FINAL_SUBMISSION schema/order mismatch")
    output_dir.mkdir(parents=True, exist_ok=True)
    audit_rows = test[["ID", "location_id"]].copy()
    audit_rows["target_start"] = targets
    audit_rows["target_end"] = test_end.dt.tz_convert(IST)
    audit_rows["prediction_origin"] = issue
    audit_rows["pm_history_cutoff"] = cutoff
    audit_rows["last_pm_end"] = audit_rows.location_id.map(station_ends)
    audit_rows["physical_target_lead_hours"] = (audit_rows.target_start-audit_rows.last_pm_end).dt.total_seconds()/3600
    audit_rows["private"] = private
    audit_rows["released_observation_match"] = matched
    audit_rows["P_fix"] = baseline
    audit_rows["diur7"] = diur
    audit_rows["Pfix_diur25"] = blend
    audit_rows["overlay_pm25"] = observed.to_numpy(float)
    metrics_rows = None
    pfix_out, blend_out = pfix_final, blend_final
    models = ["median24", "median72", "median168", "ewm72", "diur7", "diurnal7_raw",
              "hour_week4", "recent_shrink72", "recent_shrink168", "P_fix", "archive_decay72",
              "archive_decay168", "archive_piecewise", "archive_constant50", "current_decay168",
              "current_constant50"]
    report_dir.mkdir(parents=True, exist_ok=True)
    oof_path = report_dir / "task011_84_origin_oof.csv.gz"
    coverage_path = report_dir / "task011_origin_coverage.csv"
    cache_manifest_path = report_dir / "task011_84_origin_oof.manifest.json"
    fold_schedule = [t.isoformat() for t in pd.date_range("2025-04-02 00:00", "2026-11-04 00:00", freq="7D", tz=IST)]
    source_files = ["scripts/run_task011.py", "scripts/prepare_task008_submission.py",
                    "src/mumbai_pm25/final_gap.py", "src/mumbai_pm25/forecast.py",
                    "src/mumbai_pm25/historical_archive.py", "src/mumbai_pm25/oof_cache.py"]
    expected_cache_manifest = {
        "input_sha256": {name: digest(data_dir / name) for name in
                         ("Train.csv", "Test.csv", "SampleSubmission.csv", "Stations.csv", "AdditionalHistory.zip")},
        "source_sha256": {name: digest(ROOT / name) for name in source_files},
        "fold_schedule": fold_schedule,
        "configuration": {"initial_gap_hours": 15, "horizon_hours": 48, "frequency": "7D",
                          "models": models, "archive_blend_weight": 0.5},
    }
    cache_valid = False
    if oof_path.exists() and coverage_path.exists() and cache_manifest_path.exists():
        cached_manifest = json.loads(cache_manifest_path.read_text(encoding="utf-8"))
        expected_with_artifacts = {
            **expected_cache_manifest,
            "artifact_sha256": {oof_path.name: digest(oof_path), coverage_path.name: digest(coverage_path)},
        }
        cache_valid = cache_manifest_matches(cached_manifest, expected_with_artifacts)
    if cache_valid:
        metrics_rows = pd.read_csv(oof_path, parse_dates=["fold_id","prediction_origin","pm_history_cutoff","target_start","target_end","block_target_end","last_pm_end"])
        for col in ("fold_id","prediction_origin","pm_history_cutoff","target_start","target_end","block_target_end","last_pm_end"):
            metrics_rows[col] = pd.to_datetime(metrics_rows[col], utc=True).dt.tz_convert(IST)
        coverage = pd.read_csv(coverage_path)
    else:
        blocks = [ForecastBlock(t, t-pd.Timedelta(hours=15), t-pd.Timedelta(hours=15))
                  for t in pd.date_range("2025-04-02 00:00", "2026-11-04 00:00", freq="7D", tz=IST)]
        metrics_rows, coverage = __import__("mumbai_pm25.final_gap", fromlist=["labelled_blocks"]).labelled_blocks(train, archive, blocks)
    # Publish a sidecar after the OOF and coverage artifacts have been written below.
    metrics_rows["Pfix_diur10"] = .90*metrics_rows.P_fix + .10*metrics_rows.diur7.fillna(metrics_rows.P_fix)
    metrics_rows["Pfix_diur25"] = .75*metrics_rows.P_fix + .25*metrics_rows.diur7.fillna(metrics_rows.P_fix)
    metrics_rows["Pfix_diur50"] = .50*metrics_rows.P_fix + .50*metrics_rows.diur7.fillna(metrics_rows.P_fix)
    metric_models = models + ["Pfix_diur10", "Pfix_diur25", "Pfix_diur50"]
    met = metric_table(metrics_rows, metric_models)
    metrics_rows.to_csv(oof_path, index=False, compression="gzip")
    coverage.to_csv(coverage_path, index=False)
    cache_manifest = {
        **expected_cache_manifest,
        "artifact_sha256": {oof_path.name: digest(oof_path), coverage_path.name: digest(coverage_path)},
    }
    cache_manifest_path.write_text(json.dumps(cache_manifest, indent=2) + "\n", encoding="utf-8")
    met.to_csv(report_dir / "task011_baseline_comparison.csv", index=False)
    for weight in (10,25,50):
        m = f"Pfix_diur{weight}"
        metrics_rows[m] = metrics_rows.P_fix*(1-weight/100) + metrics_rows.diur7.fillna(metrics_rows.P_fix)*(weight/100)
    wrows=[]
    valid=metrics_rows.loc[metrics_rows.y.notna()]
    for w in (10,25,50):
        col=f"Pfix_diur{w}"
        err=valid[col]-valid.y
        wrows.append({"weight_pct":w,"rows":len(valid),"origins":valid.fold_id.nunique(),"full_target_rmse":float(np.sqrt(np.mean(err**2)),),"mae":float(np.abs(err).mean()),"bias":float(err.mean()),"y_lt_250_rmse":float(np.sqrt(np.mean(err[valid.y.lt(250)]**2))),"y_ge_250_rmse":float(np.sqrt(np.mean(err[valid.y.ge(250)]**2))),"origin_rmse":valid.assign(sse=err**2).groupby("fold_id").sse.mean().pow(.5).to_dict()})
    pd.DataFrame(wrows).to_json(report_dir / "task011_diur7_weight_comparison.json", orient="records", indent=2)
    # Station cutoffs, exact target-end matching, and per-row final clocks.
    audit_rows.to_csv(report_dir / "task011_final_row_audit.csv", index=False)
    for name, vals, formula in [
        ("task011_final_Pfix_20261110.csv", pfix_out, "P_fix; exact month/day archive blend"),
        ("task011_final_Pfix_diur25_20261110.csv", blend_out, "0.75*P_fix + 0.25*diur7; missing diur7 falls back to P_fix"),
    ]:
        frame = pd.DataFrame({"ID": sample_ids, "Target": vals})
        validate_submission(frame, test)
        out = output_dir/name
        if out.exists():
            if not frame.equals(pd.read_csv(out)):
                raise FileExistsError(f"Existing output differs from deterministic candidate: {out}")
        else:
            frame.to_csv(out,index=False)
        # Independent deterministic rerun from the identical frozen inputs.
        p2 = predict_test_with_hist24_blend(train, test, archive, issue_time=issue, pm_history_cutoff=cutoff).Target.to_numpy(float)
        v2 = p2.copy() if "diur25" not in name else blend_diur7(p2, diur, .25)
        v2, _ = overlay_exact_labels(train_file,test,v2)
        if not np.array_equal(vals,v2): raise ValueError("Inference rerun differs")
        rows= audit_rows[["ID","location_id","target_start","target_end","prediction_origin","pm_history_cutoff","last_pm_end","physical_target_lead_hours","private","released_observation_match"]].copy()
        rows["Target"]=vals
        rows.to_csv(out.with_suffix(".rows.csv"),index=False)
        audit={"rows":len(frame),"schema":list(frame.columns),"exact_id_order":True,"finite":bool(np.isfinite(vals).all()),"nonnegative":bool((vals>=0).all()),"deterministic_rerun":True,"overlay_rows":int(matched.sum()),"active_public_rows":int(active_match.sum()),"private_overlay_rows":int((matched&private.to_numpy()).sum()),"private_rows":int(private.sum()),"private_lead_min":float(audit_rows.loc[private,"physical_target_lead_hours"].min()),"private_lead_max":float(audit_rows.loc[private,"physical_target_lead_hours"].max()),"model_formula":formula,"input_sha256":hashes,"output_sha256":digest(out),"model_run_time":issue.isoformat(),"release_announcement_time":RELEASE.isoformat(),"pm_history_cutoff":cutoff.isoformat()}
        out.with_suffix(".audit.json").write_text(json.dumps(audit,indent=2)+"\n",encoding="utf-8")
        manifest={**audit,"git_commit":subprocess.run(["git","rev-parse","HEAD"],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip(),"source_sha256":{f:digest(ROOT/f) for f in ["scripts/run_task011.py","scripts/prepare_task008_submission.py","src/mumbai_pm25/forecast.py","src/mumbai_pm25/historical_archive.py"]},"station_cutoffs":{str(k):v.isoformat() for k,v in station_ends.items()},"source_url":"Official Zindi competition Data page; exact download URL/receipt not provided","retrieval_time":"Owner-supplied download; filesystem timestamp recorded separately in final report","zindi_action":"Human upload and selection required; not uploaded"}
        out.with_suffix(".manifest.txt").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")


if __name__ == "__main__":
    run(ROOT/"data/processed/official_releases/20261110_final",
        Path(r"C:\Users\sujal\Downloads\FINAL_SUBMISSION.csv"),
        ROOT/"reports/ml_pipeline/task011", ROOT/"artifacts/submissions",
        ROOT/"data/raw/challenge", ROOT/"data/raw/challenge/Train (2).csv")
