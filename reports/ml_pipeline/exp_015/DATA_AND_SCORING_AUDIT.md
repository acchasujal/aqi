# EXP-015 data and scoring audit

Audited the unchanged local official snapshot on 2026-11-07. `data/raw/challenge/` was read only. File hashes (SHA-256):

| File | Rows | SHA-256 |
|---|---:|---|
| Train.csv | 47,849 | `fcee20ebf7bd9c4a4e2487bab0a4f81339d6c820a53862b14443031db1f18ad6` |
| Test.csv | 2,592 | `cdb2b6c3035f6331848c565b4d3dd89ac5281efab07fa62bfabc2e7ff172db0a` |
| SampleSubmission.csv | 2,592 | `5806d6109f381043e59fffb48a5d0af5d9de56fd4e0e956e4c5e7f2e6ae5dcd9` |
| Stations.csv | 4 | `383269fa04abf8f2eb49e5ec0bb5a77c2df11acb6aca996b7edf269a109ee9cf` |
| DataDictionary.txt | — | `0d10dcbb6d31232d29558ecd50e7a08272a393048d1e62e3ac460c5863522a55` |
| AdditionalHistory.zip | — | `3233061ca4ac2af39e9f6e80e21d9261b1b8d2fd3b037e5d034bcec059a7e80e` |

Station IDs are 11606, 11611, 3409510, 3409511; Test has 648 rows each. No duplicate Train station-hour or Test ID was found. Sample IDs equal Test IDs in original order. Latest eligible PM interval end is 2026-11-02 23:00 IST at each station. Train `timestamp_ist` is the **end** of the hourly PM interval; Test `target_start_ist` and `target_end_ist` bracket its hour. This is specified by the local competition dictionary and [OpenAQ's period-end convention](https://docs.openaq.org/using-the-api/dates-datetimes). Every timestamp carries `+05:30`.

The local dictionary designates 2026-11-03–04 as the public target window and 2026-11-11–12 as private. Against the current cutoff, each has 192 Test rows: public leads 1–48 hours, median 24.5; private leads 193–240 hours, median 216.5. These are locally documented scoring windows, not independently observed hidden labels or a disclosure of exact leaderboard weighting. The entire Test file contains additional dates from October 22 to November 20, and the dictionary says only 92 public targets have observed labels; the validation set cannot exactly reproduce unknown leaderboard label availability. Actual target lead is calculated as target interval start minus the station's most recent eligible PM interval end. No `ID`, `scoring_block`, `available_at`, metadata flag, or row order is used as a predictor.

The [official competition page](https://zindi.world/competitions/google-mumbai-data-challenge) explicitly confirms a 10 November 2026 23:59:59 IST deadline and the 11–12 November private period. Its general rules are internally inconsistent about public/private percentages (approximately 30/70 and 20/80 appear on the same page) and overall submission caps (140 and 300). It does not independently establish the local dictionary's Nov 3–4 public-label subset or its 92 valid labels. Therefore these local public-window details remain assumptions for interpreting historical analogues; no leaderboard score is used to infer hidden labels.

The Train labels include very large finite positive values. They remain unmodified in all primary metrics. Full Test schema validation is implemented in `src/mumbai_pm25/data.py`; no refresh was found locally. The source snapshot needs rechecking when the organizer publishes the final Train release.
