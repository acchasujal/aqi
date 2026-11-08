# TASK008 execution report — 8 November 2026

**Current achievable work completed; final official refresh and platform submission pending.** Retain **P_fix**, with **median72** as the explicit fallback. No new model is promoted. No public leaderboard score or private-label performance is claimed.

## Branch, code and inputs

Branch: `feature/task008-final-gap-execution`, based on exact reviewed TASK007 commit `d7bfbdbaa0b112d8dc2c9341cd731287d4b57d92`. PR #4 remains open/unmerged; current main `d9bead48951b3f584ce4a8e0ba79f97950fa1edb` is preserved separately. PR/base/code review is in `PR_BASE_REVIEW.md`. The run manifests record the starting HEAD because implementation was uncommitted during execution; `run01/result_audit.json` records exact implementation/config/test SHA-256 hashes so those results are not attributed to unchanged base code. The completion commit is recorded in the final handoff entry.

Actual local raw byte hashes (these supersede assumptions about attached reports' copies):

| Input | SHA-256 |
|---|---|
| Train.csv | `fcee20ebf7bd9c4a4e2487bab0a4f81339d6c820a53862b14443031db1f18ad6` |
| Test.csv | `cdb2b6c3035f6331848c565b4d3dd89ac5281efab07fa62bfabc2e7ff172db0a` |
| SampleSubmission.csv | `5806d6109f381043e59fffb48a5d0af5d9de56fd4e0e956e4c5e7f2e6ae5dcd9` |
| Stations.csv | `383269fa04abf8f2eb49e5ec0bb5a77c2df11acb6aca996b7edf269a109ee9cf` |
| DataDictionary.txt | `0d10dcbb6d31232d29558ecd50e7a08272a393048d1e62e3ac460c5863522a55` |
| AdditionalHistory.zip | `3233061ca4ac2af39e9f6e80e21d9261b1b8d2fd3b037e5d034bcec059a7e80e` |

Train has 47,849 rows. All four stations' latest interval end is **2 November 23:00 IST**. Train interval ends map to hour starts by subtracting one hour; Test already uses hour starts, verified from the actual dictionary and loader. The current 11–12 November private grid has 192 rows with actual PM leads **193–240 hours**. These are recalculated snapshot properties, not final-refresh constants. The attachments quote different Train/Test byte hashes; equivalence of those copies is not established. Local files were never edited, and all seven raw-directory file hashes were rechecked unchanged after the run.

Environment: Python 3.12.10 Windows ARM64, pandas 3.1.1, NumPy 2.5.4, SciPy 1.18.1, scikit-learn 1.9.1, LightGBM **4.7.0.99 nightly**, pytest 8.4.2, Ruff 0.17.4. No dependency installation or lockfile change. Reproduction on another platform should check this nightly build explicitly.

## Implemented and run

- **EXP-016:** hashed 198 raw/supplied/prior artifact files, ZIP members and six local candidate CSVs/manifests. Preserved superseded artifacts. Low/High each pass exact 2,592 ordered IDs and finite/nonnegative checks; max High−Low×(1.40/.95) difference is `1.4210854715202004e-14`. Reconstructed `low/.95` is local reference only. Its forecast issue time/training lineage is unknown, so no OOF, public score or blend weight is assigned.
- **EXP-017:** reusable 48-hour fixed-origin evaluator, explicit issue/PM cutoff/last PM end/target interval/actual lead, complete station-hour grid, strict past-only predictors, full-block training availability and shared inference parity. Missing prediction coverage is reported; a candidate with missing forecasts receives no full-target score. Preserved all labelled evaluation truth. Fixed an absent-source sum-metadata bug in the identity-preserving archive loader.
- **EXP-018:** medians 24/72/168, EWM, original diur7, raw diurnal profile, supported hour-of-week profile and horizon-shrunk shape. EWM/raw profiles are vulnerable to historical extremes and did not earn promotion.
- **EXP-019:** current 28-day normal and exact-source archive normal; constant, piecewise and smooth anomaly-decay curves. Source sensitivity substitutes Borivali 5113 and each Malad source separately, without Mindspace, as diagnostics only. No stable source/decay improvement.
- **EXP-020:** three compact deterministic LightGBM formulations: raw delta, `log1p(y)-log1p(level)` (offset 1 handles zero without deleting labels), and square root inverted before raw-scale scoring. All legitimate fitting labels retained; no donor features, tuning search or label clipping. Training uses only complete prior blocks available by fitting cutoff; native missing-value handling is fitted inside each fold.
- **EXP-022:** selected one candidate per family using development only; tested three fixed weights against P_fix. Frozen selection file precedes calculation of confirmation metrics. No candidate is promoted.
- **EXP-021:** **NOT TESTED**; no verified permitted as-issued weather vintages available.
- **EXP-023:** final-refresh experiment **NOT RUN** because its future input is unavailable. Implemented and verified snapshot preservation, provisional inference, deterministic rerun, final-stage guards and output audit now.

The supplied TASK006 ZIP was inspected without executing its code. Its scripts depend on `/mnt/data/exp008_8origins.py`, which is absent from the ZIP, use machine-specific paths and differing origin conventions. Its historical scores remain external exploratory evidence and were not imported as matched TASK008 OOF results. Main's EXP-008–015 reports and code were inspected from Git objects; their retained W50 decision and reused-fold limitations remain preserved on main.

## Fold support and metrics

Predeclared weekly non-overlapping 48-hour windows from 5 April 2025 through 31 October 2026, with nominal PM gap 193h. All labels within each scheduled target block are scored; missing targets remain missing. The primary schedule is independent of target magnitude. It is not a claim that every station has 48 observed labels.

- 83 scheduled origins / 15,936 possible station-hours; 81 data-bearing origins / **13,115 labelled rows** for the baseline coverage report; no unsupported-history labelled rows.
- The predeclared >=500 prior eligible training-label gate leaves **77 matched origins / 12,401 rows** for all supervised/baseline/blend comparisons. Four early data-bearing origins (714 rows) lack supervised training support; two scheduled blocks have no labels. Baseline-only metrics on all 13,115 rows are saved separately, not used to claim a supervised gain.
- Development: **69 origins / 11,001 rows** before September 2026. Confirmation: **eight origins / 1,400 rows** between 5 September and 31 October 2026; 24 October has no labels.
- Development has eight labels >1,000, maximum 75,203.525. The schedule does **not** include the dataset's 241,587.56 maximum or every historical extreme. P_fix extreme labels contribute **99.846%** of development squared error. Confirmation has no >1,000 labels.

| Candidate | Development full RMSE | Confirmation full RMSE |
|---|---:|---:|
| P_fix | 757.9880 | 15.7963 |
| median72 | 758.0564 | 15.5786 |
| median24 | 757.9964 | 13.5857 |
| archive decay, half-life 168h | 757.9922 | 17.2336 |
| LightGBM delta | 762.8894 | 64.0780 |
| LightGBM log ratio | 758.8411 | 13.7481 |
| LightGBM square root | 758.1678 | 18.8809 |
| Development-selected 50% P_fix + 50% median24 | **757.9741** | **13.7909** |

Full station/origin/lead/day RMSE, MAE, bias, clean diagnostic, counts, missing coverage and tail share are in `run01/development/` and `run01/confirmation/`. P_fix development clean diagnostic RMSE is 23.2525; it does not replace full RMSE. Original diur7 is missing on 632 development rows, so its development full score is unavailable rather than evaluated on an easier subset.

Development-selected blend minus P_fix RMSE is **−0.01393**, with 95% paired moving-block interval **[−0.05390, +0.44730]**, 31/69 origin wins and **1/4 station wins**. Four adjacent weekly origins per bootstrap block, 2,000 repetitions, seed 20261108. Confirmation delta is −2.00546, interval [−2.67253, −0.31675], six/eight origin wins, four/four station wins. The development uncertainty includes zero; aggregate gain is tiny and uneven. The later result cannot reverse a failed development stability gate.

Historical rows have already been broadly inspected in earlier tasks. The later windows are chronological confirmation, **not an untouched holdout**. No independent promotion claim is possible on this snapshot. Source sensitivity intervals also cross zero: switching Borivali to 5113 worsens confirmation RMSE to 16.3399; single-source Malad 5102 gives 15.7925, only 0.0038 better with wide uncertainty. Preserve the reviewed predictive source policy.

## Provisional artifact and final readiness

Generated `artifacts/submissions/task008_provisional_pfix_20261108_1558.csv` with companion `.audit.json` and `.rows.csv`. It has **2,592 exact ordered unique IDs**, exact `ID,Target`, finite/nonnegative values and an **exact deterministic rerun**. SHA-256:

`3d79cffcca78cea1ad6f5e24d2568bf931bbba8c3b15fcd7db1728462050ab1d`

Maximum absolute difference from Task007 v2 is **0.0**. Inputs were copied to an ignored hash-addressed snapshot and checked unchanged. No submission CSV or input snapshot is committed. This is a current-data candidate; the final official-data artifact is **PENDING**.

The final-stage command and checklist are in `FINAL_REFRESH_RUNBOOK.md`. It refuses known initial snapshots, snapshots without newer PM history, invalid clocks and reused artifact names. The operator must establish that a download is the official final release; a release-time argument alone cannot prove provenance. Actual refreshed station leads must be audited, then the intended CSV must be manually submitted or separately authorised and its successful Zindi processing verified.

## Exact commands and observed results

```powershell
git fetch origin
git switch -c feature/task008-final-gap-execution
.venv\Scripts\python.exe scripts/audit_task008_inputs.py --supplied-dir C:\Users\sujal\Downloads
.venv\Scripts\python.exe -m pytest -q tests/test_final_gap.py -p no:cacheprovider --basetemp data/processed/task008-tests-3
.venv\Scripts\python.exe scripts/run_task008.py --output reports/ml_pipeline/task008/run01
.venv\Scripts\python.exe scripts/task008_source_sensitivity.py --run-dir reports/ml_pipeline/task008/run01
.venv\Scripts\python.exe scripts/prepare_task008_submission.py --issue-time 2026-11-08T15:58:00+05:30 --output artifacts/submissions/task008_provisional_pfix_20261108_1558.csv
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp data/processed/task008-tests-final
.venv\Scripts\python.exe scripts/audit_task008_results.py --run-dir reports/ml_pipeline/task008/run01 --candidate artifacts/submissions/task008_provisional_pfix_20261108_1558.csv
.venv\Scripts\python.exe -m ruff check src/mumbai_pm25 scripts/train_predict.py scripts/run_task008.py scripts/audit_task008_inputs.py scripts/audit_task008_results.py scripts/prepare_task008_submission.py scripts/task008_source_sensitivity.py tests/test_ml_pipeline.py tests/test_seasonal_history.py tests/test_final_gap.py
git diff --check
```

All experiment, source-sensitivity, inference and result-audit commands completed. Focused evaluator/model tests: **8 passed** before the run. Final full branch suite: **53 passed in 7.13s**. Scoped Ruff: **all checks passed**. Initial default-temp base test run had two fixture permission errors (42 passed); workspace-temp retry passed all 44 base tests. A new test initially used integer dtype for a fractional extreme and failed; corrected to float before running experiments. Broader lint found one pre-existing import-order issue in the creative test, which is outside this task. Final diff check is recorded in the completion handoff; no unrun test is claimed.

## Remaining uncertainty and next action

Official public-window conflict and actual submission controls remain unresolved; see `ORGANISER_RULES_SNAPSHOT.md`. Discussion URLs returned generic Info content. Exact archive sensor identity and interval semantics remain unverified. Historical first-publication times are unknown, so interval end is an explicit proxy. Nightly LightGBM portability and extreme-event uncertainty remain material. No weather claim, F4 promotion or Vaibhav model attribution is made.

Next: preserve the actual 9/10 November official releases, recheck active rules and legitimately released labels, rerun the retained pipeline at actual cutoffs, then obtain human platform action/authorisation and confirm successful processing. Do not fabricate completion of those future steps.
