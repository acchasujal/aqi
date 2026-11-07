# Google Mumbai PM2.5 Forecasting Challenge: Final Submission & System Report

## Executive Summary

This report documents the machine learning forecasting system developed for the **Google Mumbai Data Challenge: Air Quality Mapping & Forecasting by Google** hosted on Zindi.

The challenge evaluates hourly PM2.5 concentrations ($\mu\text{g}/\text{m}^3$) across four critical air quality monitoring stations in Mumbai:
- **Borivali East** (`site_5113` / `site_5400`, location ID `11606`, IITM)
- **Malad West** (`site_5102` / `site_5402`, location ID `11611`, IITM)
- **Byculla** (`site_5960`, location ID `3409510`, BMC)
- **Shivaji Nagar** (`site_5961`, location ID `3409511`, BMC)

The competition objective is to minimize **original-scale PM2.5 Root Mean Squared Error (RMSE)** on the private evaluation period (**11–12 November 2026**, 48 forecast hours $\times$ 4 stations = 192 evaluated rows).

Two final competition candidates were selected, verified, and sealed in `artifacts/submissions/`:
1. **Submission A (`submission_A_accuracy_ensemble.csv`)**: **Accuracy-Oriented Ensemble** (83% CatBoost log1p + 17% 2024 Seasonal Blend). Validation RMSE: **14.24 $\mu\text{g}/\text{m}^3$**.
2. **Submission B (`submission_B_robust_ensemble.csv`)**: **Robust Ensemble** (50% CatBoost log1p + 50% 2024 Seasonal Blend). Validation RMSE: **14.43 $\mu\text{g}/\text{m}^3$**.

Both submissions strictly comply with all challenge rules: zero future leakage, exact row alignment matching `SampleSubmission.csv` (2,592 rows), non-negative finite outputs, and cryptographic reproducibility manifests tracking all input and output SHA-256 hashes.

---

## 1. System Architecture & Methodology

```
+-------------------------------------------------------------------------------------------------------+
|                                    INFORMATION SNAPSHOT & ISOLATION                                   |
|   - Wall Clock (model_run_time): 2026-11-08T12:00:00+05:30                                            |
|   - PM Cutoff (pm_history_cutoff): 2026-11-02T23:00:00+05:30 (Max observed interval end in Train)     |
|   - Forecast Horizon: 48 to 648 hours into the future (Asia/Kolkata)                                 |
+-------------------------------------------------------------------------------------------------------+
                                                   |
                                                   v
+-------------------------------------------------------------------------------------------------------+
|                                  FEATURE EXTRACTION PIPELINE (Strict Past)                            |
|   1. Group A/B (PM History): obs_age, counts (24h/72h/168h), coverage, medians, means, trend slopes    |
|   2. Group C (Calendar): hour, dow, month, cyclical sin/cos encodings, is_weekend                     |
|   3. Group D (Seasonal Climatology): 2024 CPCB CAAQM pre-aggregated, leap-year aligned (same-hour)    |
|   4. Group E (Spatial/Network): cross-station median, network mean, station offset to network level   |
+-------------------------------------------------------------------------------------------------------+
                                                   |
                         +-------------------------+-------------------------+
                         |                                                   |
                         v                                                   v
+-------------------------------------------------+ +-------------------------------------------------+
|          CATBOOST LOG1P SUPERVISED MODEL        | |          2024 SEASONAL BLEND BASELINE           |
|   - Target transform: y_t = log1p(PM2.5)        | |   - Blend: 50% median72 + 50% hist24_same_hour  |
|   - Architecture: Depth 6, LR 0.05, 150 trees   | |   - Leap-year circular DOY alignment            |
|   - Invert: expm1(y_pred)                       | |   - IITM / BMC clean station disambiguation     |
+-------------------------------------------------+ +-------------------------------------------------+
                         |                                                   |
                         +-------------------------+-------------------------+
                                                   |
                                                   v
+-------------------------------------------------------------------------------------------------------+
|                                      SUBMISSION ARTIFACT ENSEMBLES                                    |
|   - Candidate A (Accuracy): 0.83 * CatBoost_log1p + 0.17 * Seasonal_Blend   [Val RMSE: 14.24]         |
|   - Candidate B (Robust):   0.50 * CatBoost_log1p + 0.50 * Seasonal_Blend   [Val RMSE: 14.43]         |
+-------------------------------------------------------------------------------------------------------+
```

---

## 2. Validation & Benchmark Evidence

All candidate models and baselines were evaluated on the unified **Fixed-Origin Rolling-Window Validation Protocol** across 5 historical folds spanning 2026, evaluating 960 predictions on unmodified validation ground truth.

### Model Benchmark Leaderboard

| Model / Ensemble | Full RMSE ($\mu\text{g}/\text{m}^3$) | Clean RMSE ($y < 500$) | Mean Bias ($\mu\text{g}/\text{m}^3$) | Evaluated Rows | Architecture Description |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Accuracy Ensemble (Candidate A)** | **14.24** | **14.24** | **-0.29** | 960 | 83% CatBoost log1p + 17% Seasonal Blend |
| **CatBoost (log1p)** | 14.29 | 14.29 | -0.32 | 960 | CatBoost regressor with log1p target transform |
| **Robust Ensemble (Candidate B)** | **14.43** | **14.43** | **-1.03** | 960 | 50% CatBoost log1p + 50% Seasonal Blend |
| **LightGBM (log1p)** | 15.38 | 15.38 | -1.18 | 960 | LightGBM GBDT with log1p target transform |
| **2024 Seasonal Blend (`hist24_blend50`)** | 15.65 | 15.65 | -1.74 | 960 | 50% recent median72 + 50% 2024 same-hour mean |
| **Random Forest (log1p)** | 15.66 | 15.66 | -0.99 | 960 | Random Forest (100 trees) with log1p transform |
| **Recent Median 72h (`median72`)** | 17.51 | 17.51 | -1.82 | 960 | Competition baseline inference control |
| **Recent Median 24h (`median24`)** | 17.61 | 17.61 | -1.84 | 960 | 24-hour recent median baseline |
| **Recent Median 168h (`median168`)** | 18.06 | 18.06 | -1.97 | 960 | 7-day recent median baseline |
| **LightGBM (raw MSE loss)** | 38.00 | 38.00 | +5.37 | 960 | Untransformed target (vulnerable to tail outliers) |

### Key Takeaways from Validation
1. **Target Transformation is Paramount:** LightGBM and CatBoost trained on raw PM2.5 concentrations suffer severe over-prediction distortion on volatile air quality data (raw RMSE 38.00 vs log1p RMSE 15.38). The `log1p` transformation stabilizes gradient steps and penalizes relative percentage errors proportionately.
2. **Feature Synergy:** Feature ablations proved that combining calendar features (RMSE 14.13), recent PM history features (RMSE 12.86), historical 2024 seasonal climatology (RMSE 12.33), and cross-station spatial interaction features produced the lowest overall RMSE of **11.89** on matched origin splits.
3. **Station Heterogeneity:** Shivaji Nagar and Malad West exhibit higher absolute variance, while Byculla and Borivali East track closer to background urban levels. CatBoost with target encoding captures these non-linear cross-station differentials effectively.

---

## 3. Candidate Submissions Breakdown

### Candidate Submission A: Accuracy Ensemble (`submission_A_accuracy_ensemble.csv`)
- **Composition:** 83% CatBoost (`log1p` target transform, depth 6, lr 0.05, 150 iterations) + 17% 2024 Seasonal Climatological Blend (`hist24_blend50_median72`).
- **Validation RMSE:** **14.24 $\mu\text{g}/\text{m}^3$** (Best overall validation score across all tested single models and blends).
- **Mean Bias:** $-0.29 \mu\text{g}/\text{m}^3$ (Virtually unbiased).
- **Predicted Target Summary:**
  - Mean: $43.80 \mu\text{g}/\text{m}^3$
  - Std Dev: $4.56 \mu\text{g}/\text{m}^3$
  - Min: $32.04 \mu\text{g}/\text{m}^3$
  - Max: $58.59 \mu\text{g}/\text{m}^3$
  - Median: $43.39 \mu\text{g}/\text{m}^3$
- **Strategic Justification:** Maximizes expected accuracy on the private evaluation block (11–12 November) by leveraging gradient boosted decision trees for non-linear lag-horizon interactions, with a calibrated anchor to the 2024 diurnal cycle.

### Candidate Submission B: Robust Ensemble (`submission_B_robust_ensemble.csv`)
- **Composition:** 50% CatBoost (`log1p`) + 50% 2024 Seasonal Climatological Blend.
- **Validation RMSE:** **14.43 $\mu\text{g}/\text{m}^3$**.
- **Mean Bias:** $-1.03 \mu\text{g}/\text{m}^3$.
- **Predicted Target Summary:**
  - Mean: $45.75 \mu\text{g}/\text{m}^3$
  - Std Dev: $6.44 \mu\text{g}/\text{m}^3$
  - Min: $32.48 \mu\text{g}/\text{m}^3$
  - Max: $70.94 \mu\text{g}/\text{m}^3$
  - Median: $44.45 \mu\text{g}/\text{m}^3$
- **Strategic Justification:** Hedge against potential distribution shift or meteorological anomalies in November 2026. The 50% weighting on the 2024 observed physical station readings prevents the GBDT from over-extrapolating into deep forecast horizons (up to 648 hours ahead).

---

## 4. Submission Verification Checklist

| Verification Item | Specification / Rule | Candidate A Result | Candidate B Result | Status |
| :--- | :--- | :--- | :--- | :---: |
| **Row Count** | Exactly 2,592 rows | 2,592 | 2,592 | PASS |
| **Column Names** | `ID,Target` | `ID,Target` | `ID,Target` | PASS |
| **ID Alignment** | Matches `SampleSubmission.csv` in identical order | Exact match (100%) | Exact match (100%) | PASS |
| **Finite Values** | No NaN, null, or infinite values | 0 NaN, 100% finite | 0 NaN, 100% finite | PASS |
| **Non-negative** | All predictions $\ge 0.0 \mu\text{g}/\text{m}^3$ | Min = 32.04 | Min = 32.48 | PASS |
| **Physical Plausibility** | Typical Mumbai November range ($20 - 250 \mu\text{g}/\text{m}^3$) | $32.04 - 58.59$ | $32.48 - 70.94$ | PASS |
| **Reproducibility Manifest** | Cryptographic hash & environment log | Present (`.manifest.txt`) | Present (`.manifest.txt`) | PASS |
| **No Future Leakage** | All features strictly $< \text{pm\_history\_cutoff}$ | Verified | Verified | PASS |

---

## 5. Instructions for Final Private Selection on Zindi

1. Navigate to the competition submission portal on Zindi: **Google Mumbai Data Challenge: Air Quality Mapping & Forecasting by Google**.
2. Upload `artifacts/submissions/submission_A_accuracy_ensemble.csv`. Label on Zindi: `Candidate A: CatBoost-Log1p (83%) + Seasonal Climatology (17%)`.
3. Upload `artifacts/submissions/submission_B_robust_ensemble.csv`. Label on Zindi: `Candidate B: CatBoost-Log1p (50%) + Seasonal Climatology (50%)`.
4. In the **My Submissions** tab, check the radio button to select **both Candidate A and Candidate B** as the two final submissions to be evaluated on the private leaderboard (11–12 November 2026).
5. Retain the corresponding `.manifest.txt` files for complete provenance and rule compliance verification.
