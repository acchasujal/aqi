# AirWindow OpenAQ Mumbai stage 1 audit

**Status: LIVE_BOUNDED_DISCOVERY.** Generated 2026-11-13T08:41:37.017643+00:00.

## Evidence and answers

- Mumbai locations discovered: **43** in bounded bbox (72.75, 18.85, 73.05, 19.35); PM2.5 sensors: **57**.
- Sufficient sampled hourly coverage (>=75%): **4** sensors in the bbox, including **4** at locations named Mumbai. This is a screening threshold, not an integration approval.
- Existing AirWindow matches confirmed with aligned local observations: **4**; see STATION_RECONCILIATION.csv.
- Additional promising stations: see discovery shortlist below; no production stations are added by this audit.
- Actual measured range in the sampled window (IST): 2025-05-01T05:00:00+05:30 to 2025-06-01T04:00:00+05:30.
- Missing data, observation regularity, and stale sensors: see HOURLY_COVERAGE_REPORT.csv and DATA_QUALITY_REPORT.md.
- Of 4 sensors, 0 have no hourly data in the sampled interval; 0 duplicate hourly timestamps and 0 stale nonempty sensors were found. Raw measurement frequency is reported per sensor.
- PM2.5 sensors at locations listing CPCB as provider: **50** of 57. This is provider metadata, not a count of independent sources. OpenAQ redistribution is not independent validation.
- Forecast verification readiness: **not established**; require station/source and hourly interval compatibility checks.

## Existing station reconciliation

| AirWindow station ID | OpenAQ location ID | OpenAQ PM2.5 sensor ID | Provider | Aligned hours | Within 0.2 µg/m³ | Mean abs. difference | Classification |
|---:|---:|---:|---|---:|---:|---:|---|
| 11611 | 11611 | 12236426 | CPCB | 624 | 0.9984 | 0.022901 | Confirmed same physical station and source |
| 3409511 | 3409511 | 12238576 | CPCB | 614 | 0.9967 | 0.023567 | Confirmed same physical station and source |
| 11606 | 11606 | 12236418 | CPCB | 627 | 1.0 | 0.02385 | Confirmed same physical station and source |
| 3409510 | 3409510 | 12238567 | CPCB | 638 | 1.0 | 0.02166 | Confirmed same physical station and source |

The comparisons align OpenAQ hourly period ends with Train `timestamp_ist` interval ends. Most values agree within 0.2 µg/m³, but rare larger differences remain unexplained; see the CSV maximum absolute difference column. Matching provider and series IDs establish shared provenance, not independent forecast validation.

## Additional locations to investigate

| Location | Sensor ID | Provider | Sampled hourly coverage |
|---|---:|---|---:|

These are discovery leads only; CPCB redistribution adds station coverage but does not provide an independent observation source. AirNow requires separate physical-site and quality verification.

## Station recommendations

| Location | PM2.5 sensor ID | Decision | Evidence |
|---|---:|---|---|
| Borivali East, Mumbai - IITM | 12236418 | ACCEPT | 94.086% sampled hourly coverage; same CPCB source as AirWindow; no independent verification |
| Malad West, Mumbai - IITM | 12236426 | ACCEPT | 94.086% sampled hourly coverage; same CPCB source as AirWindow; no independent verification |
| Byculla, Mumbai - BMC | 12238567 | ACCEPT | 94.892% sampled hourly coverage; same CPCB source as AirWindow; no independent verification |
| Shivaji Nagar, Mumbai - BMC | 12238576 | CONDITIONAL | 91.801% sampled hourly coverage; negative_lifetime_sensor_summary_review |

## Use recommendations

| Use | Decision |
|---|---|
| Historical observation enrichment | CONDITIONAL — requires compatible, sufficiently complete PM2.5 sensor history |
| Existing forecast verification | CONDITIONAL — first resolve station/source overlap and independence |
| Additional station support | REJECT for production in stage 1; needs model and UI validation in a separate task |
| Future external-observation interface | CONDITIONAL — requires provenance, freshness and terms review |

## Limits

- AirWindow source IDs in Stations.csv are local leads until authenticated OpenAQ responses verify them.
- OpenAQ location coordinates may be rounded; coordinate proximity alone cannot prove physical or source identity.
- The requested 2026-10 to 2026-11 window does not cover all replay cases from 2025-05 onward; rerun for additional bounded historical intervals.
- OpenAQ's terms require OpenAQ and underlying-source attribution; review provider terms before any downstream publication or integration.
- OpenAQ precomputed hourly periods may start at :30 UTC; comparisons use their explicit period end against AirWindow's interval-end timestamps.
- Request caps: 3 location pages, 5 pages per sensor endpoint, 4 sensors. All counts refer to bbox (72.75, 18.85, 73.05, 19.35), not an administrative Mumbai boundary.
- Only first 4 PM2.5 sensors downloaded; remaining sensors are cataloged but unassessed.

## Source documentation

- [OpenAQ API v3](https://docs.openaq.org/api)
- [API key](https://docs.openaq.org/using-the-api/api-key)
- [Rate limits](https://docs.openaq.org/using-the-api/rate-limits)
- [Terms and attribution](https://docs.openaq.org/about/terms)
- [Hourly sensor measurements](https://docs.openaq.org/api/operations/sensor_hourly_measurements_get_v3_sensors__sensors_id__hours_get)
