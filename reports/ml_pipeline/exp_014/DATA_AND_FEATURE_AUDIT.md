# EXP-014 data and feature audit

Audited the current local official release without editing `data/raw/challenge/`. Train has **47,849 rows × 10 fields**, Test **2,592 × 7**, four stations (11606, 11611, 3409510, 3409511). Train `timestamp_ist` spans 2025-02-19 03:00 through 2026-11-02 23:00 IST; it marks the interval **end**. Test `target_start_ist` marks interval start. Latest eligible PM interval end is 2026-11-02 23:00 IST at all stations. The local dictionary describes public November 3–4 (1–48h leads) and private November 11–12 (193–240h leads). The public webpage's date text conflicts with the dictionary; see EXP-013. Train SHA-256: `fcee20ebf7bd9c4a4e2487bab0a4f81339d6c820a53862b14443031db1f18ad6`; archive SHA-256: `3233061ca4ac2af39e9f6e80e21d9261b1b8d2fd3b037e5d034bcec059a7e80e`.

Train fields and pandas types: `timestamp_ist` string, `mean` float64, `count` float64, `available_at` string, `pm25` float64, `location_id` int64, `sensor_id` int64, `station_name` string, `series_id` string, `flag_high_1000` bool. All 10 fields have zero missing cells. Test fields: `ID`, `location_id`, `sensor_id`, `target_start_ist`, `target_end_ist`, `scoring_block`, `unit`. Station row counts are 12,101 Borivali East, 12,203 Malad West, 11,552 Byculla and 11,993 Shivaji Nagar. PM2.5 median is **21.8367**, 99th percentile **114.5286**, maximum **241,587.5633** µg/m³; 57 labels are ≥500 and 19 are ≥1,000. No target labels are removed or changed. `mean` duplicates `pm25` in the audited release and is excluded.

Feature availability classification:

| Inputs | Availability at a simulated issue | EXP-014 use |
|---|---|---|
| Target station identity and target calendar hour/date | Known at issue | One-hot station and calendar cycles |
| Historical target-station PM ending by explicit PM cutoff | Known from released history under the conservative cutoff proxy | Recent elapsed-hour levels, variation, missingness and trends only |
| 2024 archive seasonal climatology | Historical and predates every 2025–26 origin | Existing legacy W50 seasonal estimate; mapping caveat retained |
| Future weather observations/reanalysis | Available only after target | Excluded |
| Genuine forecast-vintage weather | Potentially available through a legitimate issued forecast, but no verified local vintage/terms set exists | Excluded |
| `ID`, `scoring_block`, `count`, `available_at`, `series_id`, `flag_high_1000`, `mean` | Administrative, source metadata, unverified release clock, diagnostic flag or duplicate label | Excluded as predictors |
| Future PM labels, target PM, hidden targets | Unavailable at issue | Labels only after feature construction; never predictors |

`data/external/weather/` contains only its README in this worktree. No external weather or auxiliary measurements enter EXP-014. The archive loader retains the EXP-007 mapping, which EXP-008 found ambiguous for Borivali East and Malad West and incorrectly pools nearby Mindspace-Malad. This experiment does not change those mappings or assert a physical sensor identity. The full feature list and availability category are in `FEATURE_CATALOG.csv`.
