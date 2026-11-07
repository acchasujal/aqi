"""Candidate Diversity and Multi-Model Reassessment across Regimes.

Evaluates CatBoost, LightGBM, XGBoost, Statistical Baseline, Candidate A, Candidate B,
and multi-model candidates across:
1. Monsoon/Autumn Folds (Original 5 folds, N=745)
2. Winter/High-Pollution Transition Folds (4 seasonal winter folds, N=626)
3. Combined All-Regime Pooled Evaluation (9 folds, N=1371)

Outputs comprehensive metrics, paired fold differences, and residual correlations to
`reports/candidate_diversity_reassessment.csv`.
"""
from __future__ import annotations

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
    print("CANDIDATE DIVERSITY & ENSEMBLE REASSESSMENT ACROSS REGIMES")
    print("=" * 80)

    # 1. Load data
    train, _, _, _ = load_data(DATA_DIR)
    hist_2024 = load_2024_history(DATA_DIR / "AdditionalHistory.zip")

    grid = train.set_index(["location_id", "target_start"])[["pm25"]].sort_index()
    station_histories = {
        int(sid): grid.xs(sid, level="location_id")["pm25"]
        for sid in train["location_id"].unique()
    }

    # 2. Define all folds: 5 original folds + 4 winter seasonal folds
    original_folds = generate_fixed_target_folds(
        train, gap_hours=48, horizon_hours=48, step_days=21, holdout_hours=48
    )
    # The 5 folds evaluated previously: folds 24, 25, 26, 27, 28
    selected_orig_indices = [-5, -4, -3, -2, -1]

    fold_specs = []
    for idx in selected_orig_indices:
        f = original_folds[idx]
        fold_specs.append({
            "fold_id": f.fold_id,
            "regime": "monsoon_autumn",
            "target_start": f.target_start,
            "target_end": f.target_end,
            "cutoff": f.pm_history_cutoff,
            "gap_hours": 48,
        })

    # Add 4 seasonal winter folds
    seasonal_defs = [
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
    fold_specs.extend(seasonal_defs)

    print(f"Total folds to evaluate: {len(fold_specs)} (5 monsoon/autumn + 4 winter transition)")

    # Storage for predictions per fold
    # Models to evaluate:
    # - catboost_log1p
    # - lightgbm_log1p
    # - xgboost_log1p
    # - stat_blend50
    # - candidate_a (83% CB + 17% Stat)
    # - candidate_b (50% CB + 50% Stat)
    # - tree_blend (50% CB + 50% LGBM)
    # - multi_ensemble (40% CB + 40% LGBM + 20% Stat)
    all_fold_preds: list[pd.DataFrame] = []

    t_min = train.target_start.min().tz_convert("Asia/Kolkata")

    for f_idx, f_info in enumerate(fold_specs):
        fid = f_info["fold_id"]
        regime = f_info["regime"]
        t_start = f_info["target_start"]
        cutoff = f_info["cutoff"]
        print(f"\nProcessing Fold [{f_idx + 1}/{len(fold_specs)}]: {fid} ({regime}) ...")

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
        print(f"  Valid targets: {len(val_target_df)} / 192 (mean y={val_target_df['y'].mean():.2f})")

        # 1. Statistical baseline
        # 72h median
        stat_medians = {}
        for sid in [11606, 11611, 3409510, 3409511]:
            s_series = station_histories[sid]
            h = s_series.loc[s_series.index < cutoff]
            w = h.loc[h.index >= cutoff - pd.Timedelta(hours=72)]
            val = float(w.median()) if w.notna().any() else 40.0
            stat_medians[sid] = val

        seas_val = build_seasonal_features(
            hist_2024,
            val_target_df[["location_id", "target_start"]],
            station_map=STATION_NAME_MAP,
            window_days=14,
            min_obs=3,
        )

        p_stat_list = []
        for r_i, r in enumerate(val_target_df.itertuples(index=False)):
            m72 = stat_medians[r.location_id]
            sh = seas_val.loc[r_i, "hist24_same_hour_mean"] if r_i in seas_val.index else np.nan
            if np.isfinite(sh):
                b = 0.5 * m72 + 0.5 * float(sh)
            else:
                b = m72
            p_stat_list.append(max(0.0, b))
        p_stat = np.array(p_stat_list)

        # 2. Train supervised models
        # Sample historical origins strictly <= cutoff - 48h
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

        # Fit CatBoost log1p
        cb = SupervisedForecaster(
            model_family="catboost",
            target_transform="log1p",
            params={"iterations": 100, "learning_rate": 0.05, "depth": 6},
        )
        cb.fit(X_tr, y_tr)
        p_cb = cb.predict(X_val)

        # Fit LightGBM log1p
        lgb = SupervisedForecaster(
            model_family="lightgbm",
            target_transform="log1p",
            params={"n_estimators": 100, "learning_rate": 0.05, "num_leaves": 31},
        )
        lgb.fit(X_tr, y_tr)
        p_lgb = lgb.predict(X_val)

        # Fit XGBoost log1p
        xgb = SupervisedForecaster(
            model_family="xgboost",
            target_transform="log1p",
            params={"n_estimators": 100, "learning_rate": 0.05, "max_depth": 6},
        )
        xgb.fit(X_tr, y_tr)
        p_xgb = xgb.predict(X_val)

        # Build candidate predictions
        p_cand_a = 0.83 * p_cb + 0.17 * p_stat
        p_cand_b = 0.50 * p_cb + 0.50 * p_stat
        p_tree_blend = 0.50 * p_cb + 0.50 * p_lgb
        p_multi = 0.40 * p_cb + 0.40 * p_lgb + 0.20 * p_stat

        df_fold = val_target_df.copy()
        df_fold["pred_catboost"] = p_cb
        df_fold["pred_lightgbm"] = p_lgb
        df_fold["pred_xgboost"] = p_xgb
        df_fold["pred_stat_blend"] = p_stat
        df_fold["pred_candidate_a"] = p_cand_a
        df_fold["pred_candidate_b"] = p_cand_b
        df_fold["pred_tree_blend"] = p_tree_blend
        df_fold["pred_multi_ensemble"] = p_multi

        all_fold_preds.append(df_fold)

    full_eval_df = pd.concat(all_fold_preds, ignore_index=True)
    print(f"\nTotal evaluated ground-truth observations across 9 folds: {len(full_eval_df)}")

    # Models list
    models = [
        ("CatBoost_log1p", "pred_catboost"),
        ("LightGBM_log1p", "pred_lightgbm"),
        ("XGBoost_log1p", "pred_xgboost"),
        ("Statistical_Blend50", "pred_stat_blend"),
        ("Candidate_A (83% CB + 17% Stat)", "pred_candidate_a"),
        ("Candidate_B (50% CB + 50% Stat)", "pred_candidate_b"),
        ("Tree_Blend (50% CB + 50% LGB)", "pred_tree_blend"),
        ("Multi_Ensemble (40% CB + 40% LGB + 20% Stat)", "pred_multi_ensemble"),
    ]

    # Compute Residuals for all models
    for m_label, col in models:
        full_eval_df[f"res_{m_label}"] = full_eval_df[col] - full_eval_df["y"]

    # Compute Residual Correlation Matrix
    res_cols = [f"res_{m_label}" for m_label, _ in models]
    res_corr = full_eval_df[res_cols].corr()
    print("\n--- RESIDUAL CORRELATION MATRIX (ALL 9 FOLDS, N=1371) ---")
    print(res_corr.round(4).to_string())

    # Build Reassessment Output Rows
    rows = []

    # 1. Residual correlations vs CatBoost and vs Statistical Blend
    for m_label, _ in models:
        r_cb = full_eval_df[f"res_{m_label}"].corr(full_eval_df["res_CatBoost_log1p"])
        r_stat = full_eval_df[f"res_{m_label}"].corr(full_eval_df["res_Statistical_Blend50"])
        rows.append({
            "section": "residual_correlation",
            "group": "all_folds (n=1371)",
            "model": m_label,
            "corr_with_catboost_res": round(r_cb, 4),
            "corr_with_stat_blend_res": round(r_stat, 4),
            "rmse": np.nan,
            "mae": np.nan,
            "bias": np.nan,
            "paired_delta_vs_cb": np.nan,
            "paired_delta_vs_cand_a": np.nan,
        })

    # 2. Performance by Regime
    regimes = [
        ("Monsoon_Autumn (5 folds)", full_eval_df[full_eval_df["regime"] == "monsoon_autumn"]),
        ("Winter_Transition (4 folds)", full_eval_df[full_eval_df["regime"] == "winter_transition"]),
        ("All_Regimes_Pooled (9 folds)", full_eval_df),
    ]

    for reg_name, reg_df in regimes:
        y_true = reg_df["y"].to_numpy()
        cb_pred = reg_df["pred_catboost"].to_numpy()
        cb_rmse = np.sqrt(np.mean((cb_pred - y_true) ** 2))
        cand_a_pred = reg_df["pred_candidate_a"].to_numpy()
        cand_a_rmse = np.sqrt(np.mean((cand_a_pred - y_true) ** 2))

        for m_label, col in models:
            preds = reg_df[col].to_numpy()
            rmse = np.sqrt(np.mean((preds - y_true) ** 2))
            mae = np.mean(np.abs(preds - y_true))
            bias = np.mean(preds - y_true)
            rows.append({
                "section": "regime_performance",
                "group": f"{reg_name} (n={len(reg_df)})",
                "model": m_label,
                "corr_with_catboost_res": np.nan,
                "corr_with_stat_blend_res": np.nan,
                "rmse": round(rmse, 4),
                "mae": round(mae, 4),
                "bias": round(bias, 4),
                "paired_delta_vs_cb": round(rmse - cb_rmse, 4),
                "paired_delta_vs_cand_a": round(rmse - cand_a_rmse, 4),
            })

    # 3. Paired metrics per fold
    for f_id in full_eval_df["fold_id"].unique():
        f_sub = full_eval_df[full_eval_df["fold_id"] == f_id]
        y_f = f_sub["y"].to_numpy()
        cb_f_rmse = np.sqrt(np.mean((f_sub["pred_catboost"].to_numpy() - y_f) ** 2))
        cand_a_f_rmse = np.sqrt(np.mean((f_sub["pred_candidate_a"].to_numpy() - y_f) ** 2))

        for m_label, col in models:
            preds = f_sub[col].to_numpy()
            rmse = np.sqrt(np.mean((preds - y_f) ** 2))
            mae = np.mean(np.abs(preds - y_f))
            bias = np.mean(preds - y_f)
            rows.append({
                "section": "per_fold_paired",
                "group": f_id,
                "model": m_label,
                "corr_with_catboost_res": np.nan,
                "corr_with_stat_blend_res": np.nan,
                "rmse": round(rmse, 4),
                "mae": round(mae, 4),
                "bias": round(bias, 4),
                "paired_delta_vs_cb": round(rmse - cb_f_rmse, 4),
                "paired_delta_vs_cand_a": round(rmse - cand_a_f_rmse, 4),
            })

    # 4. Performance by Station
    for sid in [11606, 11611, 3409510, 3409511]:
        s_sub = full_eval_df[full_eval_df["location_id"] == sid]
        y_s = s_sub["y"].to_numpy()
        cb_s_rmse = np.sqrt(np.mean((s_sub["pred_catboost"].to_numpy() - y_s) ** 2))
        cand_a_s_rmse = np.sqrt(np.mean((s_sub["pred_candidate_a"].to_numpy() - y_s) ** 2))

        for m_label, col in models:
            preds = s_sub[col].to_numpy()
            rmse = np.sqrt(np.mean((preds - y_s) ** 2))
            mae = np.mean(np.abs(preds - y_s))
            bias = np.mean(preds - y_s)
            rows.append({
                "section": "per_station",
                "group": f"station_{sid} (n={len(s_sub)})",
                "model": m_label,
                "corr_with_catboost_res": np.nan,
                "corr_with_stat_blend_res": np.nan,
                "rmse": round(rmse, 4),
                "mae": round(mae, 4),
                "bias": round(bias, 4),
                "paired_delta_vs_cb": round(rmse - cb_s_rmse, 4),
                "paired_delta_vs_cand_a": round(rmse - cand_a_s_rmse, 4),
            })

    # 5. Performance by Pollution Level
    pol_bins = [
        ("Clean (y < 50)", full_eval_df[full_eval_df["y"] < 50.0]),
        ("Moderate (50 <= y < 100)", full_eval_df[(full_eval_df["y"] >= 50.0) & (full_eval_df["y"] < 100.0)]),
        ("Elevated (y >= 100)", full_eval_df[full_eval_df["y"] >= 100.0]),
    ]
    for b_label, b_df in pol_bins:
        y_b = b_df["y"].to_numpy()
        cb_b_rmse = np.sqrt(np.mean((b_df["pred_catboost"].to_numpy() - y_b) ** 2))
        cand_a_b_rmse = np.sqrt(np.mean((b_df["pred_candidate_a"].to_numpy() - y_b) ** 2))

        for m_label, col in models:
            preds = b_df[col].to_numpy()
            rmse = np.sqrt(np.mean((preds - y_b) ** 2))
            mae = np.mean(np.abs(preds - y_b))
            bias = np.mean(preds - y_b)
            rows.append({
                "section": "pollution_regime",
                "group": f"{b_label} (n={len(b_df)})",
                "model": m_label,
                "corr_with_catboost_res": np.nan,
                "corr_with_stat_blend_res": np.nan,
                "rmse": round(rmse, 4),
                "mae": round(mae, 4),
                "bias": round(bias, 4),
                "paired_delta_vs_cb": round(rmse - cb_b_rmse, 4),
                "paired_delta_vs_cand_a": round(rmse - cand_a_b_rmse, 4),
            })

    out_df = pd.DataFrame(rows)
    csv_path = REPORTS_DIR / "candidate_diversity_reassessment.csv"
    out_df.to_csv(csv_path, index=False)
    print(f"\nSaved reassessment report to: {csv_path}")

    # Print summary highlights
    reg_summary = out_df[out_df["section"] == "regime_performance"]
    print("\n--- SUMMARY OF REGIME PERFORMANCE (RMSE) ---")
    piv = reg_summary.pivot(index="model", columns="group", values="rmse")
    print(piv.round(2).to_string())


if __name__ == "__main__":
    main()
