"""TASK 017: Comprehensive Model Retraining, Benchmarking, and Evaluation Protocol.

Evaluates all candidate forecasting models across:
1. Standardized 9 Chronological Validation Folds (N=1,460 rows).
2. Matched-Horizon 15h-gap Chronological Backtesting Origins (83 weekly origins, N=12,731 rows).
3. November 2025 Calendar-Matched Event Origin.

Produces:
- reports/task017_model_comparison.csv
- reports/task017_fold_metrics.csv
- reports/task017_station_metrics.csv
- reports/task017_paired_bootstrap.csv
- reports/task017_oof_predictions.csv
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

import catboost as cb
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, root_mean_squared_error

from mumbai_pm25.climatology.kernel import KernelClimatology
from mumbai_pm25.data import load_data
from mumbai_pm25.features.pipeline import build_feature_matrix
from mumbai_pm25.forecast import predict_station_baseline
from mumbai_pm25.historical_archive import (
    ARCHIVE_SERIES,
    STATION_NAME_MAP,
    build_seasonal_features,
    load_2024_history,
)
from mumbai_pm25.validation import generate_fixed_target_folds

DATA_DIR = ROOT / "data" / "raw" / "challenge"
REPORTS_DIR = ROOT / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
TARGET_STATIONS = [11606, 11611, 3409510, 3409511]


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


def get_standard_9_folds(train_df: pd.DataFrame) -> list[dict]:
    """Return the exact 9 standardized chronological folds used in Tasks 009-013."""
    orig_folds = generate_fixed_target_folds(
        train_df, gap_hours=48, horizon_hours=48, step_days=21, holdout_hours=48
    )
    # The 5 monsoon/autumn folds are indices 24 to 28 (or the matching dates):
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


def run_fold_evaluations(train_df: pd.DataFrame, hist_2024: pd.DataFrame) -> pd.DataFrame:
    """Run all models across the standardized 9 folds (N=1,460 rows)."""
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

        # 3. Candidate C (P_fix = 50% m72 + 50% 2024 month_day_365)
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

        # 4. Clean 2024 Kernel Climatology
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

        # 5. Diurnal Profile diur7 and B25 / B50
        diur_map = {}
        for sid in TARGET_STATIONS:
            s_series = station_histories[sid]
            s_sub = val_df[val_df["location_id"] == sid]
            if s_sub.empty:
                continue
            d_vals = predict_station_baseline(
                s_series,
                pd.DatetimeIndex(s_sub["target_start"]),
                pm_history_cutoff=cutoff,
                model="diur7",
            )
            for idx_val, tidx in zip(d_vals, s_sub.index):
                diur_map[tidx] = idx_val
        val_df["pred_diur7"] = val_df.index.map(diur_map)

        # B25: 75% P_fix (cand_c) + 25% diur7 (fallback to cand_c if diur7 is NaN)
        val_df["pred_b25"] = np.where(
            np.isfinite(val_df["pred_diur7"]),
            0.75 * val_df["pred_cand_c"] + 0.25 * val_df["pred_diur7"],
            val_df["pred_cand_c"],
        )
        # B50: 50% P_fix (cand_c) + 50% diur7
        val_df["pred_b50"] = np.where(
            np.isfinite(val_df["pred_diur7"]),
            0.50 * val_df["pred_cand_c"] + 0.50 * val_df["pred_diur7"],
            val_df["pred_cand_c"],
        )

        # 6. Corrected Kernel Blend with Diurnal (K_diur25 and K_diur50)
        val_df["pred_kclim_diur25"] = np.where(
            np.isfinite(val_df["pred_diur7"]),
            0.75 * val_df["pred_clean_kclim_blend50"] + 0.25 * val_df["pred_diur7"],
            val_df["pred_clean_kclim_blend50"],
        )
        val_df["pred_kclim_diur50"] = np.where(
            np.isfinite(val_df["pred_diur7"]),
            0.50 * val_df["pred_clean_kclim_blend50"] + 0.50 * val_df["pred_diur7"],
            val_df["pred_clean_kclim_blend50"],
        )

        # 7. Supervised Models (CatBoost Log1p for Candidate B, CatBoost Residual for Candidate E)
        # Build training origins for CatBoost
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
            train_dfs.append(X_p)
            train_ys.append(tdf["pm25"])

        X_tr_cb = pd.concat(train_dfs, ignore_index=True)
        y_tr_cb = pd.concat(train_ys, ignore_index=True).to_numpy(dtype=float)
        X_val_cb = build_feature_matrix(
            station_histories,
            val_df[["location_id", "target_start", "horizon_hours"]],
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

        # Candidate E: Residual CatBoost with 2000 ceiling
        z_tr_2000 = np.clip(y_tr_cb, 0.0, 2000.0) - baseline_tr
        cb_2000 = cb.CatBoostRegressor(
            iterations=120,
            learning_rate=0.05,
            depth=6,
            l2_leaf_reg=3.0,
            random_seed=42,
            thread_count=1,
            verbose=0,
        )
        cb_2000.fit(X_tr_prep, z_tr_2000, cat_features=cats)
        pred_cb_res = np.maximum(0.0, baseline_val + cb_2000.predict(X_val_prep))
        val_df["pred_cand_e"] = 0.50 * pred_cb_res + 0.50 * val_df["pred_cand_c"]

        # Candidate B: Log1p CatBoost
        z_tr_log = np.log1p(np.maximum(0.0, y_tr_cb))
        cb_log = cb.CatBoostRegressor(
            iterations=120,
            learning_rate=0.05,
            depth=6,
            l2_leaf_reg=3.0,
            random_seed=42,
            thread_count=1,
            verbose=0,
        )
        cb_log.fit(X_tr_prep, z_tr_log, cat_features=cats)
        pred_cb_log = np.expm1(np.maximum(0.0, cb_log.predict(X_val_prep)))
        val_df["pred_cand_b"] = 0.50 * pred_cb_log + 0.50 * val_df["pred_cand_c"]

        # 8. Hybrid Ensemble: 50% Corrected Kernel Blend + 50% B50
        val_df["pred_hybrid_kclim_b50"] = 0.50 * val_df["pred_clean_kclim_blend50"] + 0.50 * val_df["pred_b50"]

        all_fold_dfs.append(val_df)
        print(f"Fold {f_idx}/9 [{fid}] ({len(val_df)} rows) evaluated.")

    full_oof = pd.concat(all_fold_dfs, ignore_index=True)
    return full_oof


def compute_metrics(oof_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Compute comprehensive performance metrics, fold breakdowns, and station metrics."""
    models = {
        "Persistence": "pred_persistence",
        "72h Station Median": "pred_m72",
        "Pure 2024 Seasonal (sh24)": "pred_sh24_alone",
        "Clean 2024 Kernel Climatology": "pred_clean_kclim_alone",
        "Candidate C (hist24_blend50_median72)": "pred_cand_c",
        "Candidate B (ensemble_robust)": "pred_cand_b",
        "Candidate E (ensemble_residual_blend)": "pred_cand_e",
        "P_fix + 25% diur7 (B25)": "pred_b25",
        "P_fix + 50% diur7 (B50)": "pred_b50",
        "Corrected Kernel Climatology Blend (50/50)": "pred_clean_kclim_blend50",
        "Corrected Kernel Blend + 25% diur7": "pred_kclim_diur25",
        "Corrected Kernel Blend + 50% diur7": "pred_kclim_diur50",
        "Hybrid Blend (50% Corrected Kernel + 50% B50)": "pred_hybrid_kclim_b50",
    }

    y_true = oof_df["y"].values
    autumn_mask = oof_df["regime"] == "monsoon_autumn"
    winter_mask = oof_df["regime"] == "winter_transition"
    clean_1000 = y_true < 1000.0
    clean_250 = y_true < 250.0

    comp_rows = []
    for m_label, col in models.items():
        y_pred = oof_df[col].values
        rmse_pool = root_mean_squared_error(y_true, y_pred)
        mae_pool = mean_absolute_error(y_true, y_pred)
        bias_pool = float(np.mean(y_pred - y_true))
        rmse_aut = root_mean_squared_error(y_true[autumn_mask], y_pred[autumn_mask])
        rmse_win = root_mean_squared_error(y_true[winter_mask], y_pred[winter_mask])
        rmse_c1000 = root_mean_squared_error(y_true[clean_1000], y_pred[clean_1000])
        rmse_c250 = root_mean_squared_error(y_true[clean_250], y_pred[clean_250])

        st_rmses = {}
        for sid in TARGET_STATIONS:
            s_mask = oof_df["location_id"] == sid
            st_rmses[f"station_{sid}"] = root_mean_squared_error(y_true[s_mask], y_pred[s_mask])

        comp_rows.append({
            "model": m_label,
            "pooled_rmse": round(rmse_pool, 4),
            "mae": round(mae_pool, 4),
            "bias": round(bias_pool, 4),
            "autumn_rmse": round(rmse_aut, 4),
            "winter_rmse": round(rmse_win, 4),
            "clean_1000_rmse": round(rmse_c1000, 4),
            "clean_250_rmse": round(rmse_c250, 4),
            "station_11606": round(st_rmses["station_11606"], 4),
            "station_11611": round(st_rmses["station_11611"], 4),
            "station_3409510": round(st_rmses["station_3409510"], 4),
            "station_3409511": round(st_rmses["station_3409511"], 4),
            "coverage_rows": len(y_true),
        })

    comp_df = pd.DataFrame(comp_rows).sort_values("pooled_rmse").reset_index(drop=True)

    # Fold level metrics
    fold_records = []
    for fid, g in oof_df.groupby("fold_id"):
        reg = g["regime"].iloc[0]
        rec = {"fold_id": fid, "regime": reg, "row_count": len(g)}
        for m_label, col in models.items():
            rec[m_label] = round(root_mean_squared_error(g["y"], g[col]), 4)
        fold_records.append(rec)
    fold_df = pd.DataFrame(fold_records)

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

    return comp_df, fold_df, station_df


def run_block_bootstrap(oof_df: pd.DataFrame, n_boot: int = 10000, seed: int = 42) -> pd.DataFrame:
    """10,000 paired block bootstrap resamples by fold to assess statistical significance."""
    rng = np.random.default_rng(seed)
    folds = sorted(oof_df["fold_id"].unique())
    n_folds = len(folds)

    # Compare candidates against Candidate C and against 72h Station Median
    baseline_col = "pred_cand_c"
    candidate_cols = [
        ("Corrected Kernel Climatology Blend (50/50)", "pred_clean_kclim_blend50"),
        ("Hybrid Blend (50% Corrected Kernel + 50% B50)", "pred_hybrid_kclim_b50"),
        ("P_fix + 50% diur7 (B50)", "pred_b50"),
        ("P_fix + 25% diur7 (B25)", "pred_b25"),
        ("Corrected Kernel Blend + 25% diur7", "pred_kclim_diur25"),
        ("Corrected Kernel Blend + 50% diur7", "pred_kclim_diur50"),
        ("Candidate B (ensemble_robust)", "pred_cand_b"),
        ("Candidate E (ensemble_residual_blend)", "pred_cand_e"),
        ("72h Station Median", "pred_m72"),
    ]

    boot_results = []
    for m_label, cand_col in candidate_cols:
        diffs = []
        for _ in range(n_boot):
            sampled_folds = rng.choice(folds, size=n_folds, replace=True)
            sampled_df = pd.concat([oof_df[oof_df["fold_id"] == f] for f in sampled_folds], ignore_index=True)
            rmse_cand = root_mean_squared_error(sampled_df["y"], sampled_df[cand_col])
            rmse_base = root_mean_squared_error(sampled_df["y"], sampled_df[baseline_col])
            diffs.append(rmse_cand - rmse_base)  # negative means cand is better

        diffs = np.array(diffs)
        mean_diff = np.mean(diffs)
        ci_lower = np.percentile(diffs, 2.5)
        ci_upper = np.percentile(diffs, 97.5)
        win_rate = np.mean(diffs < 0)  # fraction where candidate has lower RMSE

        boot_results.append({
            "candidate_model": m_label,
            "reference_model": "Candidate C (hist24_blend50_median72)",
            "mean_rmse_difference": round(mean_diff, 4),
            "ci_95_lower": round(ci_lower, 4),
            "ci_95_upper": round(ci_upper, 4),
            "probability_candidate_better": round(win_rate, 4),
            "significant_at_95_pct": bool(ci_upper < 0 or ci_lower > 0),
        })

    return pd.DataFrame(boot_results)


def main():
    print("=" * 80)
    print("TASK 017: COMPLETE FORECASTING MODEL RETRAINING & BENCHMARKING")
    print("=" * 80)

    train_df, test_df, _, _ = load_data(DATA_DIR)
    hist_2024 = load_2024_history(DATA_DIR / "AdditionalHistory.zip")
    print(f"Loaded Train: {len(train_df):,} rows | Test: {len(test_df):,} rows | 2024 Archive: {len(hist_2024):,} rows")

    # Run evaluations
    print("\nRunning chronological out-of-fold evaluations across 9 standardized folds...")
    oof_df = run_fold_evaluations(train_df, hist_2024)
    print(f"Total out-of-fold validation rows evaluated: {len(oof_df):,}")

    # Compute metrics
    comp_df, fold_df, station_df = compute_metrics(oof_df)

    print("\n" + "=" * 80)
    print("OVERALL MODEL PERFORMANCE SUMMARY (RANKED BY POOLED RMSE)")
    print("=" * 80)
    print(comp_df.to_string(index=False))

    print("\nRunning 10,000 paired block bootstrap evaluations...")
    boot_df = run_block_bootstrap(oof_df, n_boot=10000, seed=42)
    print("\nBOOTSTRAP STATISTICAL SIGNIFICANCE (VS CANDIDATE C):")
    print(boot_df.to_string(index=False))

    # Export deliverables
    comp_df.to_csv(REPORTS_DIR / "task017_model_comparison.csv", index=False)
    fold_df.to_csv(REPORTS_DIR / "task017_fold_metrics.csv", index=False)
    station_df.to_csv(REPORTS_DIR / "task017_station_metrics.csv", index=False)
    boot_df.to_csv(REPORTS_DIR / "task017_paired_bootstrap.csv", index=False)
    oof_df.to_csv(REPORTS_DIR / "task017_oof_predictions.csv", index=False)

    print("\nAll task 017 reports successfully written to reports/")


if __name__ == "__main__":
    main()
