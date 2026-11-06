# Repository Initialization and Data Audit

**Date:** 2026-11-06
**Branch:** `codex/initialize-organize-aqi`
**Purpose:** Move the bootstrap project into the existing Git repository and verify the supplied challenge files before baseline reproduction.

## Repository state

- The existing repository is `C:\Users\sujal\projects\aqi`, branch `main` at start, with `origin` set to `https://github.com/acchasujal/aqi.git`.
- The bootstrap project was nested one directory below the repository root. Its files were moved to the root; challenge inputs were placed in `data/raw/challenge/`, and the starter notebook in `notebooks/reference/`.
- No challenge-file contents were edited. SHA-256 hashes before and after relocation match.

## Input fingerprints

| File | SHA-256 |
|---|---|
| `Train.csv` | `86a9efdcf458f02d46589f416c59057273574727478c5908a92f1e9fa626ec5e` |
| `Test.csv` | `e7b9cc8859beb939276c958393e148adae55229c34f99dcb2555fe4ac13b28db` |
| `SampleSubmission.csv` | `ee4682ce0e546c1b62beb4a08414a5ddc831fa962cff30e8a823d6b6b0e0c72f` |
| `Stations.csv` | `383269fa04abf8f2eb49e5ec0bb5a77c2df11acb6aca996b7edf269a109ee9cf` |
| `DataDictionary.txt` | `0d10dcbb6d31232d29558ecd50e7a08272a393048d1e62e3ac460c5863522a55` |
| `AdditionalHistory.zip` | `3233061ca4ac2af39e9f6e80e21d9261b1b8d2fd3b037e5d034bcec059a7e80e` |

## Audit findings

- Train: 47,849 rows, 10 columns, no blank cells, no duplicate station/timestamp keys, and `mean == pm25` on every row.
- Train interval-end timestamps span 2025-02-19 03:00 through 2026-11-02 23:00 IST.
- All four expected stations are present. The largest target is 241,587.5633; 19 targets exceed 1,000. `count` contains 40,543 values of 4 and 7,306 values of 3.
- Test and SampleSubmission each have 2,592 rows, and IDs match in exact order. Each of four stations has 648 rows; scoring-block counts are 768 public, 192 private, and 1,632 unscored.
- The test interval-start grid spans 2026-10-22 00:00 through 2026-11-20 23:00 IST.

The audit used Python's standard-library `csv`, `datetime`, `hashlib`, and `collections` modules, plus `Get-FileHash`. It did not import or modify challenge files through a dataframe pipeline.

## Baseline reproduction status

Experiment `EXP-20261106-001` remains uncompleted. Python 3.15.1 ARM64 is installed but outside `pyproject.toml`'s supported range. A temporary Python 3.12.10 ARM64 runtime was installed under `%TEMP%`; installing the already-declared NumPy and pandas dependencies into the ignored local `.venv` failed because pip had no compatible pandas ARM64 wheel and its source build could not find Visual Studio Build Tools (`vswhere.exe`). No baseline metrics or OOF predictions were produced. Re-run after establishing a supported Python/dataframe environment.

## Commands and checks

- `git switch -c codex/initialize-organize-aqi`
- PowerShell `Move-Item` commands placed the source tree and raw inputs in their documented locations; the now-empty bootstrap directory was removed.
- `Get-FileHash ... -Algorithm SHA256` before and after relocation; hashes matched.
- Python standard-library CSV audit: passed with the findings above.
- `git diff --check`: passed before staging.
- Test suite: not run; this task changes repository organization and documentation only. Baseline experiment is pending and no model code was changed.
