# Deep Repository, Architecture, and Data Audit Report

**Date:** 2026-11-08  
**Author:** Senior Data Scientist, ML Engineer, and Software Architect  
**Branch:** `feat/competition-ml-pipeline`  
**Evaluation Target:** Original-scale PM2.5 RMSE on private evaluation period (11–12 November 2026)

---

## Executive Summary

A comprehensive forensic audit of the Mumbai PM2.5 forecasting repository was conducted across all Python modules, experiment scripts, configuration assets, raw data files, and validation routines.

While the repository established sound foundation principles (such as preserving raw data immutability and tracking interval-end vs. interval-start semantics), the audit uncovered **critical defects and methodological flaws** that compromised historical seasonal features, inflated historical coverage, misaligned leap-year calendars, corrupted reporting-gap validation comparisons, and prevented competitive machine learning models from being trained.

This report documents the confirmed bugs, architectural weaknesses, leakage risks, and provides the rigorous technical roadmap for upgrading the system into a competition-grade forecasting pipeline.

---

## 1. Confirmed Critical Bugs and Architectural Defects

### A. Historical Station Mapping & False Station Merging
**Location:** `src/mumbai_pm25/historical_archive.py` (`load_2024_history`, `build_seasonal_features`)

*   **Broad Substring Collision:**
    Station matching previously relied on `name_fragment.lower() in k.lower()` with name fragment `"Malad West"` (for target location `11611`). In the 2024 archive (`History_Mumbai_2024.csv.gz`), there are two distinct stations containing `"Malad West"`:
    1.  `Malad West, Mumbai - IITM` (`site_5102`, `site_5402`)
    2.  `Mindspace-Malad West, Mumbai - MPCB` (`site_5807`)
    The code erroneously merged the MPCB industrial/commercial monitor (`site_5807`) into the IITM residential background prior (`11611`), corrupting the target station's seasonal baseline.
*   **Multi-Sensor Measurement Representation:**
    In the 2024 archive, target locations contain multiple concurrent sensor series:
    -   `Borivali East, Mumbai - IITM`: `site_5113` (8,097 rows) and `site_5400` (7,387 rows). Overlap: 6,738 hours; mean absolute difference: 22.14 µg/m³.
    -   `Malad West, Mumbai - IITM`: `site_5102` (7,486 rows) and `site_5402` (5,982 rows). Overlap: 5,145 hours; mean absolute difference: 23.90 µg/m³.
    Previously, rows from both sensor series were concatenated without timestamp pre-aggregation. This caused hours with dual sensors to be double-weighted in mean calculations and artificially inflated `hist24_coverage` by up to 200% of actual elapsed hours.
*   **Resolution:**
    Enforce exact station identifier / canonical station name mapping. Pre-aggregate concurrent readings at the same timestamp using robust aggregation (median or mean) to create a clean, single observation per station-hour before computing climatological statistics. Coverage must count unique timestamps.

---

### B. Leap-Year Calendar Misalignment (2024 vs. 2026)
**Location:** `src/mumbai_pm25/historical_archive.py` (`build_seasonal_features`)

*   **Defect:**
    2024 was a leap year (366 days, with 29 February as Day 60). 2026 is a standard year (365 days, where 1 March is Day 60).
    The previous code extracted `history['doy'] = history['hour_start'].dt.day_of_year` and matched against target 2026 `dt.day_of_year`.
    Because of 29 February:
    -   2026 Day 315 corresponds to **November 11, 2026**.
    -   2024 Day 315 corresponds to **November 10, 2024** (since Day 60 was Feb 29).
    This introduced an unaligned 24-hour seasonal calendar shift across all dates after February 28.
*   **Resolution:**
    Align historical seasonal climatology on `(month, day, hour)` calendar keys or normalize the day of year by mapping leap-year dates post-Feb 28 back by 1 day (or treating Feb 29 as day 59.5).

---

### C. Validation Target Period Shifting with Reporting Gap
**Location:** `src/mumbai_pm25/validation.py` (`rolling_oof`) and `scripts/validate_seasonal_history.py`

*   **Defect:**
    In `rolling_oof()`, folds were iterated over cutoff times, with target start computed as:
    ```python
    target_start = cutoff + pd.Timedelta(hours=gap_hours)
    targets = pd.date_range(target_start, periods=horizon_hours, freq="h")
    ```
    When running experiments comparing `gap_hours` $\in \{48, 72, 96, 120\}$, changing `gap_hours` shifted the target window into the future by 24, 48, or 72 hours!
    Consequently:
    -   At `gap=48`, the model evaluated target window $T$.
    -   At `gap=72`, the model evaluated target window $T + 24\text{h}$.
    -   At `gap=96`, the model evaluated target window $T + 48\text{h}$.
    This completely invalidates cross-gap performance comparisons because the models were evaluated on different ground-truth weather and pollution regimes.
*   **Resolution:**
    Invert fold generation: Define fixed, non-overlapping 48-hour target blocks $[T_{\text{start}}, T_{\text{end}}]$. For each fixed target block and each candidate reporting gap $g$, compute the PM history cutoff as $T_{\text{start}} - g$. All reporting-gap ablations will then evaluate the exact same ground-truth target labels.

---

### D. Stale-History Silent Fallback
**Location:** `src/mumbai_pm25/forecast.py` (`history_features`)

*   **Defect:**
    When recent observations within the 72-hour window were missing, `history_features()` silently executed:
    ```python
    level = float(observed.median()) if not observed.empty else float(history.pm25.dropna().median())
    ```
    This replaced an unavailable recent window with a lifetime historical median (spanning over 18 months of heterogeneous seasonal data), providing no indication of data staleness, observation count, or recency.
*   **Resolution:**
    Implement a multi-tier, age-aware feature extraction hierarchy:
    1.  Explicitly extract last available PM2.5 and observation age in hours.
    2.  Extract observation counts and coverage across multiple windows (6h, 12h, 24h, 48h, 72h, 168h).
    3.  Compute rolling medians, means, EWMA, and local trend slopes.
    4.  Fall back gracefully with clear missingness flags and seasonal priors rather than unweighted lifetime medians.

---

### E. Reproducibility Manifest Inaccuracies
**Location:** `src/mumbai_pm25/forecast.py` (`write_manifest`)

*   **Defect:**
    -   `AdditionalHistory.zip` was appended twice to input files when `extra_sources` was supplied.
    -   The SHA-256 hash of the generated prediction CSV itself was never calculated or recorded.
    -   Git working-tree status (clean vs. uncommitted modifications) was not recorded.
    -   Package versions for installed ML libraries (LightGBM, CatBoost, XGBoost, scikit-learn) were omitted.
    -   Global and per-station effective PM cutoffs lacked verification against issue time.
*   **Resolution:**
    Overhaul `write_manifest()` to include full input and output cryptographic hashes, git commit SHA and working-tree clean status, complete runtime environment specs, exact model configuration parameters, and verified station-specific history cutoffs.

---

### F. Configuration Disconnection
**Location:** `configs/default.yaml`

*   **Defect:**
    `configs/default.yaml` existed as a passive documentation artifact. The command-line scripts (`train_predict.py`, `validate_baselines.py`, `validate_seasonal_history.py`) did not load or validate parameters from the configuration file, resulting in hardcoded parameters scattered across scripts.
*   **Resolution:**
    Create a centralized configuration loader (`src/mumbai_pm25/config.py`) that parses and validates `configs/default.yaml`, serving as the single source of truth for paths, model parameters, validation folds, and feature flags.

---

## 2. Data Quality and Extreme Values Audit

### A. Raw Data Integrity
-   `Train.csv`: 47,849 rows, 10 columns. Timestamps span `2025-02-19 03:00:00+05:30` to `2026-11-02 23:00:00+05:30`.
-   `mean == pm25` across 100% of rows (confirmed duplicate column; dropped in feature engineering).
-   `count` represents quarter-hour valid sample counts (3 or 4); absent in Test.csv.
-   19 rows exhibit PM2.5 > 1,000 µg/m³, with an extreme outlier reaching 241,587.56 µg/m³ at Shivaji Nagar.
-   Target distribution is heavily right-skewed:
    -   Median: ~42.3 µg/m³
    -   75th percentile: ~68.1 µg/m³
    -   99th percentile: ~265.4 µg/m³
    -   Max: 241,587.56 µg/m³
-   Evaluation Metric: RMSE in original $\mu\text{g/m}^3$. A single extreme outlier contributes quadratically to the loss.
-   Rule Compliance: Validation labels must NEVER be clipped, winsorized, or deleted. Target transformations (log1p, sqrt, Huber/MAE loss) must be tested on training data and inverted for original-scale evaluation.

### B. Auxiliary Archives in AdditionalHistory.zip
1.  `History_Mumbai_2024.csv.gz`: Verified 208,043 CPCB CAAQMS rows. Contains high-resolution historical seasonal signal for all 4 target stations when cleaned and mapped correctly.
2.  `Other_Mumbai_Stations_2025_2026.csv.gz`: 14 additional Mumbai stations. Useful for spatial and citywide correlation features prior to 16 October 2026.
3.  `History_Mumbai_2018_2020.csv.gz` & `Legacy_Observations_2020_2022.csv.gz`: Irregular older series; rejected from primary target priors due to temporal drift and differing sensor standards.

---

## 3. Prioritized Implementation Plan

| Phase | Milestone | Expected Impact | Key Output / File |
|---|---|---|---|
| **Phase 1** | Deep Repository & Data Audit | Identify and document all defects | `reports/repository_audit.md` |
| **Phase 1 (Fix)** | Fix Historical Station Mapping & Leap-Year Bug | Unbiased seasonal prior; correct coverage | `src/mumbai_pm25/historical_archive.py`, tests |
| **Phase 2** | Fixed-Origin Aligned Validation Framework | Fair cross-gap and cross-model evaluation | `src/mumbai_pm25/validation.py`, `reports/validation_methodology.md` |
| **Phase 3** | Statistical Forecasting Baselines Module | 11 comprehensive historical benchmarks | `src/mumbai_pm25/models/statistical.py` |
| **Phase 4** | Modular Feature Engineering System | State, dynamics, calendar, seasonal, spatial | `src/mumbai_pm25/features/`, `reports/feature_engineering_report.md` |
| **Phase 5** | All 5 Model Families (LGBM, CatBoost, XGB, RF, Stat) | Robust non-linear and interaction modeling | `src/mumbai_pm25/models/` |
| **Phase 6** | Target Transformation & Extreme Values | Stabilize training loss against extreme spikes | `reports/target_transformation_results.csv` |
| **Phase 7** | Cross-Station & Auxiliary Spatial Features | Citywide pollution state context | Spatial feature modules |
| **Phase 8** | Adversarial Validation & Overfitting Control | Ensure training distribution matches target | `reports/adversarial_validation.md` |
| **Phase 9** | Model Comparison & Optimal Ensembling | Minimize full-target OOF RMSE | `reports/model_comparison.csv`, `reports/experiment_summary.md` |
| **Phase 10** | Final Submissions & Manifests | Two competition-grade validated submissions | `artifacts/submissions/`, `reports/final_submission_report.md` |

---

## 4. Verification Checkpoint

All identified issues are substantiated by empirical code examination and verified data properties. Testing and correction will proceed systematically, with unit and regression tests accompanying every change on branch `feat/competition-ml-pipeline`.
