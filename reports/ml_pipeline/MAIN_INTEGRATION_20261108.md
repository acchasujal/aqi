# Main integration task — 8 November 2026

User requested merging the completed existing branch into main and reusing existing branches for future tasks. No new branch is created. Starting worktree clean at feature tip `2f3b1aefe3c8b538fabd9dac4f6d1971a0eacf1e`; refreshed main is `d9bead48951b3f584ce4a8e0ba79f97950fa1edb`. Local main was fast-forwarded to that tip before a non-fast-forward merge with commit deferred for review.

Conflicts: PROGRESS.md, experiments/EXPERIMENT_LOG.csv, scripts/validate_seasonal_history.py, src/mumbai_pm25/forecast.py and src/mumbai_pm25/historical_archive.py. Main adds EXP-008–015 compatibility/parity/calendar/supervised APIs; the feature adds exact archive identities, TASK008 evaluator and AirWindow. Resolution preserves both histories and APIs, keeps source policies explicit, and checks existing W50 and selected P_fix inference separately. No raw data or historical experiment outputs will be overwritten.

Verification and final merge/push evidence are appended after execution.

## Resolution and verification

Preserved exact identity-based P_fix as the TASK008 path and isolated frozen EXP-007--015 name-pooling/calendar calculations in `legacy_seasonal.py`. Existing CLI and supervised parity checks explicitly retain legacy policy. Shared baselines exclude unfinished observation intervals at fractional cutoffs. Preserved both append-only progress histories and all 22 unique experiment records. Added three integration regression tests for source identity, observation cutoff and archived private-forecast parity. Browser captures support AIRWINDOW_SCREENSHOT_DIR so verification cannot overwrite audited submission assets.

Commands and results:
- `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --basetemp data/processed/main-merge-tests-4`: 107 passed, 19 legacy pandas deprecation warnings.
- Scoped `ruff check` across merged Python modules/scripts/tests: all checks passed.
- `scripts/train_predict.py --model hist24_blend50_median72 --model-run-time 2026-11-08T15:58:00+05:30 --output data/processed/main_merge_smoke/w50.csv`: 2,592 rows, SHA256 55e2fc8c7cad94db22f1358a8715216b0c7fbbb7a50c728c4413890f6a8716bc, identical to prior main.
- `scripts/prepare_task008_submission.py --issue-time 2026-11-08T15:58:00+05:30 --output data/processed/main_merge_smoke/pfix.csv`: 2,592 finite nonnegative ordered rows; deterministic rerun; SHA256 3d79cffcca78cea1ad6f5e24d2568bf931bbba8c3b15fcd7db1728462050ab1d, identical to reviewed feature.
- AirWindow `npm.cmd test`: 9 passed; `npm.cmd run build`: passed; `npm.cmd run test:browser` with isolated screenshot output: 5 passed. One browser retry initially failed because the dev server had stopped; restarting it resolved all five connection failures.
- Seven raw input hashes unchanged; frozen public JSON and submission screenshots preserved byte-for-byte. Submission PDF and source screenshot hashes match its audit.

No new model improvement is claimed by this integration. Future train refresh and product calibration limitations remain as documented. No new branch or history rewrite was used.
