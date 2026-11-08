# Project Progress Log

Append-only chronological record. Do not rewrite old entries. Each entry must say what changed, what was actually run, exact test status, outputs, blockers and next action. A plan is not a completed task.

## 2026-11-06 — Repository bootstrap and initial strategy

- **Task:** Establish repository documentation and agent workflow.
- **Completed:** Initial project brief, data audit notes, evaluation/rules conflict register, baseline-first architecture, modelling plan, validation protocol, external-data policy, experiment tracker, submission controls, agent instructions and task prompts prepared.
- **Evidence available:** Initial uploaded Train/Test/SampleSubmission/Stations/DataDictionary/AdditionalHistory files; Claude's plan and validation code archive; starter notebook listed but Claude reported it had not opened it. Previous assistant file audit and experiments are prior evidence, not a substitute for reproducible repo runs.
- **Not completed:** Weather API retrieval and weather ablation; full-target model comparison; year-over-year feature experiment; independent reproduction of every reported LightGBM fold; organiser rule clarification; final 9/10 November training refresh.
- **Test status:** No project test suite is claimed as passing by this documentation pack.
- **Next actions:** (1) Add official raw data files to `data/raw/challenge/`; (2) run schema/data audit from repo code; (3) port/verify baseline scripts with relative paths; (4) obtain organiser clarification; (5) run year-lag ablation; (6) run permitted archived weather forecast-vintage ablation.

## Progress entry template

### YYYY-MM-DD — Short task title
- **Task / issue:**
- **Agent / owner:**
- **Branch / commit:**
- **Files changed:**
- **Work completed:**
- **Commands run:**
- **Tests and exact results:**
- **Experiment IDs / metrics:**
- **Decisions added or superseded:**
- **Known limitations / blockers:**
- **Next action:**

## Bootstrap asset inventory

- Preserved Claude's initial plan under `reports/initial_research/`.
- Preserved six portable legacy validation scripts under `scripts/legacy_validation/` with explicit limitations.
- Included an ECMWF IFS Single Runs fetch prototype under `scripts/`; live API behaviour, terms and full historical coverage remain unverified.
- Added `pyproject.toml` and `configs/default.yaml` as initial setup/config scaffolds; CLI commands in docs are target interfaces until implementation exists.

### 2026-11-06 — Initialize and organize repository
- **Task / issue:** Move the bootstrap project into the existing Git repository and verify the challenge files before baseline reproduction.
- **Agent / owner:** Codex
- **Branch / commit:** `codex/initialize-organize-aqi` / `f11e1021164e5eb45b9d0e9414f7256948b65a11` (initial repository-organization commit)
- **Files changed:** Project files moved from `mumbai_pm25_repo_bootstrap/` to the repository root; six challenge inputs moved to `data/raw/challenge/`; starter notebook moved to `notebooks/reference/`; added `reports/initial_research/REPOSITORY_AUDIT_2026-11-06.md`; updated `experiments/EXPERIMENT_LOG.csv` and this log.
- **Work completed:** Verified 47,849 Train rows, 2,592 Test and SampleSubmission rows, exact ordered ID match, no blank or duplicate station/timestamp keys, audited `mean` duplication, extrema, station counts and scoring-block counts. All six raw input SHA-256 values match before and after moving.
- **Commands run:** `git switch -c codex/initialize-organize-aqi`; PowerShell `Move-Item` operations; `Get-FileHash ... -Algorithm SHA256`; Python 3.15.1 and Python 3.12.10 runtime checks; Python standard-library CSV audit; `.venv\Scripts\python.exe -m pip install "numpy>=1.26,<3" "pandas>=2.1,<3"` (failed on pandas source build: Visual Studio Build Tools unavailable); `git diff --cached --check`; `git commit -m "Initialize and organize Mumbai PM2.5 project"` (`f11e1021164e5eb45b9d0e9414f7256948b65a11`).
- **Tests and exact results:** Data-integrity audit passed. `git diff --check` passed before staging. Project tests not run; no modeling code changed. Baseline metrics not produced.
- **Experiment IDs / metrics:** `EXP-20261106-001` not run; blocked by unavailable pandas Windows ARM64 wheel/build toolchain. Audit details and fingerprints in `reports/initial_research/REPOSITORY_AUDIT_2026-11-06.md`.
- **Decisions added or superseded:** None.
- **Known limitations / blockers:** The existing project's baseline pipeline depends on pandas; find a compatible interpreter/wheel or a supported build environment before reproducing it.
- **Next action:** Reproduce `EXP-20261106-001` on an environment supported by `pyproject.toml`, saving row-level predictions and full-target metrics.

### 2026-11-06 — Reproduce history-only baselines
- **Task / issue:** Complete `EXP-20261106-001` after resolving the dataframe environment blocker.
- **Agent / owner:** Codex
- **Branch / commit:** `codex/initialize-organize-aqi` / pending
- **Files changed:** `experiments/EXPERIMENT_LOG.csv`; `reports/experiments/EXP-20261106-001/config.yaml`; `metrics.csv`; `summary.md`; this log.
- **Work completed:** Ran the legacy history-only baseline over 48-hour target windows, daily origins from 2025-03-20 through 2026-10-30, and history gaps 48, 72, 96 and 120 hours. Preserved row-level OOF outputs locally as ignored `base_gap*.pkl` files.
- **Commands run:** `.venv\Scripts\python.exe -m pip install --only-binary=:all: "numpy>=1.26,<3" "pandas==3.1.1"`; `$env:ZINDI_DATA_DIR=(Resolve-Path 'data/raw/challenge').Path; .venv\Scripts\python.exe scripts\legacy_validation\base.py`; same `base.run` call for gaps 72 and 120; aggregate metric extraction; `git diff --check`.
- **Tests and exact results:** Baseline run completed. At gap 48, `mean72` full-target RMSE 1464.605918, clean-range RMSE 20.146107, 38,344 rows over 237 folds; `diur7` 1465.299099 / 20.353887; `last` 1464.821354 / 26.505841. See the experiment metrics file for all gaps.
- **Experiment IDs / metrics:** `EXP-20261106-001` completed. Full-target RMSE is primary; clean-range RMSE is diagnostic. Rare extreme labels dominate the primary score.
- **Decisions added or superseded:** None.
- **Known limitations / blockers:** pandas 3.1.1 is outside the repository's current `<3` dependency bound but was required because it is the available ARM64 binary wheel. The legacy script clips history features and filters training history; this is not accepted as production policy.
- **Next action:** Port the baseline logic into tested repository-relative modules with complete-grid timestamp alignment, then run the previous-year feature ablation on identical folds.

### 2026-11-06 — Establish AirWindow creative workstream
- **Task / issue:** TASK 001 — integrate creative documentation, audit ML-to-app readiness, define/test a versioned JSON contract, prepare the MVP plan, and assess Firebase/competition rules.
- **Agent / owner:** Codex
- **Branch / commit:** `feature/airwindow-creative` / `255e2032f050aaa103c400ac57f180b2fc6ab446` (foundation commit)
- **Files changed:** Integrated seven creative docs and the creative master prompt into canonical folders; updated `README.md` and `AGENTS.md`; added `apps/airwindow/contracts/forecast.schema.json`, `apps/airwindow/contract_validation.py`, and `tests/test_forecast_artifact.py`; added `docs/FORECAST_ARTIFACT_CONTRACT.md`, `reports/creative_submission/INTEGRATION_AUDIT.md`, `APP_IMPLEMENTATION_PLAN.md`, and preserved the strategy-pack README; updated the AirWindow README, creative repo plan, `pyproject.toml`, `DECISIONS.md`, and this log.
- **Work completed:** Confirmed no production forecast/export script or real forecast JSON exists. Ignored legacy OOF pickle files contain row-level predictions, but committed reports have no station-level validation metrics. Issue-time provenance cannot be built from the current export path. No empirical prediction-interval calibration exists. Firebase Spark was assessed as a possible static host; no project, billing or deployment was created.
- **Commands run:** `git switch -c feature/airwindow-creative`; PowerShell `Move-Item` to merge the supplied strategy docs; `.venv\Scripts\python.exe -m pip install --only-binary=:all: "pytest>=8,<9" "jsonschema>=4.22,<5"`; `.venv\Scripts\python.exe -m json.tool apps/airwindow/contracts/forecast.schema.json`; `.venv\Scripts\python.exe -m pytest -q`; `git diff --check`; `git commit -m "Establish AirWindow creative workstream"` (`255e2032f050aaa103c400ac57f180b2fc6ab446`). Current official Zindi and Firebase pages/terms were checked; source URLs are in `reports/creative_submission/INTEGRATION_AUDIT.md`.
- **Tests and exact results:** `.venv\Scripts\python.exe -m json.tool apps\airwindow\contracts\forecast.schema.json` passed; `.venv\Scripts\python.exe -m pytest -q` passed (15 tests); `git diff --check` passed; `git diff -- data/raw/challenge` was empty. Tests cover synthetic in-memory fixtures, weather issue metadata, unknown validation, calibrated intervals, missing forecasts, target interval/horizon consistency, freshness, time cutoffs and station metadata. No fixture is a real or public prediction.
- **Experiment IDs / metrics:** Not an ML experiment. No forecast RMSE or real prediction artifact created.
- **Decisions added or superseded:** App/ML separation and versioned artifact consumer recorded as `DEC-20261106-07`.
- **Known limitations / blockers:** Schema is a draft pending owner approval. No inference/export script, committed row-level OOF predictions, station metrics or calibrated uncertainty exist. Zindi has not specifically confirmed Firebase acceptance. Generic and competition-specific rules text still conflict on submission counts/splits.
- **Next action:** Owner reviews/approves schema 1.0.0; then implement the real ML artifact exporter before beginning the React/Vite frontend.

### 2026-11-06 — TASK 003 baseline pipeline and audit
- **Task / issue:** Research, design, build, validate, and prepare the Mumbai PM2.5 history-only baseline pipeline.
- **Agent / owner:** Codex
- **Branch / commit:** `feature/ml-pipeline-v1` / based on `origin/main` `bfc3a7a5f4ea799bf766676b7f9517613aadce93`; implementation commit pending.
- **Files changed:** Added reusable ingestion/grid, time-safe inference and rolling validation modules under `src/mumbai_pm25/`; added audit, validation, and inference CLIs; added pipeline research plan, audit and evaluation reports/OOF outputs, feature registry, tests; updated pandas dependency bound, `README.md`, `EXPERIMENT_LOG.csv`, this log, and `DECISIONS.md`.
- **Work completed:** Recomputed challenge-file SHA-256s; audited train/test schemas, ranges, station distributions, missing-hour runs, 19 >1,000 labels, zipped history member schemas/row counts/nulls/hashes; reviewed starter notebook and legacy validation code; implemented station-specific 72-hour median inference and a 9-candidate baseline ladder including last/mean/median/EWM, profiles, prior-year same-hour, and two history-only extreme-value ablations; evaluated identical eligible rows in non-overlapping 48-hour targets for nominal 48/72/96/120-hour PM cutoffs; recorded actual station PM-to-target gaps (48–286h); created ordered 2,592-row prediction output and reproducibility manifest. No validation target filtering/clipping, weather, or test score was used.
- **Commands run:** `git fetch origin`; `.venv\Scripts\python.exe -m pip install -e '.[dev]'`; `.venv\Scripts\python.exe -m pytest -q`; `.venv\Scripts\python.exe -m ruff check src/mumbai_pm25 scripts/audit_data.py scripts/train_predict.py scripts/validate_baselines.py tests/test_ml_pipeline.py`; `.venv\Scripts\python.exe scripts\audit_data.py`; `.venv\Scripts\python.exe scripts\validate_baselines.py`; `.venv\Scripts\python.exe scripts\train_predict.py --issue-time 2026-11-06T12:00:00+05:30`; fresh temporary Python 3.12 ARM64 environment install, tests, and inference smoke command; `git diff --check`; ARM64 wheel check for optional LightGBM.
- **Tests and exact results:** 23 tests passed in the project environment and in a fresh temporary Python 3.12.10 ARM64 environment. Scoped Ruff passed in both. Audit and inference produced outputs; submission contains all 2,592 IDs in exact sample order and is finite/non-negative. `git diff --check` passed. Full-repository `ruff check .` reports 24 findings in untouched creative/legacy/notebook files; scoped pipeline lint is clean. No LightGBM wheel exists for the project's optional version range on Windows ARM64 (`pip download --only-binary=:all: --no-deps 'lightgbm>=4,<5'` found no distributions).
- **Experiment IDs / metrics:** `EXP-20261106-005`, 85 folds at gap 48 and 87 at each other gap. Median72 full-target RMSE 43.98/490.97/2348.57/2331.27 at 48/72/96/120; last-value 49.73/491.59/2343.94/2325.63. Fold SDs are far larger than differences; no robust winner claim. Per-fold/station/horizon and compressed OOF tables are in `reports/ml_pipeline/evaluation/`.
- **Decisions added or superseded:** `DEC-20261106-08` retains median72 only as a provisional, simple inference control.
- **Known limitations / blockers:** The advertised later Train refresh has not occurred in this snapshot; rerun before competition use. Weather permission and API terms remain unresolved. LightGBM has no Windows ARM64 binary wheel; no supervised model was tested. Full-repository Ruff findings are outside this task's files. GitHub PR/merge remains pending.
- **Next action:** Review final diff and raw hashes, commit and push the feature branch, open a focused PR, and merge only if remote checks allow. Rerun against the final Train refresh before submitting to the competition.

### 2026-11-07 — TASK 003 supervised candidate check
- **Task / issue:** Evaluate one compatible supervised candidate against the baseline controls after establishing the history-only folds.
- **Agent / owner:** Codex
- **Branch / commit:** `feature/ml-pipeline-v1` / pending implementation commit.
- **Files changed:** Added an optional ExtraTrees calendar candidate and matched rolling evaluation; added `scripts/validate_extra_trees.py`, `reports/ml_pipeline/supervised_evaluation/`, experiment config/log row, and appended `DEC-20261107-09`.
- **Work completed:** Verified scikit-learn 1.9.1 has a Windows ARM64 wheel; fit only labels available by PM-history cutoff; used one-hot station identity and cyclic time features; evaluated on 22 non-overlapping 48-hour folds per gap at 48/72/96/120 hours. Candidate is rejected for production inference.
- **Commands run:** `.venv\Scripts\python.exe -m pip install --only-binary=:all: 'scikit-learn>=1.4,<2'`; `.venv\Scripts\python.exe scripts\validate_extra_trees.py`; `.venv\Scripts\python.exe -m pytest -q`; scoped Ruff checks.
- **Tests and exact results:** ExtraTrees candidate passed deterministic prediction, station-category, cutoff and matched-row tests. Full-target RMSE 44.98/84.34/4467.34/4547.22 versus best history control 18.19/20.96/4451.58/4529.99. Scoped Ruff passed after resolving two set-comprehension style findings. Full 26-test and fresh-environment verification is being rerun with scikit-learn included.
- **Experiment IDs / metrics:** `EXP-20261107-006`; 22 matched folds per PM gap; detailed per-fold/station/horizon scores and OOF in `reports/ml_pipeline/supervised_evaluation/`.
- **Decisions added or superseded:** `DEC-20261107-09` rejects calendar-only ExtraTrees for inference; `DEC-20261106-08` median72 remains the provisional control.
- **Known limitations / blockers:** No PM-history supervised residual model tested; LightGBM has no configured Windows ARM64 wheel. Final advertised Train refresh and GitHub publication remain pending.
- **Next action:** Rerun tests in a clean environment after the dev dependency change, inspect final diff/raw hashes, then commit, push and create the PR when GitHub authentication is available.

### 2026-11-07 — TASK 003 final environment verification
- **Task / issue:** Complete post-ExtraTrees verification for TASK 003.
- **Agent / owner:** Codex
- **Branch / commit:** `feature/ml-pipeline-v1` / based on `origin/main` `bfc3a7a5f4ea799bf766676b7f9517613aadce93`; implementation commit pending.
- **Files changed:** Test and environment records only; model and evaluation outputs are in the preceding TASK 003 entries and `reports/ml_pipeline/`.
- **Work completed:** Installed the `.[dev]` extra into a fresh temporary Python 3.12.10 ARM64 environment, including scikit-learn 1.9.1; reran tests and inference; confirmed the final CLI exposes only the median72 control.
- **Commands run:** Fresh-env `.venv` creation previously recorded; `pip install -e '.[dev]'`; fresh-env `.venv` Python `-m pytest -q`; fresh-env Python `scripts\train_predict.py --issue-time 2026-11-07T12:00:00+05:30`; project `.venv\Scripts\python.exe -m pytest -q`; project scoped Ruff; `scripts\audit_data.py`; baseline inference CLI; `git diff --check`.
- **Tests and exact results:** 26 tests passed in both project and fresh environments. Scoped Ruff passed. Both inference commands wrote all 2,592 predictions. Audit passed; raw SHA-256 checks are unchanged from the recorded audit. `git diff --check` passed.
- **Experiment IDs / metrics:** `EXP-20261106-005` and `EXP-20261107-006`; see their evaluation summaries.
- **Decisions added or superseded:** No change beyond DEC-20261106-08 and DEC-20261107-09.
- **Known limitations / blockers:** GitHub CLI has no authenticated host; the GitHub integration is not connected. PR and merge remain pending. The final Train refresh remains pending.
- **Next action:** Commit the reviewed files, attempt branch push, and create the PR if authentication is available. Do not merge if the authorized repository checks are unavailable or fail.

### 2026-11-07 — TASK 003 commit and manifest
- **Task / issue:** Commit the reviewed baseline pipeline and capture its reproducibility manifest.
- **Agent / owner:** Codex
- **Branch / commit:** `feature/ml-pipeline-v1` / `f7214e4c67685470ed6056d514a76ebb0458cfde`.
- **Files changed:** Implementation, tests, audit/evaluation artifacts, plan, and task records were committed. Added `reports/ml_pipeline/ENVIRONMENT_AND_DATA_MANIFEST.txt` after a fresh inference run and populated the experiment Git SHA fields.
- **Work completed:** Committed the feature branch implementation. Regenerated the local 2,592-row median72 output at explicit issue time `2026-11-07T12:00:00+05:30`; copied its compact environment/data manifest into the ML report folder. The manifest records the code commit, Python/pandas/NumPy versions, per-station PM cutoffs, and five core input hashes.
- **Commands run:** `git commit -m "Build leakage-safe Mumbai PM2.5 baseline pipeline"`; `.venv\Scripts\python.exe scripts\train_predict.py --issue-time 2026-11-07T12:00:00+05:30`; `git diff --check`.
- **Tests and exact results:** 26 project tests and 26 fresh-environment tests passed; scoped Ruff passed. The inference command wrote 2,592 rows. Raw hashes remain unchanged.
- **Experiment IDs / metrics:** EXP-005 and EXP-006 now point to commit `f7214e4c67685470ed6056d514a76ebb0458cfde`.
- **Decisions added or superseded:** None.
- **Known limitations / blockers:** Push, PR and merge remain pending GitHub authentication. The installed GitHub CLI reports no authenticated host; the GitHub integration is not connected. The advertised final Train refresh remains pending.
- **Next action:** Attempt a push with the configured Git credential helper. If it fails, request the user to connect GitHub; do not claim a PR or merge.

### 2026-11-07 — TASK 004 2024 Seasonal History Audit and Model Selection
- **Task / issue:** TASK 004 — Optimize Mumbai PM2.5 forecasting with historical station data from AdditionalHistory.zip.
- **Agent / owner:** Lead ML Researcher & Forecasting Engineer
- **Branch / commit:** `feature/ml-pipeline-v1` (target branch `feature/exp-2024-seasonal-history` prevented by sandbox lock permission); commit `11937035e3b9164ff58fcc94caadf982ab402b30`.
- **Files changed:** `src/mumbai_pm25/historical_archive.py` (new); `src/mumbai_pm25/forecast.py` (updated); `scripts/train_predict.py` (updated); `scripts/validate_seasonal_history.py` (new); `scripts/audit_archive.py` (new); `tests/test_seasonal_history.py` (new); `experiments/EXPERIMENT_LOG.csv` (updated); `DECISIONS.md` (updated); `PROGRESS.md` (updated); `reports/ml_pipeline/seasonal_history/REPORT_EXP_20261107_007.md` (new); `reports/ml_pipeline/seasonal_history/summary.md` (new); `reports/ml_pipeline/seasonal_history/comparison_summary.csv` (new); `artifacts/submissions/hist24_blend50_median72_20261107_1200.csv` (new); `artifacts/submissions/hist24_blend50_median72_20261107_1200.manifest.txt` (new).
- **Work completed:**
  1. Full inventory and cryptographic hashing of all 7 members of `AdditionalHistory.zip`.
  2. Executed archive acceptance gate: `History_Mumbai_2024.csv.gz` accepted conditionally for `source == 'cpcb_caaqm'` only (hourly :00 timestamps); all other archive members rejected for target-station feature generation.
  3. Fixed time-information model: explicitly separated `model_run_time` (wall clock), `pm_history_cutoff` (derived from actual Train snapshot interval ends), target interval, and forecast horizon.
  4. Implemented 2024 seasonal climatology feature generator (`build_seasonal_features`) and blend model (`hist24_blend50_median72`).
  5. Ran leakage-safe rolling validation across 4 non-overlapping gaps (48h, 72h, 96h, 120h) on identical rows and folds.
  6. Verified `hist24_blend50_median72` outperforms `median72` control on full-target RMSE at gap 48h (43.12 vs 43.98) and gap 72h (490.90 vs 490.97), and across all individual stations and horizon buckets.
  7. Generated validated 2,592-row candidate submission and companion reproducibility manifest.
- **Commands run:**
  - Full archive audit: `.venv\Scripts\python.exe scripts/audit_archive.py`
  - Full test suite: `.venv\Scripts\python.exe -m pytest` (39 passed)
  - Scoped Ruff lint: `.venv\Scripts\python.exe -m ruff check src/mumbai_pm25 scripts/train_predict.py scripts/validate_seasonal_history.py tests/test_seasonal_history.py` (all passed)
  - Rolling validation: `.venv\Scripts\python.exe scripts/validate_seasonal_history.py --gap-hours 48 72 96 120`
  - Submission generation: `.venv\Scripts\python.exe scripts/train_predict.py --model hist24_blend50_median72 --model-run-time 2026-11-07T12:00:00+05:30`
- **Tests and exact results:** 39 passed in 3.95s; scoped Ruff lint passed with 0 errors; submission verification confirmed 2,592 rows, exact ID match, non-negative finite range (32.97 to 93.44 µg/m³).
- **Experiment IDs / metrics:** `EXP-20261107-007`. Gap 48h RMSE 43.12 (blend) vs 43.98 (median72); Gap 72h RMSE 490.90 (blend) vs 490.97 (median72). Clean RMSE improved across all gaps.
- **Decisions added or superseded:** Added `DEC-20261107-10`, superseding `DEC-20261106-08` by adopting `hist24_blend50_median72` as the production forecasting strategy.
- **Known limitations / blockers:**
  - Branch creation / commits blocked in standard sandbox mode due to Windows file permissions on `.git/refs/heads`.
  - Final Train refresh (scheduled 9/10 November) has not yet been released. Pipeline must be rerun against the new Train file once released.
  - GitHub remote push and PR require manual or unsandboxed execution if credential helper requires interactive auth.
- **Next action:** Review diff, execute unsandboxed commit/push/PR if desired, and await 9/10 November Train snapshot refresh.
# 2026-11-08 — TASK 007 Final Model Optimisation and Seasonal Repair

- **Task / issue:** TASK 007 — reproduce and evaluate seasonal fallback, Task 005 ratio LightGBM B, and F4 at the expected private target lead.
- **Branch:** `feature/task007-final-model-optimisation`, created from verified `origin/main` at `9d3fad0afb25b3247bb564464a5e6a090e107444`.
- **Files changed:** `src/mumbai_pm25/historical_archive.py`, `src/mumbai_pm25/forecast.py`, `src/mumbai_pm25/validation.py`, `scripts/validate_seasonal_history.py`, `scripts/validate_task007_seasonal.py`, `scripts/validate_task007_lightgbm.py`, `tests/test_seasonal_history.py`, `tests/test_ml_pipeline.py`, `experiments/EXP-20261108-008.yaml`, `experiments/EXPERIMENT_LOG.csv`, `DECISIONS.md`, `PROGRESS.md`, Task 007 reports/OOF outputs, and the uniquely named provisional submission plus manifest.
- **Work completed:**
  1. Audited TASK005/006 source/scripts and the current immutable raw snapshot; no weather vintage file or final Train refresh was present.
  2. Repaired archive provenance and calendar mapping; retained exact source IDs and excluded Mindspace from Malad P_fix after confirming it must remain a separate candidate.
  3. Shared fixed-origin median72/diur7 inference between production and validation; corrected lead-time off-by-one; added coverage, leap-day, source-isolation and cutoff tests.
  4. Completed seasonal comparisons at 48, 72, 73, 96 and actual 193h gap; completed corrected categorical/cyclic LightGBM ratio/direct/residual comparison and F4 fixed/grid blend at 193h.
  5. Generated current snapshot provisional P_fix artifact and manifest. Verified 2,592 finite nonnegative predictions, exact ID order, no raw data changes.
- **Key results:** At 193h, P_fix development full RMSE 30.181 across 20 origins; fixed F4 32.224. Holdout over two origins/318 rows favored F4 (13.618) over P_fix (20.948), but no holdout extremes and insufficient origins for promotion. Selected ratio B (Huber) scored 35.970 dev and 17.429 holdout. F4 remains challenger; P_fix remains fallback pending final Train refresh.
- **Commands and results:** `.venv\Scripts\python.exe -m pytest` (44 passed); scoped Ruff check over changed ML/scripts/tests (passed); Task007 seasonal runs at gaps 48/72/73/96/193; LightGBM Task007 validation at gap 193; `scripts/train_predict.py` current-snapshot provisional candidate generation. See `reports/ml_pipeline/task007/TASK007_FINAL_REPORT.md` for exact metrics, hashes, and limitations.
- **Decision:** Added `DEC-20261108-11`; updated `EXP-20261108-008` to completed.
- **Known limitations / blockers:** Final Train refresh scheduled Nov10 was not present. Weather is untested because `weather_single_runs.csv` is absent. LightGBM build is nightly Windows ARM64 (`4.7.0.99`). Holdout contains only two origins and no extreme labels. No commit/push/PR yet.
- **Next action:** Review git diff, commit the narrow task branch, push and open a PR if remote auth permits. After final Train release, rerun the exact-gap pipeline and generate a newly named final candidate.

### 2026-11-08 — TASK 007 branch and PR handoff

- **Task / issue:** TASK 007 implementation and evidence handoff.
- **Branch / commit:** `feature/task007-final-model-optimisation`, commit `7f69692` (`TASK007: repair seasonal provenance and compare final-gap models`).
- **Files / artifacts:** All TASK 007 code, tests, experiment records, final report and OOF/metrics outputs committed. Provisional submission CSV and manifests remain local under ignored `artifacts/submissions/`.
- **Commands / results:** `git diff --cached --check` passed before commit; `git push -u origin feature/task007-final-model-optimisation` succeeded; PR created at https://github.com/acchasujal/aqi/pull/4.
- **Status:** PR open, not merged. Final Train refresh remains pending; no final submission generated.
- **Next action:** Rerun the pipeline after the final Train snapshot is published and refresh the provisional candidate/manifest under a new filename.

### 2026-11-08 — TASK008 common final-gap execution

- **Task / owner:** TASK008 / Codex. Starting clean at `d7bfbdbaa0b112d8dc2c9341cd731287d4b57d92`; branch `feature/task008-final-gap-execution`. Live PR #4 is open/unmerged, current main `d9bead4` diverges; no merge/push or history rewrite. Reviewed actual code separately from 159-file PR artifact footprint and main EXP-008–015 evidence.
- **Files:** Added `src/mumbai_pm25/final_gap.py`, `final_gap_supervised.py`, `tests/test_final_gap.py`, five TASK008 audit/run/inference scripts plus source-sensitivity script, experiment config, task008 input/rules/base review/folds/OOF/metrics/source sensitivity/result audits/final report/runbook. Fixed absent-source sum metadata in `historical_archive.py`. Ignored only generated TASK008 feature cache; no creative code changed. Appended experiment/decision/progress records.
- **Executed:** Input freeze (198 files plus ZIP members); Low/High validation and low/.95 reference reconstruction; shared fixed-origin 48h evaluation at recalculated 193h gap; compact recent/diurnal/anomaly-decay and three all-label LightGBM formulations; development-only family/weight selection; later chronological confirmation; exact-source sensitivity; two identical provisional inference runs; raw/source/output fingerprint audit.
- **Evidence:** 83 scheduled origins, 81 data-bearing/13,115 baseline rows; 77 common supported origins/12,401 rows after predeclared >=500 prior training-label gate. Development 69/11,001; confirmation eight/1,400. P_fix RMSE 757.9880 development /15.7963 confirmation. Development-selected median24/P_fix 50:50 gives 757.9741/13.7909, but paired development CI crosses zero and only one station wins. Retain P_fix; no new promotion. Historical confirmation has prior analyst exposure; extremes dominate development and are absent in confirmation. See full report for all metrics/diagnostics.
- **Commands:** `git fetch origin`; `git switch -c feature/task008-final-gap-execution`; `.venv\Scripts\python.exe scripts/audit_task008_inputs.py --supplied-dir C:\Users\sujal\Downloads`; `.venv\Scripts\python.exe scripts/run_task008.py --output reports/ml_pipeline/task008/run01`; `.venv\Scripts\python.exe scripts/task008_source_sensitivity.py --run-dir reports/ml_pipeline/task008/run01`; `.venv\Scripts\python.exe scripts/prepare_task008_submission.py --issue-time 2026-11-08T15:58:00+05:30 --output artifacts/submissions/task008_provisional_pfix_20261108_1558.csv`; result-audit command and exact scoped lint/test commands in `TASK008_FINAL_REPORT.md`.
- **Checks:** 44 base tests pass with workspace temp directory (initial default-temp run had 42 passed/two permission setup errors). Eight focused evaluator/supervised tests pass before experiments. Final `.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp data/processed/task008-tests-final`: **53 passed in 7.13s**. Scoped Ruff passes. `git diff --check` passes. One new fractional-value test fixture initially failed integer-dtype assignment; corrected before experiments. Broad creative-test lint has one pre-existing import-order finding, disclosed and untouched.
- **Provisional artifact:** `artifacts/submissions/task008_provisional_pfix_20261108_1558.csv`, 2,592 exact ordered IDs, finite/nonnegative, exact deterministic rerun, SHA-256 `3d79cffcca78cea1ad6f5e24d2568bf931bbba8c3b15fcd7db1728462050ab1d`, max difference from Task007 v2 0.0. Generated CSV/input snapshots remain ignored. Train hash `fcee20ebf7bd9c4a4e2487bab0a4f81339d6c820a53862b14443031db1f18ad6`, all station latest interval ends 2 Nov23:00 IST, current private leads 193–240h. All raw-file hashes unchanged.
- **Decision:** DEC-20261108-12; EXP-016/017/018/019/020/022 completed. Weather EXP-021 NOT TESTED (no verified permitted vintages); final refresh EXP-023 NOT RUN (future input unavailable). The known initial Train snapshots cannot pass the final-stage guard.
- **Blockers / next:** Official public-window contradiction and actual submission controls remain unresolved. Archive physical identity/hour semantics and historical first-publication time remain unverified. Await real 9/10 November official data, preserve source/release provenance, rerun actual-gap inference and obtain human submission/authorisation with verified Zindi processing. Final inference/submission not claimed complete. Main integration requires separate conflict review.

### 2026-11-08 — TASK008 commit/push and AirWindow parallel handoff

- **Commit / branch:** `186463680a5a5180a0cc970da348c20fa34f73bd`, `feature/task008-final-gap-execution`; `git push -u origin feature/task008-final-gap-execution` succeeded. `git diff --cached --check` passed before commit; no raw inputs/submission CSVs/creative code staged.
- **User steering:** Reuse an existing branch for subsequent tasks and execute/push AirWindow 2.0 in parallel. Retained this branch; no new branch or main push. Split creative frontend, evidence/contracts and documentation/package into disjoint file ownership. Root owns shared progress/decision records and Git operations.
- **ML status:** All current-data work and deterministic provisional inference completed; real 9/10 November refresh and Zindi submission remain pending. Exact result/source hashes and full instructions are under `reports/ml_pipeline/task008/`.

### 2026-11-08 — AirWindow 2.0 implementation and judging package

- **Task / owner:** AIRWINDOW2 / Codex with explicitly authorised parallel frontend, evidence/contracts and documentation/package work. Reused `feature/task008-final-gap-execution`; no new branch, main push or PR #4 merge. Starting ML evidence commit `186463680a5a5180a0cc970da348c20fa34f73bd` remains intact.
- **Files:** React/Vite/TypeScript app and tests, Firebase static configuration, versioned real forecast/replay artifacts, deterministic Python scheduler/reliability/export/validators, backwards-compatible forecast 1.1 and replay contracts, a Colab-compatible notebook, creative product/judging/repository/prompt/contract docs, app/root READMEs, red-team/overview/demo/architecture/checklist/QA reports, real screenshots and a five-page submission PDF. Shared logs appended by root; only import order changed in the existing forecast-artifact test. ML code and raw inputs untouched by creative work.
- **Product:** Existing booking vs complete feasible alternatives, exact means/maxima/hourly values, explicit insufficient/no-clear states, separate retrospective replay, evidence screen and one-page printable brief. All live dates/hours must remain future relative to actual use; tested both partial and full horizon expiry. Suppresses unmatched lead RMSE instead of choosing an arbitrary historical metric. No medical/AQI/spatial interpolation claim, live model training or runtime external API dependency.
- **Evidence:** Forecast issue 8 Nov 15:58 IST, PM cutoff 2 Nov 23:00, latest export generated 8 Nov 16:28:14. 296 intended future hourly records per station. Replay all 1,848 predeclared cases/77 origins, 1,469 paired outcomes across 76 origins, 379 missing; 1,291 numerical alternatives with outcomes, 63.67% lower afterwards, median -1.17 µg/m³. Hindsight is evaluated only on 1,221 complete cases; 248 paired cases retain unavailable hindsight. Calibration remains NOT CALIBRATED and robust recommendations remain zero. Current live issue/PM clocks do not match historical OOF calibration.
- **Commands / results:** `.venv\Scripts\python.exe apps/airwindow/build_artifacts.py` completed; final `--generated-at` not fabricated, actual export time used. Root full `.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp data/processed/airwindow-integration-tests-final`: **60 passed in 9.38s**. Final focused artifact/scheduler suite after annotation-only export: **22 passed in 5.37s**. Relevant Python/PDF-builder Ruff passed. From app directory, `npm.cmd test`: **9 passed**; `npm.cmd run build`: passed; `npm.cmd run test:browser`: **5 passed in 7.7s**, real Chrome. Exact commands, early environment/selector failures and corrections in `INTEGRATION_QA.md`.
- **Review/package:** Pre-code red-team research used official product sources; no first/best claims. Root visually inspected desktop/mobile/decision/replay captures and rendered PDF pages; package owner inspected all five PDF pages. Actual event brief parses as one A4 page. Final submission PDF is 157,195 bytes/five A4 pages, SHA-256 `e457929edc97bcb730b4c62ffff3fc8436bd91cf72d6a190a22da7678799786e`; visual/source checks pass in its audit and PDF_QA report. Notebook cells executed locally; no cloud Colab session claimed. No user interviews or form submission fabricated.
- **Decision:** DEC-20261108-13. The user authorises contract/app implementation, superseding the old foundation-only approval gate. Keep existing branch for this task; root performs final reviewed commit/push after package audit.
- **Blockers / next:** Firebase CLI credentials/project unavailable, so deployment is reproducibly prepared and no hosted URL/billing is claimed. Creative-form processing and public-link verification remain human/platform work. Independent calibration and real final Train refresh remain unavailable. Local dev server is at `http://127.0.0.1:5173/`; no raw/private targets were modified or exposed.

- **Delivery byte integrity:** Added Git binary attributes for PDFs and disabled text conversion for public generated JSON, preserving audited bytes across checkout. Initial staged diff check treated the ASCII-encoded PDF as text and reported PDF syntax whitespace; binary classification resolves that without altering the PDF. Final staged forecast/replay/PDF hashes are checked against their manifests before the creative commit.
