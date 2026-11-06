# Feature Catalogue and Prediction-Time Eligibility

Feature ideas are hypotheses until they pass validation. Every generated feature must have a name, definition, units, source, timestamp semantics, earliest availability and test result.

| Family | Feature examples | Availability rule | Status |
|---|---|---|---|
| Station | canonical station category | Known from target metadata | Allowed |
| Calendar | hour, weekday, month, day-of-year, cyclic encodings | Known at target time | Candidate |
| PM recent level | 24/72/168/336-hour mean/median/EWM | Only labels before PM cutoff | Priority |
| PM diurnal profile | same hour over last 7 days | Only labels before PM cutoff; minimum sample count | Priority baseline |
| PM lag | 1/3/6/12/24/48/72/168 elapsed hours | Only if each value existed before cutoff; no row-offset shortcut | Candidate |
| PM variability | rolling std/IQR/min/max, trend/slope | Past-only window; missingness explicit | Candidate |
| Cross-station | region mean, station difference, distance weight | Only readings available by PM cutoff; never future test values | Conditional |
| Previous year | same-hour prior-year value, local robust mean, missing flag | Prior year only; robustly shrink unusual values | Experiment |
| Weather forecast | temperature, humidity, dew point, wind, precipitation, PBL | Archived forecast run published by weather issue time | Conditional on permission |
| Reanalysis/weather observations | ERA5 or measured historical weather | Not a forward predictor unless exact release timing supports it | Not default |
| Static geography | coordinates, land cover, buildings, roads | Static; may be collinear with station ID; test only if meaningful | Low priority |
| Administrative metadata | `ID`, `scoring_block`, `count`, `available_at`, flags, `series_id` | Not valid prediction signals under current understanding | Forbidden by default |

## Derived variables

Wind components (meteorological convention must be checked against source definition):
- `u = -wind_speed * sin(direction_radians)`
- `v = -wind_speed * cos(direction_radians)`

Do not assume direction convention without verifying source units and conventions.

Precipitation features should distinguish instantaneous values from hourly accumulations. For cumulative/rolling features, use only preceding valid forecast hours.

## Feature registry requirement

Maintain `configs/feature_registry.csv` with columns:
`feature_name, family, source, definition, units, timestamp_key, availability_rule, missing_rule, status, experiment_id, notes`.
