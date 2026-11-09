# Weather alignment — EXP-025-WEATHER

Current diagnostics have192 rows/source: four Stations.csv coordinates ×48 hours.
All station coordinates are inside both regular grids. Bilinear interpolation uses
the exact four surrounding corners and retains their coordinates/weights; nearest
gridpoint values are diagnostic only. Coordinate order comes from ecCodes, so
opposite CAMS/GFS scan directions do not change interpolation. Missing or duplicate
corners, incomplete rectangles and out-of-grid stations fail; no missing value is zero-filled.

The target interval midpoint is exactly target_start+30 minutes, converted to UTC.
First/last matches are2026-11-10T19:00Z and2026-11-12T18:00Z. There is no nearest-time
join or extrapolation. All target stations must have48 consecutive intervals.
GFS uses one8 November06Z run, leads61–108; CAMS uses one8 November00Z run,
leads67–114. Instantaneous PRATE is selected; interval-average PRATE remains
separately audited with its actual start/end lead and template. Surface TMP is excluded.

Clocks in aligned outputs remain distinct: actual diagnostic issue time,
PM cutoff2 November23:00 IST, weather run, possession/retrieval upper bound,
valid time, and target interval start/end. Current diagnostic issue time is
2026-11-08T18:29:06.0346564Z (23:59:06 IST). CAMS possession bound is18:18:04.687446Z;
latest GFS retrieval18:24:18.514275Z. All are earlier than diagnostic issue.
These are NOT historical forecast-publication records or final-refresh clocks.

Units are checked before conversion. CAMS PM2.5 uses kg/m3×1e9; K temperature/dewpoint
become Celsius. U/V remain separate m/s fields. GFS RH stays percent, HPBL metres,
and instantaneous PRATE remains kg/m2/s. Native decoder units, resolved units,
conversion units and HPBL table reference are separately recorded.

`WEATHER_RUN_MANIFEST.csv` has169 file/valid-hour records (121 CAMS,48 GFS), with
nested exact parameter/level definitions and four-station interpolation geometry.
It links source hashes, raw paths and ignored processed station-feature artifacts.
`WEATHER_FEATURE_COVERAGE.csv` has48 source/feature/station records:44 complete,
four missing CAMS pressure. Five-field CAMS diagnostics are explicitly partial;
the strict six-field CAMS ingestion check rejects this file for production.

The former Single Runs prototype inferred pseudo-issue times, duplicated station
coordinates, joined at local hour starts and allowed per-station fallback runs.
Its unused Open-Meteo CLI is retired and delegates to the shared audited pipeline.
This intentional interface change is documented: old Open-Meteo arguments fail
instead of silently retaining those assumptions. No production caller used it.
Open-Meteo remains disabled pending a separate terms/availability implementation.
