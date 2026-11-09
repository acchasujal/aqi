# Mandatory Instructions for Every AI Agent and Contributor

These instructions apply to every agent, script, notebook, pull request and human contributor. Read this file before touching the repository.

## 1. Read context before acting

Before editing code, read in this order:
1. `README.md`
2. `docs/CHALLENGE_SPEC.md`
3. `docs/DATA_AUDIT.md`
4. `docs/EVALUATION_AND_RULES.md`
5. `docs/FORECASTING_ARCHITECTURE.md`
6. `docs/VALIDATION_PROTOCOL.md`
7. `docs/EXTERNAL_DATA_POLICY.md`
8. `DECISIONS.md`
9. `PROGRESS.md`

Then inspect the relevant code, config, tests and current Git diff. Never rely solely on chat history or summaries.

## 2. Non-negotiable correctness rules

- Never modify or overwrite files in `data/raw/challenge/`.
- Never commit hidden/private targets, credentials, API keys, cookies, access tokens or personal information.
- Never use test targets, future observations, future station readings, future weather observations, or post-issue-time forecast products as predictors.
- Never use `scoring_block`, `ID` token fragments, or submission row order as predictive features.
- Never treat missing PM2.5 as zero.
- Never treat `mean` as an independent feature; it duplicates `pm25` in the audited release.
- Do not use `count`, `available_at`, `series_id`, flags or source metadata as predictive values unless a documented prediction-time availability test explicitly approves the use. `available_at` is not verified first-publication time.
- Station identity is allowed as a categorical feature. Do not use numeric station/sensor IDs as continuous magnitudes.
- The primary validation metric is full-target RMSE on all labelled validation rows. A clean-range metric such as `y < 500` is diagnostic only and can never replace the primary metric.
- Do not delete, clip or winsorise target values by default. Extreme-value treatments require controlled ablations and must be evaluated on unmodified validation labels.
- Do not claim a score improvement unless it is reproduced on identical chronological folds and recorded in the experiment log.
- Do not tune only to the public leaderboard.

## 3. Time and leakage rules

- All competition timestamps are Asia/Kolkata (IST, UTC+05:30).
- Train `timestamp_ist` marks the **end** of its hourly observation interval. Its aligned interval start is `timestamp_ist - 1 hour`.
- Test `target_start_ist` is the start of the target hour. Use this for test-time joins.
- Every feature row must carry an explicit `prediction_origin`/`issue_time`, `pm_history_cutoff`, `target_start`, and `target_end` in validation datasets.
- PM history cutoff and weather forecast issue time are distinct clocks. Model the actual final information set, not one approximate gap for both sources.
- For weather, select a forecast run whose publication/availability time is no later than the pseudo-issue time. A run initialisation timestamp is not the same as its publication time.
- Historical weather observations/reanalysis are not interchangeable with archived forecast vintages.
- Build lags only after constructing a complete hourly grid per station. A previous row is not necessarily a previous hour.
- Rolling/lag features must be strictly past-only relative to their prediction origin.
- Recursive forecasts must never use hidden future target values.

## 4. Modelling discipline

- Baselines before complexity: last observation, recent mean/median/EWM, hour-of-week profile, recent diurnal profile.
- Candidate supervised model: LightGBM/XGBoost/ExtraTrees only after robust baselines and fold design are stable. Current evidence supports testing LightGBM ratio-to-recent-level, not treating it as final.
- Test previous-year same-hour features as a hypothesis; do not hardcode a seasonal spike.
- Weather features are experimental until demonstrated to improve matched rolling-origin folds.
- No AutoML. No paid API, compute or dataset without explicit approval and organiser/terms compliance.
- Keep model count small. Prefer reproducible blends over complex stacking unless out-of-fold evidence supports stacking.
- Every model must report full-target RMSE, clean-range diagnostic RMSE, bias, station-level RMSE, fold variability and evaluated row counts.

## 4a. Creative product isolation

- Keep creative application code under `apps/airwindow/` and creative product documentation under `docs/` and `reports/creative_submission/`.
- Creative-app changes must not destabilise ML code or modify model behavior, training data, validation logic or submission generation without a separate ML task and matched evidence.
- The app consumes a versioned forecast artifact produced by the ML pipeline; do not duplicate model training or fabricate forecast data in the frontend.
- Preserve honest station coverage, explicit data freshness and validation metadata, and the user-safety rules in `docs/CLAIMS_AND_USER_SAFETY.md`.
- Do not show uncertainty intervals unless they have been empirically calibrated on appropriate rolling-origin residuals.

## 5. Code quality requirements

- Use small, single-purpose modules and typed function signatures where practical.
- Use `pathlib`; no hard-coded machine-specific absolute paths.
- No hidden working-directory assumptions. Resolve paths from config/repository root.
- No data processing at module import time.
- No global mutable state.
- Make random seeds explicit and centrally configured.
- Do not silently catch broad exceptions; provide actionable errors.
- Validate schemas, timezones, uniqueness, finite values and expected row counts at boundaries.
- Use vectorised Pandas/NumPy where readable; avoid unnecessary row-wise `apply` and repeated full-frame copies.
- Avoid adding heavyweight dependencies without a measured need and compatibility check for Windows ARM64.
- Keep functions deterministic; log parameters and data fingerprints for experiments.
- Write tests for feature leakage, timestamp alignment, missing-hour handling, submission order and non-negative finite outputs.
- Do not place experimental logic in production functions without a test and decision record.

## 6. Git and collaboration rules

- Reuse the current branch by default; do not create a new branch for every task. Work on `main` when the owner requests it, and create a branch only when explicitly requested or necessary to isolate unrelated work. Never force-push or rewrite shared history.
- Keep PRs narrow: one coherent experiment or one architecture change per PR.
- Do not allow two agents to edit the same file concurrently. Claim files/tasks in the PR or task issue.
- Do not edit old entries in `DECISIONS.md` or `PROGRESS.md`; append new entries only.
- For a decision, add a dated entry with evidence, confidence, alternatives and consequences.
- For progress, add a dated entry with task ID, files changed, commands/tests run, outputs and blockers.
- Never resolve a conflict by blindly choosing `ours` or `theirs`. Inspect both sides, preserve valid unique records, rerun checks and document the resolution.
- Do not commit generated model binaries, large intermediate datasets, raw weather downloads or submissions unless explicitly requested.
- Avoid unrelated formatting churn and lockfile churn.

## 7. Required workflow for every task

1. State the task and expected files changed.
2. Read relevant docs and current decisions.
3. Inspect current code/tests before editing.
4. Create or update an experiment/task record.
5. Implement the smallest change that proves the hypothesis.
6. Add/modify tests.
7. Run relevant tests and a small smoke test.
8. Report exact commands and results; do not claim unrun tests passed.
9. Update `PROGRESS.md`; update `DECISIONS.md` only if a decision is actually made.
10. Summarise changed files, evidence, remaining risks and next step.

## 8. Definition of done

A task is not complete unless:
- Scope is met.
- No raw data was modified.
- Tests pass or failures are clearly disclosed.
- No known leakage was introduced.
- Experiment results are reproducible and logged where relevant.
- Documentation and progress records are updated.
- Git diff contains only intended changes.
