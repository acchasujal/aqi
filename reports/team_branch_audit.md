# Team Branch Integration and Architecture Audit (Task 009)

**Audit Date:** 2026-11-09  
**Auditor:** Senior Data Scientist, ML Engineer, and Software Architect  
**Repository:** `acchasujal/aqi`  
**Base Commit of Divergence:** `9d3fad0` ("Merge pull request #3 from acchasujal/feature/ml-pipeline-v1")  
**Integration Merge Commit:** `efa053a`  

---

## 1. Executive Summary

Task 009 required auditing and integrating valuable contributions across all teammate branches into the primary working branch `feat/competition-ml-pipeline`.
Prior to any modifications, an immutable safety backup branch `backup/feat-competition-ml-pipeline-pre-task009` was created at commit `a191dba`.

All branches originated from common ancestor `9d3fad0`. Through systematic inspection, we identified two main parallel workstreams developed across the team:

1. **Teammate Workstream (Codex / shriza1991 / Creative Track):**
   - Conducted experiments EXP-008 through EXP-015, TASK007, TASK008, EXP-024, EXP-025, and AirWindow 2.0/2.1.
   - Refactored `src/mumbai_pm25/historical_archive.py` with exact `series_id` mapping (`P_FIX_SERIES`), isolating legacy name pooling in `src/mumbai_pm25/legacy_seasonal.py`.
   - Developed the full AirWindow 2.0/2.1 creative award package (`apps/airwindow/`, reports, and submission PDF).
   - Ingested NOAA GFS weather forecasts and CAMS archive inquiries.
   - Published the official 9 November Train refresh (`0735651`) adding 284 rows up to 9 Nov 07:00 IST.

2. **ML Pipeline Workstream (`feat/competition-ml-pipeline`):**
   - Implemented fixed-origin chronological validation framework with decoupling of issuance time, PM cutoff, target interval, and block horizon.
   - Built the modular feature engineering system (calendar, PM history, spatial interactions, seasonal climatology).
   - Built multi-model benchmarking (CatBoost, LightGBM, XGBoost, Random Forest, statistical baselines).
   - Benchmarked target transformations (`log1p`, `sqrt`, `raw`).
   - Implemented 9 standardized chronological validation folds ($N=1,316$) spanning autumn and winter regimes.
   - Formulated Candidates A, B, C, and D, and executed extreme-observation sensitivity audits.

Both workstreams were integrated into `feat/competition-ml-pipeline` at merge commit `efa053a`. All 166 pytest tests pass with zero failures (100% passing).

---

## 2. Detailed Audit of Teammate Branches

### A. `origin/feature/task007-final-model-optimisation`
- **Commits:** `7f69692`, `d7bfbdb`.
- **Primary Contribution:** Repaired seasonal provenance by identifying that broad substring matching for Malad West included Mindspace (`site_5807`). Discovered that P_fix mapping (`site_5400`, `site_5102` + `site_5402`, `site_5960`, `site_5961`) improved stability. Evaluated LightGBM F4 at 193h lead.
- **Integration Status:** Subsumed into `origin/main` at commit `d9bead4` and now fully integrated into `feat/competition-ml-pipeline`.

### B. `origin/feature/task008-final-gap-execution`
- **Commits:** `1864636`, `b8aed54`, `2f3b1ae`.
- **Primary Contribution:** Built fixed-origin final-gap evaluation across 69 development origins (11,001 rows) and 8 confirmation origins (1,400 rows) at nominal 193h gap. Preserved P_fix fallback. Prepared `scripts/prepare_task008_submission.py` to freeze inputs and verify deterministic inference. Built AirWindow 2.0 with separate forecast and replay contracts.
- **Integration Status:** Subsumed into `origin/main` at commit `d44e02c` and now fully integrated into `feat/competition-ml-pipeline`.

### C. `origin/main`
- **Commits on top of TASK008:**
  - `5d3476b`: EXP-024 / EXP-025 candidate audit. Replicated Candidate C predictions; analyzed Candidate B horizon calculation.
  - `c62ef8f`: EXP-025-WEATHER: audited NOAA GFS runs and CAMS atmospheric data. Gated weather promotion due to lack of historical operational issue timestamps.
  - `dba644a`: Verified weather ingestion publication.
  - `16e479d`, `04ad73c`: AirWindow 2.1 verified main publication.
  - `0735651`: Updated official competition data (`Train.csv` with 48,133 rows).
- **Integration Status:** Fully merged into `feat/competition-ml-pipeline` (`efa053a`).

---

## 3. Conflict Analysis and Resolution

Eight files exhibited merge conflicts, which were resolved per `AGENTS.md` Rule 6 without blindly picking "ours" or "theirs":

| Conflicted File | Nature of Conflict | Resolution Strategy |
|---|---|---|
| `.gitignore` | Different ignore rules for intermediate caches | Merged both: retained ML caches (`catboost_info/`, `wandb/`) and TASK008 / EXP-024 intermediate ignores, added `/data/processed/`. |
| `DECISIONS.md` | Concurrent decision additions | Sequentially preserved all decisions. Prefixed ML Pipeline decisions (`DEC-20261108-11A`..`14A`) and Teammate decisions (`DEC-20261108-11B`..`18B`) to guarantee unique record identity and complete audit trail. |
| `PROGRESS.md` | Concurrent chronological progress records | Concatenated both progress records in chronological order, documenting all experiments without deleting any entry. |
| `scripts/train_predict.py` | Model support & CLI arguments (`--calendar-mode`, `--seasonal-weight` vs ensemble types) | Unified parser: supports all baseline and ensemble models (`median72`, `hist24_blend50_median72`, `ensemble_accuracy`, `ensemble_robust`, `ensemble_balanced`), both calendar modes, and cryptographic manifests. |
| `src/mumbai_pm25/forecast.py` | Feature extraction & helper functions | Retained rich `history_features` dictionary (latest PM, age, rolling medians, coverage) while integrating `recent_median72` and `combine_forecasts`. `predict_test_ensemble` and `predict_test_with_hist24_blend` unified. |
| `src/mumbai_pm25/historical_archive.py` | P_fix exact series mapping vs vectorized lookup & leap-year alignment | Integrated both: retained exact `P_FIX_SERIES` and `ARCHIVE_SERIES`, `_build_exact_seasonal_features`, while preserving `normalized_doy`, `circular_doy_distance`, `_match_archive_station`, and `compute_station_seasonal_profiles`. |
| `src/mumbai_pm25/validation.py` | Fold generation & OOF columns (`forecast_lead_hours`) | Preserved `ValidationFold` and `generate_fixed_target_folds`, added `forecast_lead_hours` to output DataFrame for 100% backward compatibility. |
| `tests/test_seasonal_history.py` | Additional regression tests from both branches | Preserved all tests: station mapping exclusions, leap-year alignment, multi-series aggregation, and sparse-history inference matching. |

---

## 4. Verification and Regression Testing

Following conflict resolution, regression testing was conducted using pytest and ruff:
- **Pytest Suite:** 166 passed, 0 failed, 19 warnings in 12.94s.
- **Ruff Code Style:** All checks passed with zero errors.
- **Data Integrity:** `data/raw/challenge/` audited and verified immutable; SHA-256 digests preserved.
