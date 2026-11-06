# Legacy validation scripts from the initial Claude analysis

These scripts are preserved as a reproducibility starting point, not as canonical production code. They are the portable copy of the six files supplied with Claude's 6 Nov initial report. They have not been fully reviewed or converted into the new package architecture.

Before using:
- Put the immutable `Train.csv` in this folder or set `ZINDI_DATA_DIR` to the folder containing it.
- Inspect the code and reproduce its results in the current environment.
- Note that the ML report ranks models using `y < 500`; this is only a diagnostic and does not match official full-target RMSE.
- History features are filtered at `y < 1000` and clipped at 300 in the legacy setup. Treat this as an experiment setting, not a default.
- The legacy scripts do not build the 2,592-row submission.
- Do not silently modify these scripts; create a new experiment or port functions into `src/mumbai_pm25/` with tests.
