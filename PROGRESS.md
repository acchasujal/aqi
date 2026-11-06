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
- **Branch / commit:** `feature/airwindow-creative` / pending
- **Files changed:** Integrated seven creative docs and the creative master prompt into canonical folders; updated `README.md` and `AGENTS.md`; added `apps/airwindow/contracts/forecast.schema.json`, `apps/airwindow/contract_validation.py`, and `tests/test_forecast_artifact.py`; added `docs/FORECAST_ARTIFACT_CONTRACT.md`, `reports/creative_submission/INTEGRATION_AUDIT.md`, `APP_IMPLEMENTATION_PLAN.md`, and preserved the strategy-pack README; updated the AirWindow README, creative repo plan, `pyproject.toml`, `DECISIONS.md`, and this log.
- **Work completed:** Confirmed no production forecast/export script or real forecast JSON exists. Ignored legacy OOF pickle files contain row-level predictions, but committed reports have no station-level validation metrics. Issue-time provenance cannot be built from the current export path. No empirical prediction-interval calibration exists. Firebase Spark was assessed as a possible static host; no project, billing or deployment was created.
- **Commands run:** `git switch -c feature/airwindow-creative`; PowerShell `Move-Item` to merge the supplied strategy docs; `.venv\Scripts\python.exe -m pip install --only-binary=:all: "pytest>=8,<9" "jsonschema>=4.22,<5"`; `.venv\Scripts\python.exe -m json.tool apps/airwindow/contracts/forecast.schema.json`; `.venv\Scripts\python.exe -m pytest tests/test_forecast_artifact.py -q`.
- **Tests and exact results:** `.venv\Scripts\python.exe -m json.tool apps\airwindow\contracts\forecast.schema.json` passed; `.venv\Scripts\python.exe -m pytest -q` passed (15 tests); `git diff --check` passed; `git diff -- data/raw/challenge` was empty. Tests cover synthetic in-memory fixtures, weather issue metadata, unknown validation, calibrated intervals, missing forecasts, target interval/horizon consistency, freshness, time cutoffs and station metadata. No fixture is a real or public prediction.
- **Experiment IDs / metrics:** Not an ML experiment. No forecast RMSE or real prediction artifact created.
- **Decisions added or superseded:** App/ML separation and versioned artifact consumer recorded as `DEC-20261106-07`.
- **Known limitations / blockers:** Schema is a draft pending owner approval. No inference/export script, committed row-level OOF predictions, station metrics or calibrated uncertainty exist. Zindi has not specifically confirmed Firebase acceptance. Generic and competition-specific rules text still conflict on submission counts/splits.
- **Next action:** Owner reviews/approves schema 1.0.0; then implement the real ML artifact exporter before beginning the React/Vite frontend.
