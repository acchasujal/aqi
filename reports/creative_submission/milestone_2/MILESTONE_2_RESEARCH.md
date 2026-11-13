# AirWindow external observation research — Milestone 2

Date: 2026-11-13. Scope: OpenAQ API v3 PM2.5 history around Mumbai. This is a **research observation dataset**, not a forecast feed or a public-health classification.

## Evidence and architecture

Stage 1 discovered 43 locations and 57 PM2.5 sensor IDs in a bounded Mumbai search. One discovered location has no PM2.5 sensor; 42 locations appear in the PM2.5 inventory. Stage 1.5 assessed all 57 separate sensor series over 19 IST replay calendar months (18 complete, November 2026 partial), yielding 1,083 sensor-month records. The Stage 1.5 manifest records 35 overlapping sensors queried and 22 sensors whose catalog lifetime ended before replay. There were no final fetch failures or truncations in that source snapshot.

The Milestone 2 builder reads the retained Stage 1.5 raw hourly API responses locally. It checks sensor ID, one-hour UTC period, PM2.5 unit, source input hashes, catalog count, month count, discrepancy keys and publication schema. It retains the unmodified raw responses in the existing ignored Stage 1.5 cache. A versioned, ignored `runs/<run-id>/` directory holds normalized OpenAQ hours, exact-hour matched Train/OpenAQ rows, and full discrepancy investigation rows. The static frontend receives only aggregate sensor metadata, coverage, quality and agreement metrics in `apps/airwindow/public/data/external_observation_research.json`. It contains no hourly observation values or API credentials. The browser never calls OpenAQ.

`LOCATION_PROVIDER_METADATA.csv` retains location coordinates, provider, owner and deduplicated instrument labels from the Stage 1 catalog. The frequent “Government Monitor” label does not establish a make, model or measurement method for a particular sensor.

OpenAQ `/sensors/{id}/hours` records carry UTC and local period starts/ends. We use UTC internally and label complete calendar months in IST. Train `timestamp_ist` is an hour **end** and is matched to OpenAQ `period.datetimeTo`. No unit conversion is applied: only explicit µg/m³ spelling variants are accepted. An unknown unit blocks publication. OpenAQ's hourly aggregation is retained as delivered; it is not presented as a regulatory 24-hour mean. Negative values and flags are counted, not silently deleted. Retained normalized rows include source sensor/location, provider, original unit, UTC interval, value, flag and aggregation label.

## Quality and qualification

Stage 1.5's 75% aligned-hour screen yields **5 ACCEPT, 30 CONDITIONAL, 22 REJECT** for internal historical research only. Month-level expected and covered hours, zero months and gaps are preserved. Milestone 2 adds per-sensor invalid/missing, negative, flagged and duplicate counts and date bounds from retained hourly records. These dimensions are distinct from independent-source status, future forecast availability and redistribution rights.

Malad West, Byculla and Siddharth Nagar–Worli pass the research screen. Borivali East and Shivaji Nagar remain conditional because of large source-version mismatches. Deonar and Worli MPCB have coverage interruptions. Powai's older PM2.5 sensor ended before replay; its current sensor has only 10 of 18 full months above 75% coverage and remains conditional. AirNow Mumbai begins in the sampled replay span in August 2026; its exact physical site and instrument remain unverified. No additional operational station is approved: the frozen forecast artifact covers only the existing four.

## Discrepancies

The exact-hour comparison yields **42,212** matched Train/OpenAQ hours and retains all **384** differences above 0.2 µg/m³. In the current hourly source responses, 24 discrepant hours carry flags, 95 unflagged hours have fewer observed than expected contributing samples, and 265 have neither of those clues. We classify the 24 as *potential source revision*, 95 as *partial aggregation unresolved*, and 265 as *unresolved*. **Zero are proven fully explained.** Flags and partial counts describe current API state, not the unavailable original source snapshot. The large Borivali and Shivaji outliers, smaller differences, original one-hour alignment, and ±1-hour diagnostics are documented in Stage 1.5 and `DISCREPANCY_REPORT.md`. Correlation is descriptive and can be dominated by extreme values; it does not demonstrate independent monitoring.

## Verification and rights

Replay OOF predictions were created retrospectively on 8 November 2026 at 77 simulated origins. They are not immutable contemporaneous forecast vintages. A versioned November 8 forecast file exists for later dates but does not overlap the replay period and Git time alone is not external publication proof. Consequently **prospective historical forecast verification is unavailable**; no forecast skill score is reported from OpenAQ. CPCB via OpenAQ corresponds to the same underlying CPCB observations, so it is not independent sensor verification.

OpenAQ's [terms](https://docs.openaq.org/about/terms) require attribution and do not clear upstream rights. CPCB location license fields are null in the audited API metadata. The [India Government Open Data License](https://data.gov.in/Godl) cannot be assumed to govern these exact streams. The frontend exposes derived summaries and metadata only. Confirm upstream reuse terms before publishing raw observations or a sensor-level public time series. See the Stage 1.5 `PROVIDER_AND_LICENSING.md` and `FORECAST_VERIFICATION_FEASIBILITY.md` for source details.

## Product boundary

The **External Observation Research** page is separate from planning, replay and evidence. It shows the inventory, sensor-month coverage, quality flags, same-source reconciliation, discrepancy classification, verification status, rights limitation and generated research timestamp. The source API retrieval time was not recorded by Stage 1.5; the page says so explicitly. If the static summary is absent or invalid, the page shows an error and the planner remains usable. The frozen forecast is not presented as live.

Reproduce and recover using `REFRESH_RUNBOOK.md`. The original Stage 1 and Stage 1.5 artifacts are not overwritten by Milestone 2.
