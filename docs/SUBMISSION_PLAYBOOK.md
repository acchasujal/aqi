# Submission Build and Verification Playbook

## Required submission contract

- Exactly 2,592 rows for the audited release (recheck after any official file change).
- Columns exactly `ID`, `Target` in required order.
- IDs exactly match `Test.csv` and `SampleSubmission.csv` in original order.
- Every Target is numeric, finite and >= 0.
- No duplicate IDs, missing IDs or extra IDs.
- Target predictions use the unit µg/m³.
- Save the model/config/source-data manifest associated with the file.

## Final forecast procedure

1. Freeze the final training-data snapshot and record SHA-256.
2. Read final organiser guidance and record selected/latest submission rule.
3. Compute actual per-station last PM observation and history cutoff.
4. Determine the intended PM history cutoff and weather issue time separately.
5. Fetch only a weather forecast available by the weather issue time, if approved.
6. Build all features from the explicit information set.
7. Fit the model using the selected config and fixed seed.
8. Predict all Test rows.
9. Run schema, ID-order, finite, non-negative, range and timestamp checks.
10. Save the CSV, config, environment, data hashes and run log.
11. Submit only after manual review; record platform response/score and submission ID.

## Submission naming

`submission_<YYYYMMDD_HHMM_IST>_<model-id>_<short-git-sha>.csv`

Do not overwrite a previously submitted file. Keep all candidates locally with manifests. Do not commit generated submissions unless explicitly required; archive them as release artifacts.

## Sanity checks

- Plot predictions by station and time.
- Check station-wise prediction distributions and compare with recent history.
- Check for accidental identical constants or negative values.
- Inspect top/bottom predictions and any extreme forecast spikes.
- Never modify predictions manually based on leaderboard rank without recording a reproducible post-processing experiment.
