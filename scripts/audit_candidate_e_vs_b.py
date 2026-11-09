"""Targeted evaluation of Candidate E vs Candidate B and Candidate C.

Uses identical chronological out-of-fold predictions across all 9 folds (N=1460).
Calculates:
  - Paired RMSE differences
  - Per-fold comparison
  - Per-station comparison
  - Regime comparison (Monsoon/Autumn vs Winter)
  - Residual correlations
  - Blends: C+B, C+E, E+B
  - Block bootstrap (by fold, 10,000 iterations) with 95% CIs and win probabilities.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, root_mean_squared_error

ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"


def main() -> None:
    print("=" * 80)
    print("TASK 010: CANDIDATE E VS CANDIDATE B AND CANDIDATE C COMPREHENSIVE AUDIT")
    print("=" * 80)

    # Load the 9-fold predictions from clipping audit
    df = pd.read_csv(REPORTS_DIR / "clipping_audit_predictions.csv.gz")
    print(f"Loaded {len(df)} evaluation rows across {df['fold_id'].nunique()} folds.")

    y_true = df["y"].values
    cand_c = df["cand_c"].values
    cand_b = df["cand_b"].values
    cand_e = df["blend_e_unclipped"].values
    cand_e_clip = df["blend_e_clipped_500"].values

    models = {
        "Candidate C (Statistical Seasonal)": cand_c,
        "Candidate B (50% CatBoost log1p + 50% Cand C)": cand_b,
        "Candidate E (50% CatBoost Residual + 50% Cand C)": cand_e,
        "Candidate E (Clipped 500 Residual + 50% Cand C)": cand_e_clip,
    }

    # 1. Overall Summary Table
    print("\n1. OVERALL METRIC SUMMARY (N=1460 across 9 folds):")
    summary_rows = []
    for name, pred in models.items():
        rmse = root_mean_squared_error(y_true, pred)
        mae = mean_absolute_error(y_true, pred)
        bias = float(np.mean(pred - y_true))

        aut_mask = df["regime"] == "monsoon_autumn"
        wint_mask = df["regime"] == "winter_transition"
        clean_mask = df["y"] < 50.0
        high_mask = df["y"] >= 100.0

        rmse_aut = root_mean_squared_error(y_true[aut_mask], pred[aut_mask])
        rmse_wint = root_mean_squared_error(y_true[wint_mask], pred[wint_mask])
        rmse_clean = root_mean_squared_error(y_true[clean_mask], pred[clean_mask])
        rmse_high = root_mean_squared_error(y_true[high_mask], pred[high_mask])

        summary_rows.append({
            "Candidate": name,
            "Pooled RMSE": rmse,
            "Autumn RMSE": rmse_aut,
            "Winter RMSE": rmse_wint,
            "Clean RMSE (<50)": rmse_clean,
            "High RMSE (>=100)": rmse_high,
            "MAE": mae,
            "Mean Bias": bias,
        })
    sum_df = pd.DataFrame(summary_rows)
    print(sum_df.to_string(index=False))

    # 2. Residual Correlation Matrix
    print("\n2. RESIDUAL CORRELATIONS (y_true - y_pred):")
    resids = pd.DataFrame({
        "Cand C": y_true - cand_c,
        "Cand B": y_true - cand_b,
        "Cand E": y_true - cand_e,
        "Cand E (Clip500)": y_true - cand_e_clip,
    })
    corr = resids.corr()
    print(corr.to_string())

    # 3. Blends of Candidates: C+B, C+E, E+B
    print("\n3. HYBRID BLENDS OF CANDIDATES:")
    hybrid_blends = {
        "Blend: 50% C + 50% B": 0.50 * cand_c + 0.50 * cand_b,
        "Blend: 70% C + 30% B": 0.70 * cand_c + 0.30 * cand_b,
        "Blend: 50% C + 50% E": 0.50 * cand_c + 0.50 * cand_e,
        "Blend: 50% E + 50% B": 0.50 * cand_e + 0.50 * cand_b,
        "Blend: 40% C + 30% B + 30% E": 0.40 * cand_c + 0.30 * cand_b + 0.30 * cand_e,
    }
    hybrid_rows = []
    for h_name, h_pred in hybrid_blends.items():
        rmse = root_mean_squared_error(y_true, h_pred)
        mae = mean_absolute_error(y_true, h_pred)
        wint_rmse = root_mean_squared_error(y_true[df["regime"] == "winter_transition"], h_pred[df["regime"] == "winter_transition"])
        aut_rmse = root_mean_squared_error(y_true[df["regime"] == "monsoon_autumn"], h_pred[df["regime"] == "monsoon_autumn"])
        hybrid_rows.append({
            "Hybrid Blend": h_name,
            "Pooled RMSE": rmse,
            "Autumn RMSE": aut_rmse,
            "Winter RMSE": wint_rmse,
            "MAE": mae,
        })
    hybrid_df = pd.DataFrame(hybrid_rows).sort_values("Pooled RMSE")
    print(hybrid_df.to_string(index=False))

    # 4. Per Station Comparison
    print("\n4. PER-STATION RMSE BREAKDOWN:")
    st_records = []
    for sid, group in df.groupby("location_id"):
        y_st = group["y"].values
        st_records.append({
            "location_id": sid,
            "N": len(group),
            "RMSE (Cand C)": root_mean_squared_error(y_st, group["cand_c"].values),
            "RMSE (Cand B)": root_mean_squared_error(y_st, group["cand_b"].values),
            "RMSE (Cand E)": root_mean_squared_error(y_st, group["blend_e_unclipped"].values),
            "RMSE (Cand E Clip)": root_mean_squared_error(y_st, group["blend_e_clipped_500"].values),
        })
    st_df = pd.DataFrame(st_records)
    print(st_df.to_string(index=False))

    # 5. Per Fold Comparison
    print("\n5. PER-FOLD RMSE BREAKDOWN:")
    fold_records = []
    for fid, group in df.groupby("fold_id", sort=False):
        y_f = group["y"].values
        fold_records.append({
            "fold_id": fid,
            "regime": group["regime"].iloc[0],
            "N": len(group),
            "RMSE (Cand C)": root_mean_squared_error(y_f, group["cand_c"].values),
            "RMSE (Cand B)": root_mean_squared_error(y_f, group["cand_b"].values),
            "RMSE (Cand E)": root_mean_squared_error(y_f, group["blend_e_unclipped"].values),
            "RMSE (Cand E Clip)": root_mean_squared_error(y_f, group["blend_e_clipped_500"].values),
        })
    f_df = pd.DataFrame(fold_records)
    print(f_df.to_string(index=False))

    # 6. Block Bootstrap by Fold (10,000 iterations)
    print("\n6. CLUSTER / BLOCK BOOTSTRAP BY FOLD (10,000 resamples):")
    unique_folds = df["fold_id"].unique()
    n_folds = len(unique_folds)

    diff_CB = []  # RMSE(C) - RMSE(B) -> negative means C is better
    diff_CE = []  # RMSE(C) - RMSE(E) -> positive means E is better
    diff_BE = []  # RMSE(B) - RMSE(E) -> positive means E is better

    rng = np.random.default_rng(42)
    fold_groups = {fid: df[df["fold_id"] == fid] for fid in unique_folds}

    for _ in range(10000):
        sampled_fids = rng.choice(unique_folds, size=n_folds, replace=True)
        boot_df = pd.concat([fold_groups[fid] for fid in sampled_fids], ignore_index=True)
        y_b = boot_df["y"].values

        rmse_c = root_mean_squared_error(y_b, boot_df["cand_c"].values)
        rmse_b = root_mean_squared_error(y_b, boot_df["cand_b"].values)
        rmse_e = root_mean_squared_error(y_b, boot_df["blend_e_unclipped"].values)

        diff_CB.append(rmse_c - rmse_b)
        diff_CE.append(rmse_c - rmse_e)
        diff_BE.append(rmse_b - rmse_e)

    diff_CB = np.array(diff_CB)
    diff_CE = np.array(diff_CE)
    diff_BE = np.array(diff_BE)

    print(f"C vs B: mean delta RMSE = {np.mean(diff_CB):+.3f}, 95% CI = [{np.percentile(diff_CB, 2.5):+.3f}, {np.percentile(diff_CB, 97.5):+.3f}], Prob(C < B) = {np.mean(diff_CB < 0) * 100:.1f}%")
    print(f"E vs C: mean delta RMSE (RMSE_C - RMSE_E) = {np.mean(diff_CE):+.3f}, 95% CI = [{np.percentile(diff_CE, 2.5):+.3f}, {np.percentile(diff_CE, 97.5):+.3f}], Prob(E < C) = {np.mean(diff_CE > 0) * 100:.1f}%")
    print(f"E vs B: mean delta RMSE (RMSE_B - RMSE_E) = {np.mean(diff_BE):+.3f}, 95% CI = [{np.percentile(diff_BE, 2.5):+.3f}, {np.percentile(diff_BE, 97.5):+.3f}], Prob(E < B) = {np.mean(diff_BE > 0) * 100:.1f}%")

    # Save results to reports
    sum_df.to_csv(REPORTS_DIR / "candidate_E_vs_B_metrics.csv", index=False)
    corr.to_csv(REPORTS_DIR / "candidate_E_vs_B_correlations.csv")
    hybrid_df.to_csv(REPORTS_DIR / "candidate_E_vs_B_hybrids.csv", index=False)
    st_df.to_csv(REPORTS_DIR / "candidate_E_vs_B_stations.csv", index=False)
    f_df.to_csv(REPORTS_DIR / "candidate_E_vs_B_folds.csv", index=False)
    print("\nSaved all comparison tables to reports/candidate_E_vs_B_*.csv")


if __name__ == "__main__":
    main()
