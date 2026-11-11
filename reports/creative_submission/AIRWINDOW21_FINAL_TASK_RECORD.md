# AirWindow Mumbai 2.1 final execution record

**Date:** 11 November 2026 IST
**Branch:** `feature/final-submission-upgrades`
**Scope:** Retrospective schedule baselines, forecast provenance/freshness, application polish, verification, static Hosting and submission package. Original challenge data was not modified.

## Evidence and decisions

`apps/airwindow/baseline_comparison.py` reproduces paired later-observed PM2.5 mean differences from the committed replay. Usual-cleanest start is selected only using past origins (development origins only for held-out confirmation); latest-window baseline selects the latest-starting complete feasible candidate. Whole-origin cluster bootstrap uses 2,000 resamples and seed 20261111. All results are retrospective and all four 95% intervals cross zero.

| Replay slice / baseline | Pairs / origins | AirWindow minus baseline (µg/m³) | 95% origin-cluster interval |
|---|---:|---:|---:|
| Full / usual-cleanest | 1,414 / 76 | -2.2814 | [-5.7183, 0.6910] |
| Full / latest-window | 1,411 / 77 | -0.1583 | [-2.3410, 2.0621] |
| Held-out / usual-cleanest | 169 / 8 | -0.7317 | [-2.6400, 0.5376] |
| Held-out / latest-window | 170 / 8 | -1.0063 | [-2.6593, 0.1639] |

Forecast source remains the validated final TASK011 P_fix artifact. Its issued time is 10 November 2026 15:47:52 IST, PM observation cutoff is 10 November 09:00 IST, and validity ends 21 November 00:00 IST. The source runner's issue deadline had passed, so no rerun or extrapolation was made. Original TASK008 forecast bytes remain preserved as the fallback.

## Deployment and package

Firebase CLI Hosting-only deployment to existing project `airwindow-99085` completed at 11 November 2026 21:09 IST, release `3b43a385b43dbc71`. Public URL: https://airwindow-99085.web.app. A fresh signed-out Chrome context returned HTTP 200 and verified forecast, replay (10,510,106 bytes), baseline and fallback JSON, content types and manifest SHA-256 values. No billing changes were made; the plan was not independently confirmed.

Updated five-page PDF: `AIRWINDOW_2_SUBMISSION.pdf`, 180,988 bytes (under 10 MB), SHA-256 `fe0ed7790244d1df0d949b16f04d7e388ee150dc8f9e54efe39e774770a7ba63`. Each rendered page was visually reviewed. The 90-second action/narration script is `DEMO_SCRIPT.md`; no video was recorded.

## Verification

- `npm.cmd test`: 13 passed, 0 failed.
- `.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp data/processed/airwindow-final-python-tests`: 149 passed; 19 existing Pandas deprecation warnings.
- Development browser suite: 8 passed; production-preview browser suite: 8 passed.
- `npm.cmd run build`: passed.
- Scoped Ruff: passed.
- `npm.cmd run verify:hosting`: passed in signed-out Chrome; 4 JSON artifacts, including replay, matched deployed SHA-256 manifest.
- `apps/airwindow/audit_release.py`: final hash/contract/replay/notebook audit to run after PDF metadata finalization.
- Remaining external actions: entrant checks current Zindi form requirements and submits personally; confirm Firebase billing plan in console. GitHub push is not authorized.

- Final audit: pps/airwindow/audit_release.py passed, verified forecast/replay/baseline/PDF hashes and executed all six notebook code cells locally. git diff --check passed; data/raw/challenge/ has no changes.
