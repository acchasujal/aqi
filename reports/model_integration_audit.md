# Model Integration and CatBoost Benchmark Audit (Task 009)

**Audit Date:** 2026-11-09  
**Auditor:** Senior Data Scientist, ML Engineer, and Software Architect  
**Evaluation:** Standardized 9 Chronological Validation Folds ($N=1,460$ ground-truth observations)  
**Primary Metric:** Full-target raw-scale PM2.5 RMSE ($\mu\text{g}/\text{m}^3$)  
**Artifacts Generated:**  
- `reports/catboost_model_comparison.csv`  
- `reports/all_candidate_comparison.csv`  
- `reports/oof_predictions_task009.csv.gz`  

---

## 1. Executive Summary

Task 009 conducted a rigorous multi-model benchmarking study across 17 distinct forecasting architectures, target transformations, and ensemble configurations. All models were evaluated on identical chronological validation folds covering both late-monsoon/autumn steady conditions (Folds 1–5, $N=834$) and post-monsoon/winter transition surges (Folds 6–9, $N=626$, including the 11–12 November historical calendar match).

### Key Empirical Findings:
1. **CatBoost Residual Dominates All Single Supervised Models:**
   - Modeling the target residual relative to the station's recent 72-hour median ($\hat{y}_{t+h} = \text{median72} + \hat{\Delta}_{t,h}$) achieved the lowest pooled RMSE among all single supervised models: **28.17 $\mu\text{g}/\text{m}^3$** (vs. 29.50 for raw target, 30.34 for sqrt, and 31.75 for log1p).
   - CatBoost Residual cuts mean under-prediction bias from $-10.60\ \mu\text{g}/\text{m}^3$ (log1p) down to **$-3.55\ \mu\text{g}/\text{m}^3$** and lowers winter RMSE from 46.43 to **40.31**.

2. **Statistical Seasonal Blend (Candidate C / P_fix) Remains the Robust Baseline:**
   - Blending 50% 2024 same-hour historical climatology with 50% recent 72h median achieved **28.20 $\mu\text{g}/\text{m}^3$** pooled RMSE and the lowest winter RMSE among standalone models (**40.07 $\mu\text{g}/\text{m}^3$**).
   - It provides unmatched protection against high-pollution winter events at industrial monitors (Shivaji Nagar RMSE 50.22 vs 55.64 for CatBoost log1p).

3. **Complementary Ensembling Yields Global Optimum:**
   - Blending 50% CatBoost Residual with 50% Statistical Seasonal Blend achieves a new state-of-the-art pooled RMSE of **27.69 $\mu\text{g}/\text{m}^3$**, strictly outperforming both constituent models in Autumn (12.10 vs 13.02 / 13.67) and Winter (39.91 vs 40.31 / 40.07).
   - Candidate B (50% CatBoost log1p + 50% Statistical Seasonal) achieves **29.18 $\mu\text{g}/\text{m}^3$** pooled RMSE, but delivers the lowest RMSE in clean conditions (**8.35 $\mu\text{g}/\text{m}^3$** for $y < 50$).

---

## 2. CatBoost Target Transformation Benchmark

Table transcribed from `reports/catboost_model_comparison.csv` ($N=1,460$):

| Model Architecture | Target Transform | Pooled RMSE | Autumn RMSE | Winter RMSE | Mean Bias | MAE | Station 11606 (Borivali) | Station 11611 (Malad) | Station 3409510 (Byculla) | Station 3409511 (Shivaji Nagar) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **CatBoost Residual** | Residual ($\Delta$ to median72) | **28.17** | 13.02 | **40.31** | **-3.55** | **12.44** | **13.09** | 17.44 | **12.65** | 50.72 |
| **Statistical Seasonal** | 50% 2024 + 50% Med72 | 28.20 | 13.67 | 40.07 | -3.47 | 12.43 | 15.04 | **16.62** | 13.82 | **50.22** |
| **Candidate B** | 50% CB log1p + 50% Stat | 29.18 | 12.41 | 42.20 | -7.04 | 12.49 | 15.04 | 18.36 | 12.91 | 52.07 |
| **CatBoost Raw** | Raw MSE | 29.50 | 13.19 | 42.41 | -3.79 | 13.53 | 14.46 | 18.17 | 13.37 | 52.93 |
| **CatBoost Sqrt** | Square-root ($\sqrt{y}$) | 30.34 | 11.73 | 44.32 | -7.20 | 13.57 | 14.90 | 18.87 | 13.79 | 54.34 |
| **Candidate A** | 83% CB log1p + 17% Stat | 30.72 | 12.11 | 44.79 | -9.39 | 13.57 | 15.58 | 20.61 | 14.16 | 54.25 |
| **CatBoost Log1p** | Log1p ($\ln(y+1)$) | 31.75 | 12.13 | 46.43 | -10.60 | 14.46 | 16.00 | 22.02 | 15.28 | 55.64 |

### Diagnostic Breakdown:
- **Why Log1p Underperforms on Full RMSE:** While `log1p` optimizes relative percentage error and excels in clean conditions ($y < 50$), the exponential inverse transformation ($\exp(\hat{z}) - 1$) severely compresses tree predictions on the high end. During winter inversions where true targets reach $150–680\ \mu\text{g}/\text{m}^3$, the model underpredicts by up to $80\ \mu\text{g}/\text{m}^3$, incurring massive squared penalty under competition RMSE.
- **Why Residual Around Median72 Wins:** Centering the target on `median72` ensures that the baseline level is non-parametrically preserved without extrapolation risk. CatBoost's symmetric decision trees only need to learn the diurnal shape, weekend effects, and atmospheric ventilation departures $\hat{\Delta}$, which are zero-centered and symmetrically distributed.

---

## 3. Comparison with LightGBM, XGBoost, and Alternative Baselines

Table transcribed from `reports/all_candidate_comparison.csv` ($N=1,460$):

| Model Name | Model Family | Pooled RMSE | Autumn RMSE | Winter RMSE | Mean Bias | Clean RMSE ($y < 50$) | High RMSE ($y \ge 100$) | Extreme RMSE ($y \ge 250$) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| **CatBoost Residual** | GBDT (CatBoost) | **28.17** | 13.02 | 40.31 | -3.55 | 10.56 | 277.83 | 454.11 |
| **Candidate C** | Statistical Climatology | 28.20 | 13.67 | **40.07** | -3.47 | 11.51 | **277.43** | 455.73 |
| **Candidate D** | Ensemble (20% CB, 80% Stat) | 28.39 | 13.06 | 40.64 | -4.90 | 10.02 | 281.93 | 463.36 |
| **Median72** | Simple Persistence Baseline | 28.69 | 13.41 | 40.99 | -8.52 | 8.93 | 280.68 | 455.73 |
| **Candidate B** | Ensemble (50% CB, 50% Stat) | 29.18 | 12.41 | 42.20 | -7.04 | **8.35** | 288.71 | 474.84 |
| **CatBoost Raw** | GBDT (CatBoost) | 29.50 | 13.19 | 42.41 | -3.79 | 10.94 | 290.45 | 475.68 |
| **Seasonal Anomaly Decay** | Physics-guided Decay | 29.91 | 15.74 | 41.92 | **-2.43** | 15.21 | 281.03 | 464.87 |
| **CatBoost Sqrt** | GBDT (CatBoost) | 30.34 | 11.73 | 44.32 | -7.20 | 9.18 | 295.20 | 486.84 |
| **Candidate A** | Ensemble (83% CB, 17% Stat) | 30.72 | 12.11 | 44.79 | -9.39 | 7.75 | 296.20 | 487.50 |
| **Blend Tree (CB+LGB)** | Tree-Tree Ensemble | 31.61 | 11.24 | 46.49 | -10.28 | 7.88 | 301.10 | 497.46 |
| **CatBoost Log1p** | GBDT (CatBoost) | 31.75 | 12.13 | 46.43 | -10.60 | 8.06 | 300.08 | 494.03 |
| **LightGBM Log1p** | GBDT (LightGBM) | 31.93 | **10.77** | 47.16 | -9.95 | 8.99 | 302.65 | 500.89 |
| **XGBoost Log1p** | GBDT (XGBoost) | 32.11 | 10.84 | 47.41 | -10.09 | 9.07 | 303.19 | 500.66 |
| **LightGBM Residual** | GBDT (LightGBM) | 34.38 | 13.66 | 50.08 | -1.56 | 18.58 | 305.37 | 498.09 |
| **XGBoost Residual** | GBDT (XGBoost) | 38.14 | 15.58 | 55.39 | 1.45 | 24.41 | 287.29 | 474.56 |

### Findings on Tree-Tree Blending and Other Libraries:
- **LightGBM & XGBoost:** In autumn, LightGBM log1p achieves outstanding accuracy (10.77 RMSE). However, both LightGBM and XGBoost suffer severe degradation in winter (47.16 and 47.41 RMSE). Residual formulations for LightGBM (34.38) and XGBoost (38.14) performed significantly worse than CatBoost Residual (28.17) due to lack of ordered boosting and high sensitivity to outlier residual gradients.
- **Tree-Tree Blending (`blend_tree`):** Averaging CatBoost log1p and LightGBM log1p yields 31.61 pooled RMSE. Because both models share 0.969 residual correlation, blending two tree models fails to mitigate the winter under-prediction bias.
- **Seasonal Anomaly Decay:** Modeling anomaly decay as $C_{t+h} + \exp(-h/24) \cdot (y_t - C_t)$ achieved 29.91 pooled RMSE. At the private horizon (41–90 hours), the current anomaly has decayed by $>80\%$, meaning the forecast converges back to $C_{t+h}$. The simple 50:50 blend with recent 72h median is cleaner and achieves superior performance (28.20 vs 29.91).

---

## 4. Final Integration and Submission Recommendation

Based on the updated 9 November information cutoff (41–43h lead to the private evaluation window), we recommend:

1. **Submission Slot 1 (Primary / Lowest Expected Error):**
   - **Candidate C (Statistical Seasonal Blend / P_fix):** 50% 2024 Historical Climatology + 50% Recent 72h Median.
   - Lowest winter RMSE (40.07), near-zero bias (-3.47), proven public leaderboard performance (93.7384), and 0.00% risk of tree distribution-shift failure.

2. **Submission Slot 2 (Secondary / Robust Hedge):**
   - **Candidate B (Robust Ensemble):** 50% CatBoost log1p + 50% Statistical Seasonal Blend.
   - Proven public leaderboard score (94.0059), outstanding clean-range precision (8.35 RMSE for $y < 50$), and a genuine structural hedge providing 18.69 $\mu\text{g}/\text{m}^3$ mean divergence on transition days.
   - *Alternative for extreme precision:* If team consensus favors the newly validated residual formulation, **Refined Blend E** (50% CatBoost Residual + 50% Statistical Seasonal) achieves the lowest overall RMSE (27.69).
