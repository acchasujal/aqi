# Data Inventory and Audit Findings

**Audit basis:** initial uploaded challenge files and prior row-level audit, snapshot 2026-11-05/06. Re-run all checks from the repository after moving files; record file hashes and audit output. Values below must be treated as a baseline audit, not immutable properties of later Train.csv updates.

## Required raw files

| File | Purpose | Handling |
|---|---|---|
| `Train.csv` | Historical station-hour PM2.5 labels and metadata | Immutable raw input; later releases versioned separately |
| `Test.csv` | Fixed 2,592 station-hour prediction IDs and timestamps | Immutable raw input |
| `SampleSubmission.csv` | Required ID order and output schema | Immutable raw input |
| `Stations.csv` | Four target station metadata rows | Immutable raw input |
| `DataDictionary.txt` | Field/time/evaluation semantics | Preserve verbatim |
| `AdditionalHistory.zip` | Optional historical Mumbai station sources and metadata | Preserve archive; inspect each member before use |

The website also supplies `Mumbai_Air_Quality_Starter.ipynb`. Keep it under `notebooks/reference/` if downloaded; use it as reference only, not as the production pipeline.

## Train audit — initial snapshot

Previously audited properties:
- 47,849 rows × 10 columns.
- No missing cells, duplicate rows or duplicate station-hour keys in the audited copy.
- Timestamp range 2025-02-19 03:00 IST through 2026-11-02 23:00 IST.
- `mean` exactly equals `pm25` for every audited row.
- `count` has values 3 or 4.
- About 19 observations exceed 1,000 µg/m³; maximum recorded value about 241,587.56 µg/m³.
- Target is strongly right-skewed; rare extremes can dominate RMSE.
- Four station coverage is incomplete on the full hourly grid; missing hours are common and long gaps exist.
- Cross-station correlations and station target levels differ; treat station as a categorical identity.

Recompute counts, extrema, per-station coverage and gaps on every new Train release. Never carry these counts forward unverified.

## Field interpretation and eligibility

| Field | Meaning / status | Feature policy |
|---|---|---|
| `timestamp_ist` | End of observed hourly interval | Convert to hour-start target key (`-1 hour`) for joins; derive calendar features |
| `pm25` | Observed target | Label for training only; historical lag/rolling inputs only when available before forecast origin |
| `mean` | Same value as `pm25` in audited release | Drop; duplicate target |
| `count` | Number of valid quarter-hour readings | Do not use as test predictor; not present as equivalent future measurement metadata |
| `available_at` | Source modification/retrieval time; not verified first publication | Do not treat as exact publication time; diagnostic only unless validated |
| `location_id` | Station identifier | Use only as categorical station identity if desired; not numeric magnitude |
| `sensor_id` | Sensor identifier | Same; avoid redundant identity features unless ablated |
| `station_name` | Station name | Canonicalise to a single station categorical field |
| `series_id` | Source-specific series descriptor | Do not use as predictive signal |
| `flag_high_1000` | Diagnostic high-value flag | Do not use as predictor; may be used for audit/sensitivity analysis only |

## Test fields

- `ID`: stable identifier; not a predictive feature.
- `location_id`, `sensor_id`: identify station; map to a stable categorical station feature.
- `target_start_ist`, `target_end_ist`: define target interval.
- `scoring_block`: administrative allocation only; do not use as feature.
- `unit`: metadata only.
- No target values are supplied.

## Timestamp alignment

- Train `timestamp_ist` is the end of the target hour.
- Corresponding target/weather interval start is `timestamp_ist - 1 hour`.
- Test `target_start_ist` is already the start of the target interval.
- Do not shift timestamps casually. Add automated tests with boundary examples and an explicit timezone.
- Weather variables can have different semantics: instant, hourly mean, hourly accumulation. Preserve source definition and test +0/±1 hour alignments only as controlled experiments.

## AdditionalHistory.zip findings

Prior archive inspection identified:
1. `History_Mumbai_2018_2020.csv.gz`: CPCB-derived historic station data, different IDs and older period.
2. `History_Mumbai_2024.csv.gz`: XKDR station series; source timing and station identity require verification.
3. `Legacy_Observations_2020_2022.csv.gz`: irregular OpenAQ samples for only two older location/sensor identifiers.
4. `Other_Mumbai_Stations_2025_2026.csv.gz`: auxiliary hourly data from 14 Mumbai stations; ends around 2026-10-16 in the audited archive; Sewri dominates row count.
5. `XKDR_All_Stations.csv` and `Kaggle_All_Stations.csv`: station metadata lookups.
6. `HistoryNotes.txt`: source caveats and warnings against assuming IDs across sources are equivalent.

Default policy: do not merge archive members into target-station training labels. Auxiliary station data may be used only as separately attributed historical spatial context after provenance, timezone, temporal semantics and licence are checked. It cannot provide contemporaneous November target-station readings.

## Required automated audit

Implement `scripts/audit_data.py` to emit a timestamped JSON/Markdown report covering:
- Required file existence and SHA-256 hashes.
- Schema/dtypes and row counts.
- Nulls and duplicate IDs/keys.
- Train/test station membership.
- Timestamp timezone and monotonicity.
- Hour-grid coverage and max consecutive gaps per station.
- Target quantiles and counts above 100/300/500/1,000.
- Whether `mean == pm25`.
- Test/sample ID exact equality and order.
- Test period and scoring-block counts.

Fail loudly on schema drift or submission-grid mismatch. Do not edit the source files to make the audit pass.
