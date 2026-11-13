# OpenAQ Mumbai Stage 1.5 decision

**Coverage:** 57 PM2.5 sensor series × 19 replay calendar months (18 complete months, November 2026 partial).
**Research qualification:** 5 ACCEPT, 30 CONDITIONAL, 22 REJECT.

ACCEPT means suitable for **internal historical research with explicit missingness**. It does not approve redistribution, an independent validation claim or production forecast integration. The screening rule requires at least 15 of 18 full months at 75% aligned hourly coverage, none below 50%, a compatible unit and no incomplete API fetch. Provider/site and negative lifetime data can keep a series conditional.

Coverage here uses complete **IST calendar months** and OpenAQ interval starts. The Stage 1 May spot check used UTC date bounds, so its percentages differ slightly and should not be substituted for these monthly values.

## Priority sensors

| Location | ID | Provider | May 2025 | Later full-month median | Oct 2026 | Months ≥75% | Decision |
|---|---:|---|---:|---:|---:|---:|---|
| Mumbai | 23320 | AirNow | 0.0% | 0.0% | 80.376% | 2/18 | CONDITIONAL |
| Worli, Mumbai - MPCB | 12235914 | CPCB | 87.634% | 79.444% | 77.957% | 12/18 | CONDITIONAL |
| Deonar, Mumbai - IITM | 12236385 | CPCB | 53.36% | 88.306% | 77.016% | 15/18 | CONDITIONAL |
| Borivali East, Mumbai - IITM | 12236418 | CPCB | 94.22% | 92.222% | 82.527% | 17/18 | CONDITIONAL |
| Malad West, Mumbai - IITM | 12236426 | CPCB | 94.22% | 94.355% | 83.199% | 17/18 | ACCEPT |
| Siddharth Nagar-Worli, Mumbai - IITM | 12236435 | CPCB | 90.726% | 87.361% | 75.538% | 16/18 | ACCEPT |
| Byculla, Mumbai - BMC | 12238567 | CPCB | 95.027% | 88.472% | 83.871% | 15/18 | ACCEPT |
| Shivaji Nagar, Mumbai - BMC | 12238576 | CPCB | 91.935% | 89.247% | 84.409% | 16/18 | CONDITIONAL |

AirNow Mumbai first has observations in the sampled replay span in **2026-08**; its catalog lifetime start does not establish continuous coverage. It cannot fill earlier replay months.

## Accepted internal-research series

| Location | Sensor ID | Full months ≥75% | Median aligned coverage |
|---|---:|---:|---:|
| Malad West, Mumbai - IITM | 12236426 | 17/18 | 94.287% |
| Siddharth Nagar-Worli, Mumbai - IITM | 12236435 | 16/18 | 87.43% |
| Byculla, Mumbai - BMC | 12238567 | 15/18 | 88.591% |
| Ghatkopar, Mumbai - BMC | 12238603 | 15/18 | 90.793% |
| Chakala-Andheri East, Mumbai - IITM | 12442196 | 17/18 | 92.204% |

## Largest priority-sensor reporting interruptions

| Sensor ID | Month | Hourly coverage | Longest internal missing run |
|---:|---|---:|---:|
| 12235914 | 2026-06 | 43.611% | 311.0 h |
| 12236385 | 2026-01 | 60.081% | 242.0 h |
| 12236418 | 2026-01 | 66.667% | 242.0 h |
| 12236426 | 2026-01 | 66.532% | 242.0 h |
| 12236435 | 2026-01 | 65.726% | 242.0 h |
| 12238567 | 2026-01 | 66.532% | 242.0 h |
| 12238576 | 2026-01 | 64.113% | 242.0 h |
| 12238567 | 2025-06 | 64.861% | 204.0 h |

Whole months with no observations are recorded as 0% coverage in the CSV; their internal-gap field is zero because no two reports bracket the interruption. The missing-hours count captures those months.


## Same-sensor discrepancy findings

OpenAQ hourly period ends were compared with local Train interval-end timestamps for the four existing station/sensor IDs. All differences above 0.2 µg/m³ remain in `DISCREPANCY_ANALYSIS.csv`; no value was deleted.

| Station ID | Matched hours | >0.2 hours | Frequency | Maximum difference | Median abs. error, shifts −1 / 0 / +1 h |
|---:|---:|---:|---:|---:|---|
| 11606 | 10683 | 37 | 0.346% | 74386.525 | 3.136667 / 0.023333 / 3.06 |
| 11611 | 10836 | 88 | 0.812% | 6.497 | 3.37 / 0.01 / 3.28125 |
| 3409510 | 10113 | 57 | 0.564% | 3.138 | 1.69875 / 0.0175 / 1.6475 |
| 3409511 | 10580 | 202 | 1.909% | 42117.772 | 2.5425 / 0.0225 / 2.49 |

Of 384 differences above 0.2 µg/m³, 24 OpenAQ hourly rows carry flags and 9 exceed 1,000 µg/m³. The largest local Train readings retain their original `flag_high_1000` values. Current OpenAQ quarter-hour responses for Borivali East on 9 and 26 August 2025 contain flagged null measurements where Train has enormous hourly means; a source revision/filter is plausible, but the original quarter-hour snapshot is unavailable. Smaller unflagged disagreements, including some midnight hours, are not fully explained by rounding. The unchanged interval-end alignment is substantially better than ±1 hour for all four stations.

Two checked raw-response examples make the source-version issue concrete:

- Borivali East sensor `12236418`, 9 August 2025 13:00–14:00 IST: Train is 75,203.525 µg/m³ with `flag_high_1000=True`; current OpenAQ hourly is 817.00 µg/m³ and flagged. The current quarter-hours show 817.07 followed by three flagged null values.
- Shivaji Nagar sensor `12238576`, 4 December 2025 05:00–06:00 IST: Train is 42,206.7725 µg/m³ with `flag_high_1000=True`; current OpenAQ hourly is 89.00 µg/m³ and flagged. The current quarter-hours show 89.00 followed by three flagged null values.

These examples support later flagging/filtering as a plausible explanation; the original quarter-hour values used for Train are not available here, so the precise revision history is unresolved. Both products use PM2.5 µg/m³ and the same explicit hour-end alignment.


All 57 sensor decisions and their reasons are in `STATION_QUALIFICATION.csv`; monthly evidence is in `MONTHLY_SENSOR_COVERAGE.csv`. The 22 pre-replay sensors are rejected using their OpenAQ sensor last-report timestamps; API failures remain conditional, never zero coverage.

## Stage 2 recommendation

Proceed only with a research-only, source-labelled prototype for accepted sensor-months after upstream reuse terms and interval methodology are resolved. Keep current AirWindow station forecasts and replay artifacts unchanged. OpenAQ CPCB copies cannot independently verify CPCB-derived forecasts. Prospective verification needs immutable pre-target forecast vintages and publication-time observation evidence.

See `PROVIDER_AND_LICENSING.md`, `FORECAST_VERIFICATION_FEASIBILITY.md` and `DISCREPANCY_ANALYSIS.csv`.

## Existing integration-test artifact

`tests/test_main_integration.py::test_refreshed_app_forecast_matches_audited_task011_rows` expects four TASK011 submission-side files (`.csv`, `.rows.csv`, `.audit.json`, `.manifest.txt`) under ignored `artifacts/submissions/`. They are absent in this checkout; the tracked `reports/ml_pipeline/task011/task011_final_row_audit.csv` is a different artifact and is not substituted. The test remains unchanged and fails until the genuine TASK011 files are restored or the test is separately redesigned around committed provenance.
