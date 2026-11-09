"""TASK 009 Multi-Model and CatBoost Benchmarking Experiments.

Evaluates:
- CatBoost variants: log1p, raw, sqrt, residual_median72
- LightGBM variants: log1p, residual_median72
- XGBoost variants: log1p, residual_median72
- Statistical models: Median72, Seasonal_Blend (Strategy C), Seasonal_Anomaly_Decay
- Ensembles: Candidate A, Candidate B, Candidate C, Candidate D, Tree-Tree blend, CatBoost+AnomalyDecay

Evaluated across all 9 standardized chronological validation folds (N=1,316 ground-truth labels).
Produces:
- reports/catboost_model_comparison.csv
- reports/all_candidate_comparison.csv
- reports/oof_predictions_task009.csv.gz
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

from mumbai_pm25.data import load_data
from mumbai_pm25.features.pipeline import build_feature_matrix
from mumbai_pm25.historical_archive import (
    STATION_NAME_MAP,
    build_seasonal_features,
    load_2024_history,
)
from mumbai_pm25.models.supervised import SupervisedForecaster
from mumbai_pm25.validation import generate_fixed_target_folds

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "raw" / "challenge"
REPORTS_DIR = ROOT / "reports"


def main() -> None:
    print("=" * 80)
    print("TASK 009: MULTI-MODEL BENCHMARKING & CATBOOST INTEGRATION EXPERIMENTS")
    print("=" * 80)

    # 1. Load data
    train, _, _, _ = load_data(DATA_DIR)
    hist_2024 = load_2024_history(DATA_DIR / "AdditionalHistory.zip")

    grid = train.set_index(["location_id", "target_start"])[["pm25"]].sort_index()
    station_histories = {
        int(sid): grid.xs(sid, level="location_id")["pm25"]
        for sid in train["location_id"].unique()
    }

    # 2. Define the 9 standardized validation folds
    original_folds = generate_fixed_target_folds(
        train, gap_hours=48, horizon_hours=48, step_days=21, holdout_hours=48
    )
    # Target 5 fixed autumn/monsoon target windows matching previous audit
    autumn_indices = [-5, -4, -3, -2, -1]
    fold_specs = []
    for idx in autumn_indices:
        f = original_folds[idx]
        fold_specs.append({
            "fold_id": f.fold_id,
            "regime": "monsoon_autumn",
            "target_start": f.target_start,
            "target_end": f.target_end,
            "cutoff": f.pm_history_cutoff,
            "gap_hours": 48,
        })

    winter_defs = [
        {
            "fold_id": "fold_nov_2025_calendar_match",
            "regime": "winter_transition",
            "target_start": pd.Timestamp("2025-11-11 00:00:00", tz="Asia/Kolkata"),
            "target_end": pd.Timestamp("2025-11-12 23:00:00", tz="Asia/Kolkata"),
            "cutoff": pd.Timestamp("2025-11-09 00:00:00", tz="Asia/Kolkata"),
            "gap_hours": 48,
        },
        {
            "fold_id": "fold_dec_2025_winter",
            "regime": "winter_transition",
            "target_start": pd.Timestamp("2025-12-15 00:00:00", tz="Asia/Kolkata"),
            "target_end": pd.Timestamp("2025-12-16 23:00:00", tz="Asia/Kolkata"),
            "cutoff": pd.Timestamp("2025-12-13 00:00:00", tz="Asia/Kolkata"),
            "gap_hours": 48,
        },
        {
            "fold_id": "fold_jan_2026_early",
            "regime": "winter_transition",
            "target_start": pd.Timestamp("2026-01-05 00:00:00", tz="Asia/Kolkata"),
            "target_end": pd.Timestamp("2026-01-06 23:00:00", tz="Asia/Kolkata"),
            "cutoff": pd.Timestamp("2026-01-03 00:00:00", tz="Asia/Kolkata"),
            "gap_hours": 48,
        },
        {
            "fold_id": "fold_jan_2026_late",
            "regime": "winter_transition",
            "target_start": pd.Timestamp("2026-01-25 00:00:00", tz="Asia/Kolkata"),
            "target_end": pd.Timestamp("2026-01-26 23:00:00", tz="Asia/Kolkata"),
            "cutoff": pd.Timestamp("2026-01-23 00:00:00", tz="Asia/Kolkata"),
            "gap_hours": 48,
        },
    ]
    fold_specs.extend(winter_defs)

    t_min = train.target_start.min().tz_convert("Asia/Kolkata")
    all_fold_dfs = []

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
        val_target_df = pd.DataFrame(t_rows).dropna(subset=["y"]).reset_index(drop=True)

        # Statistical features for validation
        stat_medians = {}
        latest_obs = {}
        for sid in [11606, 11611, 3409510, 3409511]:
            s_series = station_histories[sid]
            h = s_series.loc[s_series.index < cutoff]
            w = h.loc[h.index >= cutoff - pd.Timedelta(hours=72)]
            stat_medians[sid] = float(w.median()) if w.notna().any() else 40.0
            latest_valid = h.dropna()
            latest_obs[sid] = float(latest_valid.iloc[-1]) if not latest_valid.empty else stat_medians[sid]

        seas_val = build_seasonal_features(
            hist_2024,
            val_target_df[["location_id", "target_start"]],
            station_map=STATION_NAME_MAP,
            window_days=14,
            min_obs=3,
        )

        # Compute Seasonal Climatology C(t) at cutoff
        cutoff_df = pd.DataFrame({
            "location_id": [11606, 11611, 3409510, 3409511],
            "target_start": [cutoff] * 4,
        })
        seas_cutoff = build_seasonal_features(
            hist_2024,
            cutoff_df,
            station_map=STATION_NAME_MAP,
            window_days=14,
            min_obs=3,
        )
        c_cutoff = {}
        for r_i, r in enumerate(cutoff_df.itertuples(index=False)):
            val_c = seas_cutoff.loc[r_i, "hist24_same_hour_mean"]
            c_cutoff[r.location_id] = float(val_c) if np.isfinite(val_c) else stat_medians[r.location_id]

        # 1. Baseline: Median72
        p_med72 = np.array([stat_medians[r.location_id] for r in val_target_df.itertuples(index=False)])

        # 2. Baseline: Statistical Seasonal Blend (Strategy C / P_fix)
        p_stat_list = []
        p_anomaly_decay_list = []
        tau_hours = 24.0  # atmospheric anomaly e-folding decay timescale

        for r_i, r in enumerate(val_target_df.itertuples(index=False)):
            m72 = stat_medians[r.location_id]
            sh = seas_val.loc[r_i, "hist24_same_hour_mean"] if r_i in seas_val.index else np.nan
            c_target = float(sh) if np.isfinite(sh) else m72
            # 50:50 blend
            b = 0.5 * m72 + 0.5 * c_target
            p_stat_list.append(max(0.0, b))

            # Anomaly decay: C_{t+h} + exp(-h/tau) * (y_t - C_t)
            y_curr = latest_obs[r.location_id]
            c_curr = c_cutoff[r.location_id]
            alpha_h = math.exp(-float(r.horizon_hours) / tau_hours)
            pred_decay = c_target + alpha_h * (y_curr - c_curr)
            p_anomaly_decay_list.append(max(0.0, float(pred_decay)))

        p_stat = np.array(p_stat_list)
        p_anomaly_decay = np.array(p_anomaly_decay_list)

        # 3. Supervised Model Training on historical origins strictly prior to cutoff
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
        y_tr = pd.concat(train_ys, ignore_index=True)

        X_val = build_feature_matrix(
            station_histories,
            val_target_df,
            cutoff,
            history_2024=hist_2024,
            include_seasonal=True,
            include_spatial=True,
        )

        # CatBoost Variants
        cb_log1p = SupervisedForecaster("catboost", target_transform="log1p",
                                        params={"iterations": 120, "learning_rate": 0.05, "depth": 6})
        cb_log1p.fit(X_tr, y_tr)
        p_cb_log1p = cb_log1p.predict(X_val)

        cb_raw = SupervisedForecaster("catboost", target_transform="raw",
                                      params={"iterations": 120, "learning_rate": 0.05, "depth": 6})
        cb_raw.fit(X_tr, y_tr)
        p_cb_raw = cb_raw.predict(X_val)

        cb_sqrt = SupervisedForecaster("catboost", target_transform="sqrt",
                                       params={"iterations": 120, "learning_rate": 0.05, "depth": 6})
        cb_sqrt.fit(X_tr, y_tr)
        p_cb_sqrt = cb_sqrt.predict(X_val)

        cb_res = SupervisedForecaster("catboost", target_transform="residual_median72",
                                      params={"iterations": 120, "learning_rate": 0.05, "depth": 6})
        cb_res.fit(X_tr, y_tr)
        p_cb_res = cb_res.predict(X_val)

        # LightGBM Variants
        lgb_log1p = SupervisedForecaster("lightgbm", target_transform="log1p",
                                         params={"n_estimators": 120, "learning_rate": 0.05, "num_leaves": 31})
        lgb_log1p.fit(X_tr, y_tr)
        p_lgb_log1p = lgb_log1p.predict(X_val)

        lgb_res = SupervisedForecaster("lightgbm", target_transform="residual_median72",
                                       params={"n_estimators": 120, "learning_rate": 0.05, "num_leaves": 31})
        lgb_res.fit(X_tr, y_tr)
        p_lgb_res = lgb_res.predict(X_val)

        # XGBoost Variants
        xgb_log1p = SupervisedForecaster("xgboost", target_transform="log1p",
                                         params={"n_estimators": 120, "learning_rate": 0.05, "max_depth": 6})
        xgb_log1p.fit(X_tr, y_tr)
        p_xgb_log1p = xgb_log1p.predict(X_val)

        xgb_res = SupervisedForecaster("xgboost", target_transform="residual_median72",
                                       params={"n_estimators": 120, "learning_rate": 0.05, "max_depth": 6})
        xgb_res.fit(X_tr, y_tr)
        p_xgb_res = xgb_res.predict(X_val)

        # Ensembles
        p_cand_a = 0.83 * p_cb_log1p + 0.17 * p_stat
        p_cand_b = 0.50 * p_cb_log1p + 0.50 * p_stat
        p_cand_c = p_stat
        p_cand_d = 0.20 * p_cb_log1p + 0.80 * p_stat
        p_blend_tree = 0.50 * p_cb_log1p + 0.50 * p_lgb_log1p
        p_blend_decay = 0.50 * p_cb_log1p + 0.50 * p_anomaly_decay

        df_fold = val_target_df.copy()
        df_fold["pred_median72"] = p_med72
        df_fold["pred_statistical_seasonal"] = p_stat
        df_fold["pred_anomaly_decay"] = p_anomaly_decay
        df_fold["pred_catboost_log1p"] = p_cb_log1p
        df_fold["pred_catboost_raw"] = p_cb_raw
        df_fold["pred_catboost_sqrt"] = p_cb_sqrt
        df_fold["pred_catboost_residual"] = p_cb_res
        df_fold["pred_lightgbm_log1p"] = p_lgb_log1p
        df_fold["pred_lightgbm_residual"] = p_lgb_res
        df_fold["pred_xgboost_log1p"] = p_xgb_log1p
        df_fold["pred_xgboost_residual"] = p_xgb_res
        df_fold["pred_candidate_a"] = p_cand_a
        df_fold["pred_candidate_b"] = p_cand_b
        df_fold["pred_candidate_c"] = p_cand_c
        df_fold["pred_candidate_d"] = p_cand_d
        df_fold["pred_blend_tree"] = p_blend_tree
        df_fold["pred_blend_decay"] = p_blend_decay

        all_fold_dfs.append(df_fold)

    df_oof = pd.concat(all_fold_dfs, ignore_index=True)
    print(f"\nAll 9 folds processed. Total evaluated rows: {len(df_oof):,}")

    # Save OOF predictions
    oof_path = REPORTS_DIR / "oof_predictions_task009.csv.gz"
    df_oof.to_csv(oof_path, index=False, compression="gzip")
    print(f"Saved OOF predictions to {oof_path}")

    # Evaluate models
    model_cols = [c for c in df_oof.columns if c.startswith("pred_")]
    models_dict = {c.replace("pred_", ""): c for c in model_cols}

    y_true = df_oof["y"].to_numpy()
    mask_mon = (df_oof["regime"] == "monsoon_autumn").to_numpy()
    mask_win = (df_oof["regime"] == "winter_transition").to_numpy()

    # 1. CatBoost Model Comparison Table
    cb_keys = ["catboost_log1p", "catboost_raw", "catboost_sqrt", "catboost_residual",
               "candidate_a", "candidate_b", "statistical_seasonal"]
    cb_rows = []
    for m in cb_keys:
        p = df_oof[models_dict[m]].to_numpy()
        err = p - y_true
        rmse_tot = float(np.sqrt(np.mean(err ** 2)))
        mae_tot = float(np.mean(np.abs(err)))
        bias_tot = float(np.mean(err))
        rmse_mon = float(np.sqrt(np.mean(err[mask_mon] ** 2)))
        rmse_win = float(np.sqrt(np.mean(err[mask_win] ** 2)))
        
        # Station metrics
        station_rmses = {}
        for sid in [11606, 11611, 3409510, 3409511]:
            m_sid = (df_oof["location_id"] == sid).to_numpy()
            station_rmses[f"rmse_station_{sid}"] = round(float(np.sqrt(np.mean(err[m_sid] ** 2))), 2)

        cb_rows.append({
            "model": m,
            "pooled_rmse": round(rmse_tot, 2),
            "autumn_rmse": round(rmse_mon, 2),
            "winter_rmse": round(rmse_win, 2),
            "mean_bias": round(bias_tot, 2),
            "mae": round(mae_tot, 2),
            **station_rmses,
        })
    df_cb_comp = pd.DataFrame(cb_rows).sort_values("pooled_rmse")
    cb_csv_path = REPORTS_DIR / "catboost_model_comparison.csv"
    df_cb_comp.to_csv(cb_csv_path, index=False)
    print(f"\nWrote CatBoost model comparison to {cb_csv_path}:")
    print(df_cb_comp.to_string(index=False))

    # 2. All Candidate Comparison Table
    all_rows = []
    for m, col in models_dict.items():
        p = df_oof[col].to_numpy()
        err = p - y_true
        rmse_tot = float(np.sqrt(np.mean(err ** 2)))
        mae_tot = float(np.mean(np.abs(err)))
        bias_tot = float(np.mean(err))
        rmse_mon = float(np.sqrt(np.mean(err[mask_mon] ** 2)))
        rmse_win = float(np.sqrt(np.mean(err[mask_win] ** 2)))

        # Extreme pollution metrics (y >= 100)
        m_hi = (y_true >= 100)
        rmse_hi = float(np.sqrt(np.mean(err[m_hi] ** 2))) if m_hi.any() else np.nan

        # Extreme pollution metrics (y >= 250)
        m_vhi = (y_true >= 250)
        rmse_vhi = float(np.sqrt(np.mean(err[m_vhi] ** 2))) if m_vhi.any() else np.nan

        # Clean regime metrics (y < 50)
        m_clean = (y_true < 50)
        rmse_clean = float(np.sqrt(np.mean(err[m_clean] ** 2))) if m_clean.any() else np.nan

        all_rows.append({
            "model_name": m,
            "pooled_rmse": round(rmse_tot, 2),
            "autumn_rmse": round(rmse_mon, 2),
            "winter_rmse": round(rmse_win, 2),
            "mean_bias": round(bias_tot, 2),
            "mae": round(mae_tot, 2),
            "clean_rmse_lt50": round(rmse_clean, 2),
            "high_rmse_ge100": round(rmse_hi, 2),
            "extreme_rmse_ge250": round(rmse_vhi, 2),
        })
    df_all_comp = pd.DataFrame(all_rows).sort_values("pooled_rmse")
    all_csv_path = REPORTS_DIR / "all_candidate_comparison.csv"
    df_all_comp.to_csv(all_csv_path, index=False)
    print(f"\nWrote All Candidate comparison to {all_csv_path}:")
    print(df_all_comp.to_string(index=False))


if __name__ == "__main__":
    main()
