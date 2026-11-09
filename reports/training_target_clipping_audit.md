# Training Target Clipping Audit
**Google Mumbai Data Challenge: Air Quality Mapping & Forecasting by Google (Zindi)**

---

## 1. Executive Summary

This audit evaluates whether clipping training targets improves raw-scale PM2.5 RMSE, using identical chronological folds and unmodified validation labels.

### Key Findings:
1. **Clipping at 500 µg/m³ Degrades Winter Performance:**
   - On the 9 chronological validation folds ($N=1,460$), CatBoost Residual with **no clipping** achieves a pooled RMSE of **28.17** and winter RMSE of **40.31**.
   - Clipping training labels at 500 µg/m³ **increases error**: pooled RMSE rises to **31.08** and winter RMSE degrades to **45.27** (+4.96 µg/m³ penalty).
   - In `fold_nov_2025_calendar_match`, unclipped residual CatBoost scores **79.03**, whereas clipping at 500 scores **89.99** (+10.96 µg/m³ worse).
2. **Atmospheric Context:**
   - Legitimate high-pollution winter events in Mumbai (e.g. Shivaji Nagar during November thermal inversions) reach **500 to 688 µg/m³**.
   - Capping training labels at 500 µg/m³ truncates the upper dynamic range, causing models to systematically underpredict severe winter surges.
3. **Multi-Thousand Artifacts vs. Atmospheric Peaks:**
   - Data inspection revealed discrete readings in `Train.csv` reaching **25,000, 50,000, 75,000, 99,999, and 241,587 µg/m³**.
   - Specifically, `2025-12-03 15:00` records `99999.01`, followed immediately by consecutive `0.00` values, matching standard digital overflow / maintenance codes on continuous air quality monitors.
   - Legitimate atmospheric spikes remain below ~1,000 µg/m³. Therefore, any safety ceiling should be set well above physical ambient maximums (e.g., 1,500–2,500 µg/m³) so that legitimate winter events are never clipped.

---

## 2. Experimental Results (9 Chronological Folds, $N=1,460$)

All models evaluated on the same 1,460 unmodified ground-truth validation labels:

| Model Configuration | Pooled RMSE | Autumn RMSE | Winter RMSE | High RMSE ($y \ge 100$) | MAE | Mean Bias |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Refined Blend E (Unclipped Residual)** | **27.69** | 12.10 | **39.91** | **277.58** | **11.79** | -3.51 |
| **CatBoost Residual (Unclipped)** | **28.17** | 13.02 | **40.31** | **277.83** | 12.44 | -3.55 |
| **Candidate C (Statistical Seasonal)** | 28.20 | 13.67 | 40.07 | 277.43 | 12.43 | **-3.47** |
| Refined Blend E (Clipped at 1000) | 28.52 | 11.96 | 41.31 | 281.62 | 12.09 | -3.28 |
| Refined Blend E (Clipped at 500) | 28.69 | **11.86** | 41.62 | 280.85 | 12.35 | -3.03 |
| Candidate B (CatBoost log1p) | 29.18 | 12.41 | 42.20 | 288.71 | 12.49 | -7.04 |
| CatBoost Residual (Clipped at 1000) | 30.61 | 12.55 | 44.44 | 286.36 | 13.15 | -3.09 |
| CatBoost Residual (Clipped at 500) | 31.08 | 12.37 | 45.27 | 284.33 | 13.89 | -2.59 |

---

## 3. Fold-by-Fold Breakdown

| Fold ID | Regime | N | Unclipped Residual | Clipped at 1000 | Clipped at 500 |
|---|---|:---:|:---:|:---:|:---:|
| `fold_24_20260813` | monsoon_autumn | 124 | 6.89 | 6.34 | **5.67** |
| `fold_25_20260903` | monsoon_autumn | 180 | 7.31 | 4.77 | **4.52** |
| `fold_26_20260924` | monsoon_autumn | 183 | 7.98 | 6.64 | **6.97** |
| `fold_27_20261015` | monsoon_autumn | 192 | 18.28 | 18.28 | **17.85** |
| `fold_28_20261105` | monsoon_autumn | 155 | 17.98 | 17.98 | **17.92** |
| `fold_nov_2025_calendar_match` | winter_transition | 138 | **79.03** | 89.22 | 89.99 |
| `fold_dec_2025_winter` | winter_transition | 127 | 18.02 | **13.64** | 18.71 |
| `fold_jan_2026_early` | winter_transition | 178 | **20.37** | **20.37** | 20.50 |
| `fold_jan_2026_late` | winter_transition | 183 | **14.85** | **14.85** | 15.82 |

### Conclusion:
In clean autumn regimes, clipping offers marginal stability gains (~1 µg/m³). However, on winter transition folds, unclipped training allows the gradient boosted tree to scale up into the 500–700 µg/m³ range, beating clipped models by over 10 µg/m³ on high-pollution folds.
