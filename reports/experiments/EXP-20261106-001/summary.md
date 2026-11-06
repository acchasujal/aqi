# EXP-20261106-001 — History-only baseline reproduction

The legacy baseline ran against `data/raw/challenge/` with Python 3.12.10 ARM64, NumPy 2.5.4 and pandas 3.1.1. Four chronological history-gap settings were evaluated with 48-hour target windows and daily origins. Exact aggregate results are in `metrics.csv`.

At the 48-hour gap, `mean72` gives full-target RMSE 1464.606 and clean-range RMSE 20.146 over 38,344 labelled rows. `diur7` gives 1465.299 / 20.354. Rare extreme targets dominate full-target RMSE, so clean-range results are diagnostic only. At longer gaps, `last` has the lowest full-target RMSE among the three reported controls, but worse clean-range RMSE.

Retain `mean72`, `diur7`, and `last` as matched controls for the next experiment. Do not accept the legacy clipping/filtering policy as production behavior: it removes values above 1,000 from history features and clips feature values at 300, while validation labels remain unchanged.

Reproduction command:

```powershell
$env:ZINDI_DATA_DIR=(Resolve-Path 'data/raw/challenge').Path
.\.venv\Scripts\python.exe scripts\legacy_validation\base.py
```

Row-level OOF data is retained locally as ignored `base_gap48.pkl`, `base_gap72.pkl`, `base_gap96.pkl`, and `base_gap120.pkl`; no generated prediction binary is committed. This remains a legacy pipeline, not the planned production package.
