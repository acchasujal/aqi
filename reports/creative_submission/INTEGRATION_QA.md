# AirWindow 2.0 integration verification — 8 November 2026

Work uses existing `feature/task008-final-gap-execution` at ML evidence commit `186463680a5a5180a0cc970da348c20fa34f73bd`. The user explicitly requested parallel execution on an existing branch and a push. Frontend, artifact/evidence and narrative/package work used disjoint file ownership; root owns shared records and final integration. No new branch, main push or PR #4 merge.

## Completed Python and provenance checks

`.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp data/processed/airwindow-integration-tests-final`: **60 passed in 9.38s**, process exit 0. This includes existing ML tests plus versioned forecast validation, complete-window arithmetic, missing/boundary handling, reliability states, replay validation, all-1,848-case outcome perturbation and explicit rejection of current private actuals.

`.venv\Scripts\python.exe -m ruff check apps/airwindow/*.py reports/creative_submission/build_submission_pdf.py tests/test_airwindow_decisions.py tests/test_forecast_artifact.py`: **all checks passed**. One pre-existing import-order issue in the relevant forecast-artifact test was corrected without changing its assertions. Earlier scoped lint excluded that old finding; the final relevant scope is clean.

Evidence agent's focused suite: 22 passed in 5.56s. Export completed from the real audited ML CSV/row manifest, matched OOF and full hourly cache. Notebook code cells executed locally; no live Colab execution is claimed. Forecast issue remains 8 November 15:58 IST; export generation is a separate actual timestamp. The replay's 77 forecast origins include 76 with paired outcomes; missing outcomes remain counted. No current private observations appear in the product artifacts.

Forecast data covers 296 intended future hourly records per station through 21 November 00:00 IST, including explicit missing hours. The underlying fixed Test grid has gaps; missing rows are not manufactured as forecasts. The UI must use actual artifact bounds. PM age and issue lead differ, and historical RMSE/reliability are not claimed to calibrate unmatched live clocks.

## Platform access

No Firebase command, configured `.firebaserc`, or credential file at either standard local configstore path was found. Browser access host was unavailable. Deployment is prepared, not performed. No billing, account creation, login, Google Maps, Earth Engine or runtime external forecasting API was enabled. No creative form was submitted.

## Frontend and browser completion

Executed from `apps/airwindow/`:

```powershell
npm.cmd install --no-audit --no-fund
npm.cmd install --save-dev @playwright/test --no-audit --no-fund
npm.cmd test
npm.cmd run build
npm.cmd run dev -- --port 5173
npm.cmd run test:browser
```

Final domain suite: **9 passed**. Final build: **passed**, JavaScript 268.53 KB / gzip 81.95 KB, CSS 31.75 KB / gzip 7.50 KB. Final real installed-Chrome Playwright suite: **5 passed in 7.7s**. The dev server remains available at `http://127.0.0.1:5173/` (local only). Dependencies and dev server required sandbox escalation; initial pre-install build lacked tsc, and one initial browser selector was ambiguous. Both were corrected before final checks. No failed attempt is counted as a passed final test.

Browser checks cover genuine-artifact planning and original/alternative comparison, insufficient-evidence state, a best-original/no-clear-winner case, evidence navigation, lazy replay loading, station/duration controls, invalid/missing forecasts, impossible duration, missing observed outcomes, draft edits invalidating results, 390px mobile overflow, printable brief, 19 November partial-horizon expiry and 22 November full expiry. Elapsed dates/hours are excluded from live planning; replay stays retrospective. There is no independently calibrated robust live case, so that adversarial scenario is unavailable rather than simulated in production screenshots.

Visual review caught and corrected two scientific presentation issues: the live brief initially displayed the first measured historical lead's RMSE regardless of current clocks, and replay labels could imply an archived real-time publication. The final UI requires matching issue/PM lead evidence, shows **Unavailable** for the unmatched live metric, and explicitly labels replay as a retrospectively generated forecast simulation at a recorded origin. A late partial-horizon check also prevented past event dates from remaining selectable while later forecast dates exist.

Root inspected actual desktop planning/decision/replay detail and mobile captures. The comparison retains the original and complete alternatives, with explicit units, peak hours and abstention. The default replay example displays a numerical alternative that was worse in subsequent observations, not a selected success. Missing observations have no invented zero bars. Root also inspected rendered submission PDF pages 1, 3 and 5; the package owner inspected all five pages. No screenshot is synthetic.

The event brief PDF was independently parsed as **one A4 page** (49,299 bytes at that capture). The final submission PDF is **five A4 pages, 157,195 bytes**, SHA-256 `e457929edc97bcb730b4c62ffff3fc8436bd91cf72d6a190a22da7678799786e`. Its final PDF/visual/source checks pass in `AIRWINDOW_2_SUBMISSION.audit.json` and `PDF_QA.md`. A supplementary root text-dump probe hit Windows cp1252 output encoding after successfully parsing page counts; this was a console printing limitation, not a PDF parse/layout failure.

Final backend annotation-only export at 16:28:14 IST preserved every forecast value, replay decision/state/outcome/profile and metric exactly; 22 focused tests passed again in 5.37s and scoped lint passed. No further ML code or raw data changed. Generated artifacts are versioned product outputs; dependency caches, build output, PDF dependency/render folders and test traces remain ignored.

Git attributes mark PDFs and generated public JSON payloads as binary for Git storage/diffs (including byte-preserving `-text`). The files remain ordinary readable JSON to the application. This prevents text line-ending conversion from invalidating PDF cross-reference offsets or the published forecast/replay manifest hashes, and avoids enormous line diffs for generated payloads. Staged artifact bytes are checked against their audits before commit; no document bytes are edited to satisfy a text-whitespace check.

## Remaining limits

No formal user study, independent calibration, cross-browser certification, public Firebase deployment, cloud Colab execution or creative-form processing is claimed. The app works locally and its static hosting configuration is ready. Forecasts remain the provisional current-data P_fix snapshot; actual final ML data refresh is separate pending work.
