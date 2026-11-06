# Creative Track — Repository Implementation Plan

## Separation from forecasting work

The ML forecasting package remains the source of model predictions. The creative app is a separate product that consumes a versioned export. Do not duplicate model-training code in the frontend.

## Suggested repository additions

```text
apps/
  airwindow/
    README.md
    package.json
    src/
    public/
      data/
        forecast.json       # generated artefact; update via ML export script
    firebase.json
    .firebaserc.example

docs/
  PRIZE_STRATEGY_AND_ELIGIBILITY.md
  REAL_WORLD_AIR_QUALITY_BENCHMARKS.md
  CREATIVE_PRODUCT_SPEC_AIRWINDOW.md
  CREATIVE_JUDGING_AND_DEMO.md
  CREATIVE_DATA_AND_GOOGLE_TOOL_POLICY.md
  CLAIMS_AND_USER_SAFETY.md
  CREATIVE_TRACK_REPO_PLAN.md

prompts/
  CREATIVE_STRATEGY_AGENT_PROMPT.md

reports/
  creative_submission/
    USER_FEEDBACK.md
    DEMO_SCRIPT.md
    SUBMISSION_CHECKLIST.md
    screenshots/
```

## Work plan

### Phase 0 — Rules and access gate

- Ask whether awards can stack.
- Confirm undergraduate proof and category mechanics.
- Confirm creative presentation and closing-event dates.
- Confirm whether Firebase Hosting Spark and any proposed ClimateVerse/API use are acceptable.
- Record responses in `reports/organiser_clarifications.md` and append a decision in `DECISIONS.md` only when the answer is clear.

### Phase 1 — Product proof, not frontend polish

- Write a 1-page problem statement for schools/outdoor event coordinators.
- Obtain feedback from at least 2–3 potential users if feasible.
- Confirm the exact information needed to choose an activity window.
- Record user role, feedback date and anonymised notes. Do not fabricate interviews.

### Phase 2 — Forecast export contract

- Define `forecast.json` schema from `CREATIVE_PRODUCT_SPEC_AIRWINDOW.md`.
- Export station metadata, timestamp, model, predictions, issue time, validation metrics and calibrated intervals only if they exist.
- Add schema validation tests.
- Use a frozen, reproducible artifact for the app demo.

The initial proposed contract is recorded in `docs/FORECAST_ARTIFACT_CONTRACT.md` and implemented as `apps/airwindow/contracts/forecast.schema.json`. Obtain owner approval before creating the React/Vite app scaffold or publishing an artifact.

### Phase 3 — MVP app

- Build one clear responsive page with station selection, forecast chart, duration selection, ranked time windows, trust panel and shareable brief.
- Map only actual station points.
- No login, database, chatbot or route planner.
- Use mock data only for UI development and label it; replace it with a real generated forecast before submission.

### Phase 4 — Google deployment and QA

- Deploy static app through Firebase Hosting Spark if allowed.
- Verify public URL in incognito and on mobile.
- Test missing JSON, missing forecast hours, invalid values and slow network.
- Record app version and forecast artifact hash.

### Phase 5 — Judges' package

- Prepare live link, GitHub link, PDF <=10 MB, screenshots and 90-second demo.
- Add existing-solution comparison and differentiation.
- Include actual validation evidence and limitations.
- Submit the official form before the deadline and save confirmation.

## Branch and ownership policy

- Keep creative changes on `feature/airwindow-creative` (or a similarly scoped branch).
- Do not edit `src/mumbai_pm25/`, `scripts/legacy_validation/`, `DECISIONS.md` or `PROGRESS.md` concurrently with the ML agent without task ownership.
- The creative agent owns only `apps/airwindow/`, the creative docs and creative report folder unless explicitly assigned otherwise.
- Integrator reviews the forecast JSON contract and app claims.
- All shared changes go through a PR; no force-push; preserve append-only logs.

## Definition of done

- No fabricated forecast data.
- Real source and issue-time metadata displayed.
- Every user-visible interaction works.
- Station-only spatial representation is honest.
- Health and causal claims pass the claims/safety checklist.
- Public app is tested and deployed.
- Submission PDF and demo are ready under the official requirements.
