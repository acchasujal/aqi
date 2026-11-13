# OpenAQ Mumbai Stage 1 discovery

This package audits OpenAQ API v3 observations only. It does not update AirWindow
forecasts, replay data, station mappings, or raw challenge data.

1. Obtain a free key at [OpenAQ Explore](https://explore.openaq.org/register).
2. In PowerShell, set it for the current session:

   ```powershell
   $env:OPENAQ_API_KEY = 'YOUR_KEY_HERE'
   ```

   Or set a user-level variable with
   `[Environment]::SetEnvironmentVariable('OPENAQ_API_KEY', 'YOUR_KEY_HERE', 'User')`
   and open a new terminal. Do not add the key to a repository file.
3. From the repository root, run:

   ```powershell
   py -3 -m apps.airwindow.scripts.openaq_audit.run_audit --date-from 2026-10-01T00:00:00Z --date-to 2026-11-11T00:00:00Z --max-location-pages 3 --max-measurement-pages 5 --max-sensors 60
   ```

The end is exclusive. A separate bounded run can inspect replay periods from
2025 onward. Do not interpret one month of coverage as lifetime coverage.
`--offline-status` writes explicit unverified reports without making API calls.

Results appear in `reports/creative_submission/openaq_stage1/`. The `raw/`
subdirectory holds cached API pages and exact measurement responses, keyed by
request path and parameters. It is intentionally ignored by Git because it can
be large. Summary reports are tracked. Reusing the same cache provides a stable
snapshot; remove or move the cache to query fresh data. A capped page count is
flagged as truncated and cannot establish complete coverage. API responses
contain UTC and local timestamps; analysis uses UTC internally. AirWindow
station observations are interval-end timestamps in IST.

Run offline tests with:

```powershell
py -3 -m pytest tests/test_openaq_audit.py -q
py -3 -m ruff check apps/airwindow/scripts/openaq_audit tests/test_openaq_audit.py
```

## Stage 1.5 replay-month qualification

The Stage 1.5 command reads the existing replay artifact and Stage 1 live sensor
catalog. It checks all 19 replay months for every catalogued sensor, preserving
sensor identity and marking API failures as unknown rather than missing hours.
It retrieves only sensors whose reported lifetimes overlap the replay period.

```powershell
$env:OPENAQ_API_KEY = [Environment]::GetEnvironmentVariable('OPENAQ_API_KEY', 'User')
py -3 -m apps.airwindow.scripts.openaq_audit.qualify_history --workers 4
py -3 -m apps.airwindow.scripts.openaq_audit.summarize_qualification
```

If a long-range hourly request times out, the script retries bounded calendar
months. API pages and normalized hourly responses are cached in the ignored
`reports/creative_submission/openaq_stage1_5/raw/` directory. Repeating the
same query reuses completed sensor records; the manifest records input hashes,
request bounds, fallback sensors and any incomplete fetches. Run the offline
tests with `py -3 -m pytest tests/test_openaq_history_qualification.py -q`.

The 75% coverage criterion in the qualification summary is a research screen.
It never grants permission to redistribute observations or add stations to
the app. Historical first-publication times are unavailable, so reporting
latency remains unknown.
