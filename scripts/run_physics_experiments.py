"""Evaluation of Atmospheric Micro-Meteorology Physics Pipeline across 9 Chronological Folds.

Benchmarking against the 29.5171 pooled RMSE baseline.
Produces:
- reports/physics_model_comparison.csv
- reports/physics_fold_metrics.csv
- reports/physics_station_metrics.csv
- reports/physics_lead_metrics.csv
"""
from __future__ import annotations

import re
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

warnings.filterwarnings("ignore")

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, root_mean_squared_error

from mumbai_pm25.climatology.horizon_stabilizer import HorizonStabilizer
from mumbai_pm25.climatology.kernel import KernelClimatology
from mumbai_pm25.data import load_data
from mumbai_pm25.features.physics import compute_atmospheric_physics_features
from mumbai_pm25.features.pipeline import build_feature_matrix
from mumbai_pm25.historical_archive import (
    ARCHIVE_SERIES,
    STATION_NAME_MAP,
    build_seasonal_features,
    load_2024_history,
)
from mumbai_pm25.models.physics_gam import DualScalePhysicsGAM
from mumbai_pm25.validation import generate_fixed_target_folds

DATA_DIR = ROOT / "data" / "raw" / "challenge"
REPORTS_DIR = ROOT / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
TARGET_STATIONS = [11606, 11611, 3409510, 3409511]


def get_standard_9_folds(train_df: pd.DataFrame) -> list[dict]:
    """Return the exact 9 standardized chronological folds used in Tasks 009-017."""
    orig_folds = generate_fixed_target_folds(
        train_df, gap_hours=48, horizon_hours=48, step_days=21, holdout_hours=48
    )
    target_dates = ["202608", "2026090", "2026092", "2026101", "2026110"]
    autumn_folds = []
    for d in target_dates:
        f = next(f for f in orig_folds if d in f.fold_id)
        autumn_folds.append({
            "fold_id": f.fold_id,
            "regime": "monsoon_autumn",
            "target_start": f.target_start,
            "cutoff": f.pm_history_cutoff,
        })

    winter_defs = [
        {
            "fold_id": "fold_nov_2025_calendar_match",
            "regime": "winter_transition",
            "target_start": pd.Timestamp("2025-11-11 00:00:00", tz="Asia/Kolkata"),
            "cutoff": pd.Timestamp("2025-11-09 00:00:00", tz="Asia/Kolkata"),
        },
        {
            "fold_id": "fold_dec_2025_winter",
            "regime": "winter_transition",
            "target_start": pd.Timestamp("2025-12-15 00:00:00", tz="Asia/Kolkata"),
            "cutoff": pd.Timestamp("2025-12-13 00:00:00", tz="Asia/Kolkata"),
        },
        {
            "fold_id": "fold_jan_2026_early",
            "regime": "winter_transition",
            "target_start": pd.Timestamp("2026-01-05 00:00:00", tz="Asia/Kolkata"),
            "cutoff": pd.Timestamp("2026-01-03 00:00:00", tz="Asia/Kolkata"),
        },
        {
            "fold_id": "fold_jan_2026_late",
            "regime": "winter_transition",
            "target_start": pd.Timestamp("2026-01-26 00:00:00", tz="Asia/Kolkata"),
            "cutoff": pd.Timestamp("2026-01-24 00:00:00", tz="Asia/Kolkata"),
        },
    ]
    return autumn_folds + winter_defs


def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    X = df.copy()
    drop_cols = ["target_start", "target_end", "timestamp_ist", "hist24_source_ids", "ID"]
    for col in drop_cols:
        if col in X.columns:
            X = X.drop(columns=[col])
    for col in X.select_dtypes(include=["object", "string"]).columns:
        if col != "station_id":
            X = X.drop(columns=[col])
    X.columns = [re.sub(r"[^\w]", "_", str(c)) for c in X.columns]
    return X


def run_physics_evaluations(train_df: pd.DataFrame, hist_2024: pd.DataFrame) -> pd.DataFrame:
    grid = train_df.set_index(["location_id", "target_start"])[["pm25"]].sort_index()
    station_histories = {
        sid: grid.xs(sid, level="location_id")["pm25"] for sid in TARGET_STATIONS
    }
    t_min = train_df["target_start"].min()

    # Pre-extract clean 2024 history per station
    clean_2024_dfs = {}
    for sid in TARGET_STATIONS:
        allowed = ARCHIVE_SERIES[sid]
        sub = hist_2024.loc[hist_2024["series_id"].isin(allowed)].copy()
        agg = sub.groupby("hour_start")["pm25"].median().reset_index()
        agg = agg.rename(columns={"hour_start": "timestamp"}).sort_values("timestamp").reset_index(drop=True)
        clean_2024_dfs[sid] = agg

    clim_estimator = KernelClimatology(sigma_doy=10.0, sigma_hour=1.0, clim_gap_days=14, min_weight=5.0)
    stabilizer = HorizonStabilizer(near_horizon_cutoff=24.0, far_horizon_cutoff=72.0, max_prior_weight=0.35)
    folds = get_standard_9_folds(train_df)

    all_fold_dfs = []

    for f_idx, fold_info in enumerate(folds, start=1):
        fid = fold_info["fold_id"]
        regime = fold_info["regime"]
        target_start = fold_info["target_start"]
        cutoff = fold_info["cutoff"]
        target_hours = pd.date_range(target_start, periods=48, freq="h")

        t_rows = []
        for sid in TARGET_STATIONS:
            s_series = station_histories[sid]
            for h_idx, t in enumerate(target_hours, start=1):
                y_val = s_series.loc[t] if t in s_series.index else np.nan
                lead_h = int((t - cutoff).total_seconds() / 3600.0)
                t_rows.append({
                    "fold_id": fid,
                    "regime": regime,
                    "location_id": sid,
                    "target_start": t,
                    "hour": t.hour,
                    "horizon_hours": h_idx,
                    "lead_hours": lead_h,
                    "y": y_val,
                })
        val_df = pd.DataFrame(t_rows).dropna(subset=["y"]).reset_index(drop=True)

        # 1. 72h Station Median
        stat_medians = {}
        for sid in TARGET_STATIONS:
            s_s = station_histories[sid]
            h = s_s.loc[s_s.index < cutoff]
            w = h.loc[h.index >= cutoff - pd.Timedelta(hours=72)]
            stat_medians[sid] = float(w.median()) if w.notna().any() else 40.0
        val_df["median_72"] = val_df["location_id"].map(stat_medians)
        val_df["pred_m72"] = val_df["median_72"]

        # 2. Candidate C (P_fix = 50% m72 + 50% 2024 month_day_365)
        seas_val = build_seasonal_features(
            hist_2024,
            val_df[["location_id", "target_start"]],
            station_map=STATION_NAME_MAP,
            window_days=14,
            min_obs=3,
        )
        val_df["pred_cand_c"] = np.where(
            seas_val["hist24_same_hour_mean"].notna(),
            0.50 * val_df["pred_m72"] + 0.50 * seas_val["hist24_same_hour_mean"],
            val_df["pred_m72"],
        )

        # 3. Clean 2024 Kernel Climatology
        p_clean_kclim = []
        for sid in TARGET_STATIONS:
            s_sub = val_df[val_df["location_id"] == sid]
            if s_sub.empty:
                continue
            h_df = clean_2024_dfs[sid]
            elig = clim_estimator._extract_eligible_history(h_df, cutoff)
            clim_res = clim_estimator.estimate_batch(elig, list(s_sub["target_start"]))
            for r in clim_res:
                p_clean_kclim.append(r["clim_prediction"])
        val_df["pred_kclim_alone"] = p_clean_kclim
        val_df["pred_kclim_blend50"] = 0.50 * val_df["pred_m72"] + 0.50 * val_df["pred_kclim_alone"]

        # 4. Atmospheric Physics Features & Physics GAM
        val_physics = compute_atmospheric_physics_features(val_df)
        for col in val_physics.columns:
            if col not in val_df.columns:
                val_df[col] = val_physics[col]

        # Fit Physics GAM on recent 21-day history prior to cutoff
        hist_tr_rows = []
        hist_range = pd.date_range(cutoff - pd.Timedelta(days=21), cutoff - pd.Timedelta(hours=1), freq="h")
        for sid in TARGET_STATIONS:
            s_s = station_histories[sid]
            for t in hist_range:
                if t in s_s.index and pd.notna(s_s.loc[t]):
                    hist_tr_rows.append({
                        "location_id": sid,
                        "target_start": t,
                        "hour": t.hour,
                        "pm25": s_s.loc[t],
                        "median_72": stat_medians[sid],
                    })

        hist_tr_df = pd.DataFrame(hist_tr_rows)
        hist_tr_physics = compute_atmospheric_physics_features(hist_tr_df)

        # Train target filtering: cap extreme telemetry glitch values (>1000 ug/m3) to 500 for training stability
        y_gam_train = np.where(hist_tr_physics["pm25"].values > 1000.0, 500.0, hist_tr_physics["pm25"].values)

        gam = DualScalePhysicsGAM(alpha=10.0, use_huber=True)
        gam.fit(hist_tr_physics, y_gam_train)
        val_df["pred_physics_gam"] = gam.predict(val_df)

        # 5. Micro-Meteorology LightGBM Residual Model
        # Build training origins for GBDT residual
        hist_origins = pd.date_range(
            t_min + pd.Timedelta(days=21),
            cutoff - pd.Timedelta(hours=48),
            freq="48h",
            tz="Asia/Kolkata",
        )
        if len(hist_origins) > 30:
            hist_origins = hist_origins[::len(hist_origins) // 30]

        train_dfs, train_ys = [], []
        for orig in hist_origins:
            orig_cutoff = orig - pd.Timedelta(hours=48)
            orig_target_hours = pd.date_range(orig, periods=48, freq="h")
            tr_rows = []
            for sid in TARGET_STATIONS:
                s_series = station_histories[sid]
                for h_i, t in enumerate(orig_target_hours, start=1):
                    if t in s_series.index and pd.notna(s_series.loc[t]):
                        tr_rows.append({
                            "location_id": sid,
                            "target_start": t,
                            "horizon_hours": h_i,
                            "pm25": s_series.loc[t],
                        })
            if not tr_rows:
                continue
            tdf = pd.DataFrame(tr_rows)
            X_p = build_feature_matrix(
                station_histories,
                tdf,
                orig_cutoff,
                history_2024=hist_2024,
                include_seasonal=True,
                include_spatial=True,
            )
            X_p = compute_atmospheric_physics_features(X_p)
            train_dfs.append(X_p)
            train_ys.append(tdf["pm25"])

        X_tr_all = pd.concat(train_dfs, ignore_index=True)
        y_tr_all = pd.concat(train_ys, ignore_index=True).to_numpy(dtype=float)
        y_tr_filtered = np.where(y_tr_all > 1000.0, 500.0, y_tr_all)

        X_val_all = build_feature_matrix(
            station_histories,
            val_df[["location_id", "target_start", "horizon_hours"]],
            cutoff,
            history_2024=hist_2024,
            include_seasonal=True,
            include_spatial=True,
        )
        X_val_all = compute_atmospheric_physics_features(X_val_all)

        X_tr_prep = prepare_features(X_tr_all)
        X_val_prep = prepare_features(X_val_all)

        baseline_tr = X_tr_all["median_72"].to_numpy(dtype=float) if "median_72" in X_tr_all.columns else np.full(len(y_tr_all), 40.0)
        baseline_val = X_val_all["median_72"].to_numpy(dtype=float) if "median_72" in X_val_all.columns else np.full(len(val_df), 40.0)

        # Residual target
        z_tr = y_tr_filtered - baseline_tr
        lgb_model = lgb.LGBMRegressor(
            n_estimators=100,
            learning_rate=0.04,
            num_leaves=24,
            min_child_samples=20,
            subsample=0.8,
            colsample_bytree=0.8,
            reg_alpha=0.5,
            reg_lambda=2.0,
            random_state=42,
            n_jobs=1,
            verbose=-1,
        )
        lgb_model.fit(X_tr_prep, z_tr)
        pred_lgb_res = np.maximum(0.0, baseline_val + lgb_model.predict(X_val_prep))
        val_df["pred_lgb_physics"] = 0.50 * pred_lgb_res + 0.50 * val_df["pred_kclim_blend50"]

        # 6. Horizon-Stabilized Atmospheric Ensemble
        # Dynamic composite: 50% Kernel Climatology Blend + 30% Physics GAM + 20% LightGBM Physics
        p_dynamic = 0.50 * val_df["pred_kclim_blend50"] + 0.30 * val_df["pred_physics_gam"] + 0.20 * val_df["pred_lgb_physics"]
        val_df["pred_atmospheric_composite"] = p_dynamic

        # Apply horizon stabilization: as lead hours increase towards 95h, blend gently into kclim_blend50
        val_df["pred_horizon_stabilized"] = stabilizer.stabilize(
            p_dynamic.values,
            val_df["pred_kclim_blend50"].values,
            val_df["lead_hours"].values,
        )

        all_fold_dfs.append(val_df)
        print(f"Fold {f_idx}/9 [{fid}] ({len(val_df)} rows) evaluated.")

    full_oof = pd.concat(all_fold_dfs, ignore_index=True)
    return full_oof


def evaluate_metrics(oof_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    models = {
        "72h Station Median": "pred_m72",
        "Candidate C (hist24_blend50)": "pred_cand_c",
        "Corrected Kernel Blend 50/50 (Current Best)": "pred_kclim_blend50",
        "Dual-Scale Physics GAM": "pred_physics_gam",
        "Micro-Meteorology LightGBM": "pred_lgb_physics",
        "Atmospheric Physics Composite": "pred_atmospheric_composite",
        "Horizon-Stabilized Atmospheric Ensemble": "pred_horizon_stabilized",
    }

    y_true = oof_df["y"].values
    autumn_mask = oof_df["regime"] == "monsoon_autumn"
    winter_mask = oof_df["regime"] == "winter_transition"
    clean_1000 = y_true < 1000.0
    clean_250 = y_true < 250.0

    comp_rows = []
    for m_label, col in models.items():
        y_pred = oof_df[col].values
        comp_rows.append({
            "model": m_label,
            "pooled_rmse": round(root_mean_squared_error(y_true, y_pred), 4),
            "mae": round(mean_absolute_error(y_true, y_pred), 4),
            "bias": round(float(np.mean(y_pred - y_true)), 4),
            "autumn_rmse": round(root_mean_squared_error(y_true[autumn_mask], y_pred[autumn_mask]), 4),
            "winter_rmse": round(root_mean_squared_error(y_true[winter_mask], y_pred[winter_mask]), 4),
            "clean_1000_rmse": round(root_mean_squared_error(y_true[clean_1000], y_pred[clean_1000]), 4),
            "clean_250_rmse": round(root_mean_squared_error(y_true[clean_250], y_pred[clean_250]), 4),
            "coverage_rows": len(y_true),
        })

    comp_df = pd.DataFrame(comp_rows).sort_values("pooled_rmse").reset_index(drop=True)

    # Station level metrics
    station_records = []
    for sid, g in oof_df.groupby("location_id"):
        for m_label, col in models.items():
            station_records.append({
                "location_id": sid,
                "model": m_label,
                "rmse": round(root_mean_squared_error(g["y"], g[col]), 4),
                "mae": round(mean_absolute_error(g["y"], g[col]), 4),
                "bias": round(float(np.mean(g[col] - g["y"])), 4),
                "count": len(g),
            })
    station_df = pd.DataFrame(station_records)

    # Lead horizon breakdown
    oof_df["lead_bucket"] = pd.cut(
        oof_df["lead_hours"],
        bins=[47, 59, 71, 83, 96],
        labels=["48-59h", "60-71h", "72-83h", "84-95h"],
    )
    lead_records = []
    for b, g in oof_df.groupby("lead_bucket", observed=False):
        if len(g) == 0:
            continue
        rec = {"lead_bucket": b, "count": len(g)}
        for m_label, col in models.items():
            rec[m_label] = round(root_mean_squared_error(g["y"], g[col]), 4)
        lead_records.append(rec)
    lead_df = pd.DataFrame(lead_records)

    return comp_df, station_df, lead_df


def main():
    print("=" * 80)
    print("ATMOSPHERIC MICRO-METEOROLOGY & DUAL-SCALE PHYSICS EVALUATION")
    print("=" * 80)

    train_df, test_df, _, _ = load_data(DATA_DIR)
    hist_2024 = load_2024_history(DATA_DIR / "AdditionalHistory.zip")
    print(f"Loaded Train: {len(train_df):,} rows | Test: {len(test_df):,} rows")

    print("\nRunning chronological out-of-fold evaluations across 9 standardized folds...")
    oof_df = run_physics_evaluations(train_df, hist_2024)
    print(f"Total out-of-fold validation rows evaluated: {len(oof_df):,}")

    comp_df, station_df, lead_df = evaluate_metrics(oof_df)

    print("\n" + "=" * 80)
    print("BENCHMARK COMPARISON (RANKED BY POOLED RMSE)")
    print("=" * 80)
    print(comp_df.to_string(index=False))

    print("\n" + "=" * 80)
    print("LEAD-HORIZON BREAKDOWN")
    print("=" * 80)
    print(lead_df.to_string(index=False))

    comp_df.to_csv(REPORTS_DIR / "physics_model_comparison.csv", index=False)
    station_df.to_csv(REPORTS_DIR / "physics_station_metrics.csv", index=False)
    lead_df.to_csv(REPORTS_DIR / "physics_lead_metrics.csv", index=False)
    oof_df.to_csv(REPORTS_DIR / "physics_oof_predictions.csv", index=False)

    print("\nEvaluation artifacts written to reports/")


if __name__ == "__main__":
    main()
