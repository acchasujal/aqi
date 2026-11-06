# Mumbai PM2.5 ML Pipeline — Research and Execution Plan

**Task:** TASK 003 — 2026-11-06
**Base:** `origin/main` at `bfc3a7a5f4ea799bf766676b7f9517613aadce93`
**Status:** **APPROVED FOR EXECUTION** (history-only baseline pipeline; external weather excluded pending permission)

## Data findings and defects

The challenge snapshot contains 47,849 training observations (10 fields), 2,592 test rows, four station metadata rows, and an ordered sample submission. The audited training release has `timestamp_ist` at interval end, while test has explicit interval starts and ends. Training labels are aligned by subtracting one hour. `mean` duplicates `pm25`; `count`, `available_at`, `series_id`, flags, `ID`, and `scoring_block` are excluded from predictors. All station data are converted to Asia/Kolkata-aware timestamps, station/sensor mapping is validated, and absent hours remain null on a complete per-station hourly grid.

`available_at` is not verified first-publication time, so validation uses explicit conservative PM-history cutoffs and does not use it as a release clock. The existing legacy baseline filters labels above 1,000 for history and clips history at 300; this is an unaccepted ablation and its figures are context only. Audited source fingerprints and recomputed coverage/extreme statistics are in `reports/ml_pipeline/audit/`.

## Information set and unresolved assumptions

- PM label availability is conservatively proxied by interval end (`target_start + 1 hour`) and is eligible only when that time is no later than issue time.
- Validation keeps `prediction_origin`, `pm_history_cutoff`, target start/end, and horizon distinct. The PM cutoff to target start gap is 48/72/96/120 hours.
- Primary folds use 48-hour target windows spaced seven days apart. Gaps are omitted between history and target; only timestamps at or before PM cutoff enter history features.
- Test scoring allocation is never used by prediction code. Test labels are inaccessible; no test score is claimed.
- The full 2,592-row test grid includes dates before the latest currently released training observation as well as later dates. The final information set and intended final issue time may change with the advertised November 10 Train refresh. Rerun audit, validation, and inference after that update. The supplied test output is a current snapshot control, not a claim about the eventual competition score.
- Whether all 192 private rows and the dynamic public-window dates are exact is unresolved in competition documents; no assumptions about these administrative blocks are encoded.

## Research findings

1. The 2020 AirQo Ugandan Air Quality Forecast Challenge winner publicly linked a code repository. It is a useful implementation reference, but its 25-hour Kampala task, observation density, and forecast setup do not transfer directly to four sparse Mumbai stations and long missing-hour gaps. The repository is documented in the source list below.
2. Bai et al. (2020) evaluate hourly PM gap filling with a diurnal-cycle constrained approach and note weaker performance where neighboring information is sparse. This supports treating station-specific temporal profiles as a baseline and cross-station features as an ablation, not assuming spatial pooling will transfer.
3. The competition's extreme labels make original-label full-target RMSE the selection objective. Robust losses/transformations and independently suspicious training-label treatments belong in separate matched experiments; validation targets remain untouched.
4. Individual forecast-vintage weather could be more defensible than stitched history, but the source's free API is non-commercial and current competition/rights terms remain unresolved. Weather is therefore disabled. Open-Meteo documents that model run initialization precedes distribution by several hours and that availability is model-specific.
5. Four stations and roughly 21 months of sparse labels do not justify deep learning or a broad model zoo. A well-defined station profile plus recent level is the reproducible control. LightGBM ratio models may be considered only after compatible installation and evidence from identical full-target folds.
6. The starter notebook uses a 90-day history, three-day reporting gap, two-day holdout, and station one-hot plus calendar features in a Random Forest. Its submission checks are useful; its single latest-period split and lack of recent PM features do not replace the rolling validation implemented here.
7. The previous-calendar-year same-hour baseline was weak on these folds. Historical feature clipping at 300 and excluding >1,000 readings were matched ablations: they greatly improved the plain 72-hour mean at the 48-hour gap, but did not produce a clear final full-target winner across longer gaps. These ablations never alter validation labels.
8. A deterministic calendar-only ExtraTrees model was evaluated on a secondary 28-day-spaced matched fold set. It was worse than the history controls at every PM gap and had much higher clean-range error; it is retained as a reproducible experiment, not offered as a submission model.

## Candidate ranking

| Rank | Candidate | Expected benefit | Feasibility | Leakage risk | Decision |
|---:|---|---|---|---|---|
| 1 | Station last / recent mean, median, EWM | Strong low-cost control; adapts level | High | Low with explicit cutoff | Implement and retain |
| 2 | Station 7-day hourly and 4-week hour-of-week profiles | Captures diurnal/week structure | High | Low with past-only grid | Implement and compare |
| 3 | Trend-adjusted seasonal profile | Could adapt a changing level | Medium | Medium | Defer until baseline evidence |
| 4 | ExtraTrees calendar + station one-hot | Checks whether seasonal structure adds value beyond persistence | High; scikit-learn ARM64 wheel verified | Low | Tested on 22 matched folds/gap; rejected as weaker than controls |
| 5 | Pooled LightGBM ratio-to-level | Possible nonlinear residual gains | No Windows ARM64 wheel for configured range | Medium | Deferred; no score claim |
| 6 | CatBoost/XGBoost, cross-station features | Possible nonlinear/spatial gains | Not tested; low evidence for four sparse stations | Medium/high | Defer pending a specific hypothesis |
| 7 | Archived weather vintages | Potentially valuable with stale PM | Low pending API/organiser approval | High if issue metadata wrong | Excluded pending permission |

## Architecture and model ladder

Package modules separate schema/time ingestion, complete hourly grids, past-only history, baseline validation, an optional calendar-only ExtraTrees experiment, submission checks, and CLI orchestration. Current inference uses the station-specific median from the 72 elapsed hours before issue time, falling back to all eligible station history if no value exists in that window. It is a simple control, not a proven winner, and carries a manifest with source hashes, issue time, and weather disabled. The ExtraTrees candidate is retained only for matched validation; `train_predict.py` emits the baseline control. Baseline and ExtraTrees predictions use unchanged validation labels. Nonnegative output is enforced.

## Extreme targets

All validation labels and primary scoring rows remain unchanged. Audit quantiles, counts above 100/300/500/1,000, station/time context, and squared-error contribution. Later controlled experiments may compare original-label fitting with robust loss, target transformations, and independently flagged training-only suspicious samples. Any such fit policy must be logged and compared on identical folds. Historical feature clipping is an explicit ablation only.

## Validation and ensemble

`rolling_oof` builds a complete hourly station timeline before calculating history; target windows are 48 hours and spaced at least seven days, so primary target windows do not overlap. Separate PM-history gaps are 48, 72, 96, and 120 hours. Record complete clocks and report full-target RMSE, clean-range diagnostic RMSE, MAE, bias, fold median/SD, station metrics, horizon metrics and row counts. Store compressed row-level OOF results. A model can be retained only after reproducible full-target benefit over matched folds; no blend is selected until OOF evidence exists. There is no private-label or test-score evaluation.

## Environment, compliance, and implementation sequence

The validated runtime is Python 3.12.10 ARM64 with NumPy 2.5.4, pandas 3.1.1 and scikit-learn 1.9.1; pandas below 3 had no usable wheel in the established environment. The scikit-learn ARM64 wheel is verified. No binary LightGBM wheel exists for the configured range on this runtime, so LightGBM remains a separate optional extra. No paid services, new datasets, or weather calls are used.

1. Recompute data audit and immutable input hashes.
2. Add deterministic package and schema/time/history tests.
3. Evaluate the baseline ladder on all configured gaps and export OOF rows/metrics.
4. Compare a single supervised candidate on a secondary matched, non-overlapping fold set; retain it only if supported by full-target results.
5. Generate and validate an exact-order submission with source manifest.
6. Review raw hashes, leakage surfaces, environment, tests/lint, diff, and final inference command.
7. Commit to `feature/ml-pipeline-v1`, create a focused PR, then merge only after all checks pass.
8. When the advertised final Train refresh arrives, rerun all outputs against that source fingerprint before final competition use.

Reproducible commands from the repository root (after installing `pip install -e '.[dev]'`):

```powershell
.venv\Scripts\python.exe scripts\audit_data.py
.venv\Scripts\python.exe scripts\validate_baselines.py
.venv\Scripts\python.exe scripts\validate_extra_trees.py
.venv\Scripts\python.exe scripts\train_predict.py --issue-time 2026-11-06T12:00:00+05:30
```

Pass the actual final issue time explicitly on the final Train release. The checked-in prediction code never reads scoring allocation fields.

## Acceptance criteria

- No raw input changes; audit fingerprints match original inputs.
- Test/sample submission IDs match exactly; generated output is ordered, finite, non-negative, complete.
- Feature cutoffs use interval-end availability and strictly past history; no prohibited metadata predictors.
- Baselines compare on identical non-overlapping chronological windows for all configured PM gaps and report full-target RMSE plus diagnostics.
- Tests, lint, audit, and end-to-end submission command pass on supported Windows ARM64 runtime.
- Config, OOF metrics/artifacts, manifest, experiment log, progress, and decision record are updated.
- No unverified score claim, unauthorized weather source, test/private target, or generated large model is committed.

## Risks

Rare extremes dominate RMSE and may not repeat; folds can have high variance and sparse station-hour availability. The model is intentionally simple pending evidence. The final Train refresh, late data-publication delay, test/scoring interpretation, dependency wheel availability on clean systems, and any external-data approval remain potential blockers. The historic AirQo winner is a different task, not validation of our model choice.

## Sources

- Official 2020 AirQo winner discussion linking the team's public repo: https://zindi.world/competitions/airqo-ugandan-air-quality-forecast-challenge/discussions/1708
- Winner's public code repository (MIT): https://github.com/mnm-rnd/competitions
- AirQo competition task description (five Kampala sites, 25-hour horizon, previous five days): https://airqo.net/partners/zindi
- Bai et al. (2020), *Atmospheric Measurement Techniques*, 13, 1213–1226: https://amt.copernicus.org/articles/13/1213/2020/index.html
- Open-Meteo Single Runs API (run/archive semantics and typical 4–6 hour global delay): https://open-meteo.com/en/docs/single-runs-api
- Open-Meteo terms (free API non-commercial limit and CC BY 4.0 data terms): https://open-meteo.com/en/terms
- LightGBM official installation guide: https://lightgbm.readthedocs.io/en/stable/Installation-Guide.html
- Challenge validation and external-data policies: `docs/VALIDATION_PROTOCOL.md`, `docs/EXTERNAL_DATA_POLICY.md`.
