# AirWindow forecast and decision replay contracts

The owner authorised AirWindow 2.0 implementation on 8 November 2026. The frontend consumes real, static artifacts exported from the ML pipeline; it never trains or changes the forecasting model.

## Forecast 1.1.0 and backwards compatibility

`apps/airwindow/contracts/forecast.schema.json` preserves version **1.0.0**. The new `forecast.v1.1.schema.json` uses the same fields and explicit missing-hour records, but permits exact positive numeric `forecast_horizon_hours`. An issue time such as 15:58 gives fractional elapsed hours to an hour-aligned target. Version 1.1 must not round the issue clock or truncate those horizons. The runtime validator selects the schema by version; existing 1.0 fixtures and their legacy integer horizons remain supported.

`apps/airwindow/contract_validation.py` checks schema, explicit IST, one-hour contiguous target intervals, unique ordered hours, PM/weather cutoffs before issue, generation after issue, forecast horizon, counts, freshness age and actual four-station coordinates. In 1.1 it also checks that the station's latest observation is no later than the PM cutoff. Missing predictions remain `null`; no zero filling. Prediction intervals remain null unless separately calibrated.

The exported `public/data/forecast.json` contains only target starts strictly after its actual model issue time. Earlier Test rows are excluded from the live planning surface. Its generation time is the actual export timestamp, separate from model issue and PM history cutoff. Model ID/version, source commit and training-data SHA are supplied by the ML audit. `manifest.json` additionally preserves prediction-CSV/audit hashes and exact forecasting-code fingerprints; the source commit alone does not describe uncommitted implementation at original inference time.

Current artifact: P_fix provisional, issue **8 November 2026 15:58 IST**, PM cutoff **2 November 23:00 IST**. No weather is used; provider/model/issue are null. Data freshness has no validated threshold: status is `unknown`, with measured age and an explicit note, rather than calling this old snapshot fresh. The UI must also disclose expiry when its planning horizon has passed.

## Two different lead clocks

Forecast record horizons measure target start minus **model issue**. Historical TASK008 OOF has issue equal to PM cutoff and 193–240h issue leads. The current live artifact has a later issue time while its PM information remains old. For example 11 November 00:00 has about **56.03h issue lead** and **193h PM-information lead**. Historical station RMSE at 193h is not directly matching calibration of a 56h live issue lead. The client must label these clocks and abstain from unsupported reliability claims.

The station `validation` entries preserve full-target historical P_fix RMSE, target count, origin count and fold variability by the OOF's recorded issue lead. They are historical diagnostics; matching station identity alone is not enough to assert relevant uncertainty at another issue/PM lead state.

## Separate retrospective replay 1.0.0

`apps/airwindow/contracts/replay.schema.json` and `replay_validation.py` govern `public/data/replay.json`. It contains genuine chronological fixed-origin OOF predictions and later released historical observations, exported separately from the live forecast. These OOF predictions were generated retrospectively on 8 November; the recorded historical issue times are simulated origins, not archived forecasts published in real time. PM interval end is an availability proxy because first-publication times are unknown. Previously inspected later origins are chronological confirmation, not independent calibration.

Each case records station, duration, fold/split, issue, PM cutoff, last eligible PM interval end, original/feasible/selected windows, forecast-only ranking, predicted and subsequently observed differences, hindsight gap and hourly forecasts/observations. Missing actual outcomes stay null. The validator recomputes ranking from predictions, verifies recorded outcomes, checks clocks, and rejects observations beyond the released-history cutoff. There are no current private actual targets in either public artifact.

The predeclared demonstration scenario uses original **09:00**, feasible **08:00–18:00**, durations **1/2/3h**, both days of each of the 77 matched OOF blocks, and all four stations. All 1,848 scenarios are retained. Rankings are computed before outcome availability is inspected. Missing paired outcomes reduce evaluated-outcome coverage, not the forecast candidate set. Hindsight gap is computed only when every feasible window has complete observed outcomes; otherwise it is null and counted as missing. These product scenarios are not actual user schedules or interviews.

## Scheduling and conservative decision evidence

`decision_engine.py` separates complete contiguous-window ranking, retrospective observed means and decision-state classification. It supports ROBUST IMPROVEMENT, TENTATIVE IMPROVEMENT, NO CLEAR WINNER and INSUFFICIENT EVIDENCE. This release has **no independently validated robust gate**: no probabilities or uncertainty intervals are exported.

Development-only paired difference errors are grouped by station, duration and recorded lead range. Their median absolute error is a descriptive typical-error benchmark. For later confirmation cases a numerical gain no larger than that median is NO CLEAR WINNER; a larger numerical gain can be TENTATIVE, with explicit uncalibrated wording. Fewer than two paired origins is mathematically inadequate for resampling variation and yields INSUFFICIENT EVIDENCE; two origins is not claimed to be enough for calibrated decision reliability. Development cases are not assessed using their own outcomes. Current live clock mismatch yields insufficient evidence.

Exploratory diagnostics resample all paired cases together within contiguous blocks of four ordered origins, 1,000 repetitions, seed 20261108. They preserve within-origin temporal dependence and do not bootstrap independent hours. Sampling variability is recorded in `apps/airwindow/evidence/replay_diagnostics.json`, not displayed as live confidence intervals. No claim of independent calibration, health benefit or personal exposure reduction follows from descriptive historical frequencies. Zero robust recommendations are made; the selected-alternative success fraction describes numerical retrospective choices only.

## Reproduce

```powershell
.venv\Scripts\python.exe apps/airwindow/build_artifacts.py
.venv\Scripts\python.exe -m pytest -q tests/test_airwindow_decisions.py tests/test_forecast_artifact.py -p no:cacheprovider --basetemp data/processed/airwindow-contract-tests
```

The exporter reads the audited P_fix CSV and `.rows.csv`, the TASK008 matched OOF table, and the full hourly OOF feature cache. If that ignored cache is absent, recreate it using the recorded `scripts/run_task008.py` command. Label-only OOF rows must not replace the full forecast grid, because doing so would select alternatives based on later observation availability. No source data or ML code is modified by export.

`apps/airwindow/notebooks/Decision_Replay.ipynb` is Colab-compatible and recomputes the exported replay metrics and validates all cases using committed artifacts. It does not require a live API, paid service, hidden targets or model fitting. Colab execution is prepared; no live Colab session is claimed.
