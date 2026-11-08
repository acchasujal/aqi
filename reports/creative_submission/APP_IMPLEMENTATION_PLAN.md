# AirWindow Mumbai MVP Implementation Plan

> **8 November 2026 update:** This is the historical foundation plan. The current user-authorised AirWindow 2.0 implementation and evidence are described in [PRODUCT_OVERVIEW.md](PRODUCT_OVERVIEW.md), [RED_TEAM_REPORT.md](RED_TEAM_REPORT.md), [DEMO_SCRIPT.md](DEMO_SCRIPT.md) and the current [submission/QA checklist](SUBMISSION_CHECKLIST.md). Preserve the original findings below as historical context; the earlier scaffold approval gate has been superseded by the direct implementation request.

**Status:** Planned; full frontend is gated on approval of the forecast artifact contract.

## Selected workflow

1. Choose one of the four CPCB stations by its actual location ID and display name.
2. Inspect the station's hourly observed history and model forecast, with labels that distinguish the two.
3. Choose an activity duration of 1, 2 or 3 contiguous hours.
4. Rank complete future windows by the mean of their hourly PM2.5 point forecasts. Exclude windows that overlap missing hours and explain why they are unavailable.
5. Inspect last-observation age/status, PM-history cutoff, model issue time/version, weather vintage if used, and station validation RMSE/sample count.
6. Print/export a one-page plan with station location, selected and alternative windows, predicted values, freshness, validation evidence and limitations.

Use wording such as “lower predicted concentration among the windows shown.” Do not label a slot safe or healthy. Prominently state “station-based forecast; conditions at other streets or venues may differ.”

## Structure after contract approval

```text
apps/airwindow/
  package.json                 # React, Vite, TypeScript; minimal dependencies
  src/                          # accessible planner UI and pure window-ranking logic
  public/data/forecast.json     # generated real artifact; never a mock in production
  contracts/forecast.schema.json
  firebase.json                # static Hosting only
  .firebaserc.example          # placeholder only; no project secret
```

Keep the forecast exporter in the ML package or a dedicated ML script; the frontend consumes JSON and contains no training code. Use four markers only, no interpolated surface. Prefer a static SVG station diagram or an approved map library/tiles after tile-service terms are checked. Do not add Google Maps billing dependency.

## Acceptance checks

- All four station identifiers, names and coordinates match `Stations.csv`.
- Artifact schema and semantic validation pass; no public artifact is fabricated.
- For durations 1/2/3, windows are contiguous, sorted by arithmetic mean, and skipped if any hour is missing.
- Forecast and observed history are visually distinct; all times and values have IST timestamps and `µg/m³` units.
- Missing artifact, invalid schema, stale/unknown freshness and unavailable validation metrics have explicit states.
- Print view fits a single page and includes selection, alternatives, source/model, validation note and limitations.
- Keyboard, mobile viewport, accessibility contrast and external public access are tested before release.

## Test plan

1. Unit tests for duration bounds, contiguous window mean/ranking, tie handling and gaps.
2. Artifact-schema and temporal-invariant tests (added in this task).
3. Station metadata equality test against the challenge `Stations.csv`.
4. UI tests for station/duration selectors, empty/missing/invalid artifact states and keyboard flow.
5. Browser checks for desktop/mobile layout and print output.
6. Pre-deployment check of Firebase plan, project usage quotas, public/incognito URL, attribution, artifact hash and deployed commit.

## Next three implementation tasks

1. **Approve and implement the ML export.** Owner approves schema 1.0.0; the ML workstream then adds a reproducible forecast generator/exporter that records model commit, data hash, PM cutoff, issue time, weather provenance and explicit missing stations/hours.
2. **Produce trust evidence.** Compute station- and horizon-level full-target RMSE/sample counts on saved chronological OOF rows. Calibrate intervals on held-out rolling-origin residuals only if data support it; otherwise retain null intervals and label calibration unavailable. Complete a small round of coordinator feedback before UI copy is frozen.
3. **Build the static planner.** After the contract and a real artifact are available, implement the responsive React/Vite journey, contiguous-window ranking, trust panel and printable one-page brief; test mobile, keyboard and missing-data states before Firebase deployment.
