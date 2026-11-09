"""TASK 011: Climatology-First Mumbai PM2.5 Forecasting Pipeline Validation Runner.

Evaluates across all 9 standardized chronological validation folds (N=1,460 rows).
Models evaluated:
  - Baselines:
      1. Persistence (last observed value before cutoff)
      2. Station-hour climatology (simple empirical mean by station and hour-of-day)
      3. 72h station median
  - Model A: Kernel Climatology alone
  - Model B: Lead-Bucket Ridge on anomalies (5 lead buckets: 41-50, 51-60, 61-70, 71-80, 81-90)
  - Model C: LightGBM Residual (3-seed averaged)
  - Source Series Sensitivity for Borivali and Malad:
      1. Independent series (site_5113 vs site_5400, site_5102 vs site_5402)
      2. Equal-weight average of overlapping series
      3. Timestamp median of overlapping series
      4. Timestamp mean of overlapping series
      5. Train-only (Train.csv only, no 2024 archive)
  - Model D: Candidate Blend (Climatology + Ridge Anomaly + LightGBM Residual) with leave-one-fold-out weight fitting
  - 10,000-resample block bootstrap 95% confidence intervals vs baseline climatology.
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, root_mean_squared_error

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mumbai_pm25.climatology.anomaly import extract_recent_anomalies
from mumbai_pm25.climatology.blend import ClimatologyBlend
from mumbai_pm25.climatology.kernel import KernelClimatology, normalized_doy
from mumbai_pm25.climatology.lgbm_residual import LightGBMResidualModel
from mumbai_pm25.climatology.ridge_model import LeadBucketRidge
from mumbai_pm25.data import load_data
from mumbai_pm25.historical_archive import (
    ARCHIVE_SERIES,
    P_FIX_SERIES,
    load_2024_history,
)
from mumbai_pm25.validation import generate_fixed_target_folds

DATA_DIR = ROOT / "data" / "raw" / "challenge"
REPORTS_DIR = ROOT / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

TARGET_STATIONS = [11606, 11611, 3409510, 3409511]


def build_station_archive_df(
    hist_2024: pd.DataFrame,
    station_id: int,
    mode: str = "p_fix",
) -> pd.DataFrame:
    """Build clean 2024 station history DataFrame with columns ['timestamp', 'pm25']."""
    if mode == "train_only":
        return pd.DataFrame(columns=["timestamp", "pm25"])

    if mode == "p_fix":
        allowed_series = P_FIX_SERIES.get(station_id, ())
    elif mode == "series_5113_5102":
        series_map = {11606: ("xkdr:site_5113",), 11611: ("xkdr:site_5102",)}
        allowed_series = series_map.get(station_id, ARCHIVE_SERIES.get(station_id, ()))
    elif mode == "series_5400_5402":
        series_map = {11606: ("xkdr:site_5400",), 11611: ("xkdr:site_5402",)}
        allowed_series = series_map.get(station_id, ARCHIVE_SERIES.get(station_id, ()))
    elif mode in ("equal_weight", "timestamp_mean", "timestamp_median"):
        allowed_series = ARCHIVE_SERIES.get(station_id, ())
    else:
        raise ValueError(f"Unknown mode: {mode}")

    sub = hist_2024.loc[hist_2024["series_id"].isin(allowed_series)].copy()
    if sub.empty:
        return pd.DataFrame(columns=["timestamp", "pm25"])

    if mode in ("equal_weight", "timestamp_mean"):
        agg = sub.groupby("hour_start")["pm25"].mean().reset_index()
    elif mode == "timestamp_median":
        agg = sub.groupby("hour_start")["pm25"].median().reset_index()
    else:
        agg = sub.groupby("hour_start")["pm25"].mean().reset_index()

    agg = agg.rename(columns={"hour_start": "timestamp"})
    return agg.sort_values("timestamp").reset_index(drop=True)


def build_combined_history(
    train_df: pd.DataFrame,
    hist_2024: pd.DataFrame | None,
    station_id: int,
    cutoff: pd.Timestamp,
    archive_mode: str = "p_fix",
) -> pd.DataFrame:
    """Combine 2024 archive and Train observations strictly up to cutoff."""
    frames = []
    if hist_2024 is not None and archive_mode != "train_only":
        arch = build_station_archive_df(hist_2024, station_id, mode=archive_mode)
        arch = arch.loc[arch["timestamp"] <= cutoff]
        if not arch.empty:
            frames.append(arch)

    # Train observations up to cutoff
    tr_sub = train_df.loc[
        (train_df["location_id"] == station_id) & (train_df["target_start"] <= cutoff),
        ["target_start", "pm25"],
    ].copy()
    tr_sub = tr_sub.rename(columns={"target_start": "timestamp"}).dropna(subset=["pm25"])
    if not tr_sub.empty:
        frames.append(tr_sub)

    if not frames:
        return pd.DataFrame(columns=["timestamp", "pm25"])

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    return combined


def get_standard_9_folds(train_df: pd.DataFrame) -> list[dict]:
    """Return specifications for the 9 standardized chronological validation folds."""
    original_folds = generate_fixed_target_folds(
        train_df, gap_hours=48, horizon_hours=48, step_days=21, holdout_hours=48
    )
    autumn_indices = [-5, -4, -3, -2, -1]
    folds = []
    for idx in autumn_indices:
        f = original_folds[idx]
        folds.append({
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
    folds.extend(winter_defs)
    return folds


def build_training_samples_for_fold(
    combined_histories: dict[int, pd.DataFrame],
    cutoff: pd.Timestamp,
    clim_estimator: KernelClimatology,
    min_train_history_days: int = 90,
    origin_step_hours: int = 48,
    lead_min: int = 41,
    lead_max: int = 90,
) -> tuple[pd.DataFrame, np.ndarray]:
    """Generate purged chronological training samples mimicking test inference."""
    all_timestamps = pd.concat([h["timestamp"] for h in combined_histories.values() if not h.empty])
    if all_timestamps.empty:
        return pd.DataFrame(), np.array([])

    t_min = all_timestamps.min()
    start_origin = t_min + pd.Timedelta(days=min_train_history_days)
    end_origin = cutoff - pd.Timedelta(hours=lead_max + 24)

    if start_origin >= end_origin:
        # Fallback to shorter history requirement if needed
        start_origin = t_min + pd.Timedelta(days=30)

    if start_origin >= end_origin:
        return pd.DataFrame(), np.array([])

    hist_origins = pd.date_range(start_origin, end_origin, freq=f"{origin_step_hours}h", tz="Asia/Kolkata")
    if len(hist_origins) > 25:
        hist_origins = hist_origins[::len(hist_origins) // 25]

    rows = []
    y_res_list = []

    for orig in hist_origins:
        target_times = [orig + pd.Timedelta(hours=h) for h in range(lead_min, lead_max + 1)]

        for sid in TARGET_STATIONS:
            h_df = combined_histories[sid]
            if h_df.empty:
                continue

            # Check if origin has any recent data
            prior = h_df.loc[h_df["timestamp"] <= orig]
            if len(prior) < 10:
                continue

            # Extract anomaly features strictly at origin
            anom = extract_recent_anomalies(h_df, orig, clim_estimator, window_hours=168)

            # Extract climatology for targets
            elig_clim = clim_estimator._extract_eligible_history(h_df, orig)
            if elig_clim.empty:
                continue

            clim_results = clim_estimator.estimate_batch(elig_clim, target_times)

            # Map observations
            h_indexed = h_df.set_index("timestamp")["pm25"]

            for h_idx, (t_target, clim_res) in enumerate(zip(target_times, clim_results), start=lead_min):
                if t_target in h_indexed.index:
                    y_actual = h_indexed.loc[t_target]
                    if pd.notna(y_actual) and np.isfinite(y_actual):
                        c_pred = clim_res["clim_prediction"]
                        if np.isfinite(c_pred):
                            res = float(y_actual - c_pred)
                            y_res_list.append(res)
                            rows.append({
                                "origin": orig,
                                "station_id": sid,
                                "lead_hours": h_idx,
                                "target_timestamp": t_target,
                                "hour": t_target.hour,
                                "dayofweek": t_target.day_of_week,
                                "doy": normalized_doy(t_target),
                                "clim": c_pred,
                                "a24": anom["a24"],
                                "a72": anom["a72"],
                                "a168": anom["a168"],
                                "count_168": anom["count_168"],
                                "std_168": anom["std_168"],
                                "staleness_hours": anom["staleness_hours"],
                            })

    if not rows:
        return pd.DataFrame(), np.array([])

    return pd.DataFrame(rows), np.array(y_res_list, dtype=float)


def run_experiments() -> None:
    print("=" * 80)
    print("TASK 011: RUNNING CLIMATOLOGY-FIRST VALIDATION EXPERIMENTS")
    print("=" * 80)

    train_df, _, _, _ = load_data(DATA_DIR)
    hist_2024 = load_2024_history(DATA_DIR / "AdditionalHistory.zip")

    # Grid mapping for quick lookup
    grid = train_df.set_index(["location_id", "target_start"])[["pm25"]].sort_index()
    station_train_series = {
        int(sid): grid.xs(sid, level="location_id")["pm25"]
        for sid in TARGET_STATIONS
    }

    folds = get_standard_9_folds(train_df)
    clim_estimator = KernelClimatology(sigma_doy=10.0, sigma_hour=1.0, clim_gap_days=14, min_weight=5.0)

    all_val_records = []
    ridge_bucket_stats = []

    print("\n--- Evaluating 9 Folds across Models ---")
    for f_idx, f_info in enumerate(folds):
        fid = f_info["fold_id"]
        regime = f_info["regime"]
        t_start = f_info["target_start"]
        cutoff = f_info["cutoff"]
        print(f"Fold [{f_idx + 1}/9]: {fid} ({regime})...")

        # 1. Build validation targets (unmodified raw labels)
        target_hours = pd.date_range(t_start, periods=48, freq="h")
        val_rows = []
        for sid in TARGET_STATIONS:
            s_s = station_train_series[sid]
            for h_idx, t in enumerate(target_hours, start=1):
                y_val = s_s.loc[t] if t in s_s.index else np.nan
                # Calculate lead hours relative to cutoff (or last observation)
                lead_h = int((t - cutoff).total_seconds() / 3600.0)
                val_rows.append({
                    "fold_id": fid,
                    "regime": regime,
                    "location_id": sid,
                    "target_start": t,
                    "horizon_hours": h_idx,
                    "lead_hours": lead_h,
                    "y": y_val,
                })

        val_df = pd.DataFrame(val_rows).dropna(subset=["y"]).reset_index(drop=True)

        # 2. Combined histories up to cutoff for target stations (timestamp_median mode)
        comb_histories = {
            sid: build_combined_history(train_df, hist_2024, sid, cutoff, archive_mode="timestamp_median")
            for sid in TARGET_STATIONS
        }

        # 3. Baselines: Persistence, Station-Hour, 72h Median
        p_persistence = []
        p_hour_clim = []
        p_72_median = []

        for r in val_df.itertuples(index=False):
            sid = r.location_id
            t_tar = r.target_start
            h_df = comb_histories[sid]
            # Prior observations strictly before cutoff
            prior = h_df.loc[h_df["timestamp"] <= cutoff]

            # 3a. Persistence (last observed value before cutoff)
            if not prior.empty:
                last_v = float(prior["pm25"].iloc[-1])
            else:
                last_v = 40.0
            p_persistence.append(max(0.0, last_v))

            # 3b. Station-Hour Climatology (simple empirical mean by station and hour)
            same_hr = prior.loc[prior["timestamp"].dt.hour == t_tar.hour, "pm25"]
            if len(same_hr) > 0:
                p_sh = float(same_hr.mean())
            else:
                p_sh = float(prior["pm25"].mean()) if not prior.empty else 40.0
            p_hour_clim.append(max(0.0, p_sh))

            # 3c. 72h Station Median
            w72 = prior.loc[prior["timestamp"] >= cutoff - pd.Timedelta(hours=72), "pm25"]
            if len(w72) > 0:
                p_m72 = float(w72.median())
            else:
                p_m72 = float(prior["pm25"].median()) if not prior.empty else 40.0
            p_72_median.append(max(0.0, p_m72))

        val_df["pred_persistence"] = p_persistence
        val_df["pred_hour_clim"] = p_hour_clim
        val_df["pred_72_median"] = p_72_median

        # 4. Model A: Kernel Climatology
        val_features = []
        for sid in TARGET_STATIONS:
            s_val = val_df.loc[val_df["location_id"] == sid]
            if s_val.empty:
                continue
            h_df = comb_histories[sid]
            # Climatology strictly with 14-day gap
            elig_clim = clim_estimator._extract_eligible_history(h_df, cutoff)
            clim_res = clim_estimator.estimate_batch(elig_clim, list(s_val["target_start"]))
            anom = extract_recent_anomalies(h_df, cutoff, clim_estimator, window_hours=168)

            for (_, row), cres in zip(s_val.iterrows(), clim_res):
                c_val = cres["clim_prediction"]
                t_tar = row["target_start"]
                lead_h = row["lead_hours"]
                val_features.append({
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

        val_feat_df = pd.DataFrame(val_features).sort_values("index").reset_index(drop=True)
        val_df["pred_clim"] = val_feat_df["clim"].values

        # 5. Build Training Samples for Model B (Ridge) and Model C (LightGBM)
        X_tr, y_tr_res = build_training_samples_for_fold(
            comb_histories,
            cutoff,
            clim_estimator,
            min_train_history_days=90,
            origin_step_hours=48,
            lead_min=41,
            lead_max=90,
        )

        # 6. Fit Model B: LeadBucketRidge
        ridge_model = LeadBucketRidge(n_buckets=5, alpha=100.0, feature_cols=["a24", "a72", "a168"])
        if len(X_tr) >= 50:
            ridge_model.fit(X_tr, y_tr_res, lead_col="lead_hours")
            res_pred_ridge = ridge_model.predict(val_feat_df, lead_col="lead_hours")
            for b_stat in ridge_model.bucket_stats_:
                b_stat["fold_id"] = fid
                ridge_bucket_stats.append(b_stat)
        else:
            res_pred_ridge = np.zeros(len(val_df))

        val_df["pred_ridge"] = np.maximum(0.0, val_df["pred_clim"] + res_pred_ridge)

        # 7. Fit Model C: LightGBM Residual (3 seeds)
        lgbm_model = LightGBMResidualModel(seeds=(42, 123, 999), num_leaves=8, min_child_samples=300, n_estimators=300)
        if len(X_tr) >= 100:
            lgbm_model.fit(X_tr, y_tr_res)
            res_pred_lgbm = lgbm_model.predict(val_feat_df)
        else:
            res_pred_lgbm = np.zeros(len(val_df))

        val_df["pred_lgbm"] = np.maximum(0.0, val_df["pred_clim"] + res_pred_lgbm)

        all_val_records.append(val_df)

    full_oof = pd.concat(all_val_records, ignore_index=True)
    print(f"\nTotal OOF Validation Rows across 9 folds: {len(full_oof)}")

    # 8. Model D: Climatology Blend with Temporally Separated (Leave-One-Fold-Out) Weights
    print("\nFitting Leave-One-Fold-Out Blends...")
    oof_blend_preds = np.zeros(len(full_oof))
    fold_blend_weights = []

    for fid in full_oof["fold_id"].unique():
        train_mask = full_oof["fold_id"] != fid
        val_mask = full_oof["fold_id"] == fid

        f_tr = full_oof[train_mask]
        f_val = full_oof[val_mask]

        blender = ClimatologyBlend(step=0.1)
        blender.fit(
            y_true=f_tr["y"].to_numpy(),
            p_clim=f_tr["pred_clim"].to_numpy(),
            p_ridge=f_tr["pred_ridge"].to_numpy(),
            p_lgbm=f_tr["pred_lgbm"].to_numpy(),
        )

        fold_blend_weights.append({
            "test_fold": fid,
            "w_clim": blender.weights_["clim"],
            "w_ridge": blender.weights_["ridge"],
            "w_lgbm": blender.weights_["lgbm"],
        })

        pred_val = blender.predict(
            p_clim=f_val["pred_clim"].to_numpy(),
            p_ridge=f_val["pred_ridge"].to_numpy(),
            p_lgbm=f_val["pred_lgbm"].to_numpy(),
        )
        oof_blend_preds[val_mask] = pred_val

    full_oof["pred_blend"] = oof_blend_preds

    # 9. Source Series Sensitivity Analysis across Borivali and Malad
    print("\n--- Running Source Series Sensitivity Analysis ---")
    source_modes = [
        ("p_fix", "P_FIX (Borivali: site_5400, Malad: site_5102/5402)"),
        ("series_5113_5102", "Series 5113 & 5102 (IITM Primary)"),
        ("series_5400_5402", "Series 5400 & 5402 (Secondary)"),
        ("equal_weight", "Equal-weight Overlapping Average"),
        ("timestamp_median", "Timestamp Median Overlapping"),
        ("train_only", "Train-only (No 2024 Archive)"),
    ]

    source_records = []
    for mode_key, mode_desc in source_modes:
        mode_preds = []
        for fid in folds:
            f_oof = full_oof[full_oof["fold_id"] == fid["fold_id"]]
            comb_histories = {
                sid: build_combined_history(train_df, hist_2024, sid, fid["cutoff"], archive_mode=mode_key)
                for sid in TARGET_STATIONS
            }
            for sid in TARGET_STATIONS:
                s_val = f_oof[f_oof["location_id"] == sid]
                if s_val.empty:
                    continue
                h_df = comb_histories[sid]
                elig = clim_estimator._extract_eligible_history(h_df, fid["cutoff"])
                c_res = clim_estimator.estimate_batch(elig, list(s_val["target_start"]))
                for (_, row), r in zip(s_val.iterrows(), c_res):
                    mode_preds.append({
                        "mode": mode_key,
                        "fold_id": fid["fold_id"],
                        "regime": fid["regime"],
                        "location_id": sid,
                        "target_start": row["target_start"],
                        "y": row["y"],
                        "pred": r["clim_prediction"],
                    })

        mode_df = pd.DataFrame(mode_preds)
        y_all = mode_df["y"].to_numpy()
        p_all = mode_df["pred"].to_numpy()
        rmse_all = root_mean_squared_error(y_all, p_all)

        autumn = mode_df[mode_df["regime"] == "monsoon_autumn"]
        rmse_aut = root_mean_squared_error(autumn["y"], autumn["pred"]) if not autumn.empty else np.nan

        winter = mode_df[mode_df["regime"] == "winter_transition"]
        rmse_win = root_mean_squared_error(winter["y"], winter["pred"]) if not winter.empty else np.nan

        source_records.append({
            "source_mode": mode_key,
            "description": mode_desc,
            "pooled_rmse": round(rmse_all, 3),
            "autumn_rmse": round(rmse_aut, 3),
            "winter_rmse": round(rmse_win, 3),
            "row_count": len(mode_df),
        })

    source_df = pd.DataFrame(source_records)
    print("\nSource Series Sensitivity Results:")
    print(source_df.to_string(index=False))

    # 10. Generate Validation Deliverables and Metrics
    print("\n--- Summary Performance Across Models ---")
    models = [
        ("Persistence Baseline", "pred_persistence"),
        ("Station-Hour Baseline", "pred_hour_clim"),
        ("72h Station Median Baseline", "pred_72_median"),
        ("Model A: Kernel Climatology", "pred_clim"),
        ("Model B: Lead-Bucket Ridge", "pred_ridge"),
        ("Model C: LightGBM Residual", "pred_lgbm"),
        ("Model D: OOF Climatology Blend", "pred_blend"),
    ]

    summary_rows = []
    y_true = full_oof["y"].to_numpy()
    aut_mask = full_oof["regime"] == "monsoon_autumn"
    win_mask = full_oof["regime"] == "winter_transition"

    for m_label, col in models:
        p = full_oof[col].to_numpy()
        rmse_pool = root_mean_squared_error(y_true, p)
        mae_pool = mean_absolute_error(y_true, p)
        rmse_aut = root_mean_squared_error(y_true[aut_mask], p[aut_mask])
        rmse_win = root_mean_squared_error(y_true[win_mask], p[win_mask])
        bias_pool = float(np.mean(p - y_true))

        # Station-level RMSE
        st_rmses = {}
        for sid in TARGET_STATIONS:
            s_mask = full_oof["location_id"] == sid
            st_rmses[f"rmse_{sid}"] = round(root_mean_squared_error(y_true[s_mask], p[s_mask]), 2)

        row = {
            "model": m_label,
            "pooled_rmse": round(rmse_pool, 3),
            "pooled_mae": round(mae_pool, 3),
            "monsoon_autumn_rmse": round(rmse_aut, 3),
            "winter_rmse": round(rmse_win, 3),
            "pooled_bias": round(bias_pool, 3),
            **st_rmses,
        }
        summary_rows.append(row)

    summary_df = pd.DataFrame(summary_rows)
    print(summary_df.to_string(index=False))

    # 11. Block Bootstrap Analysis (10,000 resamples over fold blocks)
    print("\n--- Running 10,000-Resample Block Bootstrap ---")
    rng = np.random.default_rng(42)
    n_resamples = 10000
    unique_folds = full_oof["fold_id"].unique()
    n_folds = len(unique_folds)

    # Pre-index folds for fast sampling
    fold_indices = {fid: np.where(full_oof["fold_id"] == fid)[0] for fid in unique_folds}

    bootstrap_results = []
    clim_pred = full_oof["pred_clim"].to_numpy()

    for m_label, col in models[4:]:  # Evaluate Ridge, LightGBM, Blend vs Climatology
        cand_pred = full_oof[col].to_numpy()
        diffs = []
        for _ in range(n_resamples):
            sampled_fids = rng.choice(unique_folds, size=n_folds, replace=True)
            sampled_idx = np.concatenate([fold_indices[f] for f in sampled_fids])

            y_b = y_true[sampled_idx]
            cand_b = cand_pred[sampled_idx]
            clim_b = clim_pred[sampled_idx]

            rmse_cand = root_mean_squared_error(y_b, cand_b)
            rmse_clim = root_mean_squared_error(y_b, clim_b)
            diffs.append(rmse_cand - rmse_clim)

        diffs = np.array(diffs)
        ci_lower = float(np.percentile(diffs, 2.5))
        ci_upper = float(np.percentile(diffs, 97.5))
        mean_diff = float(np.mean(diffs))

        bootstrap_results.append({
            "candidate_model": m_label,
            "mean_rmse_diff_vs_clim": round(mean_diff, 3),
            "ci_95_lower": round(ci_lower, 3),
            "ci_95_upper": round(ci_upper, 3),
            "excludes_zero": bool(ci_upper < 0 or ci_lower > 0),
            "statistically_significant": bool(ci_upper < 0),
        })

    boot_df = pd.DataFrame(bootstrap_results)
    print("\nBlock Bootstrap 95% Confidence Intervals (Candidate - Climatology):")
    print(boot_df.to_string(index=False))

    # 12. Fold-Level Breakdown Table
    fold_level_records = []
    for fid in unique_folds:
        f_sub = full_oof[full_oof["fold_id"] == fid]
        f_y = f_sub["y"].to_numpy()
        regime = f_sub["regime"].iloc[0]
        f_row = {"fold_id": fid, "regime": regime, "row_count": len(f_sub)}
        for m_label, col in models:
            f_row[m_label] = round(root_mean_squared_error(f_y, f_sub[col].to_numpy()), 3)
        fold_level_records.append(f_row)

    fold_df = pd.DataFrame(fold_level_records)

    # 13. Export Deliverables
    print("\nExporting deliverable CSVs and OOF files...")
    # Model A: Climatology validation
    clim_summary = summary_df[summary_df["model"].isin([
        "Persistence Baseline", "Station-Hour Baseline", "72h Station Median Baseline", "Model A: Kernel Climatology"
    ])]
    clim_summary.to_csv(REPORTS_DIR / "climatology_validation.csv", index=False)

    # Model B: Ridge Anomaly validation
    ridge_summary = summary_df[summary_df["model"].isin([
        "Model A: Kernel Climatology", "Model B: Lead-Bucket Ridge"
    ])]
    ridge_summary.to_csv(REPORTS_DIR / "ridge_anomaly_validation.csv", index=False)

    # Model C: LightGBM Residual validation
    lgbm_summary = summary_df[summary_df["model"].isin([
        "Model A: Kernel Climatology", "Model C: LightGBM Residual"
    ])]
    lgbm_summary.to_csv(REPORTS_DIR / "lightgbm_residual_validation.csv", index=False)

    # Model D: Blend validation
    blend_summary = summary_df[summary_df["model"].isin([
        "Model A: Kernel Climatology", "Model B: Lead-Bucket Ridge", "Model C: LightGBM Residual", "Model D: OOF Climatology Blend"
    ])]
    blend_summary.to_csv(REPORTS_DIR / "blend_validation.csv", index=False)

    # Fold level metrics
    fold_df.to_csv(REPORTS_DIR / "fold_level_metrics.csv", index=False)

    # Source series comparison
    source_df.to_csv(REPORTS_DIR / "source_series_validation.csv", index=False)

    # Ridge bucket statistics
    if ridge_bucket_stats:
        pd.DataFrame(ridge_bucket_stats).to_csv(REPORTS_DIR / "ridge_bucket_coefficients.csv", index=False)

    # Bootstrap metrics
    boot_df.to_csv(REPORTS_DIR / "bootstrap_climatology_diffs.csv", index=False)

    # OOF predictions
    oof_export = full_oof[[
        "fold_id", "regime", "location_id", "target_start", "horizon_hours", "lead_hours",
        "y", "pred_persistence", "pred_hour_clim", "pred_72_median",
        "pred_clim", "pred_ridge", "pred_lgbm", "pred_blend"
    ]]
    oof_export.to_csv(REPORTS_DIR / "oof_predictions.csv.gz", index=False, compression="gzip")

    print("\nAll deliverables exported successfully to reports/ directory!")


if __name__ == "__main__":
    run_experiments()
