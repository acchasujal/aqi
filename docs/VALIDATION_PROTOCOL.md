# Validation Protocol — Leakage-Safe Rolling Origin

## Purpose

Estimate final private-period error under the same information conditions as the actual submission. Public leaderboard scores are secondary diagnostics.

## Fold schema

Each fold must record:
- `fold_id`
- `pm_history_cutoff_ist`
- `weather_issue_time_ist`
- `target_start_ist`
- `target_end_ist`
- `pm_gap_hours` (elapsed time from last eligible PM hour to target start, not a guessed median)
- selected weather `model`, `run_utc`, and `run_available_at_ist`
- train-label end cutoff
- target row count overall and per station

Keep PM data cutoff separate from weather forecast issue time.

## Recommended folds

Use 48-hour target windows and history gaps of 48, 72 and 96 hours initially. Add 120-hour stress testing if time permits. Historical folds should cover multiple regimes (summer, monsoon/decline, autumn/post-monsoon) but weight the most recent comparable regime more heavily only with an explicit rationale.

Avoid overlapping target windows for primary model selection where possible. If overlapping folds are used for diagnostics, report the overlap and do not treat every fold as independent. Prefer 7-day or longer spacing for the core comparison, with a smaller recent focused set for the final seasonal regime.

## Training data availability

For a pseudo-submission origin:
- Only training labels ending before `pm_history_cutoff_ist` may be used as PM-history inputs.
- Model fitting may use historical labelled examples whose labels would have been available under the chosen simulation design. Because `available_at` is not a verified first-publication time, state the proxy assumption; use explicit conservative gaps and sensitivity tests.
- Do not leak validation target labels into historical feature aggregates.

## Weather availability

- Choose the latest archived model run whose actual/assumed publication time is no later than `weather_issue_time_ist`.
- Record a conservative availability delay (Open-Meteo documentation says global model runs commonly become available 4–6 hours after initialisation; see source registry).
- Use the complete forecast from that run for target times.
- Do not use a forecast run initialised after issue time.
- Do not use reanalysis or observed weather values as if known at forecast issue time.
- Test forecast lead and alignment explicitly.

## Metrics

Primary:
- Full-target RMSE on every labelled row in the validation target window.

Diagnostics:
- Clean-range RMSE, e.g. `target < 500` (never primary).
- MAE, bias and median absolute error.
- RMSE by station.
- RMSE by horizon bucket.
- RMSE by PM2.5 regime/quantile.
- Number of evaluation rows and extreme values.

Validation labels must remain unmodified. If any rows are excluded due to a verified source-quality defect, document the rule independently of model performance and report both excluded and full results.

## Comparison rules

- Same fold IDs and eligible target rows for every candidate being compared.
- Store row-level out-of-fold predictions, not just aggregate scores.
- Tune blend weights using training/OOF predictions only; do not use final private labels.
- Report mean, median and spread across folds; identify dependence from overlapping windows.
- Treat <1 RMSE differences as inconclusive when fold standard deviation is 6–8 or similarly large.
- Do not select a model solely on public leaderboard results.

## Required tests

- Lag feature value equals the expected prior elapsed hour after reindexing.
- No future timestamp enters a feature.
- Weather run available time <= issue time.
- Train end timestamp maps to target interval start correctly.
- Test target start matches weather valid-time key.
- Missing hours remain missing (not zero-filled).
- Validation fold target rows do not overlap unexpectedly.
