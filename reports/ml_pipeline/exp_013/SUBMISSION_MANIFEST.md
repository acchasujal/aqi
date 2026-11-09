# EXP-013 submission artifact manifest

**Prepared, not uploaded.** The current official snapshot yields the W50 artifact:

`C:\Users\dyara\aqi-exp013\artifacts\submissions\exp013\w50_fcee20ebf7bd_d1a47ee18372_20261107_1848.csv`

The command saved `ID,Target` in `SampleSubmission.csv` order, 2,592 unique IDs, no missing or nonfinite values, and no negative values. Output SHA-256: `55e2fc8c7cad94db22f1358a8715216b0c7fbbb7a50c728c4413890f6a8716bc`. Target summary: minimum 32.96853448, median 45.02977183, mean 47.79666356, maximum 93.4375 µg/m³. The W50 forecast was reproduced independently using `scripts/train_predict.py` and `scripts/refresh_official_snapshot.py`; their CSV hashes are identical. The final artifact was regenerated after the EXP-013 implementation commit. Its adjacent `.manifest.txt` records source commit `46ccc3f9cd6e64d8db9d7a88dd4fc0da01f5d596`, model configuration, runtime and file hashes; the adjacent `.json` records all six input hashes and the output hash. Earlier W50 artifacts from the same snapshot remain in this folder and have the same CSV SHA-256.

Model: original `hist24_blend50_median72`, seasonal weight 0.5, legacy day-of-year calendar, unchanged archive mapping. Run time: `2026-11-07T18:48:42+05:30`; PM history cutoff: `2026-11-02T23:00:00+05:30`; private leads: 193–240h. Main input SHA-256 values: Train `fcee20ebf7bd9c4a4e2487bab0a4f81339d6c820a53862b14443031db1f18ad6`, Test `cdb2b6c3035f6331848c565b4d3dd89ac5281efab07fa62bfabc2e7ff172db0a`, SampleSubmission `5806d6109f381043e59fffb48a5d0af5d9de56fd4e0e956e4c5e7f2e6ae5dcd9`, AdditionalHistory `3233061ca4ac2af39e9f6e80e21d9261b1b8d2fd3b037e5d034bcec059a7e80e`. `SNAPSHOT.json` lists the remaining input hashes and paths.

This CSV is based on the 5 November Train snapshot. The organiser schedules later releases, so **regenerate** with `FINAL_REFRESH_RUNBOOK.md` before any manual submission after receiving the official final Train. Never overwrite this artifact. No hybrid CSV was prepared because the locked challenger did not meet the model decision threshold.
