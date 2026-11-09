"""Final verification script for Candidate E with exact 2000 ug/m3 training ceiling.

Evaluates across all 9 standardized chronological validation folds (N=1460).
Compares:
  - Candidate E (2000 ceiling): 50% CatBoost residual (y_train clipped at 2000) + 50% Candidate C
  - Candidate E (unclipped): 50% CatBoost residual (raw y_train) + 50% Candidate C
  - Candidate C: 100% Statistical Seasonal Blend
  - Candidate B: 50% CatBoost log1p + 50% Candidate C
Validation targets (y_val) and evaluation observations are strictly unclipped.
"""
from __future__ import annotations

import re
from pathlib import Path

import catboost as cb
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, root_mean_squared_error

from mumbai_pm25.data import load_data
from mumbai_pm25.features.pipeline import build_feature_matrix
from mumbai_pm25.historical_archive import (
    STATION_NAME_MAP,
    build_seasonal_features,
    load_2024_history,
)
from mumbai_pm25.validation import generate_fixed_target_folds

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "raw" / "challenge"
REPORTS_DIR = ROOT / "reports"


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


def main() -> None:
    print("=" * 80)
    print("FINAL VERIFICATION: CANDIDATE E WITH 2000 UG/M3 TRAINING CEILING")
    print("=" * 80)

    train, _, _, _ = load_data(DATA_DIR)
    hist_2024 = load_2024_history(DATA_DIR / "AdditionalHistory.zip")

    grid = train.set_index(["location_id", "target_start"])[["pm25"]].sort_index()
    station_histories = {
        int(sid): grid.xs(sid, level="location_id")["pm25"]
        for sid in train["location_id"].unique()
    }

    original_folds = generate_fixed_target_folds(
        train, gap_hours=48, horizon_hours=48, step_days=21, holdout_hours=48
    )
    autumn_indices = [-5, -4, -3, -2, -1]
    fold_specs = []
    for idx in autumn_indices:
        f = original_folds[idx]
        fold_specs.append({
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
            "target_start": pd.Timestamp("2026-01-25 00:00:00", tz="Asia/Kolkata"),
            "cutoff": pd.Timestamp("2026-01-23 00:00:00", tz="Asia/Kolkata"),
        },
    ]
    fold_specs.extend(winter_defs)

    t_min = train.target_start.min()
    all_val_records = []

    for f_idx, f_info in enumerate(fold_specs):
        fid = f_info["fold_id"]
        regime = f_info["regime"]
        t_start = f_info["target_start"]
        cutoff = f_info["cutoff"]
        print(f"Executing Fold [{f_idx + 1}/9]: {fid} ({regime})...")

        target_hours = pd.date_range(t_start, periods=48, freq="h")
        t_rows = []
        for sid in [11606, 11611, 3409510, 3409511]:
            s_series = station_histories[sid]
            for h_idx, t in enumerate(target_hours, start=1):
                y_val = s_series.loc[t] if t in s_series.index else np.nan
                t_rows.append({
                    "fold_id": fid,
                    "regime": regime,
                    "location_id": sid,
                    "target_start": t,
                    "horizon_hours": h_idx,
                    "y": y_val,
                })
        # Validation target is strictly unclipped
        val_target_df = pd.DataFrame(t_rows).dropna(subset=["y"]).reset_index(drop=True)

        stat_medians = {}
        for sid in [11606, 11611, 3409510, 3409511]:
            s_series = station_histories[sid]
            h = s_series.loc[s_series.index < cutoff]
            w = h.loc[h.index >= cutoff - pd.Timedelta(hours=72)]
            stat_medians[sid] = float(w.median()) if w.notna().any() else 40.0

        seas_val = build_seasonal_features(
            hist_2024,
            val_target_df[["location_id", "target_start"]],
            station_map=STATION_NAME_MAP,
            window_days=14,
            min_obs=3,
        )

        # Baseline: Candidate C (Statistical Seasonal Blend 50:50)
        p_cand_c = []
        for r_i, r in enumerate(val_target_df.itertuples(index=False)):
            m72 = stat_medians[r.location_id]
            sh = seas_val.loc[r_i, "hist24_same_hour_mean"] if r_i in seas_val.index else np.nan
            p_val = 0.5 * m72 + 0.5 * sh if np.isfinite(sh) else m72
            p_cand_c.append(max(0.0, float(p_val)))
        p_cand_c = np.array(p_cand_c)

        # Sampling historical training blocks
        hist_origins = pd.date_range(
            t_min + pd.Timedelta(days=21),
            cutoff - pd.Timedelta(hours=48),
            freq="48h",
            tz="Asia/Kolkata",
        )
        if len(hist_origins) > 35:
            hist_origins = hist_origins[::len(hist_origins) // 35]

        train_dfs, train_ys = [], []
        for orig in hist_origins:
            orig_cutoff = orig - pd.Timedelta(hours=48)
            orig_target_hours = pd.date_range(orig, periods=48, freq="h")
            tr_rows = []
            for sid in [11606, 11611, 3409510, 3409511]:
                s_series = station_histories[sid]
                for h_idx, t in enumerate(orig_target_hours, start=1):
                    if t in s_series.index and pd.notna(s_series.loc[t]):
                        tr_rows.append({
                            "location_id": sid,
                            "target_start": t,
                            "horizon_hours": h_idx,
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
            train_dfs.append(X_p)
            train_ys.append(tdf["pm25"])

        X_tr = pd.concat(train_dfs, ignore_index=True)
        y_tr = pd.concat(train_ys, ignore_index=True).to_numpy(dtype=float)

        X_val = build_feature_matrix(
            station_histories,
            val_target_df,
            cutoff,
            history_2024=hist_2024,
            include_seasonal=True,
            include_spatial=True,
        )

        X_tr_prep = prepare_features(X_tr)
        X_val_prep = prepare_features(X_val)
        cats = ["station_id"] if "station_id" in X_tr_prep.columns else []

        baseline_tr = X_tr["median_72"].to_numpy(dtype=float) if "median_72" in X_tr.columns else np.full(len(y_tr), 40.0)
        baseline_val = X_val["median_72"].to_numpy(dtype=float) if "median_72" in X_val.columns else np.full(len(val_target_df), 40.0)

        # 1. CatBoost Residual: 2000 ceiling (Candidate E final production configuration)
        z_tr_2000 = np.clip(y_tr, 0.0, 2000.0) - baseline_tr
        cb_2000 = cb.CatBoostRegressor(iterations=120, learning_rate=0.05, depth=6, l2_leaf_reg=3.0,
                                       random_seed=42, thread_count=1, verbose=0)
        cb_2000.fit(X_tr_prep, z_tr_2000, cat_features=cats)
        p_res_2000 = np.maximum(0.0, baseline_val + cb_2000.predict(X_val_prep))

        # 2. CatBoost Residual: unclipped (benchmark)
        z_tr_raw = y_tr - baseline_tr
        cb_raw = cb.CatBoostRegressor(iterations=120, learning_rate=0.05, depth=6, l2_leaf_reg=3.0,
                                      random_seed=42, thread_count=1, verbose=0)
        cb_raw.fit(X_tr_prep, z_tr_raw, cat_features=cats)
        p_res_raw = np.maximum(0.0, baseline_val + cb_raw.predict(X_val_prep))

        # 3. CatBoost log1p (Candidate B component)
        z_tr_log = np.log1p(np.maximum(0.0, y_tr))
        cb_log = cb.CatBoostRegressor(iterations=120, learning_rate=0.05, depth=6, l2_leaf_reg=3.0,
                                      random_seed=42, thread_count=1, verbose=0)
        cb_log.fit(X_tr_prep, z_tr_log, cat_features=cats)
        p_cb_log = np.expm1(np.maximum(0.0, cb_log.predict(X_val_prep)))

        val_rows = val_target_df.copy()
        val_rows["cand_c"] = p_cand_c
        val_rows["cand_b"] = 0.50 * p_cb_log + 0.50 * p_cand_c
        val_rows["res_unclipped"] = p_res_raw
        val_rows["res_2000"] = p_res_2000
        val_rows["cand_e_unclipped"] = 0.50 * p_res_raw + 0.50 * p_cand_c
        val_rows["cand_e_2000"] = 0.50 * p_res_2000 + 0.50 * p_cand_c
        all_val_records.append(val_rows)

    df_eval = pd.concat(all_val_records, ignore_index=True)

    models = [
        "cand_e_2000",
        "cand_e_unclipped",
        "res_2000",
        "res_unclipped",
        "cand_c",
        "cand_b",
    ]

    labels = {
        "cand_e_2000": "Candidate E (2000 Ceiling Production)",
        "cand_e_unclipped": "Candidate E (Unclipped Benchmark)",
        "res_2000": "CatBoost Residual (2000 Ceiling)",
        "res_unclipped": "CatBoost Residual (Unclipped)",
        "cand_c": "Candidate C (Statistical Seasonal)",
        "cand_b": "Candidate B (CatBoost log1p + Cand C)",
    }

    results = []
    y_true = df_eval["y"].values
    aut_mask = df_eval["regime"] == "monsoon_autumn"
    wint_mask = df_eval["regime"] == "winter_transition"
    clean_mask = df_eval["y"] < 50.0
    high_mask = df_eval["y"] >= 100.0

    for m in models:
        y_pred = df_eval[m].values
        rmse_pool = root_mean_squared_error(y_true, y_pred)
        mae_pool = mean_absolute_error(y_true, y_pred)
        bias = float(np.mean(y_pred - y_true))

        rmse_aut = root_mean_squared_error(y_true[aut_mask], y_pred[aut_mask])
        rmse_wint = root_mean_squared_error(y_true[wint_mask], y_pred[wint_mask])
        rmse_clean = root_mean_squared_error(y_true[clean_mask], y_pred[clean_mask])
        rmse_high = root_mean_squared_error(y_true[high_mask], y_pred[high_mask])

        results.append({
            "model_key": m,
            "model_name": labels[m],
            "pooled_rmse": rmse_pool,
            "autumn_rmse": rmse_aut,
            "winter_rmse": rmse_wint,
            "clean_rmse": rmse_clean,
            "high_rmse": rmse_high,
            "mae": mae_pool,
            "mean_bias": bias,
        })

    res_df = pd.DataFrame(results).sort_values("pooled_rmse")
    print("\nOVERALL METRIC COMPARISON ACROSS ALL 9 FOLDS (N=1460, strictly unclipped y_val):")
    print(res_df[["model_name", "pooled_rmse", "autumn_rmse", "winter_rmse", "clean_rmse", "high_rmse", "mae", "mean_bias"]].to_string(index=False))

    # Per-station table
    print("\nPER-STATION RMSE BREAKDOWN:")
    st_records = []
    for sid, group in df_eval.groupby("location_id"):
        y_st = group["y"].values
        st_records.append({
            "location_id": sid,
            "N": len(group),
            "E (2000 Ceiling)": root_mean_squared_error(y_st, group["cand_e_2000"].values),
            "E (Unclipped)": root_mean_squared_error(y_st, group["cand_e_unclipped"].values),
            "Candidate C": root_mean_squared_error(y_st, group["cand_c"].values),
            "Candidate B": root_mean_squared_error(y_st, group["cand_b"].values),
        })
    st_df = pd.DataFrame(st_records)
    print(st_df.to_string(index=False))

    # Per-fold table
    print("\nPER-FOLD RMSE BREAKDOWN:")
    fold_records = []
    for fid, group in df_eval.groupby("fold_id", sort=False):
        y_f = group["y"].values
        fold_records.append({
            "fold_id": fid,
            "regime": group["regime"].iloc[0],
            "N": len(group),
            "E (2000 Ceiling)": root_mean_squared_error(y_f, group["cand_e_2000"].values),
            "E (Unclipped)": root_mean_squared_error(y_f, group["cand_e_unclipped"].values),
            "Candidate C": root_mean_squared_error(y_f, group["cand_c"].values),
            "Candidate B": root_mean_squared_error(y_f, group["cand_b"].values),
        })
    f_df = pd.DataFrame(fold_records)
    print(f_df.to_string(index=False))

    # Save verification reports
    res_df.to_csv(REPORTS_DIR / "final_verification_candidate_e_2000_metrics.csv", index=False)
    st_df.to_csv(REPORTS_DIR / "final_verification_candidate_e_2000_stations.csv", index=False)
    f_df.to_csv(REPORTS_DIR / "final_verification_candidate_e_2000_folds.csv", index=False)
    df_eval.to_csv(REPORTS_DIR / "final_verification_predictions.csv.gz", compression="gzip", index=False)
    print("\nSaved verification reports to reports/final_verification_candidate_e_2000_*.csv")


if __name__ == "__main__":
    main()
