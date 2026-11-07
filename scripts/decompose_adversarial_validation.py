"""Adversarial validation decomposition across feature subsets and historical controls.

Evaluates:
- Experiment A: Calendar-only features
- Experiment B: Pollution-state-only features
- Experiment C: All features combined
Across two evaluation baselines:
1. Seasonal Shift: Historical monsoon/autumn validation blocks vs Nov 2026 Private Window.
2. Matched Seasonal Control: Historical Nov 2025 control (identical calendar days) vs Nov 2026 Private Window.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from mumbai_pm25.data import load_data
from mumbai_pm25.features.pipeline import build_feature_matrix
from mumbai_pm25.historical_archive import load_2024_history
from mumbai_pm25.validation import generate_fixed_target_folds

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "raw" / "challenge"
REPORTS_DIR = ROOT / "reports"


def run_adversarial_decomposition(
    data_dir: Path = DATA_DIR,
    reports_dir: Path = REPORTS_DIR,
) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    print("=" * 75)
    print("RUNNING ADVERSARIAL VALIDATION DECOMPOSITION")
    print("=" * 75)

    train, test, _, _ = load_data(data_dir)
    hist_2024 = load_2024_history(data_dir / "AdditionalHistory.zip")
    grid = train.set_index(["location_id", "target_start"])[["pm25"]].sort_index()
    station_histories = {
        int(sid): grid.xs(sid, level="location_id")["pm25"]
        for sid in train["location_id"].unique()
    }

    # 1. Private Target Window (Nov 11-12, 2026, n=192)
    nov26_start = pd.Timestamp("2026-11-11 00:00:00", tz="Asia/Kolkata")
    nov26_end = pd.Timestamp("2026-11-12 23:00:00", tz="Asia/Kolkata")
    priv_test = test[(test.target_start >= nov26_start) & (test.target_start <= nov26_end)].copy()
    priv_test["horizon_hours"] = (
        (priv_test["target_start"] - nov26_start).dt.total_seconds() / 3600.0 + 1.0
    ).astype(int)
    cutoff_26 = pd.Timestamp("2026-11-02 23:00:00", tz="Asia/Kolkata")
    X_priv26 = build_feature_matrix(
        station_histories, priv_test, cutoff_26, history_2024=hist_2024, include_seasonal=True, include_spatial=True
    )

    # 2. Historical Monsoon/Autumn Validation Blocks (Folds 24-28, n=690)
    folds = generate_fixed_target_folds(
        train, gap_hours=48, horizon_hours=48, step_days=21, holdout_hours=48
    )
    selected_indices = list(range(len(folds) - 5, len(folds)))
    val_dfs = []
    for idx in selected_indices:
        f = folds[idx]
        target_hours = pd.date_range(f.target_start, periods=48, freq="h")
        rows = []
        for sid in [11606, 11611, 3409510, 3409511]:
            s_series = station_histories[sid]
            for h_idx, t in enumerate(target_hours, start=1):
                if t in s_series.index and pd.notna(s_series.loc[t]):
                    rows.append({"location_id": sid, "target_start": t, "horizon_hours": h_idx})
        tdf = pd.DataFrame(rows)
        X_val_f = build_feature_matrix(
            station_histories, tdf, f.pm_history_cutoff, history_2024=hist_2024, include_seasonal=True, include_spatial=True
        )
        val_dfs.append(X_val_f)
    X_hist_monsoon = pd.concat(val_dfs, ignore_index=True)

    # 3. Matched November 2025 Historical Control (Nov 11-12, 2025, n=192)
    nov25_start = pd.Timestamp("2025-11-11 00:00:00", tz="Asia/Kolkata")
    nov25_end = pd.Timestamp("2025-11-12 23:00:00", tz="Asia/Kolkata")
    cutoff_25 = pd.Timestamp("2025-11-02 23:00:00", tz="Asia/Kolkata")
    rows_25 = []
    for sid in [11606, 11611, 3409510, 3409511]:
        for t in pd.date_range(nov25_start, nov25_end, freq="h"):
            rows_25.append({
                "location_id": sid,
                "target_start": t,
                "horizon_hours": int((t - nov25_start).total_seconds() / 3600.0 + 1.0),
            })
    df_nov25 = pd.DataFrame(rows_25)
    X_hist_nov25 = build_feature_matrix(
        station_histories, df_nov25, cutoff_25, history_2024=hist_2024, include_seasonal=True, include_spatial=True
    )

    # Define Feature Subsets
    calendar_cols = [
        "hour", "weekday", "month", "day_of_year", "hour_sin", "hour_cos",
        "weekday_sin", "weekday_cos", "doy_sin", "doy_cos", "horizon_hours",
        "station_id", "station_11606", "station_11611", "station_3409510", "station_3409511"
    ]
    pollution_state_cols = [
        c for c in X_priv26.columns
        if c not in calendar_cols and not c.startswith("hist24") and c not in ["target_start", "target_end"]
    ]
    all_feature_cols = [
        c for c in X_priv26.columns if c not in ["target_start", "target_end"]
    ]

    feature_subsets = [
        ("Experiment A: Calendar-Only", calendar_cols),
        ("Experiment B: Pollution-State-Only", pollution_state_cols),
        ("Experiment C: All Features", all_feature_cols),
    ]

    comparisons = [
        ("Monsoon/Autumn (Aug-Oct 2026) vs Nov 2026 Private Window", X_hist_monsoon, X_priv26),
        ("Matched November 2025 Control vs Nov 2026 Private Window", X_hist_nov25, X_priv26),
    ]

    results = []

    for comp_name, X_h, X_t in comparisons:
        print(f"\n--- Comparison: {comp_name} ---")
        for exp_name, cols in feature_subsets:
            valid_cols = [c for c in cols if c in X_h.columns and c in X_t.columns]
            X_adv = pd.concat([X_h[valid_cols], X_t[valid_cols]], ignore_index=True)
            y_adv = np.array([0] * len(X_h) + [1] * len(X_t))

            clf = lgb.LGBMClassifier(
                n_estimators=100, learning_rate=0.05, random_state=42, verbose=-1, n_jobs=1
            )
            clf.fit(X_adv, y_adv)
            probs = clf.predict_proba(X_adv)[:, 1]
            auc = float(roc_auc_score(y_adv, probs))

            imp = pd.Series(clf.feature_importances_, index=valid_cols).sort_values(ascending=False)
            top_3 = ", ".join(f"{f} ({s})" for f, s in imp.head(3).items())

            results.append({
                "comparison": comp_name,
                "experiment": exp_name,
                "feature_count": len(valid_cols),
                "roc_auc": round(auc, 4),
                "top_discriminative_features": top_3,
            })
            print(f"  {exp_name:<36} | Features: {len(valid_cols):>2} | ROC-AUC: {auc:.4f} | Top: {top_3}")

    df_res = pd.DataFrame(results)
    df_res.to_csv(reports_dir / "adversarial_validation_decomposition.csv", index=False)
    print(f"\nSaved {reports_dir / 'adversarial_validation_decomposition.csv'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR)
    parser.add_argument("--reports-dir", type=Path, default=REPORTS_DIR)
    args = parser.parse_args()
    run_adversarial_decomposition(data_dir=args.data_dir, reports_dir=args.reports_dir)
