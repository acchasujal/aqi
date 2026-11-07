"""Detailed inspection and analysis of the 192 private prediction slots in Candidate A and Candidate B.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from mumbai_pm25.data import load_data
from mumbai_pm25.historical_archive import (
    STATION_NAME_MAP,
    build_seasonal_features,
    load_2024_history,
)

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "raw" / "challenge"
SUB_DIR = ROOT / "artifacts" / "submissions"


def main() -> None:
    train, test, _, _ = load_data(DATA_DIR)
    hist_2024 = load_2024_history(DATA_DIR / "AdditionalHistory.zip")

    sub_a = pd.read_csv(SUB_DIR / "submission_A_accuracy_ensemble.csv")
    sub_b = pd.read_csv(SUB_DIR / "submission_B_robust_ensemble.csv")

    # Merge with test metadata
    test_meta = test.copy()
    test_meta["pred_a"] = sub_a["Target"]
    test_meta["pred_b"] = sub_b["Target"]
    test_meta["diff_b_minus_a"] = test_meta["pred_b"] - test_meta["pred_a"]

    # Filter to 192 private evaluation rows
    priv_mask = (test_meta["target_start"] >= pd.Timestamp("2026-11-11 00:00:00", tz="Asia/Kolkata")) & \
                (test_meta["target_start"] <= pd.Timestamp("2026-11-12 23:00:00", tz="Asia/Kolkata"))
    priv_df = test_meta[priv_mask].copy().sort_values(["location_id", "target_start"])

    print(f"Total private slots identified: {len(priv_df)} (expected 192: 4 stations x 48 hours)")

    # 2024 Seasonal Prior for private window
    seas_priv = build_seasonal_features(
        hist_2024,
        priv_df[["location_id", "target_start"]],
        station_map=STATION_NAME_MAP,
        window_days=14,
        min_obs=3,
    )
    priv_df["seasonal_2024"] = seas_priv["hist24_same_hour_mean"].to_numpy()

    # Recent PM baseline from latest available train observations (72h median up to 2026-11-02 23:00)
    cutoff = pd.Timestamp("2026-11-02 23:00:00", tz="Asia/Kolkata")
    recent_medians = {}
    for sid in [11606, 11611, 3409510, 3409511]:
        s_data = train[(train["location_id"] == sid) & (train["target_start"] < cutoff)]
        w = s_data[s_data["target_start"] >= cutoff - pd.Timedelta(hours=72)]
        recent_medians[sid] = float(w["pm25"].median())
    priv_df["recent_baseline_median72"] = priv_df["location_id"].map(recent_medians)

    # Per-station distribution summary
    print("\n--- PER-STATION DISTRIBUTION SUMMARY (PRIVATE 192 SLOTS) ---")
    st_rows = []
    for sid in [11606, 11611, 3409510, 3409511]:
        s_part = priv_df[priv_df["location_id"] == sid]
        st_rows.append({
            "location_id": sid,
            "recent_median72": recent_medians[sid],
            "seasonal_mean": round(s_part["seasonal_2024"].mean(), 2),
            "cand_a_mean": round(s_part["pred_a"].mean(), 2),
            "cand_a_std": round(s_part["pred_a"].std(), 2),
            "cand_a_min": round(s_part["pred_a"].min(), 2),
            "cand_a_median": round(s_part["pred_a"].median(), 2),
            "cand_a_p90": round(s_part["pred_a"].quantile(0.9), 2),
            "cand_a_max": round(s_part["pred_a"].max(), 2),
            "cand_b_mean": round(s_part["pred_b"].mean(), 2),
            "cand_b_std": round(s_part["pred_b"].std(), 2),
            "cand_b_min": round(s_part["pred_b"].min(), 2),
            "cand_b_median": round(s_part["pred_b"].median(), 2),
            "cand_b_p90": round(s_part["pred_b"].quantile(0.9), 2),
            "cand_b_max": round(s_part["pred_b"].max(), 2),
            "mean_b_minus_a": round(s_part["diff_b_minus_a"].mean(), 2),
        })
    df_st_summary = pd.DataFrame(st_rows)
    print(df_st_summary.to_string(index=False))

    # Overall Summary
    print("\n--- OVERALL 192 PRIVATE SLOTS SUMMARY ---")
    print(f"Candidate A: Mean={priv_df['pred_a'].mean():.2f}, Std={priv_df['pred_a'].std():.2f}, Min={priv_df['pred_a'].min():.2f}, Median={priv_df['pred_a'].median():.2f}, P90={priv_df['pred_a'].quantile(0.9):.2f}, Max={priv_df['pred_a'].max():.2f}")
    print(f"Candidate B: Mean={priv_df['pred_b'].mean():.2f}, Std={priv_df['pred_b'].std():.2f}, Min={priv_df['pred_b'].min():.2f}, Median={priv_df['pred_b'].median():.2f}, P90={priv_df['pred_b'].quantile(0.9):.2f}, Max={priv_df['pred_b'].max():.2f}")
    print(f"2024 Seasonal Prior: Mean={priv_df['seasonal_2024'].mean():.2f}, Std={priv_df['seasonal_2024'].std():.2f}, Min={priv_df['seasonal_2024'].min():.2f}, Max={priv_df['seasonal_2024'].max():.2f}")
    print(f"Recent Baseline: Mean={priv_df['recent_baseline_median72'].mean():.2f}")

    # Hour of day variation
    priv_df["hour"] = priv_df["target_start"].dt.hour
    hour_summary = priv_df.groupby("hour")[["pred_a", "pred_b", "seasonal_2024"]].mean()
    print("\n--- DIURNAL PROFILE ACROSS 24 HOURS (MEANS) ---")
    print(hour_summary.round(2).to_string())

    # Divergence analysis
    print("\n--- DIVERGENCE BETWEEN CANDIDATE A AND B ---")
    print(f"Mean Difference (B - A): {priv_df['diff_b_minus_a'].mean():.2f} ug/m3")
    print(f"Max Absolute Difference: {priv_df['diff_b_minus_a'].abs().max():.2f} ug/m3")
    print(f"Correlation between A and B predictions: {priv_df['pred_a'].corr(priv_df['pred_b']):.4f}")


if __name__ == "__main__":
    main()
