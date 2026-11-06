# Experiment Tracking and Model Registry

A single aggregate metric is not enough. Maintain row-level OOF predictions and fold-level scores for all candidate models.

## Naming

- Experiment: `EXP-YYYYMMDD-NNN`
- Fold: `FOLD-<regime>-<cutoff>-G<gap>`
- Model: `M0_LAST`, `M1_RECENT`, `M2_DIUR7`, `M3_LGB_RATIO`, `M4_WEATHER`, `M5_BLEND`

## Metrics schema

`experiment_id, model_id, fold_id, pm_gap_hours, weather_lead_min, weather_lead_max, n_total, n_station_borivali, n_station_malad, n_station_byculla, n_station_shivaji, rmse_full, rmse_lt500, mae_full, bias_full, runtime_seconds, git_sha, config_path, data_hashes, status, notes`

## Current model registry (provisional)

| Model ID | Description | Status |
|---|---|---|
| M0_LAST | Last eligible PM observation | Baseline to reproduce |
| M1_RECENT | Recent mean/median/EWM | Baseline to reproduce |
| M2_DIUR7 | 7-day station-specific diurnal profile | Strong baseline candidate from Claude run |
| M3_LGB_RATIO_DOY | LightGBM ratio-to-recent-level with day-of-year | Provisional candidate; full-target reproduction required |
| M4_WEATHER | Forecast-vintage weather-enhanced model | Not yet tested |
| M5_YEAR_LAG | Previous-year same-hour/local aggregate | Not yet tested |
| M6_BLEND | Simple blend selected from OOF | Not frozen; weight must be validated |

## Experiment log

See `experiments/EXPERIMENT_LOG.csv`. Keep the log append-only and create immutable per-experiment directories under `reports/experiments/`.
