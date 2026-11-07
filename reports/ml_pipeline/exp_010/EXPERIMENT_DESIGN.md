# EXP-010 experiment design

Base: accepted EXP-009 commit `e043a6788416bcb5896b142d788e791f9cd591e7`. Current station mapping, archive timestamp interpretation, leap-year day-of-year logic, source data, and shared fallback remain unchanged. Only the seasonal blend weight varies over 0, 0.25, 0.5, 0.75, 1.

The script `scripts/validate_blend_weights.py` reconstructs corrected EXP-009 48-hour, seven-day-step OOF rows for nominal 48/72/96/120-hour gaps, retaining raw labels. It joins the 2024 seasonal value to corrected W50 by `(fold_id, location_id, target_start)`. When both components exist, the recent component is algebraically `2 × W50 - seasonal`; the script fails if any W50 row lacks prior PM history, because that value could not be recovered. It then calls the same production `combine_forecasts` function for every weight. All candidates share exact fold and row keys.

The last 20% of chronological fold dates form the confirmation partition, selected by date before metric inspection. All preceding folds are development. Choose at most one challenger from development full-target RMSE; compare it with W50 and W0 on confirmation. Primary metric is unmodified full-target RMSE. MAE, median absolute error, station, horizon, November, fallback, actual PM gap, and extreme squared-error contributions are diagnostics.

Source files and hashes, split time, and command parameters appear in `RUN_METADATA.txt`. Row-level OOF predictions are retained under ignored `data/processed/exp010_row_predictions.csv.gz`; summary metrics are versioned here. No public leaderboard score is used to select weights.

`python scripts/summarize_blend_diagnostics.py` derives extreme-error share, actual PM gap distributions, fallback frequency, and median absolute error from the ignored row-level OOF file into `DIAGNOSTICS.csv`.

The reconstructed W50 predictions were compared row by row with EXP-009 corrected OOF outputs across all 53,160 `(gap, fold, station, target)` keys: maximum absolute difference 0.0.
