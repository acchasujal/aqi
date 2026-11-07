"""Comprehensive extreme observation and paired candidate sensitivity audit.

Calculates:
1. Exact identification and prediction values for all y > 250 ug/m3 observations.
2. Full pooled RMSE, jackknife exclusions of extremes individually and collectively.
3. Block bootstrap by forecast fold (cluster bootstrap) for Candidate C vs Candidate B.
4. Paired comparisons across all segments (folds, stations, horizons, pollution bands, regimes).
5. Exports reports/candidate_C_B_paired_analysis.csv.
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

STATION_OFFICIAL_NAMES = {
    11606: "Borivali East, Mumbai - IITM",
    11611: "Malad West, Mumbai - IITM",
    3409510: "Byculla, Mumbai - BMC",
    3409511: "Shivaji Nagar, Mumbai - BMC",
}


def main() -> None:
    print("=" * 80)
    print("EXTREME OBSERVATION SENSITIVITY & PAIRED CANDIDATE C VS B AUDIT")
    print("=" * 80)

    # 1. Load data
    train, _, _, _ = load_data(DATA_DIR)
    hist_2024 = load_2024_history(DATA_DIR / "AdditionalHistory.zip")

    grid = train.set_index(["location_id", "target_start"])[["pm25"]].sort_index()
    station_histories = {
        int(sid): grid.xs(sid, level="location_id")["pm25"]
        for sid in train["location_id"].unique()
    }

    # 2. Define 9 folds
    original_folds = generate_fixed_target_folds(
        train, gap_hours=48, horizon_hours=48, step_days=21, holdout_hours=48
    )
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

    t_min = train.target_start.min().tz_convert("Asia/Kolkata")
    all_fold_preds = []

    for f_idx, f_info in enumerate(fold_specs):
        fid = f_info["fold_id"]
        regime = f_info["regime"]
        t_start = f_info["target_start"]
        cutoff = f_info["cutoff"]

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

        # Statistical seasonal (Candidate C)
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

        # CatBoost
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

        cb = SupervisedForecaster(
            model_family="catboost",
            target_transform="log1p",
            params={"iterations": 100, "learning_rate": 0.05, "depth": 6},
        )
        cb.fit(X_tr, y_tr)
        p_cb = cb.predict(X_val)

        df_fold = val_target_df.copy()
        df_fold["pred_catboost"] = p_cb
        df_fold["pred_stat_seasonal"] = p_stat
        df_fold["pred_cand_a"] = 0.83 * p_cb + 0.17 * p_stat
        df_fold["pred_cand_b"] = 0.50 * p_cb + 0.50 * p_stat
        df_fold["pred_cand_c"] = p_stat
        df_fold["pred_cand_d"] = 0.20 * p_cb + 0.80 * p_stat
        all_fold_preds.append(df_fold)

    df_all = pd.concat(all_fold_preds, ignore_index=True)
    df_all["station_name"] = df_all["location_id"].map(STATION_OFFICIAL_NAMES)

    # 1. EXTREME EVENT SENSITIVITY AUDIT
    print("\n--- 1. IDENTIFYING ALL OBSERVATIONS WITH y > 250 ug/m3 ---")
    extremes = df_all[df_all["y"] > 250.0].copy()
    print(f"Found {len(extremes)} extreme observations > 250 ug/m3:")
    print(extremes[[
        "fold_id", "location_id", "station_name", "target_start", "horizon_hours",
        "y", "pred_cand_c", "pred_cand_b", "pred_cand_a", "pred_catboost"
    ]].to_string(index=False))

    # Calculate Squared Errors
    for col in ["pred_cand_c", "pred_cand_b", "pred_cand_a", "pred_catboost"]:
        df_all[f"se_{col}"] = (df_all[col] - df_all["y"]) ** 2

    # Baseline Full Pooled RMSE
    rmse_full_c = np.sqrt(df_all["se_pred_cand_c"].mean())
    rmse_full_b = np.sqrt(df_all["se_pred_cand_b"].mean())
    rmse_full_a = np.sqrt(df_all["se_pred_cand_a"].mean())
    rmse_full_cb = np.sqrt(df_all["se_pred_catboost"].mean())

    print("\nFull Pooled RMSE (N=1316):")
    print(f"  Candidate C: {rmse_full_c:.4f}")
    print(f"  Candidate B: {rmse_full_b:.4f}")
    print(f"  Candidate A: {rmse_full_a:.4f}")
    print(f"  CatBoost alone: {rmse_full_cb:.4f}")

    # Exclude each extreme observation individually
    extreme_indices = list(extremes.index)
    single_drop_rows = []
    for idx in extreme_indices:
        row = df_all.loc[idx]
        sub = df_all.drop(index=idx)
        r_c = np.sqrt(sub["se_pred_cand_c"].mean())
        r_b = np.sqrt(sub["se_pred_cand_b"].mean())
        r_a = np.sqrt(sub["se_pred_cand_a"].mean())
        r_cb = np.sqrt(sub["se_pred_catboost"].mean())
        single_drop_rows.append({
            "dropped_index": idx,
            "station": row["station_name"],
            "timestamp": str(row["target_start"]),
            "observed_y": row["y"],
            "rmse_c": round(r_c, 4),
            "rmse_b": round(r_b, 4),
            "rmse_a": round(r_a, 4),
            "rmse_cb": round(r_cb, 4),
            "diff_b_minus_c": round(r_b - r_c, 4),
        })
    df_single_drop = pd.DataFrame(single_drop_rows)
    print("\nDiagnostic: RMSE Excluding Each Extreme Observation Individually (N=1315):")
    print(df_single_drop.to_string(index=False))

    # Exclude all extreme observations collectively
    sub_no_ext = df_all.drop(index=extreme_indices)
    r_no_ext_c = np.sqrt(sub_no_ext["se_pred_cand_c"].mean())
    r_no_ext_b = np.sqrt(sub_no_ext["se_pred_cand_b"].mean())
    r_no_ext_a = np.sqrt(sub_no_ext["se_pred_cand_a"].mean())
    r_no_ext_cb = np.sqrt(sub_no_ext["se_pred_catboost"].mean())

    print("\nDiagnostic: RMSE Excluding All 4 Extreme Observations (N=1312):")
    print(f"  Candidate C: {r_no_ext_c:.4f}")
    print(f"  Candidate B: {r_no_ext_b:.4f} (diff B - C: {r_no_ext_b - r_no_ext_c:+.4f})")
    print(f"  Candidate A: {r_no_ext_a:.4f}")
    print(f"  CatBoost alone: {r_no_ext_cb:.4f}")

    # Fold level changes for fold_nov_2025_calendar_match
    f_nov = df_all[df_all["fold_id"] == "fold_nov_2025_calendar_match"]
    f_nov_no_ext = f_nov.drop(index=[i for i in extreme_indices if i in f_nov.index])
    print(f"\nFold 'fold_nov_2025_calendar_match' with extremes (N={len(f_nov)}):")
    print(f"  Candidate C: {np.sqrt(f_nov['se_pred_cand_c'].mean()):.4f} | Candidate B: {np.sqrt(f_nov['se_pred_cand_b'].mean()):.4f}")
    print(f"Fold 'fold_nov_2025_calendar_match' without extremes (N={len(f_nov_no_ext)}):")
    print(f"  Candidate C: {np.sqrt(f_nov_no_ext['se_pred_cand_c'].mean()):.4f} | Candidate B: {np.sqrt(f_nov_no_ext['se_pred_cand_b'].mean()):.4f}")

    # 2. CLUSTER BOOTSTRAP BY FORECAST BLOCK (FOLD)
    print("\n--- 2. CLUSTER BOOTSTRAP BY FORECAST BLOCK (10,000 ITERATIONS) ---")
    np.random.seed(42)
    unique_folds = df_all["fold_id"].unique()
    n_folds = len(unique_folds)
    n_boot = 10000

    # Pre-index folds
    fold_dfs = {fid: df_all[df_all["fold_id"] == fid] for fid in unique_folds}
    boot_rmse_c = np.zeros(n_boot)
    boot_rmse_b = np.zeros(n_boot)
    boot_diff = np.zeros(n_boot)  # RMSE(B) - RMSE(C)

    for b in range(n_boot):
        sample_folds = np.random.choice(unique_folds, size=n_folds, replace=True)
        sampled_data = pd.concat([fold_dfs[f] for f in sample_folds], ignore_index=True)
        r_c = np.sqrt(sampled_data["se_pred_cand_c"].mean())
        r_b = np.sqrt(sampled_data["se_pred_cand_b"].mean())
        boot_rmse_c[b] = r_c
        boot_rmse_b[b] = r_b
        boot_diff[b] = r_b - r_c

    ci_c = np.percentile(boot_rmse_c, [2.5, 97.5])
    ci_b = np.percentile(boot_rmse_b, [2.5, 97.5])
    ci_diff = np.percentile(boot_diff, [2.5, 97.5])
    p_c_beats_b = np.mean(boot_diff > 0.0)

    print(f"Candidate C Bootstrap 95% CI: [{ci_c[0]:.2f}, {ci_c[1]:.2f}] (mean {boot_rmse_c.mean():.2f})")
    print(f"Candidate B Bootstrap 95% CI: [{ci_b[0]:.2f}, {ci_b[1]:.2f}] (mean {boot_rmse_b.mean():.2f})")
    print(f"Paired Difference (RMSE_B - RMSE_C) 95% CI: [{ci_diff[0]:.2f}, {ci_diff[1]:.2f}]")
    print(f"Probability Candidate C outperforms Candidate B (cluster-resampled): {p_c_beats_b * 100:.1f}%")

    # 3. PAIRED COMPARISON MATRIX ACROSS ALL SEGMENTS
    print("\n--- 3. GENERATING PAIRED COMPARISON TABLE ---")
    paired_rows = []

    def evaluate_segment(cat: str, seg_name: str, sub: pd.DataFrame) -> None:
        if sub.empty:
            return
        n = len(sub)
        y_true = sub["y"].to_numpy()
        p_c = sub["pred_cand_c"].to_numpy()
        p_b = sub["pred_cand_b"].to_numpy()
        p_a = sub["pred_cand_a"].to_numpy()
        se_c = (p_c - y_true) ** 2
        se_b = (p_b - y_true) ** 2
        se_a = (p_a - y_true) ** 2
        
        rmse_c = np.sqrt(np.mean(se_c))
        rmse_b = np.sqrt(np.mean(se_b))
        rmse_a = np.sqrt(np.mean(se_a))
        mae_c = np.mean(np.abs(p_c - y_true))
        mae_b = np.mean(np.abs(p_b - y_true))
        bias_c = np.mean(p_c - y_true)
        bias_b = np.mean(p_b - y_true)
        
        diff_rmse = rmse_b - rmse_c  # Positive means C is lower RMSE
        # Correlation between C and B predictions
        pred_corr = float(pd.Series(p_c).corr(pd.Series(p_b))) if n > 1 else np.nan
        # Mean absolute difference between C and B predictions
        mean_abs_div = float(np.mean(np.abs(p_c - p_b)))

        paired_rows.append({
            "segment_category": cat,
            "segment_name": seg_name,
            "sample_count": n,
            "rmse_cand_c": round(rmse_c, 4),
            "rmse_cand_b": round(rmse_b, 4),
            "diff_rmse_b_minus_c": round(diff_rmse, 4),
            "cand_c_advantage": "Yes" if diff_rmse > 0 else "No",
            "mae_cand_c": round(mae_c, 4),
            "mae_cand_b": round(mae_b, 4),
            "bias_cand_c": round(bias_c, 4),
            "bias_cand_b": round(bias_b, 4),
            "pred_correlation_c_b": round(pred_corr, 4),
            "mean_abs_divergence_ug": round(mean_abs_div, 2),
            "rmse_cand_a": round(rmse_a, 4),
        })

    # Regimes
    evaluate_segment("regime", "All Regimes Pooled (9 folds)", df_all)
    evaluate_segment("regime", "Monsoon/Autumn Folds (5 folds)", df_all[df_all["regime"] == "monsoon_autumn"])
    evaluate_segment("regime", "Winter Transition Folds (4 folds)", df_all[df_all["regime"] == "winter_transition"])

    # Folds
    for fid in unique_folds:
        evaluate_segment("fold", fid, df_all[df_all["fold_id"] == fid])

    # Stations
    for sid, sname in STATION_OFFICIAL_NAMES.items():
        evaluate_segment("station", f"{sname} ({sid})", df_all[df_all["location_id"] == sid])

    # Forecast Horizon Buckets
    df_all["h_bucket"] = pd.cut(
        df_all["horizon_hours"],
        bins=[0, 12, 24, 36, 48],
        labels=["Block 1-12h", "Block 13-24h", "Block 25-36h", "Block 37-48h"],
    )
    for hb in ["Block 1-12h", "Block 13-24h", "Block 25-36h", "Block 37-48h"]:
        evaluate_segment("horizon_bucket", hb, df_all[df_all["h_bucket"] == hb])

    # Day 1 vs Day 2
    evaluate_segment("day_of_forecast", "Day 1 (Hours 1-24)", df_all[df_all["horizon_hours"] <= 24])
    evaluate_segment("day_of_forecast", "Day 2 (Hours 25-48)", df_all[df_all["horizon_hours"] > 24])

    # Pollution Bands
    evaluate_segment("pollution_band", "Clean (y < 50)", df_all[df_all["y"] < 50.0])
    evaluate_segment("pollution_band", "Moderate (50 <= y < 75)", df_all[(df_all["y"] >= 50.0) & (df_all["y"] < 75.0)])
    evaluate_segment("pollution_band", "Elevated (75 <= y < 100)", df_all[(df_all["y"] >= 75.0) & (df_all["y"] < 100.0)])
    evaluate_segment("pollution_band", "High (100 <= y < 250)", df_all[(df_all["y"] >= 100.0) & (df_all["y"] < 250.0)])
    evaluate_segment("pollution_band", "Extreme (y >= 250)", df_all[df_all["y"] >= 250.0])
    evaluate_segment("pollution_band", "Diagnostic Non-Extreme (y < 250)", df_all[df_all["y"] < 250.0])

    df_paired = pd.DataFrame(paired_rows)
    csv_path = REPORTS_DIR / "candidate_C_B_paired_analysis.csv"
    df_paired.to_csv(csv_path, index=False)
    print(f"\nSaved paired analysis to: {csv_path}")


if __name__ == "__main__":
    main()
