# EXP-013 final official-file refresh

Download the organiser's updated files manually and save them in a new directory. Keep every earlier release intact. Verify the file names and release time against the official [data page](https://zindi.world/competitions/google-mumbai-data-challenge/data). The command below accepts explicit official paths, copies all six inputs into an immutable hash-named snapshot under `data/processed/official_snapshots/`, validates the schemas and target IDs, recalculates the station-specific PM cutoff and November 11–12 forecast leads, and writes a new W50 CSV plus text/JSON manifests under `artifacts/submissions/exp013/`. It refuses to overwrite an existing output. It never uploads to Zindi.

From `C:\Users\dyara\aqi-exp013` in PowerShell, set `$release` to the directory containing the freshly downloaded official files, then run:

```powershell
$release = 'C:\path\to\official\release'
$env:PYTHONPATH = 'src'
python scripts/refresh_official_snapshot.py `
  --train-csv (Join-Path $release 'Train.csv') `
  --test-csv (Join-Path $release 'Test.csv') `
  --samplesubmission-csv (Join-Path $release 'SampleSubmission.csv') `
  --stations-csv (Join-Path $release 'Stations.csv') `
  --datadictionary-txt (Join-Path $release 'DataDictionary.txt') `
  --additionalhistory-zip (Join-Path $release 'AdditionalHistory.zip') `
  --issue-time '2026-11-10T10:00:00+05:30'
```

Set `--issue-time` to the actual timezone-aware run time after obtaining the release. The command errors if a PM observation ends after that time, a target station lacks eligible PM history, the expected private 48-hour four-station grid is absent, the submission has missing/reordered/duplicate IDs or nonfinite/negative predictions, or the versioned output name already exists. Check the printed cutoff and lead range; a fresh Train may shorten the 193–240h lead distribution. Inspect the adjacent `.json` manifest for all input hashes, source paths, cutoff, lead range, row count, output hash and prediction summary. The adjacent `.manifest.txt` also records the Git commit and Python/library versions.

The current accepted model is `hist24_blend50_median72`, with seasonal weight 0.5 and legacy day-of-year alignment. The EXP-012 hybrid was not qualified for a manual leaderboard test on the present data, so this workflow intentionally generates W50 only. Reassess the locked hybrid on a genuinely new official release before adding any challenger generation. Do not retune it using the public leaderboard. Do not run this script against hidden target labels or replace `data/raw/challenge/` files.
