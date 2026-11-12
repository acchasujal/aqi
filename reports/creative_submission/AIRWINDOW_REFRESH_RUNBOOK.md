# AirWindow forecast refresh gate

**Status (12 November 2026):** No refresh is scheduled or claimed. The live artifact is the frozen TASK011 final P_fix issue from 10 November. Existing `refresh_forecast_artifact.py` only validates and exports that exact audited prediction hash; it deliberately rejects a different candidate. The workflow in `.github/workflows/firebase-hosting-merge.yml` builds and deploys static files on `main`; it does not generate forecasts.

## Required input and review gate

1. Obtain a newly released, permitted source snapshot. Record the official source URL, retrieval/release time, source licence and organiser permission. Preserve raw challenge files unchanged; put versioned inputs in a new processed release directory with exact hashes.
2. Run the existing final-refresh inference pipeline on the accepted snapshot with actual issue time and station-specific PM history cutoff. Do not use `available_at` as publication time; reject any PM observation after its cutoff. Keep PM cutoff separate from weather issue time. Weather remains out unless a defensible archived as-issued vintage and terms are documented.
3. Reproduce matched chronological validation for the candidate against P_fix. Report full-target RMSE, clean-range diagnostic, bias, station/origin results, fold variability and row counts. Do not promote based on public leaderboard feedback.
4. Export forecast JSON to a versioned staging directory, never directly over `public/data/forecast.json`. Run the forecast schema validator and check explicit IST offsets, issue/cutoff ordering, contiguous one-hour targets, unique sorted timestamps, finite non-negative available predictions, exact missingness counts, expected four station IDs/coordinates, horizon, artifact/source hashes and generation time after issue.
5. Validate every consumer artifact against the source forecast/replay hashes. Preserve the current `forecast.json` and fallback bytes, compare staged schema/coverage/metadata, and only then prepare a reviewed change. Keep a previous known-good artifact for rollback. No scheduled job may publish or deploy on its own until a human-reviewed refresh succeeds end to end.
6. The existing GitHub Actions deployment is Hosting-only but deploys on a push to `main`. Do not push a candidate or change workflow triggers as a way to test refresh. Verify the built static app and exact artifact hashes locally first; publication still requires explicit owner authorization.

## Current implementation boundaries

`apps/airwindow/refresh_forecast_artifact.py` checks the frozen TASK011 prediction, manifest, integrity record, exact SampleSubmission ID order, overlay/private counts, temporal cutoffs, and contract before writing the static artifact and manifest. It has a hard-coded reviewed output hash and is not a general future-release runner. The upstream `scripts/run_task011.py` currently generates competition submissions and OOF reports; connecting it to an automated product refresh would require a separate versioned export interface and deterministic staging/rollback tests. Do not relax the pinned hash or schedule a job against the current expired source.

## Go/no-go criteria

Do not refresh if source licensing/organiser permission is unclear, data fingerprints or station cutoffs fail, issue time is missing, any prediction row is missing/duplicate/nonfinite/negative without an explicit missing status, hour continuity breaks, station identity is ambiguous, matched validation is unavailable, or staged hashes cannot be reproduced. On failure, retain the current artifact and record the blocker; never silently extend validity.
