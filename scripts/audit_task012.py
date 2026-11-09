"""TASK 012: Comprehensive Regression Audit and Model Comparison.

Reproduces and evaluates:
  1. 72-hour Station Median Baseline
  2. Persistence Baseline
  3. Previous Candidate C (hist24_blend50_median72)
  4. Previous Candidate E (50% CatBoost residual [2000 ceiling] + 50% Candidate C)
  5. Timestamp-median seasonal climatology (sh24 alone, pure 2024)
  6. Task 011 Kernel Climatology (standalone, combined history)
  7. Clean 2024 Kernel Climatology (standalone 2024 archive)
  8. Corrected Kernel Climatology Blend (50% m72 + 50% Clean Kernel Clim 2024)
  9. Task 011 Lead-Bucket Ridge Anomaly
  10. Task 011 LightGBM Residual
  11. Task 011 Climatology Blend

Evaluated across the exact 9 standardized chronological validation folds (N=1,460 rows).
Computes 10,000 paired block bootstrap confidence intervals against the strongest baseline.
Exports:
  - reports/task012_candidate_comparison.csv
  - reports/task012_fold_metrics.csv
  - reports/task012_paired_bootstrap.csv
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

import catboost as cb
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, root_mean_squared_error

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from mumbai_pm25.climatology.anomaly import extract_recent_anomalies
from mumbai_pm25.climatology.blend import ClimatologyBlend
from mumbai_pm25.climatology.kernel import KernelClimatology, normalized_doy
from mumbai_pm25.climatology.lgbm_residual import LightGBMResidualModel
from mumbai_pm25.climatology.ridge_model import LeadBucketRidge
from mumbai_pm25.data import load_data
from mumbai_pm25.features.pipeline import build_feature_matrix
from mumbai_pm25.historical_archive import (
    ARCHIVE_SERIES,
    STATION_NAME_MAP,
    build_seasonal_features,
    load_2024_history,
)
from mumbai_pm25.validation import generate_fixed_target_folds
from scripts.run_task011_experiments import (
    build_combined_history,
    build_training_samples_for_fold,
)
from scripts.verify_candidate_e_2000_ceiling import prepare_features

DATA_DIR = ROOT / "data" / "raw" / "challenge"
REPORTS_DIR = ROOT / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
TARGET_STATIONS = [11606, 11611, 3409510, 3409511]


def get_standard_9_folds(train_df: pd.DataFrame) -> list[dict]:
    orig_folds = generate_fixed_target_folds(
        train_df, gap_hours=48, horizon_hours=48, step_days=21, holdout_hours=48
    )
    folds = [
        {
            "fold_id": orig_folds[idx].fold_id,
            "regime": "monsoon_autumn",
            "target_start": orig_folds[idx].target_start,
            "cutoff": orig_folds[idx].pm_history_cutoff,
        }
        for idx in [-5, -4, -3, -2, -1]
    ]
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
    folds.extend(winter_defs)
    return folds


def main() -> None:
    print("=" * 80)
    print("TASK 012: RESOLVE TASK 011 REGRESSION AND FINAL MODEL SELECTION")
    print("=" * 80)

    train_df, _, _, _ = load_data(DATA_DIR)
    hist_2024 = load_2024_history(DATA_DIR / "AdditionalHistory.zip")

    grid = train_df.set_index(["location_id", "target_start"])[["pm25"]].sort_index()
    station_histories = {
        int(sid): grid.xs(sid, level="location_id")["pm25"]
        for sid in TARGET_STATIONS
    }

    folds = get_standard_9_folds(train_df)
    clim_estimator = KernelClimatology(sigma_doy=10.0, sigma_hour=1.0, clim_gap_days=14, min_weight=5.0)

    # Pre-build clean 2024 archive DataFrame per station using timestamp_median
    clean_2024_dfs = {}
    for sid in TARGET_STATIONS:
        sub = hist_2024[hist_2024["series_id"].isin(ARCHIVE_SERIES[sid])]
        agg = sub.groupby("hour_start")["pm25"].median().reset_index().rename(columns={"hour_start": "timestamp"})
        clean_2024_dfs[sid] = agg.sort_values("timestamp").reset_index(drop=True)

    all_fold_dfs = []
    t_min = train_df.target_start.min()

    print("\nExecuting all 9 folds across models...")
    for f_idx, f_info in enumerate(folds):
        fid = f_info["fold_id"]
        regime = f_info["regime"]
        t_start = f_info["target_start"]
        cutoff = f_info["cutoff"]
        print(f"[{f_idx + 1}/9] {fid} ({regime})...")

        target_hours = pd.date_range(t_start, periods=48, freq="h")
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
        val_df["pred_m72"] = val_df["location_id"].map(stat_medians)

        # 2. Persistence Baseline
        p_pers = []
        for r in val_df.itertuples(index=False):
            s_s = station_histories[r.location_id]
            h = s_s.loc[s_s.index < cutoff].dropna()
            p_pers.append(float(h.iloc[-1]) if not h.empty else 40.0)
        val_df["pred_persistence"] = p_pers

        # 3. Candidate C: hist24_same_hour_mean and Candidate C blend
        seas_val = build_seasonal_features(
            hist_2024,
            val_df[["location_id", "target_start"]],
            station_map=STATION_NAME_MAP,
            window_days=14,
            min_obs=3,
        )
        val_df["pred_sh24_alone"] = seas_val["hist24_same_hour_mean"].fillna(val_df["pred_m72"]).values
        val_df["pred_cand_c"] = np.where(
            seas_val["hist24_same_hour_mean"].notna(),
            0.50 * val_df["pred_m72"] + 0.50 * seas_val["hist24_same_hour_mean"],
            val_df["pred_m72"],
        )

        # 4. Task 011 Kernel Climatology (using combined history with Train up to cutoff)
        comb_histories_t011 = {
            sid: build_combined_history(train_df, hist_2024, sid, cutoff, archive_mode="timestamp_median")
            for sid in TARGET_STATIONS
        }
        val_features_t011 = []
        for sid in TARGET_STATIONS:
            s_sub = val_df[val_df["location_id"] == sid]
            if s_sub.empty:
                continue
            h_df = comb_histories_t011[sid]
            elig = clim_estimator._extract_eligible_history(h_df, cutoff)
            clim_res = clim_estimator.estimate_batch(elig, list(s_sub["target_start"]))
            anom = extract_recent_anomalies(h_df, cutoff, clim_estimator, window_hours=168)
            for (_, row), cres in zip(s_sub.iterrows(), clim_res):
                c_val = cres["clim_prediction"]
                t_tar = row["target_start"]
                lead_h = row["lead_hours"]
                val_features_t011.append({
                    "index": row.name,
                    "clim": c_val,
                    "lead_hours": lead_h,
                    "hour": t_tar.hour,
                    "dayofweek": t_tar.day_of_week,
                    "doy": normalized_doy(t_tar),
                    "a24": anom["a24"],
                    "a72": anom["a72"],
                    "a168": anom["a168"],
                    "count_168": anom["count_168"],
                    "std_168": anom["std_168"],
                    "staleness_hours": anom["staleness_hours"],
                    "station_id": sid,
                })
        val_feat_t011_df = pd.DataFrame(val_features_t011).sort_values("index").reset_index(drop=True)
        val_df["pred_t011_clim"] = val_feat_t011_df["clim"].values

        # 5. Clean 2024 Kernel Climatology (2024 archive only, free of Train.csv logger corruption)
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
        val_df["pred_clean_kclim_alone"] = p_clean_kclim
        val_df["pred_clean_kclim_blend50"] = 0.50 * val_df["pred_m72"] + 0.50 * val_df["pred_clean_kclim_alone"]

        # 6. Fit Task 011 Ridge and LightGBM
        X_tr, y_tr_res = build_training_samples_for_fold(
            comb_histories_t011,
            cutoff,
            clim_estimator,
            min_train_history_days=90,
            origin_step_hours=48,
            lead_min=41,
            lead_max=90,
        )
        ridge_model = LeadBucketRidge(n_buckets=5, alpha=100.0, feature_cols=["a24", "a72", "a168"])
        if len(X_tr) >= 50:
            ridge_model.fit(X_tr, y_tr_res, lead_col="lead_hours")
            res_pred_ridge = ridge_model.predict(val_feat_t011_df, lead_col="lead_hours")
        else:
            res_pred_ridge = np.zeros(len(val_df))
        val_df["pred_t011_ridge"] = np.maximum(0.0, val_df["pred_t011_clim"] + res_pred_ridge)

        lgbm_model = LightGBMResidualModel(seeds=(42, 123, 999), num_leaves=8, min_child_samples=300, n_estimators=300)
        if len(X_tr) >= 100:
            lgbm_model.fit(X_tr, y_tr_res)
            res_pred_lgbm = lgbm_model.predict(val_feat_t011_df)
        else:
            res_pred_lgbm = np.zeros(len(val_df))
        val_df["pred_t011_lgbm"] = np.maximum(0.0, val_df["pred_t011_clim"] + res_pred_lgbm)

        # 7. Candidate E (50% CatBoost Residual [2000 ceiling] + 50% Candidate C)
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
            for sid in TARGET_STATIONS:
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

        X_tr_cb = pd.concat(train_dfs, ignore_index=True)
        y_tr_cb = pd.concat(train_ys, ignore_index=True).to_numpy(dtype=float)

        X_val_cb = build_feature_matrix(
            station_histories,
            val_df,
            cutoff,
            history_2024=hist_2024,
            include_seasonal=True,
            include_spatial=True,
        )

        X_tr_prep = prepare_features(X_tr_cb)
        X_val_prep = prepare_features(X_val_cb)
        cats = ["station_id"] if "station_id" in X_tr_prep.columns else []

        baseline_tr = X_tr_cb["median_72"].to_numpy(dtype=float) if "median_72" in X_tr_cb.columns else np.full(len(y_tr_cb), 40.0)
        baseline_val = X_val_cb["median_72"].to_numpy(dtype=float) if "median_72" in X_val_cb.columns else np.full(len(val_df), 40.0)

        z_tr_2000 = np.clip(y_tr_cb, 0.0, 2000.0) - baseline_tr
        cb_2000 = cb.CatBoostRegressor(
            iterations=120, learning_rate=0.05, depth=6, l2_leaf_reg=3.0,
            random_seed=42, thread_count=1, verbose=0,
        )
        cb_2000.fit(X_tr_prep, z_tr_2000, cat_features=cats)
        p_res_2000 = np.maximum(0.0, baseline_val + cb_2000.predict(X_val_prep))
        val_df["pred_cand_e"] = 0.50 * p_res_2000 + 0.50 * val_df["pred_cand_c"]

        all_fold_dfs.append(val_df)

    full_oof = pd.concat(all_fold_dfs, ignore_index=True)
    print(f"\nTotal OOF Validation Rows across 9 folds: {len(full_oof)}")

    # 8. Task 011 Climatology Blend (Leave-One-Fold-Out)
    oof_t011_blend = np.zeros(len(full_oof))
    for fid in full_oof["fold_id"].unique():
        train_mask = full_oof["fold_id"] != fid
        val_mask = full_oof["fold_id"] == fid
        f_tr = full_oof[train_mask]
        f_val = full_oof[val_mask]
        blender = ClimatologyBlend(step=0.1)
        blender.fit(
            y_true=f_tr["y"].to_numpy(),
            p_clim=f_tr["pred_t011_clim"].to_numpy(),
            p_ridge=f_tr["pred_t011_ridge"].to_numpy(),
            p_lgbm=f_tr["pred_t011_lgbm"].to_numpy(),
        )
        oof_t011_blend[val_mask] = blender.predict(
            p_clim=f_val["pred_t011_clim"].to_numpy(),
            p_ridge=f_val["pred_t011_ridge"].to_numpy(),
            p_lgbm=f_val["pred_t011_lgbm"].to_numpy(),
        )
    full_oof["pred_t011_blend"] = oof_t011_blend

    # Models Dictionary
    models = [
        ("72h Station Median Baseline", "pred_m72"),
        ("Persistence Baseline", "pred_persistence"),
        ("Previous Candidate C (hist24_blend50_median72)", "pred_cand_c"),
        ("Previous Candidate E (CatBoost residual + Cand C)", "pred_cand_e"),
        ("Timestamp-Median Seasonal (sh24 alone)", "pred_sh24_alone"),
        ("Task 011 Kernel Climatology (standalone)", "pred_t011_clim"),
        ("Clean 2024 Kernel Climatology (standalone)", "pred_clean_kclim_alone"),
        ("Corrected Kernel Climatology Blend (50% m72 + 50% Clean Kernel Clim)", "pred_clean_kclim_blend50"),
        ("Task 011 Lead-Bucket Ridge Anomaly", "pred_t011_ridge"),
        ("Task 011 LightGBM Residual", "pred_t011_lgbm"),
        ("Task 011 Climatology Blend", "pred_t011_blend"),
    ]

    # 9. Candidate Comparison Table
    y_true = full_oof["y"].to_numpy()
    aut_mask = full_oof["regime"] == "monsoon_autumn"
    win_mask = full_oof["regime"] == "winter_transition"

    summary_rows = []
    for m_label, col in models:
        p = full_oof[col].to_numpy()
        rmse_pool = root_mean_squared_error(y_true, p)
        mae_pool = mean_absolute_error(y_true, p)
        rmse_aut = root_mean_squared_error(y_true[aut_mask], p[aut_mask])
        rmse_win = root_mean_squared_error(y_true[win_mask], p[win_mask])
        bias_pool = float(np.mean(p - y_true))

        st_rmses = {}
        for sid in TARGET_STATIONS:
            s_mask = full_oof["location_id"] == sid
            st_rmses[f"rmse_{sid}"] = round(root_mean_squared_error(y_true[s_mask], p[s_mask]), 2)

        summary_rows.append({
            "model": m_label,
            "pooled_rmse": round(rmse_pool, 3),
            "pooled_mae": round(mae_pool, 3),
            "monsoon_autumn_rmse": round(rmse_aut, 3),
            "winter_rmse": round(rmse_win, 3),
            "pooled_bias": round(bias_pool, 3),
            **st_rmses,
        })

    summary_df = pd.DataFrame(summary_rows)
    print("\n" + "=" * 80)
    print("TASK 012 CANDIDATE COMPARISON TABLE (N=1,460)")
    print("=" * 80)
    print(summary_df.to_string(index=False))

    # 10. Fold-Level Breakdown Table
    fold_level_records = []
    for fid in full_oof["fold_id"].unique():
        f_sub = full_oof[full_oof["fold_id"] == fid]
        f_y = f_sub["y"].to_numpy()
        regime = f_sub["regime"].iloc[0]
        f_row = {"fold_id": fid, "regime": regime, "row_count": len(f_sub)}
        for m_label, col in models:
            f_row[m_label] = round(root_mean_squared_error(f_y, f_sub[col].to_numpy()), 3)
        fold_level_records.append(f_row)
    fold_df = pd.DataFrame(fold_level_records)

    # 11. 10,000 Paired Block Bootstrap vs Strongest Existing Baselines
    print("\n" + "=" * 80)
    print("RUNNING 10,000 PAIRED BLOCK BOOTSTRAP AGAINST STRONGEST BASELINES")
    print("=" * 80)
    rng = np.random.default_rng(42)
    n_resamples = 10000
    unique_folds = full_oof["fold_id"].unique()
    n_folds = len(unique_folds)
    fold_indices = {fid: np.where(full_oof["fold_id"] == fid)[0] for fid in unique_folds}

    cand_c_pred = full_oof["pred_cand_c"].to_numpy()
    m72_pred = full_oof["pred_m72"].to_numpy()

    bootstrap_rows = []
    for m_label, col in models:
        if col in ("pred_cand_c", "pred_m72"):
            continue
        p = full_oof[col].to_numpy()
        diffs_vs_c = []
        diffs_vs_m72 = []
        for _ in range(n_resamples):
            sampled_fids = rng.choice(unique_folds, size=n_folds, replace=True)
            s_idx = np.concatenate([fold_indices[f] for f in sampled_fids])
            y_b = y_true[s_idx]
            p_b = p[s_idx]
            c_b = cand_c_pred[s_idx]
            m_b = m72_pred[s_idx]

            rmse_model = root_mean_squared_error(y_b, p_b)
            rmse_c = root_mean_squared_error(y_b, c_b)
            rmse_m72 = root_mean_squared_error(y_b, m_b)

            diffs_vs_c.append(rmse_model - rmse_c)
            diffs_vs_m72.append(rmse_model - rmse_m72)

        diffs_c_arr = np.array(diffs_vs_c)
        diffs_m_arr = np.array(diffs_vs_m72)

        bootstrap_rows.append({
            "model": m_label,
            "mean_diff_vs_CandC": round(float(np.mean(diffs_c_arr)), 3),
            "ci95_vs_CandC": f"[{np.percentile(diffs_c_arr, 2.5):.3f}, {np.percentile(diffs_c_arr, 97.5):.3f}]",
            "p_beats_CandC": round(float(np.mean(diffs_c_arr < 0)), 3),
            "mean_diff_vs_m72": round(float(np.mean(diffs_m_arr)), 3),
            "ci95_vs_m72": f"[{np.percentile(diffs_m_arr, 2.5):.3f}, {np.percentile(diffs_m_arr, 97.5):.3f}]",
            "p_beats_m72": round(float(np.mean(diffs_m_arr < 0)), 3),
        })

    boot_df = pd.DataFrame(bootstrap_rows)
    print("\nPaired Block Bootstrap 95% CIs (Model - Baseline):")
    print(boot_df.to_string(index=False))

    # 12. Export Deliverables
    print("\nExporting Task 012 Deliverables to reports/ ...")
    summary_df.to_csv(REPORTS_DIR / "task012_candidate_comparison.csv", index=False)
    fold_df.to_csv(REPORTS_DIR / "task012_fold_metrics.csv", index=False)
    boot_df.to_csv(REPORTS_DIR / "task012_paired_bootstrap.csv", index=False)
    print("Reports exported successfully!")


if __name__ == "__main__":
    main()
