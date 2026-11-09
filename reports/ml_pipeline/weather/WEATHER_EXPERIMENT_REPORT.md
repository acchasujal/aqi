# EXP-025-WEATHER execution report — 8–9 November2026

Retain **P_fix**. Weather ingestion/alignment and current-period diagnostics
completed; historical weather model validation and promotion are **BLOCKED**.
The owner explicitly confirmed no documented historical issue-time policy and
instructed that one must not be invented. No weather skill or score improvement
is claimed. Final10 November data and inference remain future-dependent.

## Scope and source integrity

Reused clean main at5d3476b; refreshed origin/main matches. No branch created,
merge/history rewrite, challenge-input modification or AirWindow change.
Existing EXP-20261108-025 is a different completed source-candidate experiment;
its config/report/results remain untouched. This work uses EXP-025-WEATHER and
its requested EXP-025 label is recorded in the new config.

Actual supplied inputs are NOT the two example files in the pasted request.
The raw audit was saved before code edits. CAMS has605 GRIB1 messages:
five fields at every lead0–120, not only endpoint leads. The missing sixth field
is surface pressure. Private-window PM2.5 grid range is20.47–76.99ug/m3.
NOAA f061 has8 GRIB2 messages: six intended instant fields plus surface TMP and
interval-average PRATE. All values and metadata came from official ecCodes;
raw framing checks do not decode meteorological values.

Fresh NOAA retrieval succeeded for all48 hours61–108, after the first file passed.
Downloaded raw files and receipts remain ignored. The first fresh f061 SHA256
matches the supplied file exactly. Full per-file message audits are committed as
metadata, with hashes, URLs and completed retrieval times. Neither source has
verified challenge-catalogue permission. CAMS authenticated retrieval was not
attempted after the owner asked first for exact missing-content identification.
The minimal pressure-only request and full/final requests are saved as JSON.

## Candidate status and evidence gates

| Candidate | Executed evidence | Status |
|---|---|---|
| M0 P_fix | Recomputed all2592 values twice, exact deterministic equality and exact value match to TASK008 | Retained control |
| M1 CAMS PM2.5 | Bilinear station extraction, correct units and exact midpoint match on192 current private rows | Provisional inference diagnostic; no labels/RMSE |
| M2 calibrated CAMS | No historical issue-time policy or vetted as-issued pairs | BLOCKED; no calibration fitted |
| M3 P_fix+GFS | Complete current48h extraction, six instant fields, all station corners | BLOCKED for model selection/correction |
| M4 P_fix+CAMS+GFS | Current diagnostics available except CAMS pressure | BLOCKED; no blend/model fitted |

Existing matched non-weather evidence remains the selection reference:
[TASK008 report](../task008/TASK008_FINAL_REPORT.md) has P_fix full-target RMSE
757.988014 development/15.796318 later confirmation on11001/1400 labelled rows,
69/8 origins. Those are prior reproduced results, not a new weather comparison.
No new non-weather hypothesis was introduced; station calibration and candidate C
already failed their recorded promotion gates. Existing validation code/labels,
folds, targets, model behavior and experiment histories remain unchanged.

Current192-row diagnostic means are CAMS47.6032ug/m3 vs P_fix56.4655ug/m3.
Their difference is not evidence of error reduction; no calibration or weight
was chosen from these levels. Neither uncertainty intervals nor hidden targets
were used. Station-level forecast comparisons remain local in
`data/processed/weather/diagnostic_run01/cams_vs_pfix_provisional.csv`.

Every required GFS field has48 finite hours at all four stations. CAMS has48 hours
for each of five present fields; pressure has0/48 at each station. Full coverage
and169-record provenance manifest are saved beside this report. CAMS production
ingestion correctly rejects missing pressure; the five-field research diagnostic
does not bypass the production gate. Missing data are not zero-filled.

## Implementation

- `weather_grib.py`: verified decoder audit, GRIB framing, exact identifiers/levels,
  one-run coverage, hourly lead/valid-time consistency and finite values/units.
- `weather_download.py` and `weather_pipeline.py`: reproducible CAMS and filtered
  NOAA requests, retry/backoff/timeouts, prepublication decoder validation,
  exclusive raw-file publication, matching hash receipts and safe reuse.
- `weather_features.py`: unit checks/conversions, bilinear/nearest diagnostics,
  exact48-hour midpoint joins, separate clocks and deterministic control export.
- `prepare_weather_diagnostics.py`: current-data diagnostics, metadata compaction
  and production P_fix parity; no weather correction path exists.
- Existing `fetch_single_run_weather.py` now delegates to shared audited ingestion.
  Its unsafe/unvalidated Open-Meteo arguments are intentionally retired; see alignment report.
- Twelve weather features are registered as candidates with permission,
  availability and validation gates, never production/allowed.

## Commands and validation

Decoder provisioning/audit/download commands are in DECODER_SETUP.md. All48 GFS
downloads and the288-field combined block passed. Exact diagnostic command:

```powershell
.venv\Scripts\python.exe scripts/prepare_weather_diagnostics.py --cams-decoded data/processed/weather_tools/cams_decoded.json --gfs-decoded data/processed/weather_tools/gfs_block_decoded.json --issue-time 2026-11-08T18:29:06.0346564Z --cams-available-at 2026-11-08T18:18:04.687446+00:00 --gfs-available-at 2026-11-08T18:24:18.514275+00:00 --output data/processed/weather/diagnostic_run01
.venv\Scripts\python.exe -m pytest tests/test_weather.py -q -p no:cacheprovider --basetemp data/processed/weather-tests-2
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp data/processed/weather-full-tests
.venv\Scripts\python.exe -m ruff check src/mumbai_pm25/weather_grib.py src/mumbai_pm25/weather_features.py src/mumbai_pm25/weather_download.py scripts/weather_pipeline.py scripts/fetch_single_run_weather.py scripts/prepare_weather_diagnostics.py tests/test_weather.py
git diff --check
.venv\Scripts\python.exe scripts/audit_weather_results.py --diagnostics data/processed/weather/diagnostic_run01
```

The issue-time argument was captured from the actual system UTC clock at invocation;
it is recorded here for replay, not an instruction to backdate future exports.
Initial focused tests:15 pass/5 fail from DatetimeArray.sort_values incompatibility;
corrected to DatetimeIndex before successful20/20 focused run. Two additional
coverage/HTTP-protection tests were then added. Full suite: **139 passed**,19 existing
pandas deprecation warnings,46.42s. Scoped Ruff and diff checks passed. No frontend
tests rerun because no frontend files or artifacts changed.

Final artifact review passed: supplied/raw/download hashes, 48 NOAA files,
169 manifest rows, 44 complete station-feature series, candidate statuses,
all prepared CAMS request fields against the captured official ADS form,
separate availability clocks and deterministic control parity. A real-ecCodes
offline smoke also exercised exclusive hard-link publication and a second
hash-verified reuse with network access forbidden; both passed. This confirms
the final publication implementation as well as the initial live download.
Implementation/report text fingerprints in ARTIFACT_REVIEW.json normalize CRLF
to LF so Git checkout conversion does not invalidate them. Raw data/download
SHA256 values always refer to the unchanged original bytes.

P_fix current export SHA256 is
`1259efdec9d9781869c0c81b55f101feb4bee8373edeb1b1fd750326f73a6aa5`;
two independently computed exports are byte-identical. All2592 parsed prediction
values/IDs exactly match prior TASK008 output (maximum absolute difference0.0).
The old3d79cffc… CSV hash differs due LF versus CRLF line endings, not predictions.
Both local control CSVs remain ignored. All seven raw-directory hashes match the
pre-task record. No Zindi action was performed.

## Remaining work

Obtain missing CAMS pressure only if useful for research; no additional token
setup is required to understand the current file. Resolve source eligibility and
a defensible historical issue-time mapping before selecting any historical runs.
Audit their actual hourly retention/availability before fitting weather residual
models on unchanged TASK008 rows. If those gates remain blocked, keep P_fix for
the actual final-refresh workflow in FINAL_WEATHER_REFRESH_RUNBOOK.md. Do not
claim complete historical experimentation or final-release inference now.
