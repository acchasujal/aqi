# AirWindow Mumbai

Separate creative-submission product. The repository currently has no production forecast exporter or real forecast artifact. This directory contains the proposed contract and validator only; the React/Vite application is gated on owner approval of the contract.

Read before implementing:
- `docs/CREATIVE_PRODUCT_SPEC_AIRWINDOW.md`
- `docs/CREATIVE_JUDGING_AND_DEMO.md`
- `docs/CREATIVE_DATA_AND_GOOGLE_TOOL_POLICY.md`
- `docs/CLAIMS_AND_USER_SAFETY.md`
- `docs/CREATIVE_TRACK_REPO_PLAN.md`
- `AGENTS.md`
- `docs/FORECAST_ARTIFACT_CONTRACT.md`

## MVP

React + Vite + TypeScript static app. Use four station markers, hourly forecast chart, duration selection, lower-predicted-window ranking, trust centre and shareable brief. Use only four station points; no continuous spatial interpolation.

## Data contract

The proposed artifact schema is `contracts/forecast.schema.json`. Validate the schema and temporal invariants before the browser loads `public/data/forecast.json`. No real `forecast.json` exists yet. If no artifact or metadata is available, show an explicit missing/unknown state; do not fabricate values, station validation metrics or confidence intervals.

## Deployment

Firebase Hosting Spark is a candidate for static hosting if the project remains on Spark and within quotas. Hosting plan review found no payment method is needed for Spark, but Zindi has not specifically confirmed Firebase acceptance. Do not enable a billing plan or paid service. No Firebase project, site, URL or deployment exists.
