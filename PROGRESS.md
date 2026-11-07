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

### 2026-11-07 — EXP-009 Production/Validation Parity
- **Branch / base:** `feature/exp-009-forecast-parity` worktree from `9d3fad0`; EXP-008 changes remain isolated.
- **Files:** Shared median and blend in `forecast.py`; validation calls both; parity tests and five reports plus diagnostic CSVs added. Experiment log and progress appended. No raw data, station mapping, leap policy, or model selection changed.
- **Evidence:** Production CSVs: 2,592 rows, zero changes, identical SHA-256 `55e2fc8c7cad94db22f1358a8715216b0c7fbbb7a50c728c4413890f6a8716bc`. Matched OOF results in `VALIDATION_IMPACT.md`.
- **Checks:** Focused parity tests 7 passed. Full suite was run three times: first 38 passed/1 unrelated ExtraTrees exact-equality failure before adding parity tests; second 45 passed; final 45 passed/1 ExtraTrees exact-equality failure. Focused parity + seasonal tests: 21 passed. Ruff passed; `git diff --check` passed.
- **Limitation:** Existing fold construction skips no-prior-PM station rows; synthetic test covers seasonal-only fallback.

### 2026-11-07 — EXP-009 Acceptance Update
- **ExtraTrees test diagnosis:** Base commit `9d3fad0` also fails the exact-equality test intermittently. Five direct paired seeded fits on the base differed by at most `3.552713678800501e-15` with NumPy 2.3.5, pandas 2.3.3, scikit-learn 1.8.0 and `n_jobs=2`. Changed only the assertion to `rtol=0, atol=1e-12`; model configuration unchanged.
- **Verification:** `$env:PYTHONPATH='src'; python -m pytest -q` — 47 passed, 1 warning. EXP-009 production artifact remains byte-identical to its reference as recorded in `reports/ml_pipeline/exp_009/BEFORE_AFTER_COMPARISON.md`.
- **Decision:** EXP-009 accepted for EXP-010 base with this documented pre-existing numerical test issue resolved at the assertion level.

### 2026-11-07 — EXP-010 Seasonal Blend Weight Comparison
- **Branch / base:** `feature/exp-010-blend-weights` from accepted EXP-009 commit `e043a6788416bcb5896b142d788e791f9cd591e7`.
- **Files changed:** `scripts/train_predict.py` adds explicit seasonal-weight CLI option; `scripts/validate_blend_weights.py` evaluates five fixed weights using corrected EXP-009 folds; `tests/test_blend_weights.py`; EXP-010 report and metric files; experiment log and this progress entry. Raw challenge files, source mapping, timestamps, and leap policy unchanged.
- **Commands:** `$env:PYTHONPATH='src'; python scripts/validate_blend_weights.py` — completed four gaps, 85/87/87/87 folds and 13,528/13,060/13,177/13,395 rows per weight. `$env:PYTHONPATH='src'; python -m pytest -q` — 56 passed, 1 warning. `python -m ruff check src/mumbai_pm25/forecast.py scripts/train_predict.py scripts/validate_blend_weights.py tests/test_blend_weights.py` — passed.
- **Results:** W0 provisional development winner (pooled RMSE 1883.266538 vs W50 1883.387394), but gain is driven by the 2025-12-03 extreme window duplicated across 96h/120h gaps. Non-extreme development rows favor W50. Confirmation RMSE favors W0 but has no extreme or November labels. Recommendation RETAIN BASELINE W50; no challenger CSV.
- **Next action:** Resolve EXP-008 provenance and run a regime-aware confirmation after the official Train refresh, without tuning on leaderboard scores.

### 2026-11-07 — EXP-010 Verification Addendum
- **Commands:** `$env:PYTHONPATH='src'; python scripts/train_predict.py --model hist24_blend50_median72 --seasonal-weight 0.5 --model-run-time 2026-11-07T12:00:00+05:30 --output data/processed/exp010_w50_smoke.csv` — 2,592 rows, SHA-256 `55e2fc8c7cad94db22f1358a8715216b0c7fbbb7a50c728c4413890f6a8716bc`, identical to EXP-009. `$env:PYTHONPATH='src'; python scripts/train_predict.py --model median72 --model-run-time 2026-11-07T12:00:00+05:30 --output data/processed/exp010_median72_smoke.csv` — 2,592 valid rows. Both preserve sample ID order and have finite nonnegative targets. `python scripts/summarize_blend_diagnostics.py` — 40 diagnostic rows.

### 2026-11-07 — EXP-010 OOF Reproduction Check
- **Result:** Reconstructed W50 OOF predictions match EXP-009 corrected OOF on all 53,160 keyed rows; maximum absolute difference 0.0. The first comparison attempt omitted gap from the join and failed the one-to-one key check; rerun with gap included passed.

### 2026-11-07 — EXP-011 Leap-Year Calendar Alignment
- **Branch / base:** `feature/exp-011-calendar-alignment` from accepted EXP-010 commit `0270e58c491b87913cae53234edbf3981ffac1a7`; EXP-009 commit `e043a6788416bcb5896b142d788e791f9cd591e7` verified.
- **Files:** Added opt-in `month_day_365` feature mode in `historical_archive.py`; threaded calendar mode through forecast, CLI and seasonal validation; added matched validation runner and calendar tests; five EXP-011 reports plus metrics/feature comparison CSVs. Legacy default, W50 weight, source mapping, timestamp semantics, and raw data unchanged.
- **Results:** Matched 48/72/96/120h rows: 13,528/13,060/13,177/13,395. Confirmation RMSE improves slightly at each gap but folds and November evidence are mixed; retain original W50. In-memory corrected inference would change 2,218 of 2,592 rows (mean absolute 1.015863, max 53.4625); no challenger CSV.
- **Commands/checks:** `$env:PYTHONPATH='src'; python scripts/validate_calendar_alignment.py` completed all gaps; `$env:PYTHONPATH='src'; python -m pytest -q` — 64 passed, 1 warning; focused calendar/parity tests — 16 passed; original W50 and median72 inference smoke runs — 2,592 rows each. Original W50 SHA-256 `55e2fc8c7cad94db22f1358a8715216b0c7fbbb7a50c728c4413890f6a8716bc`. Ruff and diff checks recorded in final report.
- **Next:** Resolve EXP-008 station identity and hourly interval uncertainty, then rerun after official Train refresh.

### 2026-11-07 — EXP-011 Final Verification Addendum
- **Final checks:** `$env:PYTHONPATH='src'; python -m pytest -q` — 64 passed, 1 warning. `python -m ruff check src/mumbai_pm25/historical_archive.py src/mumbai_pm25/forecast.py scripts/train_predict.py scripts/validate_seasonal_history.py scripts/validate_calendar_alignment.py scripts/summarize_calendar_diagnostics.py tests/test_calendar_alignment.py` — passed. `git diff --check` — passed. `python scripts/summarize_calendar_diagnostics.py` — completed.
- **Evidence:** Full-gap metrics, station/fold/horizon diagnostics, extreme squared-error share and actual PM gaps are under `reports/ml_pipeline/exp_011/`. The first slower paired validation run was interrupted before producing results; an optimized complete rerun used the identical source series and generated all four matched gaps. No source raw data were modified.

### 2026-11-07 — EXP-012 November-Focused Forecasting Challengers
- **Branch / base:** `feature/exp-012-november-forecasting` worktree from accepted EXP-011 commit `4d7a98b73e4d279e86d510a9e3139d08bddbec81`.
- **Files:** New `src/mumbai_pm25/november_candidates.py` defines fixed robust median/trend candidates; `scripts/audit_exp012_folds.py`, `scripts/validate_november_candidates.py`, and `scripts/summarize_exp012.py` generate fold audit, matched comparisons and diagnostics; `tests/test_november_candidates.py`; EXP-012 reports/metric tables; experiment log and this progress record. Existing production model code and raw inputs unchanged.
- **Audit:** Four stations, 648 Test rows each; latest PM interval ends 2026-11-02 23:00 IST, announced private Nov 11–12 target starts 193–240h later. Existing 48h windows have shorter nominal gaps, so added 192h diagnostic. 432 `(gap,fold)` combinations audited; November historical coverage limited.
- **Commands:** `$env:PYTHONPATH='src'; python scripts/audit_exp012_folds.py` — 346 standard-gap combinations; `$env:PYTHONPATH='src'; python scripts/validate_november_candidates.py` — 48/72/96/120/192h comparisons, 13,528/13,060/13,177/13,395/13,999 rows per model; `$env:PYTHONPATH='src'; python scripts/summarize_exp012.py` — 70 diagnostic rows plus 86 192h folds. Focused candidate tests 4 passed; full suite 68 passed, 1 warning; scoped Ruff passed.
- **Result:** Hybrid W50/M24 improves reused late-2026 folds but is weak/extreme-driven on 192h development and loses to W50 on November 192h. Recommendation PROMISING BUT UNVALIDATED; retain production W50 and do not generate challenger submission. In-memory hybrid would change all 2,592 predictions; no CSV saved. W50 smoke SHA-256 `55e2fc8c7cad94db22f1358a8715216b0c7fbbb7a50c728c4413890f6a8716bc`.
- **Failed/retried runs:** First candidate run failed on mixed timestamp dtypes before metrics were written; fixed explicit IST parsing. Initial focused test fixture expectations were corrected for the exact cutoff boundary; candidate code was not changed for those test assertions. The completed rerun and final tests pass.
- **Next:** Seek genuinely unseen November-style validation at approximately 193–240h PM gap after official Train refresh; investigate EXP-008 source identity and hourly interval semantics.

### 2026-11-07 — EXP-013 Competition-Horizon Validation and Final Readiness
- **Preflight:** Accepted EXP-012 after 12 focused and 68 full tests passed, Ruff passed, and original W50 hash reproduced; committed it as `1acce2693199a9f48dbe44351dca9d2b41bee1ae`. Created isolated `feature/exp-013-final-readiness` worktree at `C:\Users\dyara\aqi-exp013`. Main EXP-008 worktree has unrelated uncommitted changes and was untouched.
- **Files:** New horizon helper, snapshot audit, 193–240h matched validation runner, official-file refresh command, focused tests and EXP-013 reports/metrics. Experiment log and this progress entry appended. Production forecast code, raw challenge files, historical source mappings, calendar default and model selection unchanged.
- **Snapshot and rules:** Official organiser discussion confirms November 10 23:59:59 IST deadline, 10/day and 140 total submissions, and latest-valid private November 11–12 RMSE. Official data page schedules Train updates November 9 and final November 10 09:00 IST. Local 5 November Train SHA-256 `fcee20ebf7bd9c4a4e2487bab0a4f81339d6c820a53862b14443031db1f18ad6`; 47,849 rows, 4 stations. Test/sample 2,592 rows; current PM interval end November 2 23:00 IST. Actual private leads 193–240h, 192 station-hours.
- **Validation:** `$env:PYTHONPATH='src'; python scripts/validate_exp013_competition_shape.py` — 85 folds and 13,244 identical scored rows/model with actual 193–240h leads. All matched rows overlap prior EXP-012 scoring; exploratory only. Pooled RMSE W50 690.2117, hybrid 690.1778; November RMSE W50 62.6158, hybrid 63.1823. Seventeen targets ≥500 contribute 99.8818% of W50 squared error; the two largest contribute 99.4946%. Retain W50; no hybrid submission.
- **Artifact:** `$env:PYTHONPATH='src'; python scripts/train_predict.py --model hist24_blend50_median72 --model-run-time 2026-11-07T12:00:00+05:30 --output artifacts/submissions/exp013/w50_train_fcee20eb_20261107_1200.csv` — 2,592 valid rows. `$env:PYTHONPATH='src'; python scripts/refresh_official_snapshot.py --train-csv data/raw/challenge/Train.csv --test-csv data/raw/challenge/Test.csv --samplesubmission-csv data/raw/challenge/SampleSubmission.csv --stations-csv data/raw/challenge/Stations.csv --datadictionary-txt data/raw/challenge/DataDictionary.txt --additionalhistory-zip data/raw/challenge/AdditionalHistory.zip --issue-time 2026-11-07T12:00:00+05:30` — 2,592 rows, versioned snapshot, 193–240h private leads. Both W50 CSV hashes equal `55e2fc8c7cad94db22f1358a8715216b0c7fbbb7a50c728c4413890f6a8716bc`. No upload.
- **Checks:** `$env:PYTHONPATH='src'; python scripts/audit_exp013_snapshot.py` — 47,849 Train/2,592 Test/192 private rows; focused `$env:PYTHONPATH='src'; python -m pytest -q tests/test_exp013_horizon.py` — 5 passed; full `$env:PYTHONPATH='src'; python -m pytest -q` — 73 passed, 1 warning; `python -m ruff check src/mumbai_pm25/horizon.py scripts/audit_exp013_snapshot.py scripts/validate_exp013_competition_shape.py scripts/refresh_official_snapshot.py tests/test_exp013_horizon.py` — passed; `git diff --check` — passed.
- **Next:** After the organiser's final official Train update, run the documented explicit-file refresh command, verify the new PM cutoff and leads, and reassess the locked hybrid only on genuinely new eligible rows. EXP-008 historical station provenance and interval semantics remain unresolved.

### 2026-11-07 — EXP-013 Reproducibility Addendum
- Repeated the 193–240h matched validation: 85 folds, 13,244 rows/model, 100% prior-row overlap. The original partition-only `MODEL_COMPARISON.csv` SHA-256 was `416c80e0b4144ca7eb6f72ba38f02a64a1991449a4d9f7242da5c0ce14ca2ca5` on both runs. Added overall pooled rows and `LEAD_METRICS.csv` to the final tables without changing scored rows or predictions. Re-ran snapshot audit and scoped Ruff; both passed. A second W50 generation through the immutable refresh workflow reproduced the original CSV hash exactly.
- Final row-audit correction records one pseudo issue time per 48-hour fold using the audited 109-hour issue-to-PM-cutoff offset. Re-ran validation: 85 folds, 13,244 rows/model, identical RMSEs; all scored target times follow issue time and each fold has one issue. Re-ran full pytest after this change: 73 passed, 1 warning; scoped Ruff passed.
- Committed implementation/reports as `46ccc3f9cd6e64d8db9d7a88dd4fc0da01f5d596`, then regenerated a final current-snapshot W50 CSV with `--issue-time 2026-11-07T18:48:42+05:30`. The generated manifest records that source commit, 2,592 valid rows and the unchanged output SHA-256 `55e2fc8c7cad94db22f1358a8715216b0c7fbbb7a50c728c4413890f6a8716bc`. Existing artifacts were preserved.

### 2026-11-07 — EXP-014 Supervised Forecasting
- **Branch / base:** Isolated `feature/exp-014-supervised-forecasting` worktree at `C:\Users\dyara\aqi-exp014`, from clean EXP-013 commit `ae8ebdcb75b4ce2030d0c7d68871ee474ffd61c3`. The separate EXP-008 worktree's uncommitted files were untouched. Current Train SHA-256 `fcee20ebf7bd9c4a4e2487bab0a4f81339d6c820a53862b14443031db1f18ad6`; no raw file changed.
- **Files:** Added `src/mumbai_pm25/supervised.py`, bounded rolling validation and in-memory inference scripts, focused tests, EXP-014 feature/data/model/leakage/results reports and CSV metrics. Existing W50 production code and model selection unchanged. No challenger CSV, binary, Zindi upload, push or merge.
- **Design:** 26,580 cutoff-safe examples from weekly 48-hour public-style (actual 1–48h) and private-style (actual 193–240h) historical windows; target labels joined after features. Five fixed supervised candidates plus W50 on 22 matched chronological folds and 3,430 scored rows per model (1,719 public, 1,711 private). Every fitting fold restricts training labels to end by its validation PM cutoff. The known August 2025 and May 2026 extreme periods are predeclared stress evidence, not confirmation.
- **Results:** CatBoost Huber is the best supervised model. Full RMSE public W50 1913.7996 vs Huber 1913.6724; private W50 1918.1655 vs Huber 1918.1244. Five extreme labels account for >99.97% of W50 squared error in each regime, so gains are not material. Ordinary-range RMSE public 22.5466 vs 18.6724, but private 27.3418 vs 34.0943. November RMSE public 35.3695 vs 29.3171, but private 44.2262 vs 63.0407. Recommendation RETAIN W50.
- **Commands:** `$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe scripts/validate_supervised.py --smoke` — 4 folds, 635 rows/model. `$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe scripts/validate_supervised.py` — 22 folds, 3,430 rows/model. `$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe scripts/smoke_supervised_inference.py` — 384 in-memory public/private rows, finite nonnegative, exact W50 feature parity, serialized CatBoost predictions identical, no CSV. `python scripts/train_predict.py --model hist24_blend50_median72 --model-run-time 2026-11-07T12:00:00+05:30 --output data/processed/exp014_w50_py313.csv` and the same command via `.venv\Scripts\python.exe` — both 2,592 rows and reference SHA-256 `55e2fc8c7cad94db22f1358a8715216b0c7fbbb7a50c728c4413890f6a8716bc`.
- **Verification:** Focused `$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -m pytest -q tests/test_supervised.py` — 7 passed. Full `$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -m pytest -q` — 80 passed, 1 warning. `.\.venv\Scripts\ruff.exe check src/mumbai_pm25/supervised.py scripts/validate_supervised.py scripts/smoke_supervised_inference.py tests/test_supervised.py` and `git diff --check` — passed. Initial full suite under isolated pandas 3.1.1 failed one existing empty-history test; isolated pandas 2.3.3 restored full pass without production edits. Dependency-version mismatch with `pyproject.toml` is documented.
- **Next:** Use the organiser's final Train refresh to audit new cutoff/leads and obtain new eligible labels. Investigate archive provenance and historical PM release timing before further supervised model promotion. No public leaderboard score was used to tune models.

### 2026-11-07 — EXP-014 Reproducibility Addendum
- Repeated the full pinned-environment rolling validation with identical 22 folds and 3,430 rows/model; `HORIZON_RESULTS.csv` SHA-256 remained `4b8ee1684129858a4a4bd3bc09a55a2c3eebf3a5d5c68ab8905587ed46a08cc1`. After the final focused test addition, 7 focused tests and 80 full tests passed (one existing pandas warning); scoped Ruff and diff checks passed. Initial pandas 3.1.1 failure and the isolated 2.3.3 compatibility pin are recorded in `MODEL_CONFIGURATIONS.md`.
