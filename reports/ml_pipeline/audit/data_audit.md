# Challenge data audit

Generated UTC: 2026-11-06T18:34:04.451107+00:00

Train: 47,849 rows; test: 2,592 rows; stations: 4.
Target range: 0.000–241587.563; >1,000: 19 rows.
Test target intervals: 2026-10-22T00:00:00+05:30 to 2026-11-21T00:00:00+05:30.

## Station coverage

| Location ID | Observed hours | Largest gap (hours) | Start | End |
|---:|---:|---:|---|---|
| 11606 | 12101 | 243 | 2025-02-19T02:00:00+05:30 | 2026-11-02T22:00:00+05:30 |
| 11611 | 12203 | 243 | 2025-02-19T02:00:00+05:30 | 2026-11-02T22:00:00+05:30 |
| 3409510 | 11552 | 243 | 2025-02-19T02:00:00+05:30 | 2026-11-02T22:00:00+05:30 |
| 3409511 | 11993 | 243 | 2025-02-19T02:00:00+05:30 | 2026-11-02T22:00:00+05:30 |

## Station target distributions

| Location ID | Rows | Median | P90 | P99 | Max | >1,000 |
|---:|---:|---:|---:|---:|---:|---:|
| 11606 | 12101 | 26.48 | 63.89 | 106.93 | 75203.52 | 4 |
| 11611 | 12203 | 16.32 | 61.58 | 106.26 | 718.23 | 0 |
| 3409510 | 11552 | 17.85 | 59.30 | 94.65 | 3320.63 | 3 |
| 3409511 | 11993 | 24.59 | 64.26 | 181.86 | 241587.56 | 12 |

The audit lists 19 individual rows above 1,000 µg/m³ in `data_audit.json`; all remain unmodified.

## SHA-256

| File | SHA-256 |
|---|---|
| Train.csv | `fcee20ebf7bd9c4a4e2487bab0a4f81339d6c820a53862b14443031db1f18ad6` |
| Test.csv | `cdb2b6c3035f6331848c565b4d3dd89ac5281efab07fa62bfabc2e7ff172db0a` |
| SampleSubmission.csv | `5806d6109f381043e59fffb48a5d0af5d9de56fd4e0e956e4c5e7f2e6ae5dcd9` |
| Stations.csv | `383269fa04abf8f2eb49e5ec0bb5a77c2df11acb6aca996b7edf269a109ee9cf` |
| DataDictionary.txt | `0d10dcbb6d31232d29558ecd50e7a08272a393048d1e62e3ac460c5863522a55` |
| AdditionalHistory.zip | `3233061ca4ac2af39e9f6e80e21d9261b1b8d2fd3b037e5d034bcec059a7e80e` |
