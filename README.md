# Mumbai PM2.5 Forecasting — Zindi Google Mumbai Data Challenge

Research and modelling repository for hourly PM2.5 forecasting at four Mumbai CPCB CAAQMS stations.

> **Project status (baseline planning):** data audit completed from the initial challenge release; history-only baselines and an initial LightGBM comparison reported; weather-vintage experiment, complete raw-target model selection, final rule interpretation and final training refresh remain open. Do not treat the proposed blend as a proven final winner.

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
