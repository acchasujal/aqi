# AirWindow Mumbai 2.1

An activity scheduling prototype for school sports coordinators and outdoor-event organisers. Compare the original activity slot with every feasible consecutive one-, two- or three-hour window at one of the four actual Mumbai monitoring stations. A station is a measurement proxy and may not represent the school ground or event venue. Forecast differences, historical evidence and reasons to abstain stay visible.

The React/Vite/TypeScript client reads real, versioned static artifacts. It does not train a model or call external air-quality APIs. The current artifact is the frozen TASK011 final P_fix run, issued **10 November 2026 at 15:47:52 IST**, with PM history through **10 November at 09:00 IST**. Each station has 248 future forecast hours, ending **21 November 00:00 IST**. The UI shows issue, observation cutoff and validity horizon, and disables new planning after expiry. The former 8 November TASK008 forecast is preserved as `public/data/forecast_fallback_task008.json`.

## Run locally

Node 24 and npm were used on Windows ARM64. From this directory:

```powershell
npm.cmd ci --no-audit --no-fund
npm.cmd run dev -- --port 5173
```

Open `http://127.0.0.1:5173/`. On shells where npm is directly executable, `npm` is equivalent to `npm.cmd`. PowerShell execution policy on the development machine required the `.cmd` form.

```powershell
npm.cmd test
npm.cmd run build
npm.cmd run test:browser
```

`npm test` runs deterministic domain/boundary tests using Node's TypeScript stripping. `npm run build` checks TypeScript and creates `dist/`. The nine Playwright browser tests require the development server and an installed Google Chrome (`channel: chrome`); no browser download or live cloud service is required. They exercise actual artifacts, every main screen, paired baseline metrics, changed-input invalidation, original-slot retention, abstention, impossible ranges, invalid/missing forecasts, missing historical outcomes, partial/full horizon expiry, mobile overflow and a printable brief. Test fixtures never populate production data.

Browser captures are written to `reports/creative_submission/screenshots/` from the repository root. Playwright's temporary results remain under ignored `data/processed/airwindow-browser-tests/`.

## Forecast and replay data

- `public/data/forecast.json`: forecast schema **1.1.0**. It retains actual issue time and fractional issue-to-target horizons. Schema 1.0.0 and its validator remain supported. Every value has explicit IST intervals, PM cutoffs, model/source fingerprints and missing-value status.
- `public/data/replay.json`: separate retrospective OOF simulation, schema **1.0.0**. It is lazy-loaded when comparison evidence or replay is opened, so its uncompressed size does not block the initial form.
- `public/data/baseline_comparison.json`: reproducible expanding-origin and held-out schedule-baseline results derived from the replay artifact; pinned to its SHA-256 in the manifest.
- `public/data/manifest.json`: artifact/input/source hashes and exact generation metadata.
- `public/data/forecast_fallback_task008.json`: byte-preserved prior forecast snapshot for rollback.
- `evidence/replay_diagnostics.json`: chronological decision diagnostics and contiguous-origin resampling results.
- `contracts/` and the Python validators enforce forecast and replay boundaries. The browser also rejects invalid timestamps, horizons, units, station coordinates, values and completeness metadata.

To regenerate using the real upstream TASK008 provisional CSV, companion audit/row files and common OOF outputs, run **from the repository root**:

```powershell
.venv\Scripts\python.exe -m apps.airwindow.build_artifacts --prediction artifacts/submissions/task008_provisional_pfix_20261108_1558.csv --run-dir reports/ml_pipeline/task008/run01 --output-dir apps/airwindow/public/data
```

The builder requires the ignored `run01/all_block_rows.csv.gz` feature/prediction cache as well as labelled matched OOF. If that cache is absent, reproduce the upstream experiment with its documented command before export. Ranking uses complete forecast windows before actual outcomes are joined; historical missing outcomes remain in coverage counts. No private/hidden target labels are present in the app.

The shipped replay contains 1,848 predefined scenarios across 77 forecast origins: 1,469 paired observed outcomes and 379 cases without complete paired outcomes. Aggregate statistics and baseline comparisons appear immediately; each selected case's later observations stay hidden until explicitly revealed. The 63.67% lower-observed outcome rate describes 1,291 numerical alternatives with known paired outcomes. It is **not a calibrated probability or measured health benefit**. No changes are endorsed as calibrated recommendations. Schedule-baseline reports include pooled mean and median deltas, case/origin counts, origin-cluster bootstrap intervals, origin-level direction counts, and an equal-origin Student-t sensitivity interval. See the generated diagnostics for strict hindsight coverage and station/duration results.

## Reliability and product limits

The deterministic Python engine separates window ranking, paired historical errors, reliability and decision states. Independent chronological decision calibration has not passed. The live interface therefore abstains with **INSUFFICIENT EVIDENCE**, or **NO CLEAR WINNER** when the original is already as well ranked. It does not invent confidence percentages or intervals. Historical tentative/no-clear states are descriptive, and robust classification remains gated on independently validated calibration.

Historical OOF simulations freeze PM history at recorded pseudo-origins; first-publication timing is an explicitly unverified interval-end proxy. These simulations were generated retrospectively, not archived real-time published forecasts. Live issue/PM clocks differ from the historical 193–240h issue-lead experiment. The UI and event brief show relevant station RMSE as unavailable when exact clocks/leads do not match, rather than selecting an arbitrary favourable metric.

Only the four actual stations are represented, with exact identities and coordinates. They are measurement proxies and may not represent any school ground or venue; no nearest-station or representativeness claim is made. No spatial interpolation, street-level inference, medical advice, hourly-to-AQI conversion or personal exposure estimate is provided. Freshness shows the real PM age at issue; no arbitrary fresh/stale threshold is invented. See `docs/CLAIMS_AND_USER_SAFETY.md` and `docs/FORECAST_ARTIFACT_CONTRACT.md` from the repository root.

## Firebase Hosting

`firebase.json` hosts only the static `dist/` output and configures security/cache headers. The app is deployed to the existing `airwindow-99085` project at **https://airwindow-99085.web.app**. Hosting release `3b43a385b43dbc71` completed on 11 November 2026 at 21:09 IST. A fresh signed-out Chrome context verified the homepage and forecast, replay (10.5 MB), baseline comparison and preserved fallback JSON against the public manifest SHA-256 values. Deployment used Hosting only and did not change billing. The project billing plan was not independently verified.

To reproduce the Hosting-only release from this directory:

```powershell
npm.cmd run build
firebase.cmd deploy --only hosting --project airwindow-99085 --non-interactive
```

No billing-plan change, Maps or other paid service was enabled; the existing project billing tier has not been independently checked. The app works locally without Firebase or runtime network APIs. Google Colab-compatible replay material is under `notebooks/`; all six cells were executed locally, but a hosted Colab session has not been verified. It is not a dependency of the live app.

GitHub Actions are configured in the repository root at `.github/workflows/firebase-hosting-merge.yml`. Pushes to `main` build from this directory and deploy the live Hosting channel. The encrypted repository secret is `FIREBASE_SERVICE_ACCOUNT_AIRWINDOW_99085`. Once the workflow commit is pushed to `main`, subsequent `main` updates deploy automatically.

The judging package, actual screenshots, 90-second demo script, red-team review, submission PDF and deployment checklist are under `reports/creative_submission/`.

## 9 November final audit

Work now continues on `main`; older feature-branch instructions are historical.
Replay starts with forecasts only, reveals subsequent observations on request, and
lists every ranked complete candidate. Switching cases hides outcomes again.
The browser checks replay ranking, arithmetic, clocks and coverage before display;
failed replay loads have a working retry. The trust centre exposes exact historical
station/lead RMSE, rows, origins and fold variability with the unmatched-clock warning.
Current observation age updates every minute; it does not invent a freshness limit.
The printable brief includes PM cutoff and both peak times on one A4 page.

From the repository root, verify forecast/replay/PDF source hashes and execute all
six notebook code cells locally:

```powershell
.venv/Scripts/python.exe apps/airwindow/audit_release.py
```

[Open Decision Replay in Google Colab](https://colab.research.google.com/github/acchasujal/aqi/blob/main/apps/airwindow/notebooks/Decision_Replay.ipynb).
Run all cells; setup clones public main if needed. Local execution passed; no
Google-hosted session is claimed. Colab must provide pandas, NumPy and jsonschema.

For the built-static smoke test, run `npm.cmd run preview -- --port 5174` and use
`AIRWINDOW_BASE_URL=http://127.0.0.1:5174` with `npm.cmd run test:browser`.
Set `AIRWINDOW_SCREENSHOT_DIR=../../data/processed/airwindow21-review` for ordinary
reruns so audited package screenshots are not overwritten. Rebuild and review the
PDF whenever its source screenshots change. No service worker is installed: the
app needs a local static server for disconnected use; a first visit to a public
URL is not guaranteed to work offline.

See the final gap audit and completion report under `reports/creative_submission/`
for exact results, public-deployment blockers and human submission actions.
