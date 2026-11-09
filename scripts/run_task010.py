"""Audit TASK010 supplied forecasts and run matched station-gap seasonal OOF."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mumbai_pm25.final_gap import ForecastBlock, baseline_predictions, block_features
from mumbai_pm25.historical_archive import (
    P_FIX_SERIES,
    build_seasonal_features,
    load_2024_history,
)

STATIONS = (11606, 11611, 3409510, 3409511)
FIRST_GAP = {11606: 42, 11611: 41, 3409510: 43, 3409511: 41}
FOLD_STARTS = (
    "2026-08-13", "2026-09-03", "2026-09-24", "2026-10-15", "2026-11-05",
    "2025-11-11", "2025-12-15", "2026-01-05", "2026-01-25",
)
BRANCH = "4be5c10"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def branch_bytes(path: str) -> bytes:
    return subprocess.run(["git", "show", f"{BRANCH}:{path}"], cwd=ROOT,
                          capture_output=True, check=True).stdout


def score(rows: pd.DataFrame, models: list[str], keys: tuple[str, ...] = ()) -> pd.DataFrame:
    groups = rows.groupby(list(keys), dropna=False) if keys else [((), rows)]
    result = []
    for key, part in groups:
        key = key if isinstance(key, tuple) else (key,)
        y = part.y.to_numpy(float)
        for model in models:
            pred = part[model].to_numpy(float)
            err = pred - y
            finite = np.isfinite(pred)
            clean = y < 500
            result.append({**dict(zip(keys, key)), "model": model, "rows": len(y),
                           "missing_predictions": int((~finite).sum()),
                           "full_target_rmse": float(np.sqrt(np.mean(err**2))) if finite.all() else np.nan,
                           "mae": float(np.mean(np.abs(err))) if finite.all() else np.nan,
                           "bias": float(np.mean(err)) if finite.all() else np.nan,
                           "clean_rmse_y_lt_500": float(np.sqrt(np.mean(err[clean]**2))) if finite.all() and clean.any() else np.nan,
                           "rows_y_ge_100": int((y >= 100).sum()),
                           "rmse_y_ge_100": float(np.sqrt(np.mean(err[y >= 100]**2))) if finite.all() and (y >= 100).any() else np.nan,
                           "rows_y_ge_250": int((y >= 250).sum()),
                           "rmse_y_ge_250": float(np.sqrt(np.mean(err[y >= 250]**2))) if finite.all() and (y >= 250).any() else np.nan,
                           "rmse_y_lt_250_sensitivity": float(np.sqrt(np.mean(err[y < 250]**2))) if finite.all() and (y < 250).any() else np.nan,
                           "extreme_sse_share_y_ge_250": float(np.sum(err[y >= 250]**2)/np.sum(err**2)) if finite.all() and np.sum(err**2) else 0.0})
    return pd.DataFrame(result)


def paired_bootstrap(rows: pd.DataFrame, candidate: str, comparator: str,
                     seed: int = 20261109, repetitions: int = 5000) -> dict[str, object]:
    """Paired moving-origin bootstrap; each resample retains all rows in an origin."""
    grouped = rows.groupby("fold_id", sort=True).apply(
        lambda g: pd.Series({"a": np.square(g[candidate]-g.y).sum(),
                             "b": np.square(g[comparator]-g.y).sum(), "n": len(g)}),
        include_groups=False)
    vals = grouped.to_numpy(float)
    n = len(vals)
    if n < 2:
        raise ValueError("Need at least two origins for paired bootstrap")
    length = min(3, n)
    rng = np.random.default_rng(seed)
    start = rng.integers(0, n-length+1, size=(repetitions, int(np.ceil(n/length))))
    ix = (start[..., None] + np.arange(length)).reshape(repetitions, -1)[:, :n]
    sample = vals[ix].sum(axis=1)
    deltas = np.sqrt(sample[:, 0]/sample[:, 2]) - np.sqrt(sample[:, 1]/sample[:, 2])
    return {"candidate": candidate, "comparator": comparator,
            "rmse_delta": float(np.sqrt(vals[:, 0].sum()/vals[:, 2].sum()) - np.sqrt(vals[:, 1].sum()/vals[:, 2].sum())),
            "lower95": float(np.quantile(deltas, .025)), "upper95": float(np.quantile(deltas, .975)),
            "origin_wins": int((vals[:, 0] < vals[:, 1]).sum()), "origins": n,
            "block_origins": length, "repetitions": repetitions, "seed": seed}


def legacy_doy_same_hour(history: pd.DataFrame, targets: pd.DataFrame) -> pd.Series:
    """Reproduce legacy 365-day DOY matching while holding P_fix source IDs fixed."""
    by_series = {key: frame.assign(doy=frame.hour_start.dt.day_of_year,
                                   hour=frame.hour_start.dt.hour)
                 for key, frame in history.groupby("series_id", sort=False)}
    values = []
    for row in targets.itertuples(index=False):
        sources = P_FIX_SERIES[int(row.location_id)]
        ts = pd.Timestamp(row.target_start)
        doy = ts.day_of_year
        selected = []
        for source in sources:
            frame = by_series.get(source)
            if frame is None:
                continue
            distance = ((frame.doy - doy + 182) % 365) - 182
            keep = frame.hour.eq(ts.hour) & distance.abs().le(14)
            selected.extend(frame.loc[keep, "pm25"].tolist())
        values.append(float(np.mean(selected)) if len(selected) >= 3 else np.nan)
    return pd.Series(values, index=targets.index, dtype=float)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train", type=Path, required=True)
    parser.add_argument("--supplied-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"Refusing to overwrite run directory: {args.output}")
    args.output.mkdir(parents=True)

    # Preserve the supplied release byte-for-byte under ignored data/processed.
    snapshot = ROOT / "data/processed/task010/input_snapshot"
    snapshot.mkdir(parents=True, exist_ok=True)
    snap_train = snapshot / "Train_20261109.csv"
    if snap_train.exists() and sha256(snap_train) != sha256(args.train):
        raise FileExistsError("Existing task010 Train snapshot has different bytes")
    if not snap_train.exists():
        snap_train.write_bytes(args.train.read_bytes())

    train = pd.read_csv(args.train)
    train_original = train.copy()
    required = {"timestamp_ist", "pm25", "mean", "location_id", "sensor_id", "station_name"}
    if required - set(train):
        raise ValueError(f"Train schema missing: {sorted(required-set(train))}")
    train["timestamp_ist"] = pd.to_datetime(train.timestamp_ist, utc=True).dt.tz_convert("Asia/Kolkata")
    train["target_start"] = train.timestamp_ist - pd.Timedelta(hours=1)
    if train.duplicated(["location_id", "target_start"]).any():
        raise ValueError("Duplicate train station-hour key")

    test = pd.read_csv(ROOT / "data/raw/challenge/Test.csv")
    sample = pd.read_csv(ROOT / "data/raw/challenge/SampleSubmission.csv")
    test["target_start"] = pd.to_datetime(test.target_start_ist, utc=True).dt.tz_convert("Asia/Kolkata")
    supplied_names = {
        "exp030_a": "exp030_a_alpha25_nov9.csv",
        "exp030_b": "exp030_b_adaptive_nov9.csv",
        "task012_corrected_blend": "submission_task012_corrected_blend_test.csv",
    }
    candidates: dict[str, pd.DataFrame] = {}
    for key, name in supplied_names.items():
        frame = pd.read_csv(args.supplied_dir / name)
        if list(frame.columns) != ["ID", "Target"] or not frame.ID.equals(sample.ID):
            raise ValueError(f"{name}: invalid columns or ID order")
        values = frame.Target.to_numpy(float)
        if not np.isfinite(values).all() or (values < 0).any():
            raise ValueError(f"{name}: invalid prediction values")
        candidates[key] = frame

    all_predictions = candidates["exp030_a"].rename(columns={"Target": "exp030_a"})
    for key in ("exp030_b", "task012_corrected_blend"):
        all_predictions = all_predictions.merge(
            candidates[key].rename(columns={"Target": key}), on="ID", validate="one_to_one")
    all_predictions = all_predictions.merge(test[["ID", "location_id", "target_start"]], on="ID", validate="one_to_one")
    pred_cols = ["exp030_a", "exp030_b", "task012_corrected_blend"]
    all_predictions[pred_cols].corr().rename_axis("model").to_csv(args.output / "supplied_prediction_correlation.csv")
    supplied_pair_rows = []
    for left, right in (("exp030_a", "exp030_b"), ("exp030_a", "task012_corrected_blend"),
                        ("exp030_b", "task012_corrected_blend")):
        delta = all_predictions[left]-all_predictions[right]
        private_ids = all_predictions.target_start.ge(pd.Timestamp("2026-11-11", tz="Asia/Kolkata")) & all_predictions.target_start.lt(pd.Timestamp("2026-11-13", tz="Asia/Kolkata"))
        supplied_pair_rows.append({"left": left, "right": right,
                                   "correlation": all_predictions[[left, right]].corr().iloc[0, 1],
                                   "identical_rows": int(delta.eq(0).sum()), "mean_difference": float(delta.mean()),
                                   "private_mean_left": float(all_predictions.loc[private_ids, left].mean()),
                                   "private_mean_right": float(all_predictions.loc[private_ids, right].mean()),
                                   "private_mean_abs_difference": float(delta.loc[private_ids].abs().mean()),
                                   "private_max_abs_difference": float(delta.loc[private_ids].abs().max())})
    pd.DataFrame(supplied_pair_rows).to_csv(args.output / "supplied_prediction_pair_summary.csv", index=False)

    combined = candidates["exp030_a"].rename(columns={"Target": "pred_a"}).merge(
        candidates["exp030_b"].rename(columns={"Target": "pred_b"}), on="ID", validate="one_to_one")
    combined = combined.merge(test[["ID", "location_id", "target_start"]], on="ID", validate="one_to_one")
    diff = combined.pred_a - combined.pred_b
    combined["abs_difference"] = diff.abs()
    combined["identical"] = diff.eq(0)
    combined.to_csv(args.output / "exp030_row_comparison.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
    corr = float(combined[["pred_a", "pred_b"]].corr().iloc[0, 1])
    private_mask = combined.target_start.ge(pd.Timestamp("2026-11-11", tz="Asia/Kolkata")) & combined.target_start.lt(pd.Timestamp("2026-11-13", tz="Asia/Kolkata"))
    private = combined.loc[private_mask]
    private_station = private.groupby("location_id").agg(
        rows=("ID", "size"), mean_a=("pred_a", "mean"), mean_b=("pred_b", "mean"),
        mae_difference=("abs_difference", "mean"), max_abs_difference=("abs_difference", "max")).reset_index()
    private_station.to_csv(args.output / "exp030_private_station_divergence.csv", index=False)
    dates = combined.groupby(combined.target_start.dt.strftime("%Y-%m-%d")).agg(
        rows=("ID", "size"), identical=("identical", "sum")).reset_index(names="date")
    dates.to_csv(args.output / "exp030_identical_by_date.csv", index=False)

    # New 9-origin OOF: per-station PM cutoffs reproduce 41-43h onset gaps.
    archive = load_2024_history(ROOT / "data/raw/challenge/AdditionalHistory.zip")
    rows = []
    for fold_id, day in enumerate(FOLD_STARTS, 1):
        start = pd.Timestamp(day, tz="Asia/Kolkata")
        for sid in STATIONS:
            cutoff = start - pd.Timedelta(hours=FIRST_GAP[sid])
            block = ForecastBlock(start, cutoff, cutoff, "development", 48)
            feat = baseline_predictions(block_features(train, archive, block, station_ids=(sid,)))
            labels = train.loc[train.location_id.eq(sid), ["target_start", "pm25"]]
            part = feat.merge(labels, on="target_start", how="left", validate="one_to_one").rename(columns={"pm25": "y"})
            seasonal_legacy = legacy_doy_same_hour(archive, part[["location_id", "target_start"]])
            seasonal_exact = build_seasonal_features(
                archive, part[["location_id", "target_start"]], series_map=P_FIX_SERIES,
                window_days=14, min_obs=3)
            part["legacy_seasonal_raw"] = seasonal_legacy.to_numpy(float)
            part["exact_month_day_seasonal_raw"] = seasonal_exact.hist24_same_hour_mean.to_numpy(float)
            part["P_fix"] = part.P_fix.clip(lower=0)
            for label, seasonal_col in (("C_legacy_doy", "legacy_seasonal_raw"),
                                        ("C_exact_month_day", "exact_month_day_seasonal_raw")):
                seasonal = part[seasonal_col].where(part[seasonal_col].notna(), part.median72)
                part[label] = (.5*part.median72 + .5*seasonal).clip(lower=0)
            part["fold_id"] = f"{fold_id:02d}_{day}"
            part["first_target_gap_hours"] = FIRST_GAP[sid]
            part["pm_history_cutoff"] = cutoff
            part["prediction_origin"] = cutoff
            part["target_end"] = part.target_start + pd.Timedelta(hours=1)
            part["actual_lead_hours"] = (part.target_start-cutoff).dt.total_seconds()/3600
            rows.append(part)
    oof = pd.concat(rows, ignore_index=True)
    labelled = oof.loc[oof.y.notna()].copy()
    model_names = ["P_fix", "median72", "C_legacy_doy", "C_exact_month_day"]
    labelled.to_csv(args.output / "matched_oof.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
    overall = score(labelled, model_names)
    fold_metrics = score(labelled, model_names, ("fold_id",))
    variability = fold_metrics.groupby("model").full_target_rmse.agg(
        fold_rmse_sd="std", fold_rmse_median="median", fold_rmse_min="min", fold_rmse_max="max")
    overall = overall.merge(variability, on="model", validate="one_to_one")
    overall.to_csv(args.output / "model_metrics.csv", index=False)
    score(labelled, model_names, ("location_id",)).to_csv(args.output / "station_metrics.csv", index=False)
    fold_metrics.to_csv(args.output / "fold_metrics.csv", index=False)
    horizon = labelled.copy()
    horizon["horizon_bucket"] = pd.cut(horizon.actual_lead_hours, [40, 48, 60, 72, 84, 96],
                                       labels=["41-48", "49-60", "61-72", "73-84", "85-90"], include_lowest=True)
    score(horizon, model_names, ("horizon_bucket",)).to_csv(args.output / "horizon_metrics.csv", index=False)
    corr_rows = []
    for left, right in (("P_fix", "C_legacy_doy"), ("P_fix", "C_exact_month_day"), ("C_legacy_doy", "C_exact_month_day")):
        corr_rows.append({"left": left, "right": right,
                          "prediction_correlation": labelled[[left, right]].corr().iloc[0, 1],
                          "residual_correlation": (labelled[left]-labelled.y).corr(labelled[right]-labelled.y)})
    pd.DataFrame(corr_rows).to_csv(args.output / "candidate_correlations.csv", index=False)
    bootstrap = [paired_bootstrap(labelled, m, "P_fix") for m in model_names if m != "P_fix"]
    bootstrap.append(paired_bootstrap(labelled, "C_exact_month_day", "C_legacy_doy"))
    (args.output / "paired_bootstrap.json").write_text(json.dumps(bootstrap, indent=2)+"\n", encoding="utf-8")

    # Recompute the already-published TEAM OOF on its identical row set and pin its source.
    branch_oof_raw = branch_bytes("reports/oof_predictions_task009.csv.gz")
    old_oof = pd.read_csv(io.BytesIO(branch_oof_raw), compression="gzip")
    branch_train_raw = branch_bytes("data/raw/challenge/Train.csv")
    branch_train = pd.read_csv(io.BytesIO(branch_train_raw))
    branch_metrics = []
    for name, col in (("Candidate_C", "pred_candidate_c"), ("Candidate_B", "pred_candidate_b"),
                      ("Candidate_D", "pred_candidate_d")):
        e = old_oof[col]-old_oof.y
        branch_metrics.append({"model": name, "rows": len(old_oof), "origins": old_oof.fold_id.nunique(),
                              "rmse": float(np.sqrt(np.mean(e**2))), "mae": float(np.mean(abs(e))),
                              "bias": float(e.mean()), "source": "fetched branch OOF; nominal common 48h cutoff; not new 41-43h run"})
    pd.DataFrame(branch_metrics).to_csv(args.output / "branch_oof_reference_metrics.csv", index=False)
    old_oof = old_oof.rename(columns={"pred_candidate_c": "Candidate_C",
                                     "pred_candidate_b": "Candidate_B",
                                     "pred_candidate_d": "Candidate_D"})
    score(old_oof, ["Candidate_C", "Candidate_B", "Candidate_D"]).to_csv(
        args.output / "branch_oof_model_metrics.csv", index=False)
    score(old_oof, ["Candidate_C", "Candidate_B", "Candidate_D"], ("location_id",)).to_csv(
        args.output / "branch_oof_station_metrics.csv", index=False)
    score(old_oof, ["Candidate_C", "Candidate_B", "Candidate_D"], ("fold_id",)).to_csv(
        args.output / "branch_oof_fold_metrics.csv", index=False)
    branch_corr = []
    for left, right in (("Candidate_C", "Candidate_B"), ("Candidate_C", "Candidate_D"),
                        ("Candidate_B", "Candidate_D")):
        branch_corr.append({"left": left, "right": right,
                            "prediction_correlation": old_oof[[left, right]].corr().iloc[0, 1],
                            "residual_correlation": (old_oof[left]-old_oof.y).corr(old_oof[right]-old_oof.y)})
    pd.DataFrame(branch_corr).to_csv(args.output / "branch_oof_candidate_correlations.csv", index=False)

    # Audit C/B/E test artifacts against manifests, accounting for Git LF normalization.
    artifact_audits = {}
    for key, artifact, manifest_path in (
        ("Candidate_C", "artifacts/submissions/submission_1_primary_candidate_C.csv",
         "artifacts/submissions/submission_1_primary_candidate_C.manifest.txt"),
        ("Candidate_B", "artifacts/submissions/submission_2_hedge_candidate_B.csv",
         "artifacts/submissions/submission_2_hedge_candidate_B.manifest.txt"),
        ("Candidate_E", "artifacts/submissions/submission_1_primary_candidate_E.csv",
         "artifacts/submissions/submission_1_primary_candidate_E.manifest.txt"),
    ):
        blob = branch_bytes(artifact)
        frame = pd.read_csv(io.BytesIO(blob))
        manifest_text = branch_bytes(manifest_path).decode("utf-8", errors="replace")
        expected = next((line.split(":", 1)[1].strip() for line in manifest_text.splitlines()
                         if line.startswith("output_sha256:")), "MISSING")
        input_train_hash = next((line.split(":", 1)[1].strip() for line in manifest_text.splitlines()
                                 if line.strip().startswith("Train.csv:")), "MISSING")
        crlf_hash = hashlib.sha256(blob.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")).hexdigest()
        if list(frame.columns) != ["ID", "Target"] or not frame.ID.equals(sample.ID):
            raise ValueError(f"{key}: artifact schema or ID order invalid")
        artifact_audits[key] = {"path": artifact, "raw_git_sha256": hashlib.sha256(blob).hexdigest(),
                                "manifest_sha256": expected, "sha256_as_crlf": crlf_hash,
                                "manifest_train_sha256": input_train_hash,
                                "manifest_uses_fetched_train": input_train_hash == hashlib.sha256(branch_train_raw).hexdigest(),
                                "manifest_matches_after_crlf_normalization": crlf_hash == expected,
                                "rows": len(frame), "min": float(frame.Target.min()), "max": float(frame.Target.max())}
        if key == "Candidate_E":
            e_frame = frame
            e_bytes = blob
    e_aligned = e_frame.merge(test[["ID", "target_start"]], on="ID", how="left", validate="one_to_one")
    e_private_mask = e_aligned.target_start.ge(pd.Timestamp("2026-11-11", tz="Asia/Kolkata")) & e_aligned.target_start.lt(pd.Timestamp("2026-11-13", tz="Asia/Kolkata"))
    e_private = e_aligned.loc[e_private_mask, "Target"]
    e_max_row = e_aligned.loc[e_private_mask].sort_values("Target").iloc[-1]
    e_audit = {**artifact_audits["Candidate_E"],
               "rows": len(e_frame), "columns": list(e_frame.columns), "all_min": float(e_frame.Target.min()),
               "all_max": float(e_frame.Target.max()), "private_rows": len(e_private),
               "private_min": float(e_private.min()), "private_max": float(e_private.max()),
               "private_mean": float(e_private.mean()),
               "private_max_row": {"ID": e_max_row.ID, "location_id": int(test.loc[test.ID.eq(e_max_row.ID), "location_id"].iloc[0]),
                                   "target_start": e_max_row.target_start.isoformat(), "Target": float(e_max_row.Target)},
               "manifest_claims_private_range": "29.87 to 116.72"}
    (args.output / "candidate_e_artifact_audit.json").write_text(json.dumps(e_audit, indent=2)+"\n", encoding="utf-8")

    raw_hashes = {"train_download": sha256(args.train), "train_snapshot": sha256(snap_train),
                  **{name: sha256(args.supplied_dir/name) for name in supplied_names.values()},
                  "task_test": sha256(ROOT/"data/raw/challenge/Test.csv"),
                  "task_sample": sha256(ROOT/"data/raw/challenge/SampleSubmission.csv"),
                  "fetched_branch_train_sha256": hashlib.sha256(branch_train_raw).hexdigest(),
                  "branch_oof_sha256": hashlib.sha256(branch_oof_raw).hexdigest(),
                  "candidate_e_artifact_sha256": hashlib.sha256(e_bytes).hexdigest()}
    integrity = {"git_commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip(),
                 "branch_ref": BRANCH, "train_rows": len(train), "train_parsed_equal_to_branch_release": train_original.equals(branch_train),
                 "train_release_provenance": "Owner-supplied file named as official 9 November release; download URL/receipt not provided, so origin independently unverified",
                 "train_sha256": raw_hashes["train_download"], "train_station_interval_end_cutoffs": {
                     str(s): train.loc[train.location_id.eq(s), "timestamp_ist"].max().isoformat() for s in STATIONS},
                 "test_rows": len(test), "sample_ids_equal_test_order": test.ID.equals(sample.ID),
                 "exp030_a_both_valid_exact_order": True, "exp030_identical_rows": int(combined.identical.sum()),
                 "exp030_fully_identical_dates": dates.loc[dates.identical.eq(dates.rows), "date"].tolist(),
                 "exp030_manifests": "NOT FOUND in supplied input list; model definitions unknown",
                 "exp030_correlation": corr, "exp030_private_rows": len(private), "exp030_private_station_rows": private_station.to_dict("records"),
                 "validation_origins": labelled.fold_id.nunique(), "validation_rows": len(labelled),
                 "validation_label_clipping": "none", "catboost": "NOT RUN: CatBoost unavailable in current Windows ARM64 environment",
                 "task012_supplied_prediction_summary": supplied_pair_rows,
                 "artifact_manifest_hash_audits": artifact_audits, "hashes": raw_hashes}
    (args.output / "integrity_audit.json").write_text(json.dumps(integrity, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"train_rows": len(train), "oof_rows": len(labelled), "origins": labelled.fold_id.nunique(),
                      "exp030_identical": int(combined.identical.sum()), "exp030_correlation": corr,
                      "model_metrics": overall.to_dict("records"), "candidate_e": e_audit}, indent=2))


if __name__ == "__main__":
    main()
