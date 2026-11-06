# AI Agent Operating Guide

## Agent roles

Prefer one clearly scoped agent at a time for shared core files. Possible roles:
- Data auditor: only `audit.py`, audit report and tests.
- Weather researcher: only weather data fetch/manifest and external-data notes.
- Validation engineer: fold generation, validation tests and metrics.
- Modelling engineer: one model module/config per experiment.
- Integrator: review PRs, reconcile decisions and progress, run end-to-end checks.

## Task handoff contract

Each agent must receive:
- Task ID and exact question.
- Files it owns and files it must not edit.
- Required reads.
- Data version/hash.
- Validation folds and metrics.
- Acceptance criteria.
- Expected artifacts.

## Agent report format

1. Objective.
2. Repository state and commit SHA.
3. Files changed.
4. Methods and assumptions.
5. Commands actually run.
6. Test results (passed/failed/not run).
7. Experiment results with exact fold IDs.
8. Leakage and licence checks.
9. Decisions proposed (do not silently adopt).
10. Remaining issues and next step.

## No-go behaviours

- Do not invent missing API responses, results or files.
- Do not say “complete” if a network-dependent step was not run.
- Do not leave unfinished background processes or claim future work.
- Do not rewrite canonical docs wholesale. Make focused changes and preserve history.
- Do not create multiple competing copies of the same plan. Update the canonical docs and append a progress record.
