# Final Submission Selection and Model Strategy Optimization

**Target Period:** 11 November 2026 00:00 IST – 12 November 2026 23:00 IST (192 private hourly evaluations)  
**Evaluation Metric:** Official Full-Target Original-Scale RMSE ($\mu\text{g}/\text{m}^3$) on raw, unmodified ground-truth labels  
**Date of Selection:** 8 November 2026  
**Status:** Final Competition Decision Document  

---

## 1. Executive Summary and The Model Selection Dilemma

Prior to this study, the candidate pool was centered on machine learning ensembles:
- **Candidate A (83% CatBoost + 17% Statistical Seasonal):** Developed as the precision candidate during August–October validation.
- **Candidate B (50% CatBoost + 50% Statistical Seasonal):** Formulated as a hedge against winter drift.

However, the nine-fold multi-regime generalization audit uncovered a decisive empirical fact:
**The Statistical Seasonal Model alone (Strategy C: 50% 2024 CAAQMS same-hour climatology + 50% recent 72h station median) achieves the lowest overall error across the entire validation corpus:**
- **Pooled 9-Fold RMSE ($N=1,316$):** **29.30 $\mu\text{g}/\text{m}^3$** (vs 30.65 for Candidate B, 32.67 for Candidate A, and 34.00 for CatBoost alone).
- **Winter Transition RMSE ($N=626$):** **39.28 $\mu\text{g}/\text{m}^3$** (vs 41.66 for Candidate B, 44.72 for Candidate A, and 46.67 for CatBoost alone).
- **Mean Prediction Bias:** **-0.54 $\mu\text{g}/\text{m}^3$** (virtually unbiased, compared to severe negative under-prediction biases of -8.75 to -10.43 $\mu\text{g}/\text{m}^3$ for tree-heavy models).

Rather than blindly retaining Candidate A and Candidate B, this final study rigorously compared four distinct strategies across all 9 folds, evaluated every ensemble against its constituent models, and optimized the final two-submission pairing.

---

## 2. Multi-Strategy Evaluation Matrix ($N=1,316$ Ground-Truth Observations)

| Strategy | Strategy Description | Formula | Monsoon / Autumn RMSE (N=690) | Winter Transition RMSE (N=626) | All Regimes Pooled RMSE (N=1,316) | Overall Mean Bias ($\mu\text{g}/\text{m}^3$) | Residual Corr with CatBoost |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Strategy C** | **Statistical Seasonal Alone** | $1.00 \times \text{Stat}$ | 15.41 | **39.28** | **29.30** | **-0.54** | **0.805** |
| **Strategy D** | **Validation-Driven Optimal Blend** | $0.20 \times \text{CB} + 0.80 \times \text{Stat}$ | 15.02 | 39.87 | 29.58 | -2.52 | 0.884 |
| **Strategy B** | **Existing Robust Ensemble** | $0.50 \times \text{CB} + 0.50 \times \text{Stat}$ | **14.75** | 41.66 | 30.65 | -5.49 | 0.957 |
| **Strategy A** | **Existing Accuracy Ensemble** | $0.83 \times \text{CB} + 0.17 \times \text{Stat}$ | 14.89 | 44.72 | 32.67 | -8.75 | 0.998 |
| *Constituent* | *CatBoost log1p alone* | $1.00 \times \text{CB}$ | 15.14 | 46.67 | 34.00 | -10.43 | 1.000 |

---

## 3. Comparing Ensembles Directly Against Both Constituent Models

A fundamental principle of rigorous ML engineering is that an ensemble must not be assumed superior simply because it blends multiple algorithms. We tested every ensemble directly against **both** of its constituent models:

### 3.1 Candidate A (83% CatBoost + 17% Statistical) vs Constituents
- **Vs CatBoost alone:** Candidate A improves autumn RMSE from 15.14 to 14.89, winter RMSE from 46.67 to 44.72, and pooled RMSE from 34.00 to 32.67.
- **Vs Statistical alone:** Candidate A is worse on winter RMSE (44.72 vs 39.28, a deficit of **5.44 $\mu\text{g}/\text{m}^3$**) and worse on pooled RMSE (32.67 vs 29.30).
- **Verdict:** Candidate A is superior to CatBoost alone, but inferior to the Statistical model under winter distribution shifts.

### 3.2 Candidate B (50% CatBoost + 50% Statistical) vs Constituents
- **Vs CatBoost alone:** Candidate B strictly beats CatBoost alone across all regimes (14.75 vs 15.14 in autumn; 41.66 vs 46.67 in winter; 30.65 vs 34.00 pooled).
- **Vs Statistical alone:** Candidate B beats Statistical alone in autumn (14.75 vs 15.41), but loses in winter (41.66 vs 39.28).
- **Verdict:** Candidate B is an authentic compromise that achieves the lowest Autumn RMSE of any tested model while offering substantial winter protection.

### 3.3 Candidate D (20% CatBoost + 80% Statistical) vs Constituents
- **Vs CatBoost alone:** Candidate D beats CatBoost alone across every metric by massive margins (pooled 29.58 vs 34.00).
- **Vs Statistical alone:** Candidate D improves Autumn RMSE over pure Statistical (15.02 vs 15.41) with only a minimal winter trade-off (39.87 vs 39.28).
- **Verdict:** If a single compromise ensemble were required, Candidate D mathematically minimizes pooled error while keeping winter RMSE under 40.

---

## 4. Performance Across Pollution Regimes and Stations

### 4.1 Ground-Truth Pollution Bins (RMSE)

| Pollution Band | Sample Count | Strategy C (Stat Alone) | Strategy D (20/80 Blend) | Strategy B (50/50 Blend) | Strategy A (83/17 Blend) | CatBoost Alone |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Clean ($y < 50 \mu\text{g}/\text{m}^3$)** | 846 | 15.03 | 13.61 | 11.97 | **11.12** | 11.15 |
| **Moderate ($50 \le y < 75$)** | 388 | **15.96** | 16.76 | 19.52 | 23.98 | 26.64 |
| **Elevated ($75 \le y < 100$)** | 71 | **25.14** | 27.19 | 32.57 | 40.47 | 45.02 |
| **High ($100 \le y < 250$)** | 7 | 47.29 | 46.16 | 44.47 | 42.63 | **41.69** |
| **Extreme ($y \ge 250$)** | 4 | **441.35** | 452.20 | 468.59 | 486.79 | 496.22 |

### 4.2 Per-Station RMSE Summary

| Official Station Name | Station ID | Strategy C (Stat Alone) | Strategy D (20/80 Blend) | Strategy B (50/50 Blend) | Strategy A (83/17 Blend) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Borivali East** | 11606 | **13.27** | 13.65 | 14.53 | 15.87 |
| **Malad West** | 11611 | 17.19 | **17.09** | 17.87 | 19.83 |
| **Byculla** | 3409510 | 18.33 | 17.72 | **17.62** | 18.61 |
| **Shivaji Nagar** | 3409511 | **52.56** | 53.36 | 55.40 | 58.70 |

---

## 5. Final Two-Submission Decision

Zindi permits two final submission selections. To maximize expected standing on the private leaderboard, the two submissions must **not** be minor variations of each other. They must represent **two genuinely distinct, complementary meteorological hypotheses**:

### Selection 1: `submission_C_statistical_seasonal.csv` (The Seasonal Transition Solution)
- **Model:** `hist24_blend50_median72` (Strategy C)
- **Hypothesis:** The private 11–12 November period undergoes the typical post-monsoon meteorological transition observed in 2024 and 2025 (wind stagnation, boundary-layer shallowing, particulate accumulation).
- **Why It Wins:** Lowest pooled RMSE (**29.30**), lowest winter RMSE (**39.28**), near-zero bias (**-0.54 $\mu\text{g}/\text{m}^3$**), and lowest error at high-emission industrial stations (Shivaji Nagar: 52.56 vs 58.70).
- **Cryptographic Hash:** `SHA-256: e82ff30bc8867a07fc26fb51e737c73dbca63fc9ad4a2ad528404a3f21d3f237`

### Selection 2: `submission_B_robust_ensemble.csv` (The Balanced Precision Solution)
- **Model:** `ensemble_robust` (50% CatBoost log1p + 50% Statistical Seasonal Blend)
- **Hypothesis:** Late-monsoon meteorological persistence delays the winter inversion, keeping ambient air quality relatively low (similar to late October 2026), or local emissions fluctuate rapidly around recent 72-hour levels.
- **Why It Wins:** Achieved the lowest Autumn RMSE of all tested models (**14.75**), retains fine-grained gradient-boosted tree sensitivity to day-of-week and hourly trends, while incorporating 50% climatology to maintain winter RMSE (**41.66**) well below CatBoost alone (46.67) and Candidate A (44.72).
- **Cryptographic Hash:** `SHA-256: 01db64673628bb9c072bfef693ef2b8df1c8b36a188be923832cce6bb79c298c`

*(Note: Candidate A and Candidate D are fully generated and preserved in `artifacts/submissions/` with complete manifests, should the team elect to prioritize late-autumn persistence over winter surge protection).*

---

## 6. Manifest of Candidate Artifacts

All candidate files are verified: exactly 2,592 rows matching `SampleSubmission.csv` IDs in exact order, non-negative, finite, with zero missing values.

| Candidate Identifier | File Path | Model Spec | SHA-256 Digest |
| :--- | :--- | :--- | :--- |
| **Candidate C (Recommended #1)** | `artifacts/submissions/submission_C_statistical_seasonal.csv` | 50% 2024 CAAQMS Climatology + 50% Median72 | `e82ff30bc8867a07fc26fb51e737c73dbca63fc9ad4a2ad528404a3f21d3f237` |
| **Candidate B (Recommended #2)** | `artifacts/submissions/submission_B_robust_ensemble.csv` | 50% CatBoost log1p + 50% Statistical Seasonal | `01db64673628bb9c072bfef693ef2b8df1c8b36a188be923832cce6bb79c298c` |
| **Candidate A (Archived)** | `artifacts/submissions/submission_A_accuracy_ensemble.csv` | 83% CatBoost log1p + 17% Statistical Seasonal | `0417e435941c48c6e7c10b71329c21147a4f9104043b4fdb3288f4b0d0c36785` |
| **Candidate D (Alternative)** | `artifacts/submissions/submission_D_balanced_ensemble.csv` | 20% CatBoost log1p + 80% Statistical Seasonal | `da7e8d626e259b1dc710927e1f4fcbbbb68aa9dbfb4e680d28362ea5317b9666` |

---

## 7. Protocol for Refreshed Train Data on 10 November 2026

When the organizers publish the refreshed `Train.csv` (expected cutoff `2026-11-09T23:00:00+05:30`):
1. Place the refreshed file into `data/raw/challenge/Train.csv`.
2. Generate refreshed Candidate C:
   ```bash
   python scripts/train_predict.py \
       --model hist24_blend50_median72 \
       --model-run-time 2026-11-10T12:00:00+05:30 \
       --output artifacts/submissions/submission_C_refreshed.csv
   ```
3. Generate refreshed Candidate B:
   ```bash
   python scripts/train_predict.py \
       --model ensemble_robust \
       --model-run-time 2026-11-10T12:00:00+05:30 \
       --output artifacts/submissions/submission_B_refreshed.csv
   ```
4. Run regression suite: `pytest -ra`.
5. Upload `submission_C_refreshed.csv` and `submission_B_refreshed.csv` as the official final private submission pair on Zindi.
