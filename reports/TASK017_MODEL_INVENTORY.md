# TASK 017 — Complete Forecasting Model Inventory

**Date:** 2026-11-10  
**Repository:** `acchasujal/aqi`  
**Dataset:** Official Final 10 November 2026 Release (`Train.csv` 48,400 rows, `Test.csv` 2,592 rows)

---

## 1. Inventory Summary

This inventory catalogs all implemented forecasting models in the repository capable of generating out-of-sample predictions on the official challenge datasets.

Every model is assessed for:
- Input features and historical dependencies.
- Target transformation and loss function.
- Horizon support (specifically the 16–63h private evaluation horizon).
- Permitted data source compliance (zero unapproved external data).
- Telemetry corruption immunity.

---

## 2. Model Catalog

| Category | Model Name | Implementation File | Key Features / Methodology | Horizon Support | Telemetry Robustness | Status |
|---|---|---|---|---|---|---|
| **Simple Baseline** | `median72` | `src/mumbai_pm25/forecast.py` | Rolling 72h station median before cutoff | Any (flat level) | High (median is outlier-proof) | Core Baseline |
| **Simple Baseline** | `persistence` | `src/mumbai_pm25/models/baseline.py` | Last valid station observation | Any (flat level) | Low (sensitive to single spike) | Reference Baseline |
| **Simple Baseline** | `clean_kernel_climatology` | `src/mumbai_pm25/climatology/kernel.py` | Circular Gaussian kernel ($\sigma_{\text{doy}}=10.0, \sigma_{\text{hour}}=1.0$) on clean 2024 CPCB CAAQS archive | 0–168h+ | High (clean 2024 data has max <350 µg/m³) | Core Climatology |
| **Simple Baseline** | `P_fix` | `src/mumbai_pm25/historical_archive.py` | Exact month/day same-hour historical 2024 CAAQS profile | Fixed hourly | High (clean historical archive) | Core Historical |
| **Simple Baseline** | `P_fix_diur25` (B25) | `scripts/run_task011.py` | 75% P_fix + 25% recent 7-day diurnal profile (`diur7`) | 0–90h | Medium-High | Teammate Candidate |
| **Simple Baseline** | `P_fix_diur50` (B50) | `reports/ml_pipeline/PRIVATE_WAR_ROOM/candidates/build_diur50_candidate.py` | 50% P_fix + 50% recent 7-day diurnal profile (`diur7`) | 0–90h | Medium-High | War Room Candidate |
| **Statistical Candidate** | `Candidate C` (`hist24_blend50_median72`) | `src/mumbai_pm25/forecast.py` | 50% recent 72h median + 50% 2024 month_day_365 seasonal profile | 0–90h | High (median + clean archive) | Top Prior Candidate |
| **Statistical Candidate** | `Corrected Kernel Climatology Blend` | `src/mumbai_pm25/climatology/pipeline.py` & `scripts/generate_task013_submission.py` | 50% recent 72h median + 50% clean 2024 Gaussian kernel climatology | 0–90h | High (Task 012 champion, 27.232 RMSE) | Current Primary |
| **Statistical Ensemble** | `Candidate B` (`ensemble_robust`) | `src/mumbai_pm25/forecast.py` & `src/mumbai_pm25/models/supervised.py` | 50% CatBoost log1p + 50% Candidate C | 0–90h | High (log1p dampens spikes) | Benchmark Candidate |
| **Statistical Ensemble** | `Candidate E` (`ensemble_residual_blend`) | `src/mumbai_pm25/forecast.py` & `src/mumbai_pm25/models/supervised.py` | 50% CatBoost residual (2000 ceiling) + 50% Candidate C | 0–90h | Medium-High (clipped ceiling) | Benchmark Candidate |
| **Supervised** | `ridge_anomaly` | `src/mumbai_pm25/climatology/ridge_model.py` | Lead-bucket Ridge regression on $a_{24}, a_{72}, a_{168}$ anomalies | 5 lead buckets | Low (sensitive to squared error on raw spikes) | Diagnostic Baseline |
| **Supervised** | `lightgbm_residual` | `src/mumbai_pm25/climatology/lgbm_residual.py` | Compact LightGBM fitted on climatology residuals | 0–90h | Low (tree extrapolation error on 40-60h leads) | Diagnostic Baseline |
| **Supervised** | `catboost_residual` | `src/mumbai_pm25/models/supervised.py` | CatBoost regressor fitted on recent level residuals with 2000 ceiling | 0–90h | Medium | Benchmark Supervised |

---

## 3. Data Source Eligibility & Compliance

All candidate models rely strictly on:
1. `data/raw/challenge/Train.csv` (official 48,400 rows).
2. `data/raw/challenge/Test.csv` (official 2,592 rows).
3. `data/raw/challenge/Stations.csv` (4 stations).
4. `data/raw/challenge/AdditionalHistory.zip` (`History_Mumbai_2024.csv.gz`).

Zero external, unapproved APIs, live web feeds, or unverified weather observations are utilized.
