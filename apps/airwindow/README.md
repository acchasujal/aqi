# AirWindow Mumbai 2.0

An activity scheduling prototype for school sports coordinators and outdoor-event organisers. Compare the original activity slot with every feasible consecutive one-, two- or three-hour window at one of the four actual Mumbai monitoring stations. Forecast differences, historical evidence and reasons to abstain stay visible.

The React/Vite/TypeScript client reads real, versioned static artifacts. It does not train a model or call external air-quality APIs. The current artifact is a frozen provisional TASK008 P_fix forecast, issued **8 November 2026 at 15:58 IST**, with PM history through **2 November at 23:00 IST**. Each station has 296 future forecast hours, ending **21 November 00:00 IST**. The UI calculates expiry from the actual artifact horizon and disables new planning after it ends.

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

`npm test` runs nine deterministic domain/boundary tests using Node's TypeScript stripping. `npm run build` checks TypeScript and creates `dist/`. The five Playwright browser tests require the development server and an installed Google Chrome (`channel: chrome`); no browser download or live cloud service is required. They exercise actual artifacts, every main screen, changed-input invalidation, original-slot retention, abstention, impossible ranges, invalid/missing forecasts, missing historical outcomes, partial/full horizon expiry, mobile overflow and a printable brief. Test fixtures never populate production data.

Browser captures are written to `reports/creative_submission/screenshots/` from the repository root. Playwright's temporary results remain under ignored `data/processed/airwindow-browser-tests/`.

## Forecast and replay data

- `public/data/forecast.json`: forecast schema **1.1.0**. It retains actual issue time and fractional issue-to-target horizons. Schema 1.0.0 and its validator remain supported. Every value has explicit IST intervals, PM cutoffs, model/source fingerprints and missing-value status.
- `public/data/replay.json`: separate retrospective OOF simulation, schema **1.0.0**. It is lazy-loaded when comparison evidence or replay is opened, so its uncompressed size does not block the initial form.
- `public/data/manifest.json`: artifact/input/source hashes and exact generation metadata.
- `evidence/replay_diagnostics.json`: chronological decision diagnostics and contiguous-origin resampling results.
- `contracts/` and the Python validators enforce forecast and replay boundaries. The browser also rejects invalid timestamps, horizons, units, station coordinates, values and completeness metadata.

To regenerate using the real upstream TASK008 provisional CSV, companion audit/row files and common OOF outputs, run **from the repository root**:

```powershell
.venv\Scripts\python.exe -m apps.airwindow.build_artifacts --prediction artifacts/submissions/task008_provisional_pfix_20261108_1558.csv --run-dir reports/ml_pipeline/task008/run01 --output-dir apps/airwindow/public/data
```

The builder requires the ignored `run01/all_block_rows.csv.gz` feature/prediction cache as well as labelled matched OOF. If that cache is absent, reproduce the upstream experiment with its documented command before export. Ranking uses complete forecast windows before actual outcomes are joined; historical missing outcomes remain in coverage counts. No private/hidden target labels are present in the app.

The shipped replay contains 1,848 predefined scenarios across 77 forecast origins: 1,469 paired observed outcomes and 379 cases without complete paired outcomes. The 63.67% lower-observed outcome rate describes 1,291 numerical alternatives with known paired outcomes. It is **not a calibrated probability or measured health benefit**. No changes are endorsed as calibrated recommendations. See the generated diagnostics for strict hindsight coverage and station/duration results.

## Reliability and product limits

The deterministic Python engine separates window ranking, paired historical errors, reliability and decision states. Independent chronological decision calibration has not passed. The live interface therefore abstains with **INSUFFICIENT EVIDENCE**, or **NO CLEAR WINNER** when the original is already as well ranked. It does not invent confidence percentages or intervals. Historical tentative/no-clear states are descriptive, and robust classification remains gated on independently validated calibration.

Historical OOF simulations freeze PM history at recorded pseudo-origins; first-publication timing is an explicitly unverified interval-end proxy. These simulations were generated retrospectively, not archived real-time published forecasts. Live issue/PM clocks differ from the historical 193–240h issue-lead experiment. The UI and event brief show relevant station RMSE as unavailable when exact clocks/leads do not match, rather than selecting an arbitrary favourable metric.

Only the four actual stations are represented, with exact identities and coordinates. No spatial interpolation, street-level inference, medical advice, hourly-to-AQI conversion or personal exposure estimate is provided. Freshness shows the real PM age at issue; no arbitrary fresh/stale threshold is invented. See `docs/CLAIMS_AND_USER_SAFETY.md` and `docs/FORECAST_ARTIFACT_CONTRACT.md` from the repository root.

## Firebase deployment preparation

`firebase.json` hosts only the static `dist/` output and configures security/cache headers. `.firebaserc.example` contains a placeholder, not a real project. Firebase CLI and authenticated project credentials were unavailable; **no site has been deployed and no billing has been enabled**.

After the account owner supplies an existing authorised **Spark** project and verifies current terms/quotas, build and deploy from this directory:

```powershell
npm.cmd run build
firebase login
firebase use --add
firebase deploy --only hosting --project YOUR_EXISTING_SPARK_PROJECT_ID
```

Do not upgrade to Blaze or enable Maps/paid services. Verify the deployed link, artifact hashes, mobile workflow and print output before using it in the creative submission. The app works locally without Firebase or network APIs. Google Colab replay material is prepared separately under `notebooks/`; it is not a dependency of the live app.

The judging package, actual screenshots, 90-second demo script, red-team review, submission PDF and deployment checklist are under `reports/creative_submission/`.
