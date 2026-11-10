# TASK011 final refresh and submission report

**Run date:** 10 November 2026, Asia/Kolkata  
**Branch/commit:** `main`, `00f766aa2c8da9ab3efdc062ab9b0ea6bea07ebc` (same as fetched `origin/main`)  
**Status:** Two deterministic submission files generated locally; no Zindi upload or selection performed.

## Final release integrity

The owner-supplied `Train (2).csv` matches the requested SHA-256 `8adbcf55315f166d7dc3dc1d3e4d7400651f26c1d8b95ff387eef38f4e70a283`, has 48,400 rows, 10 columns, no missing cells or duplicate station/interval-end keys, and `mean == pm25`. Its 48,133 overlapping rows match the previous release; the 267 new records are 83 on Nov 7, 88 on Nov 8, 64 on Nov 9 and 32 on Nov 10. Each station's latest interval end is 2026-11-10 09:00 IST.

The release announcement time is recorded as 12:27 IST. The owner-supplied file's local filesystem modified time is recorded in the integrity JSON as an audit hint, not asserted as a verified download time. An exact download receipt/URL was not present; therefore source bytes were hash-verified against the task brief, while independent organiser download provenance remains unverified. The other five competition inputs were copied unchanged from `data/raw/challenge/` into the frozen snapshot. Their SHA-256 hashes, schemas, row counts, missingness and ID order are recorded in `task011_final_data_release_integrity.json`. Raw files were not edited.

| Station `location_id` | Latest interval end (IST) |
|---:|---|
| 11606 | 2026-11-10 09:00 |
| 11611 | 2026-11-10 09:00 |
| 3409510 | 2026-11-10 09:00 |
| 3409511 | 2026-11-10 09:00 |

`available_at - interval_end` ranged from 1.59 to 381.62 hours (median 84.01h, p90 94.01h). This is only a diagnostic; `available_at` was not treated as verified first-publication time. The simulated validation PM availability clock is the target interval end.

## Forecast horizon and released-observation overlay

The final issue time is taken from the actual runtime and recorded per output manifest. For all four stations the cutoff is Nov 10 09:00 IST. The 192 private rows run from target starts Nov 11 00:00 through Nov 12 23:00, with physical leads 15–62 hours. Row-level issue time, PM cutoff, target start/end and physical lead are in the final `.rows.csv` files.

The exact join used Train `(location_id, timestamp_ist)` to Test `(location_id, target_end_ist)`. It found 1,284 already-observed Test IDs overall, including exactly 201 active public-window IDs through the final released hour; zero private IDs matched. All exact matches were replaced by released `pm25` values in both files. The private predictions remain their model outputs. A zero public score after disclosure is not evidence of private-period skill.

## Reproduced validation

The 84 scheduled weekly origins from Apr 2 2025 through Nov 4 2026 were constructed with a 15-hour initial target-start gap and 48-hour horizon. There are 12,731 labelled station-hours across 83 origins with labels; one scheduled origin (Jan 14 2026) has zero labelled targets in this sparse source and is retained in coverage metadata. All labels, including 28 values at least 250 and 8 above 1,000, were left unmodified. `task011_84_origin_oof.csv.gz` contains the 16,128 expected station-hour rows and explicit issue/cutoff/target clocks.

| Candidate | Full-target RMSE | MAE | Bias | RMSE, y < 250 | RMSE, y >= 250 | Missing predictions |
|---|---:|---:|---:|---:|---:|---:|
| P_fix | 2391.7163 | 48.5044 | -36.4632 | 15.0393 | 50998.0227 | 0 |
| P_fix + 10% diur7 | 2391.7244 | 48.2705 | -36.6142 | 14.7469 | 50998.2344 | 0 |
| P_fix + 25% diur7 | 2391.7375 | 48.0024 | -36.8407 | 14.4472 | 50998.5529 | 0 |
| P_fix + 50% diur7 | 2391.7619 | 47.7965 | -37.2183 | 14.3407 | 50999.0863 | 0 |

These reproduce the exploratory broad OOF results to rounding. All three diur7 blends are marginally worse than P_fix on the primary raw full-target RMSE, so the second file is a hedge, not a claimed improvement. The 25% blend is the middle conservative weight and wins over P_fix on 2026-only origins in this rerun, but the gain is small and the regime subset is diagnostic. diur7 alone is unavailable on 563 of 12,731 rows due its 24-observation recent-coverage gate; the blend falls back to P_fix on those rows. Weight and paired-origin results are in the comparison artifacts.

The other scored baseline columns (all on the same labelled targets) are in `task011_baseline_comparison.csv`. The diur7 standalone full-set score is not reported as comparable because it lacks complete coverage; its missing count is explicit. Station, origin, physical lead-bucket, prediction correlation and per-origin paired differences are separately exported. Extreme labels dominate squared error: all models' `y >= 250` RMSE is about 51,000 and the all-label primary must not be replaced with a clean-range metric.

## Final files

1. [P_fix submission](../../../artifacts/submissions/task011_final_Pfix_20261110.csv) — SHA-256 `f450b68212463f64bab67adfb0d98e1c4cce7ee83ec118f2564d38d738e34c13`
2. [P_fix + 25% diur7 submission](../../../artifacts/submissions/task011_final_Pfix_diur25_20261110.csv) — SHA-256 `96aff853c4692d29fd25c460e7efa0c25caa04fd84119c8bb0914ca0a1c6f2d1`

Each file has exactly `ID,Target`, 2,592 rows in SampleSubmission order, finite non-negative values, an audit JSON, row-level CSV and manifest. Manifests record the six frozen-input hashes, source hashes, model formula, cutoff/lead details, release announcement and actual run time, overlay counts, output hash, deterministic duplicate inference and the human-only Zindi action.

## Checks and human action

The script ran inference twice on the same frozen inputs and checked identical private predictions, output order, values and the overlay. The supplied `FINAL_SUBMISSION.csv` was preserved and its schema/ID order was checked; it was not silently treated as a validated model artifact. Full pytest passed (144 tests, 19 existing deprecation warnings); focused final-gap/integration tests passed (15 tests); scoped Ruff and `git diff --check` passed.

Upload these two newly generated files on Zindi. On the Submissions page select the two new TASK011 submissions, not older EXP030 or prior P_fix entries, then save and confirm the UI reports exactly two selected submissions and a successful save. Upload and selection remain owner actions; this run did not access or change Zindi.
