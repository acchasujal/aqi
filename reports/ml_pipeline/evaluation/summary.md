# EXP-20261106-005 — Rolling-origin baseline evaluation

## Design

All six controls were evaluated on the same eligible target rows per fold, with 48-hour target windows spaced seven days apart. PM-history cutoff and prediction origin are stored independently. Nominal PM cutoff-to-target gaps are 48, 72, 96 and 120 hours. Because observations can be missing, actual PM interval-end-to-target-start gaps ranged from 48 to 286 hours across folds/stations. Validation labels were unchanged, including extremes; no historical feature clipping or target filtering was used.

Folds: 85 at 48-hour gap, 87 at each of 72/96/120-hour gaps. The corresponding OOF CSV.gz files retain row-level predictions. Model, fold, station and horizon tables are saved beside them.

## Full-target RMSE (primary)

| PM gap (h) | Last | Mean 72h | Median 72h | EWM 72h | Diurnal 7d | Hour-of-week 4w | Mean clipped at 300 | Mean excluding >1,000 | Previous calendar year |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 48 | 49.73 | 177.59 | 43.98 | 177.32 | 153.82 | 50.31 | **43.74** | 43.61 | 220.57 |
| 72 | 491.59 | 600.36 | 490.97 | 609.98 | 658.84 | 556.42 | **490.96** | **490.96** | 492.49 |
| 96 | **2343.94** | 2389.22 | 2348.57 | 2393.54 | 2424.91 | 2709.44 | 2348.44 | 2348.24 | 2398.76 |
| 120 | **2325.63** | 2369.77 | 2331.27 | 2373.80 | 2406.57 | 2687.95 | 2331.11 | 2330.86 | 2380.80 |

The 72-hour median wins narrowly on the 48/72-hour results; last-value wins on the 96/120-hour results. Differences are small relative to fold RMSE standard deviations (about 42–2,565), so the experiment does not establish a general winner. Median 72h is retained as a simple, robust inference control; keep last-value as a permanent comparator. This is not a claim about private/test performance.

## Diagnostics and extreme contribution

For median 72h, clean-range RMSE (`y < 500`) is 22.66, 22.23, 22.74 and 21.93 across the four nominal gaps. This metric is diagnostic only. There are 2/3/6/8 validation rows above 1,000 in these respective gap sets; their share of squared error is 61%, 100%, 100% and 100%. This confirms that a handful of extreme labels drive full-target instability. The audit contains all 19 source observations above 1,000 with station and timestamp for review. No target was removed or altered.

The two historical-only mean ablations altered input history, never validation labels: cap historical feature values at 300, or omit historical readings above 1,000. Both reduced the unmodified 72-hour mean's full-target RMSE from 177.59 to about 43.6–43.7 at gap 48, and were close to median72 at the other gaps. The previous-calendar-year same-hour baseline was weak (RMSE 220.57–2,398.76), so it is not selected. These results are simple baseline sensitivities, not a supervised training-label treatment.

Station-level bias/RMSE and horizon buckets are available in `station_metrics.csv` and `horizon_metrics.csv`; `fold_metrics.csv` is the independent fold table. Check the same files before any model/ensemble decision. No LightGBM result is reported: no compatible binary wheel for the optional LightGBM range was available on the project's Windows ARM64 runtime.

## Limitations

These folds span multiple seasonal regimes. They are non-overlapping in target time, but folds share historical training data and are not independent samples. The training file is the currently audited snapshot through 2 November; the advertised later refresh must be audited and the full evaluation rerun. No weather vintages or prior-year features were fit. No test or private score can be computed.
