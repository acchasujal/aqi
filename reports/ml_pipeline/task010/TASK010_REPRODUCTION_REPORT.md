# TASK010 reproduction and EXP030 audit

**Date:** 9 November 2026 (IST)  
**Status:** Completed with limitations; no final submission generated.  
**Branch:** `main`, starting commit `0735651dcec9af6ef7c53ec822ec6b8a8c088b53`. The fetched candidate branch is read at `origin/feat/competition-ml-pipeline` (`4be5c10`); it was not merged or checked out.

## Result

The owner-supplied 9 November Train file has 48,133 rows and parses exactly equal to the Train file on the fetched team branch. Its downloaded CRLF SHA-256 is `11d6c4a4b20cc9ccf212b5e5f683ff5cc41f032fa0681e461b22fe0bd41047ee`; the team's LF-form SHA-256 is `e107dda18670583c333be0966530fc444c18fdb30c870156ac25688a2c152210`. All station cutoffs match the brief. The input was copied byte-for-byte into ignored `data/processed/task010/input_snapshot/Train_20261109.csv`. The download URL/receipt was not supplied, so its official origin is not independently authenticated.

On a new nine-origin, station-specific 41–43 hour first-target-gap experiment, P_fix and the exact month/day 2024 seasonal blend tie at raw full-target RMSE **27.3948** over **1,475** labelled rows. This tie is expected: with the same P_fix source IDs, exact month/day seasonality and a 50:50 median72 blend are the P_fix definition. Legacy 365-day DOY alignment scores **27.9122**. Exact month/day lowers RMSE by **0.5175**, but the paired moving-origin 95% interval is **[-1.0169, +0.0377]**, so the improvement is not conclusive. Median72 alone is **28.4303** and loses to P_fix by **1.0355** (95% interval **[+0.2172, +1.8130]**).

The existing team OOF file can be reaggregated and does reproduce its Candidate C/B/D figures on its own 1,460 rows: **28.1984 / 29.1840 / 28.3861** RMSE. Those values are reference evidence only: that fold file has different target starts and a common nominal 48-hour cutoff, so it is not the corrected station-specific 41–43-hour experiment. CatBoost is not installed in this Windows ARM64 environment; Candidate B and D were not retrained or independently reproduced. EXP030 A/B and the TASK012 blend are valid test-grid forecasts, but there are no supplied manifests or validation labels for them. Their private predictions cannot be scored from the available data.

**Recommendation for the 10 November final refresh:** retain Candidate C / P_fix as the primary. Candidate B remains the branch's previously selected hedge because it had the best clean/autumn diagnostics in the branch's older OOF, but do not represent it as validated under the corrected 41–43-hour protocol. Generate C and B only after the final Train release arrives and B can be run in a compatible CatBoost environment. If that runtime is unavailable, do not silently substitute EXP030 or Candidate E; use the documented P_fix/median72 operational fallback policy and disclose that it is a weaker second model. No private score is known.

## Branch reconciliation

The branch has **25 commits** beyond `origin/main` and 113 changed paths. The report's 41–43 versus 41–90 hour statements describe different points in one forecast: the first target starts 41–43 hours after each station's latest PM interval end; the 48-hour block then reaches leads of 88–90 hours. The task010 fold rows carry `prediction_origin`, `pm_history_cutoff`, target start/end and physical lead separately.

The row-count/RMSE disagreement is a stale-artifact issue:

| Artifact | Rows / folds | Candidate C | Candidate B | Candidate D | Interpretation |
|---|---:|---:|---:|---:|---|
| `reports/final_candidate_comparison.csv` | 1,316 / 9 | 29.2979 | 30.6547 | 29.5751 | Older report committed with the earlier model-selection study; its fold IDs include Aug 6, Aug 27, Sep 17, Oct 8 and Oct 29. |
| `reports/oof_predictions_task009.csv.gz` (recomputed) | 1,460 / 9 | 28.1984 | 29.1840 | 28.3861 | Later branch OOF; its folds include Aug 13, Sep 3, Sep 24, Oct 15 and Nov 5. The current `all_candidate_comparison.csv` and TASK009 summary are consistent with this OOF. |
| TASK010 station-gap run | 1,475 / 9 | P_fix/exact C 27.3948 | not run | not run | New midnight-aligned target blocks and station-specific 41–43h cutoffs; same 1,475 labels for each scored baseline. |

The first two rows do not share the same validation row set or fold dates, so their RMSEs cannot be reconciled by rounding. Candidate C/B manifests cite the team Train hash above; that release is parsed-equal to the supplied download. Their committed CSV hashes match the manifest hashes after restoring Windows CRLF line endings. Candidate C's manifest identifies `hist24_blend50_median72`; Candidate B's identifies `ensemble_robust` (50% CatBoost log1p + 50% C). The manifest evidence verifies the referenced input/output artifacts, but this run did not regenerate either candidate CSV. The team CLI only offers `legacy_doy` and `month_day_365`; neither is the exact leap-year month/day mapping used by current main P_fix. The checked-in C/B manifests both record `legacy_doy`, so do not describe those artifacts as using the exact calendar fix.

The Task009 validation code uses fixed 48-hour cutoffs and block-hour features 1–48. It is not a substitute for the newly run station-specific PM-history cutoffs. The exact first-target gaps from the 9 November file are:

| Station | Latest interval end (IST) | First target gap | Lead to block end |
|---|---|---:|---:|
| 11606 | Nov 9 06:00 | 42h | 89h |
| 11611 | Nov 9 07:00 | 41h | 88h |
| 3409510 | Nov 9 05:00 | 43h | 90h |
| 3409511 | Nov 9 07:00 | 41h | 88h |

## Matched station-gap results

All model scores use the same 1,475 unmodified labelled targets across nine 48-hour origins. Four labels are at least 250; they remain in primary full-target RMSE. No validation labels were clipped, removed or winsorised. The `y < 500` column is diagnostic only.

| Model | RMSE | MAE | Bias | RMSE, y < 500 | RMSE, y ≥ 250 (n=4) | Fold RMSE SD | Missing |
|---|---:|---:|---:|---:|---:|---:|---:|
| P_fix / C exact month-day | **27.3948** | 12.3887 | -1.3119 | 18.7217 | 440.7474 | 22.4225 | 0 |
| Candidate C, legacy_doy calendar | 27.9122 | **12.2368** | -1.7433 | 18.7747 | 454.9425 | 23.0924 | 0 |
| median72 | 28.4303 | 12.4586 | -8.6937 | 19.5376 | 454.9425 | 22.8262 | 0 |

Across these folds, the four `y ≥ 250` observations account for about **70.2%** of P_fix squared error. Removing them is shown only as a sensitivity calculation in `run06/model_metrics.csv`; the primary metric retains them. Station, fold, lead-bucket, residual/prediction correlation and bootstrap tables are in `run06/`.

Exact month/day alignment maps (for example) 9 November 2026 to 9 November 2024, using the leap-year archive as a calendar. `legacy_doy` compares day numbers on a 365-day cycle and shifts dates after February 2024 by one day. A regression test locks this edge behavior. The tested seasonal source IDs are held constant at the reviewed P_fix mapping, so this comparison isolates calendar alignment.

### Team branch OOF reference (not the corrected station-gap run)

| Candidate | RMSE | MAE | Bias | RMSE, y < 500 |
|---|---:|---:|---:|---:|
| Candidate C | **28.1984** | 12.4286 | -3.4719 | 19.0497 |
| Candidate D | 28.3861 | **12.2315** | -4.8984 | 19.0083 |
| Candidate B | 29.1840 | 12.4927 | -7.0381 | 19.7145 |

Candidate B's branch OOF clean diagnostic was best among the three under the branch's `y < 50` definition. Its residual correlation with C was **0.9766** (prediction correlation **0.9517**), so it is only a modest hedge. Candidate D is closer in aggregate RMSE but more redundant with C (residual correlation **0.9962**). These regime differences explain the branch's C+B choice; they do not establish that B beats C on the final private window.

Candidate E's branch `final_verification_candidate_e_2000_metrics.csv` reports 28.7481 RMSE for the 2,000-ceiling variant on 1,460 OOF rows; its unclipped OOF blend reports 27.6867. Source inspection confirms the 2,000 ceiling is applied to **training residual labels** in `SupervisedForecaster` and in `verify_candidate_e_2000_ceiling.py`; validation labels remain raw, and prediction outputs are not capped at 2,000. Neither OOF number proves the submitted artifact's test-time range. The Candidate E CSV's CRLF-normalized hash matches its manifest and its manifest cites the 9 November Train. However, the actual 192 private predictions have minimum **21.7880**, maximum **532.5419**, and mean **119.0835**; the maximum is Malad West at 11 Nov 12:00 IST. The report states a private range of 29.87–116.72 and mean 57.61. This output/report inconsistency remains unexplained, so E is not promoted.

## Supplied forecast audit

All supplied prediction files have exact `ID,Target` schema, the 2,592 sample IDs in order, and finite non-negative predictions. EXP030 A/B are identical on **1,472/2,592 rows**. Their identical full dates are Oct 22–23 and Oct 27–Nov 8; 32 of the 96 rows on Nov 9 are also identical. No rows are identical on the remaining dates. Overall prediction correlation is **0.9550**.

| Station | EXP030 A private mean | EXP030 B private mean | Mean absolute A/B difference | Maximum absolute difference |
|---|---:|---:|---:|---:|
| 11606 | 62.3572 | 61.4381 | 0.9191 | 1.8219 |
| 11611 | 62.1386 | 71.3832 | 9.2447 | 10.7475 |
| 3409510 | 47.3691 | 54.7677 | 7.3985 | 8.6364 |
| 3409511 | 74.8927 | 74.5007 | 0.3921 | 1.1315 |

EXP030 manifests were not supplied or found beside the input files. Filenames suggest intended variants, but do not establish model definitions, training cutoffs or issue time. The TASK012 corrected blend also passes the grid/value checks; it differs from both EXP030 files on every row. Correlations are 0.7054 with A and 0.7709 with B. These are forecast-distribution comparisons only, not private performance scores.

## Submission readiness and commands

The 9 November Train was not copied into `data/raw/challenge/` and no final submission CSV was generated. The existing final-stage inference gate was updated: it rejects both known byte forms of the 9 November Train and any final-stage snapshot whose latest PM interval does not advance beyond the 9 November 07:00 cutoff. This closes the stale test/gate that allowed the 9 November release to be marked final with a user-asserted 10 November release time.

For the actual 10 November release, first preserve all official files and record source URL, retrieval time and hashes under `data/processed/official_releases/20261110_0900/`. Then run Candidate C/P_fix with the refreshed file:

```powershell
.venv\Scripts\python.exe scripts/prepare_task008_submission.py --data-dir data/processed/official_releases/20261110_0900 --stage final --release-time <actual-release-time-IST> --issue-time <actual-run-time-IST> --model P_fix --output artifacts/submissions/task010_final_candidate_C.csv
```

Candidate B remains conditional on a compatible CatBoost 1.2.10 runtime, exact month/day seasonal implementation, and matched station-gap confirmation. The pinned team CLI command uses `legacy_doy` by default; the `month_day_365` option is not the tested leap-year exact-month/day behavior. If B is selectively ported and validated, its reviewed command shape is `python scripts/train_predict.py --model ensemble_robust --model-run-time <actual-run-time-IST> --output artifacts/submissions/task010_final_candidate_B.csv`, followed by a manifest and full schema/determinism audit. Do not generate a final artifact or claim it was reproduced before those gates pass. The main-branch supported baseline fallback command is the same main preparation command with `--model median72` and a distinct output filename; its matched RMSE was weaker than P_fix.

## Reproduction and checks

```powershell
.venv\Scripts\python.exe scripts/run_task010.py --train "C:\Users\sujal\Downloads\Train (1).csv" --supplied-dir C:\Users\sujal\Downloads --output reports/ml_pipeline/task010/run06
.venv\Scripts\python.exe -m pytest tests/test_task010.py tests/test_final_gap.py -q -p no:cacheprovider --basetemp data/processed/task010-tests-final
.venv\Scripts\python.exe -m ruff check scripts/run_task010.py scripts/prepare_task008_submission.py tests/test_task010.py tests/test_final_gap.py
git diff --check
```

Focused tests passed: **11 passed**. The full repository suite passed: **141 passed, 19 existing pandas deprecation warnings, in 19.81s**. Scoped Ruff and `git diff --check` passed. Two independent run outputs produced byte-identical matched OOF (SHA-256 `511039797cc901b27125ff430144471cd2682b4f0a3e1b099437dd892c6f139e`); the duplicate intermediate run was removed after recording the check. The final run writes row-level OOF, metrics, branch OOF reaggregations, artifact/input hashes, EXP030 date equality, paired bootstrap and correlation tables under `run06/`. The 9 November Train download and ignored snapshot hashes are identical; `data/raw/challenge/` has no working-tree changes.

Branch source inventory is retained in `branch_commits.txt` (25 commits) and `branch_changed_paths.txt` (113 paths); no changes were merged from that branch.
