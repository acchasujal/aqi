"""Rebuild TASK011 OOF and run isolated TASK012 research experiments."""
from __future__ import annotations

import hashlib
import json
import platform
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import HuberRegressor, Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mumbai_pm25.data import load_data
from mumbai_pm25.final_gap import ForecastBlock, labelled_blocks, paired_bootstrap
from mumbai_pm25.historical_archive import load_2024_history

IST = "Asia/Kolkata"
TRAIN_SHA256 = "8adbcf55315f166d7dc3dc1d3e4d7400651f26c1d8b95ff387eef38f4e70a283"
OUT = ROOT / "reports/ml_pipeline/task012_vayudrishti_transfer"
OOF_SOURCE_FILES = [
    "scripts/run_task012.py", "src/mumbai_pm25/final_gap.py",
    "src/mumbai_pm25/forecast.py", "src/mumbai_pm25/historical_archive.py",
    "experiments/TASK012.yaml",
]
BLOCKS = [ForecastBlock(t, t-pd.Timedelta(hours=15), t-pd.Timedelta(hours=15))
          for t in pd.date_range("2025-04-02 00:00", "2026-11-04 00:00", freq="7D", tz=IST)]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def rebuild_oof() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    data_dir = ROOT / "data/processed/official_releases/20261110_final"
    train, _test, _sample, _ = load_data(data_dir)
    train_path = data_dir / "Train.csv"
    if sha(train_path) != TRAIN_SHA256:
        raise ValueError("Frozen final Train fingerprint mismatch")
    archive = load_2024_history(data_dir / "AdditionalHistory.zip")
    rows, coverage = labelled_blocks(train, archive, BLOCKS)
    for weight in (0.10, 0.25, 0.50):
        rows[f"Pfix_diur{int(weight*100)}"] = rows.P_fix + weight * (rows.diur7.fillna(rows.P_fix)-rows.P_fix)
    rows["Pfix_diur50"] = rows.P_fix + .5 * (rows.diur7.fillna(rows.P_fix) - rows.P_fix)
    hashes = {p: sha(ROOT / p) for p in OOF_SOURCE_FILES}
    manifest = {
        "train_sha256": sha(train_path),
        "additional_history_sha256": sha(data_dir / "AdditionalHistory.zip"),
        "test_sha256": sha(data_dir / "Test.csv"),
        "sample_submission_sha256": sha(data_dir / "SampleSubmission.csv"),
        "stations_sha256": sha(data_dir / "Stations.csv"),
        "data_dictionary_sha256": sha(data_dir / "DataDictionary.txt"),
        "source_sha256": hashes,
        "fold_schedule": [b.target_start.isoformat() for b in BLOCKS],
        "fold_count": len(BLOCKS), "labelled_origins": int(rows.loc[rows.y.notna(), "fold_id"].nunique()),
        "oof_rows": len(rows), "labelled_rows": int(rows.y.notna().sum()),
        "pm_gap_hours": 15, "horizon_hours": 48,
        "python": platform.python_version(), "pandas": pd.__version__,
    }
    if len(rows) != 16128 or rows.y.notna().sum() != 12731 or rows.loc[rows.y.notna(), "fold_id"].nunique() != 83:
        raise ValueError("Rebuilt OOF does not match frozen TASK011 row/origin contract")
    return rows, coverage, manifest


def score(frame: pd.DataFrame, pred_col: str) -> dict:
    v = frame.loc[frame.y.notna()]
    err = v[pred_col].to_numpy(float) - v.y.to_numpy(float)
    complete = bool(np.isfinite(err).all())
    clean = v.y.to_numpy(float) < 500
    return {"model": pred_col, "rows": len(v), "origins": int(v.fold_id.nunique()),
            "missing_predictions": int((~np.isfinite(err)).sum()),
            "full_target_rmse": float(np.sqrt(np.mean(err**2))) if complete else np.nan,
            "mae": float(np.mean(np.abs(err))) if complete else np.nan,
            "bias": float(np.mean(err)) if complete else np.nan,
            "clean_y_lt_500_rmse": float(np.sqrt(np.mean(err[clean]**2))) if complete else np.nan,
            "extreme_rows_y_ge_1000": int((v.y >= 1000).sum())}


def alpha_fit(rows: pd.DataFrame, lam: float | None) -> tuple[float, dict[int, float]]:
    v = rows.loc[rows.y.notna() & rows.Pfix_diur50.notna()].copy()
    x = (v.Pfix_diur50 - v.P_fix).to_numpy(float)
    z = (v.y - v.P_fix).to_numpy(float)
    denom = float(x @ x)
    global_a = float(np.clip((x @ z) / denom, 0, 1)) if denom > 0 else 0.0
    station_a: dict[int, float] = {}
    for station, part in v.groupby("location_id"):
        xs = (part.Pfix_diur50-part.P_fix).to_numpy(float)
        zs = (part.y-part.P_fix).to_numpy(float)
        ds = float(xs @ xs)
        raw = float(np.clip((xs @ zs)/ds, 0, 1)) if ds > 0 else global_a
        # Ridge penalty lam*(alpha_station-alpha_global)^2; data curvature is sum(x^2).
        if lam is None:
            station_a[int(station)] = global_a
        elif lam == -1:
            station_a[int(station)] = raw
        else:
            # Dimensionless empirical-Bayes precision ratio avoids a lambda
            # whose meaning changes with the units/scale of B50-P_fix.
            station_a[int(station)] = float(np.clip((raw + lam*global_a)/(1.0+lam), 0, 1))
    return global_a, station_a


def chronological_shrinkage(rows: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    valid = rows.loc[rows.y.notna()].copy()
    origins = sorted(valid.fold_id.unique())
    split_origin = origins[60]
    dev_eval = origins[20:60]
    forward = origins[60:]
    lambdas: list[float | None] = [None, -1.0, 0.1, 1.0, 10.0, 100.0]
    dev_results: list[dict] = []
    for lam in lambdas:
        preds = []
        for fold in dev_eval:
            block = valid.loc[valid.fold_id.eq(fold)]
            cutoff = block.pm_history_cutoff.iloc[0]
            hist = valid.loc[valid.block_target_end.le(cutoff)]
            ga, sa = alpha_fit(hist, lam)
            p = block.P_fix.to_numpy(float) + np.array([sa[int(s)] for s in block.location_id]) * (block.Pfix_diur50.to_numpy(float)-block.P_fix.to_numpy(float))
            preds.extend(zip(block.index, p))
        pred = pd.Series(dict(preds))
        joined = valid.loc[pred.index].copy()
        joined["pred"] = pred
        label = "global" if lam is None else ("station_specific" if lam == -1 else lam)
        dev_results.append({"lambda": label,
                            "full_target_rmse": score(joined, "pred")["full_target_rmse"],
                            "rows": len(joined), "origins": joined.fold_id.nunique()})
    # Pick regularisation only on the development window; evaluate fixed choice on forward origins.
    best = min(dev_results, key=lambda x: x["full_target_rmse"])
    chosen_lam = None if best["lambda"] == "global" else (-1.0 if best["lambda"] == "station_specific" else float(best["lambda"]))
    test_parts = []
    alpha_records = []
    for fold in forward:
        block = valid.loc[valid.fold_id.eq(fold)].copy()
        cutoff = block.pm_history_cutoff.iloc[0]
        hist = valid.loc[valid.block_target_end.le(cutoff)]
        ga, raw_sa = alpha_fit(hist, -1.0)
        _, sa = alpha_fit(hist, chosen_lam)
        block["alpha_global"] = ga
        block["alpha_station_unregularized"] = [raw_sa[int(s)] for s in block.location_id]
        block["alpha_station"] = [sa[int(s)] for s in block.location_id]
        block["pred_global_alpha"] = block.P_fix + ga*(block.Pfix_diur50-block.P_fix)
        block["pred_station_alpha"] = block.P_fix + block.alpha_station_unregularized*(block.Pfix_diur50-block.P_fix)
        block["pred_shrunk_alpha"] = block.P_fix + block.alpha_station*(block.Pfix_diur50-block.P_fix)
        block["B50"] = block.Pfix_diur50
        test_parts.append(block)
        alpha_records.append({"fold_id": fold.isoformat(), "global_alpha": ga,
                              "unregularized_station_alphas": {str(k): v for k, v in raw_sa.items()},
                              "station_alphas": {str(k): v for k, v in sa.items()},
                              "training_rows": len(hist)})
    result = pd.concat(test_parts, ignore_index=True)
    metrics = pd.DataFrame([score(result, c) for c in ["P_fix", "B50", "pred_global_alpha", "pred_station_alpha", "pred_shrunk_alpha"]])
    # Fold-level metrics support the required complete 48h x four-station pair review.
    fold_rows = []
    for fold, part in result.groupby("fold_id", sort=True):
        for c in ["P_fix", "B50", "pred_global_alpha", "pred_station_alpha", "pred_shrunk_alpha"]:
            fold_rows.append({"fold_id": fold.isoformat(), **score(part, c)})
    # Station/lead diagnostics use prespecified physical lead buckets.
    station_rows = []
    for keys, part in result.groupby(["location_id", pd.cut(result.forecast_lead_hours, [0, 24, 48, 72, 96, 120], right=False)], observed=True):
        for c in ["P_fix", "B50", "pred_global_alpha", "pred_station_alpha", "pred_shrunk_alpha"]:
            station_rows.append({"location_id": keys[0], "lead_bucket": str(keys[1]), **score(part, c)})
    info = {"development_alpha_grid": dev_results, "chosen_lambda": best["lambda"],
            "development_origins": [x.isoformat() for x in origins[:60]],
            "forward_origins": [x.isoformat() for x in forward], "alpha_by_forward_origin": alpha_records,
            "forward_rows": len(result), "forward_labelled_origins": result.fold_id.nunique(),
            "forward_first_origin": split_origin.isoformat()}
    return result, metrics, {"fold_metrics": pd.DataFrame(fold_rows), "station_lead_metrics": pd.DataFrame(station_rows), "info": info}


def feature_matrix(frame: pd.DataFrame) -> pd.DataFrame:
    cols = ["diur7", "hour_sin", "hour_cos", "forecast_lead_hours", "median72", "median168", "age_hours",
            "std72", "archive_target", "archive_now", "station_11606", "station_11611", "station_3409510", "station_3409511"]
    x = frame.reindex(columns=cols).astype(float).copy()
    x["diur7_minus_pfix"] = frame.diur7.fillna(frame.P_fix)-frame.P_fix
    x["median72_minus_archive"] = frame.median72-frame.archive_target
    return x


def causal_past_median(train: pd.DataFrame, row: pd.Series) -> float:
    # Only observations ending by the example's origin may determine its replacement value.
    prior = train.loc[train.location_id.eq(row.location_id) &
                      (train.target_start + pd.Timedelta(hours=1) <= row.prediction_origin), "pm25"].dropna().tail(24)
    if prior.empty:
        return float(row.P_fix)
    return float(prior.median())


def residual_experiments(rows: pd.DataFrame, train: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    valid = rows.loc[rows.y.notna()].copy()
    origins = sorted(valid.fold_id.unique())
    forward = origins[60:]
    variants = ["ridge_raw", "huber_raw", "ridge_past_median_1000"]
    out_parts = []
    training_counts = {name: 0 for name in variants}
    for fold in forward:
        block = valid.loc[valid.fold_id.eq(fold)].copy()
        cutoff = block.pm_history_cutoff.iloc[0]
        hist = valid.loc[valid.block_target_end.le(cutoff) & valid.y.notna()].copy()
        if len(hist) < 100:
            block[variants] = block.P_fix.to_numpy()[:, None]
            out_parts.append(block)
            continue
        x_train, x_test = feature_matrix(hist), feature_matrix(block)
        raw_resid = hist.y.to_numpy(float)-hist.P_fix.to_numpy(float)
        cleaned_y = hist.y.to_numpy(float).copy()
        flagged = cleaned_y >= 1000
        training_counts["ridge_raw"] += len(hist)
        training_counts["huber_raw"] += len(hist)
        training_counts["ridge_past_median_1000"] += len(hist)
        training_counts["ridge_past_median_1000_training_labels_changed"] = training_counts.get("ridge_past_median_1000_training_labels_changed", 0) + int(flagged.sum())
        if flagged.any():
            cleaned_y[flagged] = [causal_past_median(train, r) for (_, r) in hist.loc[flagged].iterrows()]
        responses = {"ridge_raw": raw_resid,
                     "huber_raw": raw_resid,
                     "ridge_past_median_1000": cleaned_y-hist.P_fix.to_numpy(float)}
        for name, response in responses.items():
            model = (make_pipeline(SimpleImputer(strategy="median", add_indicator=True), StandardScaler(),
                                   HuberRegressor(epsilon=1.35, alpha=10.0, max_iter=500))
                     if name == "huber_raw" else make_pipeline(SimpleImputer(strategy="median", add_indicator=True),
                                                                StandardScaler(), Ridge(alpha=100.0)))
            model.fit(x_train, response)
            block[name] = np.maximum(0.0, block.P_fix.to_numpy(float)+model.predict(x_test))
        out_parts.append(block)
    result = pd.concat(out_parts, ignore_index=True)
    metrics = pd.DataFrame([score(result, c) for c in ["P_fix", "Pfix_diur50", *variants]])
    return result, metrics, training_counts


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows, coverage, manifest = rebuild_oof()
    rows.to_csv(OUT / "task012_rebuilt_oof.csv.gz", index=False,
                compression={"method": "gzip", "mtime": 0})
    coverage.to_csv(OUT / "fold_coverage.csv", index=False)
    manifest["oof_sha256"] = sha(OUT / "task012_rebuilt_oof.csv.gz")
    manifest["coverage_sha256"] = sha(OUT / "fold_coverage.csv")
    (OUT / "oof_manifest.json").write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")
    shrink, shrink_metrics, extras = chronological_shrinkage(rows)
    shrink.to_csv(OUT / "station_shrinkage_oof.csv", index=False)
    shrink_metrics.to_csv(OUT / "station_shrinkage_metrics.csv", index=False)
    fold_table = extras["fold_metrics"].copy()
    fold_table["fold_id"] = pd.to_datetime(fold_table.fold_id, utc=True).dt.tz_convert(IST)
    fold_metrics = fold_table.merge(
        coverage.assign(fold_id=pd.to_datetime(coverage.fold_id, utc=True).dt.tz_convert(IST)),
        on="fold_id", how="left", validate="many_to_one")
    fold_metrics.to_csv(OUT / "station_shrinkage_fold_metrics.csv", index=False)
    extras["station_lead_metrics"].to_csv(OUT / "station_shrinkage_station_lead_metrics.csv", index=False)
    paired = fold_metrics.pivot(index="fold_id", columns="model", values="full_target_rmse").reset_index()
    for candidate in ["B50", "pred_global_alpha", "pred_station_alpha", "pred_shrunk_alpha"]:
        paired[f"{candidate}_minus_Pfix"] = paired[candidate] - paired.P_fix
        paired[f"{candidate}_origin_win"] = paired[f"{candidate}_minus_Pfix"] < 0
    paired.to_csv(OUT / "paired_origin_differences.csv", index=False)
    controls = ["P_fix", "Pfix_diur10", "Pfix_diur25", "Pfix_diur50", "median24", "median72", "median168",
                "ewm72", "diur7", "archive_decay72", "archive_decay168", "archive_piecewise", "archive_constant50"]
    pd.DataFrame([score(rows, c) for c in controls]).to_csv(OUT / "control_metrics.csv", index=False)
    subgroup_rows = []
    scored = rows.loc[rows.y.notna()].copy()
    scored["lead_bucket"] = pd.cut(scored.forecast_lead_hours, [0, 24, 48, 72, 96, 120], right=False)
    for grouping, keys in [("origin", ["fold_id"]), ("station", ["location_id"]), ("lead", ["lead_bucket"]),
                           ("station_lead", ["location_id", "lead_bucket"])]:
        for group_key, part in scored.groupby(keys, observed=True, dropna=False):
            group_key = group_key if isinstance(group_key, tuple) else (group_key,)
            identity = dict(zip(keys, group_key))
            for model in controls:
                subgroup_rows.append({"group_type": grouping, **identity, **score(part, model)})
    pd.DataFrame(subgroup_rows).to_csv(OUT / "control_group_metrics.csv", index=False)
    labelled = rows.loc[rows.y.notna()]
    correlation_rows = []
    corr_models = [c for c in controls if c in labelled and np.isfinite(labelled[c].to_numpy(float)).all()]
    for i, left in enumerate(corr_models):
        for right in corr_models[i:]:
            correlation_rows.append({"left": left, "right": right,
                                     "prediction_correlation": float(labelled[left].corr(labelled[right])),
                                     "residual_correlation": float((labelled[left]-labelled.y).corr(labelled[right]-labelled.y)),
                                     "rows": len(labelled)})
    pd.DataFrame(correlation_rows).to_csv(OUT / "control_prediction_residual_correlations.csv", index=False)
    (OUT / "station_shrinkage_config.json").write_text(json.dumps(extras["info"], indent=2)+"\n", encoding="utf-8")
    data_dir = ROOT / "data/processed/official_releases/20261110_final"
    train, _test, _sample, _ = load_data(data_dir)
    residual, residual_metrics, training_counts = residual_experiments(rows, train)
    residual.to_csv(OUT / "residual_model_oof.csv", index=False)
    residual_metrics.to_csv(OUT / "residual_model_metrics.csv", index=False)
    causal_rows = []
    by_model = residual_metrics.set_index("model")
    for model, treatment, train_key, changed in [
        ("ridge_raw", "raw target; Ridge squared loss", "ridge_raw", 0),
        ("huber_raw", "raw target; Huber loss epsilon=1.35 alpha=10", "huber_raw", 0),
        ("ridge_past_median_1000", "training y>=1000 replaced by median of 24 prior eligible station observations", "ridge_past_median_1000", training_counts["ridge_past_median_1000_training_labels_changed"]),
    ]:
        causal_rows.append({"variant": model, "training_treatment": treatment,
                            "training_rows_fit_across_forward_origins": training_counts[train_key],
                            "training_labels_changed_across_forward_fits": changed,
                            "validation_labels_modified": False,
                            "full_target_rmse": by_model.loc[model, "full_target_rmse"],
                            "mae": by_model.loc[model, "mae"], "bias": by_model.loc[model, "bias"],
                            "clean_y_lt_500_rmse": by_model.loc[model, "clean_y_lt_500_rmse"],
                            "status": "measured"})
    causal_rows.append({"variant": "flag_based", "training_treatment": "flag_high_1000",
                        "training_rows_fit_across_forward_origins": 0, "training_labels_changed_across_forward_fits": 0,
                        "validation_labels_modified": False, "full_target_rmse": np.nan, "mae": np.nan,
                        "bias": np.nan, "clean_y_lt_500_rmse": np.nan,
                        "status": "blocked; historical flag availability is not verified"})
    pd.DataFrame(causal_rows).to_csv(OUT / "causal_cleaning_metrics.csv", index=False)
    bootstrap = {model: paired_bootstrap(shrink, model, "P_fix", repetitions=4000)
                 for model in ["B50", "pred_global_alpha", "pred_station_alpha", "pred_shrunk_alpha"]}
    (OUT / "paired_origin_bootstrap.json").write_text(json.dumps(bootstrap, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"manifest": manifest, "shrinkage": shrink_metrics.to_dict("records"),
                      "residual": residual_metrics.to_dict("records"), "chosen_lambda": extras["info"]["chosen_lambda"]}, indent=2))


if __name__ == "__main__":
    main()
