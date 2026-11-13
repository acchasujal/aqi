# OpenAQ research refresh and recovery

All commands run from the repository root on `feature/airwindow-openaq-stage1`. The app is static on Firebase Hosting; this is a **manual local workflow**, not a backend or scheduled job. The current forecast/replay artifacts and four operational stations remain unchanged.

## API key

Register through [OpenAQ](https://explore.openaq.org/register). In PowerShell, set the key for this process without writing it to a tracked file:

```powershell
$env:OPENAQ_API_KEY = [Environment]::GetEnvironmentVariable('OPENAQ_API_KEY', 'User')
```

If the user-level variable is unset, configure it locally through Windows Environment Variables or set `$env:OPENAQ_API_KEY` in your private shell. Never paste it into a command log, source file or frontend configuration.

## Reproduce the audited snapshot

The committed Stage 1.5 CSVs and manifest describe the 2026-11-13 source snapshot. The private cached API hours must also be present under `reports/creative_submission/openaq_stage1_5/raw/hourly/`; they are intentionally ignored by Git. With that cache present:

```powershell
py -3 -m apps.airwindow.scripts.openaq_audit.milestone2 --run-id stage15-local-review
$env:PYTHONPATH = 'src'
py -3 -m pytest tests/test_openaq_audit.py tests/test_openaq_history_qualification.py tests/test_openaq_milestone2.py -q
py -3 -m ruff check apps/airwindow/scripts/openaq_audit tests/test_openaq_audit.py tests/test_openaq_history_qualification.py tests/test_openaq_milestone2.py
cd apps/airwindow
npm test
npm run build
```

Use a **new** run ID; immutable `runs/<run-id>/` directories are never overwritten. The builder refuses incomplete Stage 1.5 fetches, changed source hashes, incompatible units, missing hourly source records, duplicate discrepancy keys and inconsistent counts. It writes private normalized and matched rows to ignored `reports/creative_submission/milestone_2/runs/<run-id>/` and updates aggregate CSV/JSON reports. Only the validated derived JSON under `apps/airwindow/public/data/` is build input.

## New live refresh of the same reviewed sensor catalog

```powershell
$env:OPENAQ_API_KEY = [Environment]::GetEnvironmentVariable('OPENAQ_API_KEY', 'User')
py -3 -m apps.airwindow.scripts.openaq_audit.refresh_research --run-id 20261113T120000Z --workers 4
```

Choose a fresh run ID matching the actual UTC execution time. The script reads the reviewed Stage 1 location/sensor catalog, downloads into an immutable ignored `milestone_2/source_runs/<run-id>/`, recomputes every replay-month summary, checks failures/truncations, builds the private research dataset, and publishes the derived static JSON only after validation. It uses the existing bounded OpenAQ v3 client with environment authentication, pagination, retry and a paced request gate. The source run manifest records query bounds, input hashes, sensor count, failures and fallback sensors; the Milestone 2 manifest records source IDs, software version, output checksums and validation counts. Stage 1/1.5 published reports remain unchanged.

A different date range or newly discovered location requires an explicit new catalog and replay-period review before publishing. This command does not silently add sensors or stations. The existing Stage 1 `run_audit.py` can be executed into a **new output directory** for discovery, then reviewed separately.

## Validation before inclusion in a release

1. Inspect `reports/creative_submission/milestone_2/RUN_MANIFEST.json`, `SENSOR_INVENTORY.csv`, `LOCATION_PROVIDER_METADATA.csv`, `SENSOR_QUALITY.csv`, `AGREEMENT_SUMMARY.csv` and `DISCREPANCY_REPORT.md`. Investigate any count or qualification change. A new 384 count is **not** assumed for refreshed data.
2. Run the focused Python tests, `npm test`, `npm run build` and browser tests from the app directory. Confirm there are no `api.openaq.org` browser requests and no `OPENAQ_API_KEY` string or raw hourly values in the public JSON.
3. Review `git diff --check` and the staged diff. Only derived metadata/aggregates may enter a frontend build. Do not copy ignored `raw/`, `source_runs/` or `runs/` into `public/`.
4. Deployment remains a separate approval step. Do not push or deploy as part of refresh.

## Failure and rollback

An API failure or truncated page leaves the previously published `external_observation_research.json` intact. The failed source run remains locally for diagnosis. A failed validation must not be labelled a successful refresh. If a completed derived artifact later proves unsuitable, restore the last reviewed static JSON and Milestone 2 aggregate reports from the previous Git commit or saved copy, keeping private run directories for forensic comparison. The frontend also has a missing/invalid-artifact state that does not interrupt planning or replay.

The Stage 1.5 source API retrieval timestamp was not stored. The Milestone 2 `generated_at_utc` value is the derived build time and is labelled as such; it is not silently presented as an OpenAQ publication time. OpenAQ does not provide a verified historical first-publication timestamp in the audited responses.
