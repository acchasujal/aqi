# Mumbai PM2.5 Forecasting — Zindi Google Mumbai Data Challenge

Research and modelling repository for hourly PM2.5 forecasting at four Mumbai CPCB CAAQMS stations.

> **Current repository status (2026-11-13):** the main competition work has concluded; this branch develops AirWindow's external-observation research from the versioned OpenAQ audits. Earlier baseline planning below is preserved as project history, not a current model-selection recommendation. The AirWindow forecast is a frozen November 2026 artifact, not a live feed.

## Start here (humans and AI agents)

1. Read [`AGENTS.md`](AGENTS.md) before changing anything.
2. Read [`docs/CHALLENGE_SPEC.md`](docs/CHALLENGE_SPEC.md), [`docs/DATA_AUDIT.md`](docs/DATA_AUDIT.md), [`docs/EVALUATION_AND_RULES.md`](docs/EVALUATION_AND_RULES.md), and [`docs/FORECASTING_ARCHITECTURE.md`](docs/FORECASTING_ARCHITECTURE.md).
3. Read [`DECISIONS.md`](DECISIONS.md) and [`PROGRESS.md`](PROGRESS.md) to understand what has and has not been decided or completed.
4. Use [`prompts/MASTER_AGENT_PROMPT.md`](prompts/MASTER_AGENT_PROMPT.md) to initialise a new coding/research agent.
5. Before starting a task, create or update an experiment entry in [`experiments/EXPERIMENT_LOG.csv`](experiments/EXPERIMENT_LOG.csv).

## Objective

Predict hourly PM2.5 concentration (µg/m³) for every ID in the fixed 2,592-row `Test.csv`. The competition metric is RMSE. The submission must preserve test ID order and contain finite, non-negative predictions.

## Canonical repository layout

```text
.
├── AGENTS.md / CLAUDE.md / GEMINI.md
├── README.md
├── DECISIONS.md
├── PROGRESS.md
├── data/
│   ├── raw/challenge/       # immutable challenge-supplied files
│   ├── external/weather/   # external data snapshots; normally git-ignored
│   └── processed/          # generated/intermediate data; git-ignored
├── docs/                   # specs, audit, architecture, policies
├── configs/                # versioned model/validation configuration
├── src/mumbai_pm25/        # reusable package code
├── scripts/                # command-line entry points
├── tests/                  # unit, integration and leakage tests
├── notebooks/reference/    # supplied starter notebook; exploration only
├── experiments/            # experiment log and immutable experiment configs
├── reports/                # generated analysis reports
├── artifacts/submissions/  # generated CSVs; do not commit by default
└── prompts/                # agent prompts and task templates
```

The bootstrap pack does not duplicate your six challenge data files. Put them in `data/raw/challenge/` using the official names, or update a single path configuration if the repository already uses another layout. Avoid keeping duplicate copies.

## Initial strategy

Build and retain a strong, simple station-history baseline first. Use a station-specific recent hourly/diurnal profile as the reference model. Compare recent mean/median/EWM and a small LightGBM ratio model using the same chronological rolling-origin folds. Consider a blend only if it improves full-target RMSE consistently.

Weather forecasts are the highest-priority external-data experiment, but only after licensing/competition permission is confirmed and historical forecasts are reconstructed from forecast runs that would have been available at each pseudo-issue time. Add previous-year same-hour features as a controlled experiment. Do not begin with deep learning, broad static GIS layers, or blind data merging.

## Current source-of-truth policy

- Raw challenge files are immutable. Do not edit them in place.
- `DataDictionary.txt` and official organiser announcements govern timestamp and evaluation interpretation, but contradictions must remain explicitly logged until resolved.
- `available_at` is not a verified publication timestamp. Do not use it as a precise historical availability clock.
- No feature may use data that would not have been available at its simulated prediction time.
- The full target RMSE is the primary model-selection metric. A filtered clean-range RMSE is diagnostic only.
- A model is not accepted based on public leaderboard improvement alone.

## Quick links

- [Official Zindi competition](https://zindi.world/competitions/google-mumbai-data-challenge)
- [Official challenge data page](https://zindi.world/competitions/google-mumbai-data-challenge/data)
- [ClimateVerse challenge catalogue](https://india.climateverse.net/dataverse/google-air-quality-forecasting-challenge)
- [Open-Meteo Single Runs API](https://open-meteo.com/en/docs/single-runs-api)
- [Open-Meteo Historical Forecast API](https://open-meteo.com/en/docs/historical-forecast-api)

## Important

This repository is a reproducible forecasting project, not a leaderboard-hacking or target-recovery project. Do not seek or use hidden test labels, post-deadline observations, leaked submissions, private participant code, or unauthorised data.

## Preserved initial research assets

- `reports/initial_research/CLAUDE_INITIAL_PLAN_2026-11-06.md` preserves the initial plan as received (historical evidence, not policy).
- `scripts/legacy_validation/` preserves the portable validation scripts. They require review/reproduction before being used as authoritative.
- `scripts/fetch_single_run_weather.py` is a weather-vintage fetch prototype. It has not been validated against live API data in this bootstrap; check terms and run a smoke test before relying on it.

## Workstreams

### PM2.5 forecasting (ML)

The main workstream evaluates leakage-safe station forecasts for the Zindi RMSE task. Model code and validation belong under `src/mumbai_pm25/`, experiments under `experiments/` and `reports/experiments/`, and immutable challenge inputs under `data/raw/challenge/`. Start with `docs/FORECASTING_ARCHITECTURE.md` and `docs/VALIDATION_PROTOCOL.md`.

The initial reproducible baseline pipeline, rolling validation and audit commands are described in [`reports/ml_pipeline/PIPELINE_RESEARCH_AND_PLAN.md`](reports/ml_pipeline/PIPELINE_RESEARCH_AND_PLAN.md). It currently retains a station-specific 72-hour median as a simple inference control; this is not a claimed winning model.

### AirWindow Mumbai (creative product)

AirWindow Mumbai 2.1 is a separate React/Vite/TypeScript planning product for school sports coordinators and outdoor-event organisers. It compares an existing booking with feasible one-, two- or three-hour windows at four genuine Mumbai monitoring stations, then exposes forecast limits and reasons to abstain. Historical replay separates aggregate retrospective evidence from each case's later observations, which remain hidden until revealed. The event brief is printable. The verified static application is deployed at <https://airwindow-99085.web.app/>. See [`apps/airwindow/README.md`](apps/airwindow/README.md), [`reports/creative_submission/PRODUCT_OVERVIEW.md`](reports/creative_submission/PRODUCT_OVERVIEW.md), the product and safety docs below, and [`docs/CREATIVE_TRACK_REPO_PLAN.md`](docs/CREATIVE_TRACK_REPO_PLAN.md).

AirWindow consumes a validated, versioned P_fix forecast artifact and a separate replay artifact generated from TASK008 OOF predictions. The browser does not train or change the model. It shows the four actual stations, ranks complete contiguous one-, two- or three-hour windows, and retains the original schedule and honest missing-data/freshness information. Decision reliability remains uncalibrated: no robust recommendations, calibrated probabilities or prediction intervals are shown.

The OpenAQ research branch adds an **External Observation Research** page using derived static coverage and provenance summaries. It does not add operational stations or make the frozen forecast live. See the [Milestone 2 research report](reports/creative_submission/milestone_2/MILESTONE_2_RESEARCH.md) and [refresh runbook](reports/creative_submission/milestone_2/REFRESH_RUNBOOK.md). The [historical decision replay notebook](https://colab.research.google.com/github/acchasujal/aqi/blob/main/apps/airwindow/notebooks/Decision_Replay.ipynb) is Colab-compatible and has been executed locally; hosted Colab execution is unverified.

Read:

- `docs/PRIZE_STRATEGY_AND_ELIGIBILITY.md`
- `docs/REAL_WORLD_AIR_QUALITY_BENCHMARKS.md`
- `docs/CREATIVE_PRODUCT_SPEC_AIRWINDOW.md`
- `docs/CREATIVE_JUDGING_AND_DEMO.md`
- `docs/CREATIVE_DATA_AND_GOOGLE_TOOL_POLICY.md`
- `docs/CLAIMS_AND_USER_SAFETY.md`
- `docs/FORECAST_ARTIFACT_CONTRACT.md`
- `prompts/CREATIVE_STRATEGY_AGENT_PROMPT.md`

The creative app remains isolated from ML training and inference. Its versioned forecast schema 1.1 supports exact fractional issue leads while retaining 1.0 compatibility. The frozen TASK011 P_fix artifact was issued 10 November 2026 at 15:47:52 IST, uses PM history through 09:00 IST that day, and is valid through 21 November 00:00 IST. The replay contains 1,848 predeclared retrospective cases across 77 matched forecast origins; missing outcomes are counted, and these simulations are not archived real-time forecasts. Firebase Hosting serves the static public application. A Colab-compatible decision replay notebook was executed locally; a hosted Colab session is not claimed. See [`apps/airwindow/README.md`](apps/airwindow/README.md) and [`reports/creative_submission/PRODUCT_OVERVIEW.md`](reports/creative_submission/PRODUCT_OVERVIEW.md) for run/reproduction steps, evidence and limits. The four monitors are measurement proxies and may not represent an event venue.
