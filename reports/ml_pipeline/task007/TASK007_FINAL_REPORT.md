# TASK 007 — Final PM2.5 Model Optimisation and Seasonal Repair

**Date:** 2026-11-08
**Branch:** `feature/task007-final-model-optimisation`
**Status:** Current-snapshot work complete; final Train refresh and private-window rerun pending.

## Recommendation

Keep the repaired, source-restricted **P_fix** as the provisional fallback and do not promote F4 yet. F4 (fixed 25% ratio-model B, 25% diur7, 50% P_fix) scored better on the two late-October holdout origins, but it lost to P_fix across the 19 development folds at the actual 193-hour gap. The apparent holdout gain is based on only 318 labelled rows, with no extreme targets and two origins, so it does not establish stable seasonal or extreme-event performance. Re-evaluate after the advertised final Train refresh.

The final current-snapshot candidate is `artifacts/submissions/task007_provisional_pfix_current_train_v2.csv`, with manifest `artifacts/submissions/task007_provisional_pfix_current_train_v2.manifest.txt`. It is provisional, not a final competition submission. A first Task 007 draft candidate using a Mindspace source in the Malad mapping is retained unchanged for provenance, but superseded; do not submit `task007_provisional_pfix_current_train.csv`.

## Snapshot, timing and integrity

Train has 47,849 rows; its latest interval-end timestamp is **2026-11-02 23:00 IST**. Test has 2,592 rows, from 2026-10-22 00:00 to 2026-11-20 23:00 IST. SampleSubmission IDs match Test in exact order. The four competition stations are 11606 (Borivali East), 11611 (Malad West), 3409510 (Byculla), and 3409511 (Shivaji Nagar).

The expected private window starts **2026-11-11 00:00 IST**. The actual first-target lead from the latest Train interval end is **193 hours**; the 48 hourly targets span leads 193–240h. The per-station latest timestamps are all 2026-11-02 23:00 IST. No final Train refresh was present in the inspected snapshot. The submission manifest records the derived PM cutoff, all station cutoffs, model generation time, source lookup and raw-file hashes.

Raw input SHA-256 values (no raw file modified):

| File | SHA-256 |
|---|---|
| Train.csv | `fcee20ebf7bd9c4a4e2487bab0a4f81339d6c820a53862b14443031db1f18ad6` |
| Test.csv | `cdb2b6c3035f6331848c565b4d3dd89ac5281efab07fa62bfabc2e7ff172db0a` |
| SampleSubmission.csv | `5806d6109f381043e59fffb48a5d0af5d9de56fd4e0e956e4c5e7f2e6ae5dcd9` |
| Stations.csv | `383269fa04abf8f2eb49e5ec0bb5a77c2df11acb6aca996b7edf269a109ee9cf` |
| DataDictionary.txt | `0d10dcbb6d31232d29558ecd50e7a08272a393048d1e62e3ac460c5863522a55` |
| AdditionalHistory.zip | `3233061ca4ac2af39e9f6e80e21d9261b1b8d2fd3b037e5d034bcec059a7e80e` |

The provisional v2 CSV has 2,592 rows, exact `ID,Target` schema and Test order, 2,592 unique IDs, finite nonnegative targets (33.09–93.44). Its SHA-256 is `3d79cffcca78cea1ad6f5e24d2568bf931bbba8c3b15fcd7db1728462050ab1d`.

## Corrections and archive provenance

- Replaced station-name substring pooling with exact `series_id` selection while preserving archive provenance columns. CPCB-only rows are used; source coverage and missingness remain explicit.
- Changed day-of-year matching to month/day calendar alignment, with explicit Feb 29 behavior, circular date windows of ±7/±14/±21 days, and -1/0/+1 hour alignment sensitivity.
- Kept low-coverage profiles unavailable rather than presenting them as reliable measurements.
- Aligned production and pseudo-origin baseline behavior through a shared prediction function and restored Task 005 diur7 cleaning/profile coverage rules.
- Corrected all pseudo-origin leads to target-start minus the PM cutoff. The first target lead is the configured gap; 48-hour target rows use leads `gap` through `gap+47`.
- Validation freezes the PM information set at each origin and records issue/cutoff, target start/end, per-station last available observation, gap and lead. Validation labels remain unmodified.

Archive candidates selected on development folds at the 193-hour gap:

| Competition station | P_fix archive candidate | Development RMSE of station blend | Mean profile coverage | Qualification |
|---|---|---:|---:|---|
| Borivali East | `xkdr:site_5400` | 16.113 | 0.776 | Predictive candidate; physical equivalence unverified |
| Malad West | `xkdr:site_5102` + `xkdr:site_5402` | 18.858 | 0.739 | Explicit combination; no identity claim |
| Byculla | `xkdr:site_5960` | 15.324 | 0.958 | Named source candidate |
| Shivaji Nagar | `xkdr:site_5961` | 51.205 | 0.733 | Named source candidate; high station error |

Mindspace `xkdr:site_5807` remains a separate diagnostic candidate. Its 18.697 development RMSE for the Malad competition rows does not establish sensor identity and it is excluded from P_fix and production inference. Coverage for Shivaji Nagar is modest; seasonal fallback remains important.

## Validation design

The main comparison uses 48-hour chronological target windows, 28-day origin spacing, fixed PM cutoff, and the exact 193-hour gap. Twenty development origins end by 2026-09-30; two later origins (2026-10-20 and 2026-10-27 IST) are held out after source/model/weight selection. The holdout origins were reserved before this task, but earlier Task 005/006 reports examined overlapping broad seasonal regimes; this is not a wholly analyst-blind dataset. At the supervised model’s common support there are 2,656 development rows across 19 eligible origins (one early origin lacked the required training volume) and 318 holdout rows across two origins. Seasonal baseline common support has 2,820 development rows and 318 holdout rows.

Paired confidence intervals are moving-block bootstrap intervals over development fold-level squared errors (block length two adjacent origins, 2,000 resamples, fixed seed). They do not correct for candidate/source selection on development folds. No holdout confidence interval is reported because only two origins are available. Metrics use full raw target labels and full-target RMSE as primary; clean RMSE (`y < 500`) is diagnostic.

### Actual 193-hour gap: seasonal baselines

| Model | Regime | Full RMSE | Clean RMSE | MAE | Bias | Paired Δ vs P_fix (95% CI) | Rows / origins |
|---|---|---:|---:|---:|---:|---:|---:|
| median72 | Dev | 33.110 | 23.779 | 15.495 | -5.110 | +2.929 [-0.033, 5.017] | 2,820 / 20 |
| diur7 | Dev | 33.983 | 25.212 | 16.230 | -2.575 | +3.802 [0.197, 6.247] | 2,820 / 20 |
| Original production | Dev | 30.192 | 20.481 | 13.597 | -2.101 | +0.011 [-0.527, 0.329] | 2,820 / 20 |
| P_fix | Dev | 30.181 | 20.464 | 13.515 | -1.011 | 0.000 [0.000, 0.000] | 2,820 / 20 |
| P_fix | Holdout | 20.948 | 20.948 | 17.910 | +3.546 | 0.000 (CI unavailable) | 318 / 2 |
| median72 | Holdout | 23.177 | 23.177 | 20.462 | +1.946 | +2.229 (CI unavailable) | 318 / 2 |
| diur7 | Holdout | 17.724 | 17.724 | 15.349 | -3.792 | -3.224 (CI unavailable) | 318 / 2 |

The original production blend and P_fix are nearly tied on development folds. P_fix’s point estimate is 0.011 RMSE below original production; its paired interval includes zero. P_fix is also 2.229 RMSE better than median72 on the two holdout origins.

### Actual 193-hour gap: supervised B and F4

| Model | Regime | Full RMSE | Clean RMSE | MAE | Bias | Paired Δ vs P_fix (95% CI) | Rows / origins |
|---|---|---:|---:|---:|---:|---:|---:|
| Ratio B (Huber selected in dev) | Dev | 35.970 | 27.211 | 16.827 | -0.313 | +5.370 [-0.345, 11.251] | 2,656 / 19 |
| Ratio B (Huber selected in dev) | Holdout | 17.429 | 17.429 | 14.726 | +6.101 | -3.519 (CI unavailable) | 318 / 2 |
| F4 fixed 25/25/50 | Dev | 32.224 | 22.386 | 14.141 | -0.639 | +1.624 [-0.860, 3.399] | 2,656 / 19 |
| F4 fixed 25/25/50 | Holdout | 13.618 | 13.618 | 11.212 | +2.350 | -7.330 (CI unavailable) | 318 / 2 |
| F4 grid-selected 12.5/12.5/75 | Dev | 31.283 | 21.185 | 13.560 | -0.370 | +0.683 [-0.543, 1.510] | 2,656 / 19 |
| F4 grid-selected 12.5/12.5/75 | Holdout | 17.103 | 17.103 | 14.306 | +2.948 | -3.845 (CI unavailable) | 318 / 2 |

The ratio model uses all eligible training labels, station one-hot features, cyclic annual time, actual forecast lead, recent level/history/profile features and no previous-year predictor or multiplicative smearing. The selected ratio variant was Huber loss; raw day-of-year, cyclic, direct-target and baseline-residual variants were also tested. The best individual development candidate was direct-target LightGBM (31.623 RMSE), still worse than P_fix (30.600 on the identical supervised common support). F4 fixed loses to P_fix on development and wins on both holdout origins; F4’s holdout gain is not sufficient evidence to promote given only two origins and its development loss.

### Gap sensitivity and diagnostics

The same seasonal source-selection/control evaluation was run at 48, 72, 73, 96 and 193-hour PM gaps. Full summaries, paired CIs, per-station, lead-day and alignment sensitivity tables are under `reports/ml_pipeline/task007/seasonal_final_gap{48,72,73,96}/` and `seasonal_repaired_v4/` for 193h. At each historical gap, P_fix was selected on development among the approved Borivali and Malad source choices; Mindspace was not eligible for the P_fix mapping. The 73-hour run is retained separately because exact operational gaps need not be multiples of 24.

| Gap | P_fix dev RMSE | Original blend dev RMSE | P_fix holdout RMSE | Original blend holdout RMSE |
|---:|---:|---:|---:|---:|
| 48h | 28.474 | 28.427 | 15.999 | 15.858 |
| 72h | 29.787 | 29.736 | 17.080 | 16.918 |
| 73h | 29.811 | 29.760 | 17.099 | 16.936 |
| 96h | 30.301 | 30.263 | 17.573 | 17.991 |
| 193h | 30.181 | 30.192 | 20.948 | 21.430 |

Thus P_fix and the original blend are close on development folds. The original blend is marginally better on the 48/72/73-hour holdout; P_fix is slightly better at the actual 193-hour holdout gap. The 96-hour gap is included as historical sensitivity, not treated as independent evidence from the adjacent 72/73-hour comparisons.

At 193h, F4 fixed reduced RMSE relative to P_fix in the holdout on each station (11606: 11.16 vs 16.87; 11611: 15.33 vs 24.07; 3409510: 15.80 vs 22.51; 3409511: 11.90 vs 20.19), on both holdout origins (11.48 vs 16.15 and 16.01 vs 25.96), and both target days (12.40 vs 18.75; 14.52 vs 22.54). This consistency is encouraging, but remains only two origins. The ratio model’s holdout bias is +6.10, compared with +2.35 for F4 and +3.55 for P_fix.

There were four validation targets above 500 in development and none above 1,000; neither holdout origin contained a target above 500. Thus extreme-event fold RMSE and squared-error share above 1,000 are uninformative here (zero extreme folds/zero contribution), not evidence that models handle extreme pollution well. No validation targets were clipped, deleted or winsorised.

Weather was **not run**: `weather_single_runs.csv` was absent, so no archived forecast vintages or verified publication/availability times were available. No observed/reanalysis weather substitute was used. Cross-station donor features were not prioritised, consistent with earlier unstable Task 006 findings.

## Candidate artifact, tests and remaining work

The provisional candidate uses the shared production inference and exact P_fix source mapping, derives PM cutoff from Train, and preserves SampleSubmission order. The earlier Task007 candidate using `site_5807` for Malad remains unchanged solely as an audit artifact; it is superseded and must not be submitted. The final refresh run must use the refreshed Train snapshot and recompute the actual per-station cutoffs/gap, then regenerate and verify a uniquely named candidate and manifest.

Commands run:

- `.venv\Scripts\python.exe -m pytest` — **44 passed** (3.62s).
- `.venv\Scripts\python.exe -m ruff check src/mumbai_pm25 scripts/train_predict.py scripts/validate_seasonal_history.py scripts/validate_task007_seasonal.py scripts/validate_task007_lightgbm.py tests/test_ml_pipeline.py tests/test_seasonal_history.py` — passed.
- A broader Ruff invocation that included `tests/test_forecast_artifact.py` reports one pre-existing import-order issue in that untouched file; the scoped changed-file lint above passes.
- `.venv\Scripts\python.exe scripts\validate_task007_seasonal.py --gap-hours {48,72,73,96,193} ...` — completed; detailed commands/results are represented by the separate gap output directories.
- `.venv\Scripts\python.exe scripts\validate_task007_lightgbm.py --seasonal-oof ...seasonal_repaired_v4\seasonal_oof_gap193.csv.gz --output-dir ...supervised_gap193_v5 --gap-hours 193` — completed with LightGBM 4.7.0.99.
- `.venv\Scripts\python.exe scripts\train_predict.py --model hist24_blend50_median72 --model-run-time 2026-11-08T01:03:15+05:30 --output artifacts\submissions\task007_provisional_pfix_current_train_v2.csv` — completed; 2,592 outputs and manifest written.

LightGBM 4.7.0.99 came from the official nightly Windows ARM64 wheel because the stable package did not offer a compatible wheel in this environment. The wheel was installed only in the local virtual environment; it is not committed. This limits exact environment reproduction and should be revisited on the final run.

No final Train refresh was present. Commit `7f69692` was pushed on `feature/task007-final-model-optimisation`; [PR #4](https://github.com/acchasujal/aqi/pull/4) is open for review and has not been merged. The provisional submission CSV/manifest are local ignored artifacts and are not included in the PR. The source-specific P_fix selection is predictive, not proof of sensor equivalence. Revisit the recommendation after the final data refresh, and promote F4 only if it continues to improve full-target RMSE on sufficiently many untouched origins and across station/lead diagnostics.
