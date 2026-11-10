# TASK 016 — Final Competition Data & Active Pipeline Verification Audit

**Date:** 2026-11-10  
**Repository:** `acchasujal/aqi`  
**Branch:** `feat/competition-ml-pipeline`  
**Base Commit:** `7cd7324c3508d797b8d217e600e3ed6a74680e6a`  
**Audit Status:** Fully Verified — Active Pipelines Ready for 10 November 2026 Final Refresh

---

## 1. Executive Summary

This audit verifies the official **10 November 2026 final release** datasets provided in `data/raw/challenge/` and audits all active training, validation, feature extraction, and inference pipelines.

Key findings:
1. **Canonical `Train.csv`:** Exactly **48,400 rows**, SHA-256 `8adbcf55315f166d7dc3dc1d3e4d7400651f26c1d8b95ff387eef38f4e70a283`. Matches the organizer's expected hash character-for-character. All 4 target stations have observations extending to **2026-11-10 09:00:00+05:30**.
2. **Canonical `Test.csv` & `SampleSubmission.csv`:** Exactly **2,592 rows** with identical `ID` ordering. Target intervals are strictly 1-hour in Asia/Kolkata (`+05:30`).
3. **Private Evaluation Window:** Exactly **192 rows** labeled `scoring_block == "private"` spanning **2026-11-11 00:00 IST to 2026-11-13 00:00 IST** (48 hours $\times$ 4 stations).
4. **Physical Forecast Horizon:** The physical lead from the latest station observation (10 Nov 09:00 IST) to the first private target interval start (11 Nov 00:00 IST) is exactly **15.0 hours** (spanning through **62.0 hours** to the start of the final hour, or **63.0 hours** to target interval end).
5. **Historical Archive Integrity:** `AdditionalHistory.zip` (SHA-256 `3233061c...`) contains 208,043 historical CPCB CAAQS observations. Clean 2024 climatology correctly isolates IITM stations, excludes Mindspace-Malad, and eliminates unflagged 2025 telemetry spikes (>2,000 µg/m³).
6. **Pipeline Verification:** Active pipelines ([`src/mumbai_pm25/data.py`](file:///c:/Users/ram/Documents/Projects/aqi/src/mumbai_pm25/data.py), [`scripts/generate_task013_submission.py`](file:///c:/Users/ram/Documents/Projects/aqi/scripts/generate_task013_submission.py), [`scripts/train_predict.py`](file:///c:/Users/ram/Documents/Projects/aqi/scripts/train_predict.py)) dynamically read the updated 48,400-row Train and 2,592-row Test. All 201 repository unit and regression tests pass (100% pass rate).

---

## 2. Official Dataset Inventory & Hash Verification

| Dataset Path | Size (Bytes) | Row / Line Count | Raw SHA-256 Digest | Normalized LF SHA-256 | Official Release Match |
|---|---|---|---|---|---|
| `data/raw/challenge/Train.csv` | 6,837,802 | 48,400 rows | `8adbcf55315f166d7dc3dc1d3e4d7400651f26c1d8b95ff387eef38f4e70a283` | `38095a5ea2cc0e03e13e9340d6f351008723753f1d1e719ced0a483dee36b8ae` | **Yes (Official Final)** |
| `data/raw/challenge/Test.csv` | 296,429 | 2,592 rows | `e7b9cc8859beb939276c958393e148adae55229c34f99dcb2555fe4ac13b28db` | `cdb2b6c3035f6331848c565b4d3dd89ac5281efab07fa62bfabc2e7ff172db0a` | **Yes (Official Final)** |
| `data/raw/challenge/SampleSubmission.csv` | 80,363 | 2,592 rows | `ee4682ce0e546c1b62beb4a08414a5ddc831fa962cff30e8a823d6b6b0e0c72f` | `5806d6109f381043e59fffb48a5d0af5d9de56fd4e0e956e4c5e7f2e6ae5dcd9` | **Yes (Official Final)** |
| `data/raw/challenge/Stations.csv` | 369 | 4 rows | `383269fa04abf8f2eb49e5ec0bb5a77c2df11acb6aca996b7edf269a109ee9cf` | `383269fa04abf8f2eb49e5ec0bb5a77c2df11acb6aca996b7edf269a109ee9cf` | **Yes (Official Final)** |
| `data/raw/challenge/DataDictionary.txt` | 3,581 | 71 lines | `8786b98f78784e1b53a27cb23c8df64ab92ef76d3be2885098b00c0830a8c985` | `8786b98f78784e1b53a27cb23c8df64ab92ef76d3be2885098b00c0830a8c985` | **Yes (Official Final)** |
| `data/raw/challenge/AdditionalHistory.zip` | 4,817,970 | 208,043 rows | `3233061ca4ac2af39e9f6e80e21d9261b1b8d2fd3b037e5d034bcec059a7e80e` | `abfead08465a1d22af320f95ae4cd357badc0f7c516a7896c3097d31f2548058` | **Yes (Official Final)** |
| `data/raw/challenge/Train (2).csv` | 6,789,401 | 48,400 rows | `38095a5ea2cc0e03e13e9340d6f351008723753f1d1e719ced0a483dee36b8ae` | `38095a5ea2cc0e03e13e9340d6f351008723753f1d1e719ced0a483dee36b8ae` | Secondary snapshot from `origin/main` |

---

## 3. Train.csv Deep Data Quality Audit

- **Total Rows:** 48,400
- **Missing Values:** 0 across all 10 columns (`timestamp_ist`, `mean`, `count`, `available_at`, `pm25`, `location_id`, `sensor_id`, `station_name`, `series_id`, `flag_high_1000`).
- **Target Equivalence:** `pm25 == mean` across all 48,400 rows (mean column remains an exact duplicate).
- **Timezone Offsets:** 100% of timestamps carry explicit `+05:30` offset (`Asia/Kolkata`).
- **Duplicates:**
  - `(location_id, sensor_id, timestamp_ist)`: **0**
  - `(location_id, timestamp_ist)`: **0**
- **PM2.5 Distribution:**
  - Min: 0.0 µg/m³
  - Max: 241,587.56 µg/m³ (known raw sensor overflow at Shivaji Nagar on 2025-12-03)
  - Mean: 44.2075 µg/m³
  - Median: 22.0712 µg/m³
  - Negative values: 0
  - Zero values: 566 rows
  - Values > 250 µg/m³: 124 rows
  - Values > 500 µg/m³: 60 rows
  - Values > 1,000 µg/m³: 19 rows
- **Quality Flags:**
  - `flag_high_1000`: 19 rows flagged `True`, 48,381 rows `False`.
- **Newly Added Station-Hours (7–10 November):**
  - Total rows $\ge$ 2026-11-07 00:00 IST: **284 rows**
  - Verified 201 public-window station readings across 8–10 November incorporated into training history.

### Location and Sensor Breakdown

| Station Name | Location ID | Sensor ID | Row Count | Min Timestamp (IST) | Max Timestamp (IST) | PM2.5 Median |
|---|---|---|---|---|---|---|
| Borivali East | 11606 | 12236418 | 12,241 | 2025-02-19 03:00 | 2026-11-10 09:00 | 26.71 µg/m³ |
| Malad West | 11611 | 12236426 | 12,343 | 2025-02-19 03:00 | 2026-11-10 09:00 | 16.55 µg/m³ |
| Byculla | 3409510 | 12238567 | 11,683 | 2025-02-19 03:00 | 2026-11-10 09:00 | 18.04 µg/m³ |
| Shivaji Nagar | 3409511 | 12238576 | 12,133 | 2025-02-19 03:00 | 2026-11-10 09:00 | 24.77 µg/m³ |

---

## 4. Test.csv & SampleSubmission.csv Audit

- **Total Test Rows:** 2,592 unique IDs.
- **Total SampleSubmission Rows:** 2,592 unique IDs.
- **ID Sequence Parity:** `(Test["ID"] == SampleSubmission["ID"]).all() == True`.
- **Target Interval Duration:** Exactly 1 hour (`target_end_ist - target_start_ist == 1 hour`) for all 2,592 rows.
- **Scoring Block Distribution:**
  - `unscored`: 1,632 rows (historical public gap periods & late November buffer).
  - `public`: 768 rows (22 Oct – 07 Nov historical public blocks).
  - `private`: **192 rows** (the actual competition private evaluation window).

---

## 5. Private Evaluation Window & Physical Forecast Leads

The private evaluation block (`scoring_block == "private"`) comprises exactly 192 rows:
- **Date Range:** 2026-11-11 00:00:00+05:30 to 2026-11-13 00:00:00+05:30.
- **Rows per Station:** Exactly 48 hourly predictions per station across all 4 target stations.
- **Station Cutoff:** Every station has latest observation at **2026-11-10 09:00:00+05:30**.

### Per-Station Private Forecast Horizon & History Availability

| Location ID | Station Name | Station Cutoff (IST) | First Private Target Start (IST) | Min Lead (Hours) | Max Lead (Hours) | Private Rows | Recent 72h Obs Count | Recent 72h Median |
|---|---|---|---|---|---|---|---|---|
| **11606** | Borivali East | 2026-11-10 09:00 | 2026-11-11 00:00 | **15.0 h** | **62.0 h** | 48 | 66 | 45.93 µg/m³ |
| **11611** | Malad West | 2026-11-10 09:00 | 2026-11-11 00:00 | **15.0 h** | **62.0 h** | 48 | 65 | 56.48 µg/m³ |
| **3409510** | Byculla | 2026-11-10 09:00 | 2026-11-11 00:00 | **15.0 h** | **62.0 h** | 48 | 60 | 55.59 µg/m³ |
| **3409511** | Shivaji Nagar | 2026-11-10 09:00 | 2026-11-11 00:00 | **15.0 h** | **62.0 h** | 48 | 64 | 77.26 µg/m³ |

*Note: Target intervals span from `target_start` to `target_end`. Lead to target interval end is `16.0h` to `63.0h`.*

---

## 6. Repository Data Path Audit

All production and verification modules point directly to canonical datasets:

1. **Core Data Loading Module:**
   - [`src/mumbai_pm25/data.py`](file:///c:/Users/ram/Documents/Projects/aqi/src/mumbai_pm25/data.py): Default path `DATA_DIR = ROOT / "data" / "raw" / "challenge"`. Explicitly validates row counts (2,592 test rows, 4 stations), IST timezone offsets, non-negative values, and interval durations.
2. **Task 013 Inference Pipeline:**
   - [`scripts/generate_task013_submission.py`](file:///c:/Users/ram/Documents/Projects/aqi/scripts/generate_task013_submission.py): Reads `DATA_DIR / "Train.csv"`, dynamically computes station cutoffs (10 Nov 09:00 IST), and generates compliant 2,592-row submissions.
3. **Candidate C & Baseline Inference Pipeline:**
   - [`scripts/train_predict.py`](file:///c:/Users/ram/Documents/Projects/aqi/scripts/train_predict.py): Dynamically derives `pm_history_cutoff` from the canonical Train snapshot and computes `hist24_blend50_median72`.
4. **Climatology-First Production Pipeline:**
   - [`scripts/train_predict_climatology.py`](file:///c:/Users/ram/Documents/Projects/aqi/scripts/train_predict_climatology.py): Default path `DATA_DIR = ROOT / "data" / "raw" / "challenge"`.
5. **Cleaned Task 011 Baseline Runner:**
   - [`scripts/run_task011.py`](file:///c:/Users/ram/Documents/Projects/aqi/scripts/run_task011.py): Default CLI argument updated from `Train (2).csv` to `data/raw/challenge/Train.csv`.

---

## 7. Model Compatibility & Safeguards

The two candidate models remain fully operational and compatible with the updated data:

1. **Corrected Kernel Climatology Blend (Candidate 1):**
   - Formula: $0.50 \times \text{median72} + 0.50 \times \text{clean\_2024\_climatology}$
   - Temporal Eligibility: Strictly past-only relative to $\min(c_s, t_{\text{target}})$.
   - Clean 2024 Archive Climatology: Gaussian kernel ($\sigma_{\text{doy}}=10.0, \sigma_{\text{hour}}=1.0$) using `timestamp_median` aggregation over CPCB CAAQS series. Completely immune to 2025 raw Train telemetry corruptions.
   - Private prediction range: Min 31.84 µg/m³, Max 111.42 µg/m³, Mean 62.45 µg/m³.
2. **Candidate C (Candidate 2):**
   - Formula: `hist24_blend50_median72` with exact `month_day_365` seasonal calendar matching.
   - Private prediction range: Min 27.60 µg/m³, Max 114.71 µg/m³, Mean 63.82 µg/m³.

---

## 8. Issues Discovered and Fixes Applied

1. **`scripts/run_task011.py` Data Path:**
   - *Issue:* Defaulted to `data/raw/challenge/Train (2).csv` instead of `Train.csv`.
   - *Fix:* Updated default train path in `scripts/run_task011.py` line 229 to `ROOT / "data/raw/challenge/Train.csv"`.
2. **`tests/test_final_gap.py` 9 November Snapshot Gate Assertion:**
   - *Issue:* `test_submission_final_stage_rejects_initial_release_and_overwrite` asserted that running `prepare(data, stage="final")` raises a `ValueError` for the 9 November snapshot. Because `data/raw/challenge/Train.csv` was updated to the final 10 November release, it rightly succeeded instead of raising an error.
   - *Fix:* Updated the rejection check to use the preserved 9 November snapshot directory in `data/processed/task008_snapshots/e107dda1...` and verified that running with the canonical final release in `data/raw/challenge` produces a valid final run.
3. **`tests/test_independent_verification.py` Fold ID Assertion:**
   - *Issue:* `test_missing_targets_are_excluded_not_imputed` searched for fold IDs with `"20260903"` or `"20260813"`. When Train's latest timestamp advanced from 9 Nov 07:00 to 10 Nov 09:00, the 21-day rolling anchor shifted by one day (`20260904` and `20260814`).
   - *Fix:* Generalized the test to match fold IDs across anchor cycles (`20260904`, `20260814`, `20260903`, `20260813`), preserving the missing-target exclusion assertion.
4. **New Comprehensive Verification Suite:**
   - Added [`tests/test_task016_data_and_pipeline.py`](file:///c:/Users/ram/Documents/Projects/aqi/tests/test_task016_data_and_pipeline.py) covering all 12 programmatic verification checks required by the task.

---

## 9. Quality Gate Verification

- **Pytest:** **201 passed**, 0 failed in 27.09s across the complete repository test suite.
- **Ruff:** All checks passed across all new and modified modules.
- **Git State:** `git diff --check` clean. Branch `feat/competition-ml-pipeline` ready for final model generation and submission when requested by user.
