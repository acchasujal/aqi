# AirWindow 2.1 final completion report

Task AIRWINDOW21, 9 November 2026 IST. Existing app extended, not rebuilt.

Starting commit: `dba644a1d0e7394794335dc2d98c2d64c548633c`, clean `main`.
`git fetch origin main` confirmed local/fetched main equality before edits. No
unmerged local work, branch creation, history rewrite or ML integration was needed.
Final implementation commit and publication evidence are recorded below after
the reviewed commit is created. This report does not claim an unperformed push.

## Delivered and preserved

- COMPLETE: original booking and complete consecutive 1/2/3-hour candidate
  arithmetic, genuine P_fix forecast, exact four stations, all replay cases and
  missing outcomes preserved. No training/model/raw data/private targets changed.
- COMPLETE: school-coordinator audience is explicit on opening; original remains
  prominent, lower numerical forecast remains separate from a justified move.
- COMPLETE: current elapsed observation age and age at issue are separate;
  minute refresh updates time context without an invented freshness threshold.
  Frozen snapshot, issue/cutoff and horizon remain explicit.
- COMPLETE: replay initially hides subsequent observations and hindsight; reveal
  is explicit and resets on case change. Chart scaling initially uses predictions
  only. Every complete forecast candidate is inspectable, including the original
  and selected labels. Original is retained on ties in the historical engine.
- COMPLETE: browser validates replay clocks, station IDs, complete candidate
  arithmetic/order, original/selected outcomes and aggregate coverage before
  render. Malformed or failed artifacts fail visibly; replay retry works.
- COMPLETE: trust centre exposes real historical station/lead full-target RMSE,
  row/origin counts and fold variability, with the exact unmatched-live-clocks
  warning. Provenance identifiers remain available. No live calibration is implied.
- COMPLETE: keyboard comparison moves focus to results; labels/focus/skip link
  and all main controls tested. Supporting mobile text enlarged and darkened.
- COMPLETE: actual one-page A4 brief includes original/alternative, both peaks,
  exact station/times, issue, PM cutoff, model/artifact and abstention/limitations.
- COMPLETE: active source links and repository plan use main; historical records
  remain historical. Submission overview/demo/checklist/PDF reflect current work.
- COMPLETE: all six notebook code cells executed locally and summary matched
  committed replay; direct Colab opening link and public-checkout setup provided.
  No raw challenge files or hidden targets are loaded by the notebook.

The core journey completes in the automated genuine-artifact browser test in
seconds; this is an engineering check, not a measured human usability result.
There were no user interviews, health-impact measurements or invented feedback.

## Exact verification

Environment: Windows ARM64, Python 3.12.10 (existing venv), Node v24.22.1,
npm 11.19.1, Vite 7.3.7, installed Google Chrome via Playwright. Existing
dependencies reused; no install or lockfile change.

Root commands:

```powershell
git fetch origin main
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --basetemp data/processed/airwindow21-python-tests
.venv/Scripts/python.exe apps/airwindow/audit_release.py
.venv/Scripts/python.exe -m ruff check apps/airwindow/*.py reports/creative_submission/build_submission_pdf.py tests/test_airwindow_decisions.py tests/test_forecast_artifact.py
git diff --check
```

Results: full Python suite **139 passed, 19 existing pandas deprecation warnings,
20.24s**. Includes AirWindow contracts/decision/replay and existing weather/ML
regressions. No existing Python behavior changed. The new release-audit entry
point passed separately: both artifact hashes/schema/semantics, final PDF size/hash
and screenshot source hashes, six notebook cells and all reproduced summary keys.
Scoped Ruff and diff checks passed.

App-directory commands:

```powershell
npm.cmd test
npm.cmd run build
npm.cmd run dev -- --port 5173
$env:AIRWINDOW_SCREENSHOT_DIR='../../reports/creative_submission/screenshots'
npm.cmd run test:browser
npm.cmd run preview -- --port 5174
$env:AIRWINDOW_BASE_URL='http://127.0.0.1:5174'
$env:AIRWINDOW_SCREENSHOT_DIR='../../data/processed/airwindow21-production'
npm.cmd run test:browser
```

Final domain tests: **12 passed**. Production TypeScript/Vite build: **passed**,
JS 276.75 kB / gzip 83.93 kB, CSS 33.03 kB / gzip 7.73 kB. Final dev-server Chrome
suite: **8 passed in 17.4s**. Final built-static Chrome suite: **8 passed in 14.5s**.
Genuine-path test checks browser exceptions, failed requests (excluding intentional
React StrictMode cancellation) and HTTP errors; none remain.

| Adversarial requirement | Actual evidence |
|---|---|
| Frozen/stale snapshot; unmatched issue/PM clocks; uncalibrated | Visible snapshot, actual ages, unmatched RMSE/abstention assertions |
| Missing forecast/original/alternative hour | Missing original fails; every candidate using missing alternative hour excluded; domain gaps never bridged |
| Incomplete replay outcome | Real missing-outcome case retained and explicitly unavailable after reveal |
| No improvement | Best-original/no-clear-winner browser case |
| Impossible duration | Invalid duration domain checks; too-short feasible range browser error |
| Past activity / partial expiry | Past starts rejected; 19 November clock excludes elapsed dates/hours |
| Complete expiry | 22 November clock prevents comparison and shows expiry message |
| Invalid JSON/schema / broken URL | Corrupt forecast/replay payloads, forecast 404, replay 503 and retry |
| Slow replay | Delayed route shows real loading before failure, no invented outcome |
| Mobile / zoom reflow | Plan/replay/trust fit 390px and 320px; 720px layout is 200%-equivalent reflow |
| Keyboard / headings / labels | Skip link focus, native selects, Enter comparison, result focus, three screens and labelled controls |
| Print | Chrome print-to-PDF, one A4 page, parsed required text and inspected rendered page |

Desktop plan/comparison/replay/trust, mobile captures, all five final PDF pages
and the print-rendered brief were visually inspected. Colour/focus and larger
supporting text were reviewed; this is not a WCAG or screen-reader certification.
Native browser zoom and native print-dialog inspection remain unverified: browser
host was unavailable; native Computer Use stopped because it could not confidently
verify the current Chrome URL. No further native input was attempted.

Failed intermediate attempts are not counted as passes: sandbox fetch first
failed to write FETCH_HEAD, then authorised fetch succeeded; isolated PDF package
reads first failed with PermissionError, then authorised rendering succeeded.
The new replay validator initially rejected legitimate original-retained ties
and cross-language nearly equal means; corrected before final tests. StrictMode's
intentional aborted initial request was initially counted as a network error;
the test now excludes ERR_ABORTED while retaining real failures. A PowerShell rg
glob failed and was replaced by directory/glob arguments. No raw input was edited
to satisfy any check.

## Final artifacts and package

| Artifact | SHA-256 |
|---|---|
| Forecast (unchanged) | `821c6b01078200baa61a754ff19b6af9a5ccee063f5cca51b5fa24f13f58f541` |
| Replay (unchanged) | `e99d60bfdade3db297f3553e80de0d6c4f08300e5b747978b59c54a134d32c10` |
| Final submission PDF | `aa0adabe83849a2bb647472d2ea935406a15768b5f34dca10494c42d72dfd168` |

The final submission PDF is **162,376 bytes, five A4 pages**, below 10 MB. Its
existing filename is retained to preserve package links. Source screenshot hashes,
page/text counts and all-page visual inspection are in its `.audit.json` and
`PDF_QA.md`. It was rebuilt because screenshots and the source-branch link changed.
The overview, architecture diagram, real evidence, red-team report, Google-tool
status, attribution/limitations, 90-second script and checklist are present. No
video was recorded/uploaded; the exact recording plan remains in DEMO_SCRIPT.md.

PDF command (existing isolated dependencies; no new installation):

```powershell
.venv/Scripts/python.exe reports/creative_submission/build_submission_pdf.py --desktop reports/creative_submission/screenshots/airwindow_desktop_decision.png --replay reports/creative_submission/screenshots/airwindow_desktop_replay_detail.png
```

## External gates and human actions

- BLOCKED: Firebase deployment. `Get-Command firebase` found no CLI; app
  `.firebaserc` and both standard configstore login paths were absent. No existing
  authenticated project or actual plan could be verified. Spark is the required
  plan, not a verified account state. No project, billing, Maps/AI service or public
  resource was created. **Deployed URL: none.** Exact Hosting-only handoff is in
  SUBMISSION_CHECKLIST.md. Owner must authenticate locally to an existing
  authorised Spark project and verify its plan before deployment.
- PENDING HUMAN ACTION: signed-in official form check and manual submission.
  The [official challenge page](https://zindi.world/competitions/google-mumbai-data-challenge)
  was reopened on 9 November and confirms **13 November 18:29 GMT / 23:59 IST**,
  impact/novelty/functionality and Google-tools bonus. The linked form redirects to
  `https://docs.google.com/forms/d/e/1FAIpQLSfv9KGRIAcMMvGFXRYRF2QOwpZ1vt7RU0e8-nFsUcJFxZkX-A/viewform`.
  Public web retrieval failed; authorised read returned **HTTP 401**, so current
  response status, fields, upload limit and video requirement are unverified.
  Earlier supplied fields/10 MB limit are preparation evidence only. The checklist
  provides accurate product text, source link and attachment, with public URL
  explicitly absent. Owner chooses identity/eligibility/travel answers and submits.
- NOT CLAIMED: Google-hosted Colab execution. Local notebook execution passed;
  the direct opening link is in app README. No login/session was used.
- NOT REQUIRED: new forecast, calibration or weather/ML experiment. Frozen issue
  remains 8 November 15:58 IST; PM cutoff remains 2 November 23:00 IST. No newer
  official release is assumed. Existing 1,848 scenarios/77 origins, 1,469 paired
  outcomes/379 missing and 63.67% of 1,291 numerical alternatives remain descriptive.

Scientific limits: four monitors cannot establish venue/street exposure; no
independent decision calibration, verified historical first-publication timing,
uncertainty interval, health guarantee or measured exposure benefit. Historical
RMSE includes all unmodified labels and is not a live reliability estimate.

## Changed files and publication record

Application: `src/main.tsx`, `src/domain.ts`, `src/styles.css`, both test files,
`playwright.config.mjs`, notebook, README and `audit_release.py` under
`apps/airwindow/`. Documentation: creative product/judging/repo-plan docs,
overview/red-team/demo/checklist/integration-QA/PDF-QA, PDF builder/audit/document,
genuine screenshots/brief, final gap audit and this report. Shared records:
append-only DECISIONS.md and PROGRESS.md. No ML source/config, raw files,
forecast/replay JSON, dependency lockfile or generated submission CSV changed.

Publication record follows after staged review. Human/platform gates above remain
open regardless of Git publication.
