# Final weather refresh — pending real10 November release

Do not execute future-run retrieval now. This supplements, and does not replace,
`../task008/FINAL_REFRESH_RUNBOOK.md`. No platform submission is authorised here.

1. Preserve all six actual official final-release files in a new official-release
directory, unchanged; hash and verify official provenance. Never overwrite raw/challenge.
2. Run the existing final-stage P_fix command from the TASK008 runbook. Recompute
station PM cutoffs/actual leads; do not relabel the2 November snapshot as final.
It freezes inputs, rejects known initial snapshots, runs deterministic inference
twice and checks all2592 Test IDs, order, schema and finite/nonnegative outputs.
3. If doing weather research, request CAMS10 November00Z, six variables, leads19–66,
area[20,72,18,74], GRIB. Exact request: `CAMS_REQUEST_FINAL_20261110.json`.
Use only after availability; guarantee10:00 UTC/15:30 IST is a planning bound,
while completed request/retrieval time is separately recorded.
4. Retrieve GFS10 November06Z leads13–60 using the command below. If incomplete or
not available before actual model issue time, attempt00Z leads19–66 in a different
directory. Latest is determined among verified complete runs, never nominal cycles.
Do not combine pieces from different runs. The first file must pass before bulk work.
5. Decode/check all48 target midpoints, levels, units, grids, station corners,
missing/duplicates, raw hashes and retrieval receipts. Confirm latest completed
retrieval <= actual model issue time. If a source is incomplete, preserve the failure
and fall back; do not silently choose newer post-issue files.
6. **Weather corrections remain disabled** until competition permission,
historical issue-time policy, archived as-issued vintages and matched development/
confirmation improvement are all established. Otherwise final output remains P_fix.
The diagnostic script is explicitly tied to the current November private window;
it is not the official final-stage export command.
7. Review final manifest and deterministic2592-row export. Keep a new filename.
Do not upload to Zindi automatically; local success is not platform processing.

Decoder-environment commands (see DECODER_SETUP.md):

```powershell
data\processed\weather_tools\python_x64\python.exe scripts/weather_pipeline.py cams --date 2026-11-10 --cycle 0 --first 19 --last 66 --request-only --output data/external/weather/cams/cams_20261110_00Z_019-066.grib
data\processed\weather_tools\python_x64\python.exe scripts/weather_pipeline.py gfs --date 2026-11-10 --cycle 6 --first 13 --last 60 --output data/external/weather/noaa_gfs/20261110_06Z
```

The first command prints the request only. Authenticated CAMS retrieval requires
removing `--request-only`, locally configured credentials and provider terms
acceptance. Never put secrets in command arguments or Git. For the supplied
8 November file, the minimal missing-field web request is
`CAMS_REQUEST_MISSING_PRESSURE_20261108.json`: only surface_pressure,00Z,
leads67–114 inclusive, same area and GRIB. Preserve the resulting supplement
separately and audit the combined six-field coverage without modifying originals.
