# EXP-20261107-006 — Calendar ExtraTrees candidate

## Design

This secondary experiment fits an ExtraTrees regressor to unchanged historical PM2.5 labels using only station one-hot and cyclic hour, weekday, and day-of-year features. For every fold, labels whose interval end is after the fold's PM-history cutoff are excluded from model fitting. We compare it to the same nine baseline models, on identical eligible targets, using 48-hour target windows spaced 28 days apart. There are 22 non-overlapping folds per PM-history gap. No test or private labels were used.

Configuration is in `../experiment_extra_trees.yaml`. Row-level OOF predictions, metrics by model/fold/station/horizon, and fold-level rows are stored in this directory.

## Results

| Nominal PM gap (h) | ExtraTrees RMSE | Best history baseline | Baseline RMSE | ExtraTrees clean-range RMSE | ExtraTrees fold RMSE SD |
|---:|---:|---|---:|---:|---:|
| 48 | 44.98 | EWM 72h | 18.19 | 44.59 | 35.32 |
| 72 | 84.34 | EWM 72h | 20.96 | 83.69 | 67.04 |
| 96 | 4467.34 | Last value | 4451.58 | 237.99 | 4,876.72 |
| 120 | 4547.22 | Last value | 4529.99 | 239.41 | 5,088.05 |

The candidate is worse on full-target RMSE at every gap, with much worse clean-range performance. The extreme values still account for all squared error at the 96- and 120-hour gaps. The calendar-only model adds little useful signal and is rejected for inference. It remains in the experiment code so the comparison can be reproduced; the production submission command exposes only the retained median72 baseline.

This result does not rule out a model combining station-specific recent PM history with supervised residual prediction. The simple calendar-only ExtraTrees test did not establish value for that more complex hypothesis.
