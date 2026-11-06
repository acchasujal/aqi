# EXP-20261107-007 — 2024 Seasonal History Evaluation

## Experiment Design

**Hypothesis**: 2024 same-station same-hour-of-year PM2.5 climatology from
AdditionalHistory.zip provides a useful seasonal prior for November 2025–2026 targets,
particularly when recent PM history is stale (gap ≥ 72h).

**Archive acceptance gate**:
- `History_Mumbai_2024.csv.gz` filtered to `source == 'cpcb_caaqm'` only.
- Station identity by name fragment matching only (not sensor ID cross-reference).
- PM2.5 values are pre-capped at 1000 µg/m³ in the archive (documented limitation).
- HistoryNotes.txt warns averaging intervals are not fully aligned; cpcb_caaqm
  timestamps at minute=0 treated as hour-start (same as competition target_start).

**New candidate models**:
- `hist24_same_hour`: same station, same hour-of-day, ±14 calendar days in 2024.
- `hist24_month_hour`: same station, same month + hour-of-day in 2024.
- `hist24_blend50_median72`: 50:50 blend of median72 and hist24_same_hour.

**Controls**: `median72`, `last`, `mean72_exclude_gt1000` (from EXP-20261106-005).

**Primary metric**: Full-target RMSE on all labelled validation rows.

## Results

### Gap 48h

| Model | Full-target RMSE | MAE | Bias | Clean RMSE (<500) | Rows |
|---|---:|---:|---:|---:|---:|
| hist24_blend50_median72 | 43.12 | 12.86 | -1.51 | 20.94 | 13528 |
| mean72_exclude_gt1000 | 43.61 | 14.07 | -0.54 | 22.95 | 13528 |
| hist24_same_hour | 43.68 | 14.57 | -0.48 | 21.52 | 13308 |
| mean72_clip300 | 43.74 | 13.91 | -0.82 | 22.68 | 13528 |
| median72 | 43.98 | 13.79 | -2.42 | 22.66 | 13528 |
| hist24_month_hour | 44.00 | 15.05 | -0.27 | 22.71 | 13528 |
| last | 49.73 | 17.23 | 3.24 | 32.57 | 13528 |
| hour_week4 | 50.31 | 16.10 | 0.24 | 32.85 | 13528 |
| diurnal7 | 153.82 | 16.42 | 2.31 | 149.44 | 13528 |
| ewm72 | 177.32 | 18.73 | 4.07 | 173.47 | 13528 |
| mean72 | 177.59 | 20.89 | 6.30 | 173.75 | 13528 |
| year_ago | 220.57 | 18.36 | 1.90 | 217.42 | 13528 |

### Gap 72h

| Model | Full-target RMSE | MAE | Bias | Clean RMSE (<500) | Rows |
|---|---:|---:|---:|---:|---:|
| hist24_blend50_median72 | 490.90 | 18.48 | -7.55 | 20.39 | 13060 |
| mean72_clip300 | 490.96 | 19.70 | -6.63 | 22.48 | 13060 |
| mean72_exclude_gt1000 | 490.96 | 19.88 | -6.33 | 22.90 | 13060 |
| median72 | 490.97 | 19.50 | -8.29 | 22.23 | 13060 |
| hist24_month_hour | 490.99 | 20.69 | -6.69 | 22.19 | 13060 |
| last | 491.59 | 23.31 | -2.58 | 33.34 | 13060 |
| year_ago | 492.49 | 21.84 | -6.11 | 44.63 | 13060 |
| hist24_same_hour | 494.29 | 20.23 | -6.80 | 20.83 | 12883 |
| hour_week4 | 556.42 | 26.92 | -0.61 | 262.93 | 13060 |
| mean72 | 600.36 | 38.48 | 12.30 | 346.45 | 13060 |
| ewm72 | 609.98 | 37.00 | 10.71 | 362.86 | 13060 |
| diurnal7 | 658.84 | 29.35 | 3.50 | 440.17 | 13060 |

### Gap 96h

| Model | Full-target RMSE | MAE | Bias | Clean RMSE (<500) | Rows |
|---|---:|---:|---:|---:|---:|
| last | 2343.94 | 53.49 | -31.73 | 33.86 | 13177 |
| mean72_exclude_gt1000 | 2348.24 | 50.06 | -35.61 | 23.60 | 13177 |
| mean72_clip300 | 2348.44 | 49.87 | -35.92 | 23.21 | 13177 |
| median72 | 2348.57 | 49.64 | -37.59 | 22.74 | 13177 |
| hist24_blend50_median72 | 2348.74 | 48.54 | -36.80 | 21.00 | 13177 |
| hist24_month_hour | 2349.02 | 50.63 | -35.85 | 22.83 | 13177 |
| hist24_same_hour | 2372.81 | 50.76 | -36.63 | 21.92 | 12913 |
| mean72 | 2389.22 | 78.57 | -7.07 | 441.54 | 13177 |
| ewm72 | 2393.54 | 77.57 | -8.25 | 464.87 | 13177 |
| year_ago | 2398.76 | 57.23 | -29.97 | 488.99 | 13177 |
| diurnal7 | 2424.91 | 66.80 | -18.59 | 602.11 | 13177 |
| hour_week4 | 2709.44 | 86.06 | -0.74 | 1351.31 | 13177 |

### Gap 120h

| Model | Full-target RMSE | MAE | Bias | Clean RMSE (<500) | Rows |
|---|---:|---:|---:|---:|---:|
| last | 2325.63 | 52.94 | -31.22 | 31.14 | 13395 |
| mean72_exclude_gt1000 | 2330.86 | 50.32 | -35.05 | 22.91 | 13395 |
| mean72_clip300 | 2331.11 | 50.12 | -35.36 | 22.54 | 13395 |
| median72 | 2331.27 | 49.90 | -37.06 | 21.93 | 13395 |
| hist24_blend50_median72 | 2331.45 | 48.67 | -36.04 | 20.29 | 13395 |
| hist24_month_hour | 2331.75 | 50.36 | -34.95 | 21.85 | 13395 |
| hist24_same_hour | 2366.09 | 51.23 | -36.07 | 21.91 | 13008 |
| mean72 | 2369.77 | 77.23 | -8.10 | 428.59 | 13395 |
| ewm72 | 2373.80 | 75.98 | -9.36 | 450.99 | 13395 |
| year_ago | 2380.80 | 57.16 | -29.67 | 484.00 | 13395 |
| diurnal7 | 2406.57 | 66.58 | -18.56 | 596.24 | 13395 |
| hour_week4 | 2687.95 | 85.95 | -0.32 | 1338.34 | 13395 |

## Archive Acceptance Decisions

| Archive Member | Decision | Reason |
|---|---|---|
| History_Mumbai_2024.csv.gz | CONDITIONAL PASS (cpcb_caaqm rows only) | Four target station names present; timestamps at :00 for cpcb_caaqm; values capped at 1000 (documented); interval semantics unverified by organiser |
| History_Mumbai_2018_2020.csv.gz | REJECTED | Only Borivali East present; 2018-2020 data too old for 2026 seasonal prior |
| Legacy_Observations_2020_2022.csv.gz | REJECTED | Irregular sub-hourly samples; not qualified hourly labels |
| Other_Mumbai_Stations_2025_2026.csv.gz | REJECTED | Location IDs do not match competition target stations |
| XKDR_All_Stations.csv | N/A | Metadata lookup only |
| Kaggle_All_Stations.csv | N/A | Metadata lookup only |

## Limitations

- Sensor identity not verified across archives; name matching only.
- Archive PM2.5 values capped at 1000 µg/m³; competition train has values up to ~241 k.
- Averaging intervals not confirmed identical to competition semantics.
- 2024 is one prior year; seasonal patterns may not repeat exactly.
- Fold RMSE standard deviations are large; small improvements are inconclusive.
