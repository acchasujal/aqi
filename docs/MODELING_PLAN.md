# Initial Modelling Plan and Model Decisions

## Current evidence

Claude's reported initial experiments (see `PLAN_Zindi_Mumbai_PM25.md` and validation archive supplied in chat) indicate:
- A station-specific recent diurnal profile / recent average is strong.
- A basic calendar-only Random Forest is weak in a recent distribution-shift period.
- A compact LightGBM ratio-to-7-day-level model with day-of-year can help in some regimes.
- A 50:50 blend of that model and a 7-day diurnal profile performed well in the reported six regime/gap cells.
- The evidence is not final because clean-range RMSE (`y < 500`) was used in important comparisons, several architectures were not tested, the code was not fully reproduced by a separate environment, and weather is untested.

## Models to implement in order

### Baselines

1. Last available observation per station.
2. Recent station mean over 24/72/168/336 elapsed hours.
3. Recent station median over the same windows.
4. Exponentially weighted recent mean with tested half-lives.
5. Station-specific 7-day hour-of-day profile (M2).
6. Station-specific 7-day hour-of-week profile.
7. Robust trend-adjusted recent profile, only if it beats M2 across folds.

All baselines must respect missing timestamps and the PM history cutoff.

### Supervised candidate

LightGBM is the first supervised candidate, not because it is guaranteed best but because previous experiments indicate modest value and it is suitable for tabular, engineered features.

Candidate target:
- Predict residual/ratio relative to a stable recent station level.
- Avoid division by zero or tiny denominator using explicit floor and validity checks.
- If using `log(y / level)`, clip/floor only the denominator, not the validation labels. Convert predictions back carefully and test smearing/calibration on out-of-fold data.
- Compare raw target and transformed target; retain the one that improves full-target RMSE across folds.

Initial feature families:
- Station categorical feature.
- Hour/day/week/month and cyclical encodings.
- PM history level/trend/variability features.
- `doy` only as a tested seasonal hint.
- Previous-year same-hour/local aggregate features as a separate ablation.
- Weather forecast-vintage features only after permission and correct backtesting.

### Candidate alternatives

Only after baseline + LightGBM tests are reproducible:
- ExtraTrees for nonlinear, lower-tuning diversity.
- XGBoost if Windows ARM64 environment permits a supported build or Colab is justified.
- CatBoost only if installation and validation effort are worth it.

Do not run an architecture bake-off without an explicit hypothesis. No TFT/LSTM/Transformer in the first implementation.

## Outlier treatment

Run separate training policies:
- All labels unchanged.
- Exclude only values above a high diagnostic threshold (e.g. 1,000) from model fitting.
- Robust loss / target transforms.
- Clip only historical *features* to a documented cap while retaining labels.

All validation labels remain unmodified. The full-target RMSE is primary. A model that improves clean-range RMSE while degrading full-target RMSE is not automatically better.

## Model acceptance gate

A candidate is kept only if:
1. It beats or complements the baseline on multiple non-overlapping/reasonably independent folds.
2. It does not rely on unavailable future inputs.
3. Its full-target RMSE and station-wise behaviour are acceptable.
4. Its improvement is larger than plausible fold noise, or it adds useful robustness/diversity.
5. It is reproducible from a saved config and deterministic seed.

## Provisional final model

Fallback: best validated station-specific recent profile/level baseline.

Candidate: LightGBM ratio-to-level with seasonal hint.

Candidate blend: profile + LightGBM; test weights using out-of-fold predictions. Do not hardcode 0.5 before final revalidation.

Weather model: optional upgrade, only if it improves both expected final-gap folds and at least two distinct pollution regimes.
