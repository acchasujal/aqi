# AirWindow OpenAQ Mumbai stage 1 audit

**Status: LIVE_BOUNDED_DISCOVERY.** Generated 2026-11-13T08:42:17.338152+00:00.

## Evidence and answers

- Mumbai locations discovered: **43** in bounded bbox (72.75, 18.85, 73.05, 19.35); PM2.5 sensors: **57**.
- Sufficient sampled hourly coverage (>=75%): **24** sensors in the bbox, including **19** at locations named Mumbai. This is a screening threshold, not an integration approval.
- Existing AirWindow matches confirmed with aligned local observations: **4**; see STATION_RECONCILIATION.csv.
- Additional promising stations: see discovery shortlist below; no production stations are added by this audit.
- Actual measured range in the sampled window (IST): 2026-10-01T05:00:00+05:30 to 2026-11-11T04:00:00+05:30.
- Missing data, observation regularity, and stale sensors: see HOURLY_COVERAGE_REPORT.csv and DATA_QUALITY_REPORT.md.
- Of 57 sensors, 24 have no hourly data in the sampled interval; 0 duplicate hourly timestamps and 1 stale nonempty sensors were found. Raw measurement frequency is reported per sensor.
- PM2.5 sensors at locations listing CPCB as provider: **50** of 57. This is provider metadata, not a count of independent sources. OpenAQ redistribution is not independent validation.
- Forecast verification readiness: **not established**; require station/source and hourly interval compatibility checks.

## Existing station reconciliation

| AirWindow station ID | OpenAQ location ID | OpenAQ PM2.5 sensor ID | Provider | Aligned hours | Within 0.2 µg/m³ | Mean abs. difference | Classification |
|---:|---:|---:|---|---:|---:|---:|---|
| 11611 | 11611 | 12236426 | CPCB | 708 | 0.9873 | 0.056547 | Confirmed same physical station and source |
| 3409511 | 3409511 | 12238576 | CPCB | 710 | 0.9986 | 0.026496 | Confirmed same physical station and source |
| 11606 | 11606 | 12236418 | CPCB | 709 | 0.9929 | 0.035132 | Confirmed same physical station and source |
| 3409510 | 3409510 | 12238567 | CPCB | 710 | 0.9915 | 0.030223 | Confirmed same physical station and source |

The comparisons align OpenAQ hourly period ends with Train `timestamp_ist` interval ends. Most values agree within 0.2 µg/m³, but rare larger differences remain unexplained; see the CSV maximum absolute difference column. Matching provider and series IDs establish shared provenance, not independent forecast validation.

## Additional locations to investigate

| Location | Sensor ID | Provider | Sampled hourly coverage |
|---|---:|---|---:|
| Siddharth Nagar-Worli, Mumbai - IITM | 12236435 | CPCB | 79.37% |
| Worli, Mumbai - MPCB | 12235914 | CPCB | 76.728% |
| Deonar, Mumbai - IITM | 12236385 | CPCB | 80.386% |
| Mumbai | 23320 | AirNow | 82.724% |

These are discovery leads only; CPCB redistribution adds station coverage but does not provide an independent observation source. AirNow requires separate physical-site and quality verification.

## Station recommendations

| Location | PM2.5 sensor ID | Decision | Evidence |
|---|---:|---|---|
| Borivali East, Mumbai - IITM | 12236418 | ACCEPT | 85.061% sampled hourly coverage; same CPCB source as AirWindow; no independent verification |
| Malad West, Mumbai - IITM | 12236426 | ACCEPT | 85.163% sampled hourly coverage; same CPCB source as AirWindow; no independent verification |
| Byculla, Mumbai - BMC | 12238567 | ACCEPT | 84.858% sampled hourly coverage; same CPCB source as AirWindow; no independent verification |
| Shivaji Nagar, Mumbai - BMC | 12238576 | CONDITIONAL | 85.061% sampled hourly coverage; negative_lifetime_sensor_summary_review |
| Borivali East, Mumbai - IITM | 39428 | REJECT | 0.0% sampled hourly coverage; coverage_below_75_percent |
| Malad West, Mumbai - IITM | 39454 | REJECT | 0.0% sampled hourly coverage; coverage_below_75_percent |
| Powai, Mumbai - MPCB | 20079 | REJECT | 0.0% sampled hourly coverage; coverage_below_75_percent |
| Powai, Mumbai - MPCB | 12235896 | REJECT | 44.512% sampled hourly coverage; coverage_below_75_percent |
| Siddharth Nagar-Worli, Mumbai - IITM | 20033 | REJECT | 0.0% sampled hourly coverage; coverage_below_75_percent, negative_lifetime_sensor_summary_review |
| Siddharth Nagar-Worli, Mumbai - IITM | 12236435 | ACCEPT | 79.37% sampled hourly coverage; requires source agreement check |
| Bandra Kurla Complex, Mumbai - IITM | 39404 | REJECT | 0.0% sampled hourly coverage; coverage_below_75_percent |
| Deonar, Mumbai - IITM | 39416 | REJECT | 0.0% sampled hourly coverage; coverage_below_75_percent |
| Siddharth Nagar-Worli, Mumbai - IITM | 389761 | REJECT | 0.0% sampled hourly coverage; coverage_below_75_percent |
| Worli, Mumbai - MPCB | 12235914 | ACCEPT | 76.728% sampled hourly coverage; requires source agreement check |
| Bandra Kurla Complex, Mumbai - IITM | 12708246 | CONDITIONAL | 57.419% sampled hourly coverage; coverage_below_75_percent |
| Deonar, Mumbai - IITM | 12236385 | ACCEPT | 80.386% sampled hourly coverage; requires source agreement check |
| Bandra Kurla Complex, Mumbai - MPCB | 12238375 | CONDITIONAL | 71.037% sampled hourly coverage; coverage_below_75_percent, negative_lifetime_sensor_summary_review |
| Navi Mumbai Municipal Corporation Airoli | 5404 | REJECT | 0.0% sampled hourly coverage; coverage_below_75_percent |
| Pimpleshwar Mandir, Thane - MPCB | 14806 | REJECT | 0.0% sampled hourly coverage; coverage_below_75_percent |
| Colaba, Mumbai - MPCB | 20143 | REJECT | 0.0% sampled hourly coverage; coverage_below_75_percent, negative_lifetime_sensor_summary_review |
| Colaba, Mumbai - MPCB | 12235926 | CONDITIONAL | 74.39% sampled hourly coverage; coverage_below_75_percent |
| Mahape, Navi Mumbai - MPCB | 20046 | REJECT | 0.0% sampled hourly coverage; coverage_below_75_percent |
| Mahape, Navi Mumbai - MPCB | 12235905 | ACCEPT | 81.199% sampled hourly coverage; requires source agreement check |
| Kurla, Mumbai - MPCB | 19978 | REJECT | 0.0% sampled hourly coverage; coverage_below_75_percent |
| Kurla, Mumbai - MPCB | 12235834 | ACCEPT | 80.488% sampled hourly coverage; requires source agreement check |
| Chhatrapati Shivaji Intl. Airport (T2), Mumbai - MPCB | 19981 | REJECT | 0.0% sampled hourly coverage; coverage_below_75_percent |
| Chhatrapati Shivaji Intl. Airport (T2), Mumbai - MPCB | 12235860 | REJECT | 21.341% sampled hourly coverage; coverage_below_75_percent |
| Borivali East, Mumbai - MPCB | 20087 | REJECT | 0.0% sampled hourly coverage; coverage_below_75_percent |
| Borivali East, Mumbai - MPCB | 12252658 | CONDITIONAL | 70.02% sampled hourly coverage; coverage_below_75_percent |
| Sion, Mumbai - MPCB | 20096 | REJECT | 0.0% sampled hourly coverage; coverage_below_75_percent, negative_lifetime_sensor_summary_review |
| Sion, Mumbai - MPCB | 12243930 | ACCEPT | 78.557% sampled hourly coverage; requires source agreement check |
| Vile Parle West, Mumbai - MPCB | 20251 | REJECT | 0.0% sampled hourly coverage; coverage_below_75_percent, negative_lifetime_sensor_summary_review |
| Vile Parle West, Mumbai - MPCB | 12235851 | REJECT | 0.0% sampled hourly coverage; coverage_below_75_percent |
| Bandra, Mumbai - MPCB | 36447 | REJECT | 0.0% sampled hourly coverage; coverage_below_75_percent |
| Mumbai | 23320 | CONDITIONAL | 82.724% sampled hourly coverage; negative_lifetime_sensor_summary_review |
| Sector-19A Nerul, Navi Mumbai - IITM | 39460 | REJECT | 0.0% sampled hourly coverage; coverage_below_75_percent |
| Chakala-Andheri East, Mumbai - IITM | 40571 | REJECT | 0.0% sampled hourly coverage; coverage_below_75_percent |
| Chakala-Andheri East, Mumbai - IITM | 12442196 | ACCEPT | 80.488% sampled hourly coverage; requires source agreement check |
| Khindipada-Bhandup West, Mumbai - IITM | 40608 | REJECT | 0.0% sampled hourly coverage; coverage_below_75_percent |
| Khindipada-Bhandup West, Mumbai - IITM | 12236394 | ACCEPT | 79.98% sampled hourly coverage; requires source agreement check |
| Mulund West, Mumbai - MPCB | 40641 | REJECT | 0.0% sampled hourly coverage; coverage_below_75_percent |
| Mulund West, Mumbai - MPCB | 12236481 | ACCEPT | 77.541% sampled hourly coverage; requires source agreement check |
| Kandivali East, Mumbai - MPCB | 40650 | REJECT | 0.0% sampled hourly coverage; coverage_below_75_percent |
| Kandivali East, Mumbai - MPCB | 12236472 | REJECT | 0.0% sampled hourly coverage; coverage_below_75_percent |
| Pimpleshwar Mandir, Thane - MPCB | 12235644 | REJECT | 44.614% sampled hourly coverage; coverage_below_75_percent |
| Kasarvadavali, Thane - MPCB | 12238258 | CONDITIONAL | 83.028% sampled hourly coverage; negative_lifetime_sensor_summary_review |
| Upvan Fort, Thane - MPCB | 12238285 | CONDITIONAL | 74.492% sampled hourly coverage; coverage_below_75_percent, negative_lifetime_sensor_summary_review |
| CBD Belapur, Belapur - MPCB | 12238321 | CONDITIONAL | 85.264% sampled hourly coverage; negative_lifetime_sensor_summary_review |
| Kopripada-Vashi, Navi Mumbai - MPCB | 12238330 | CONDITIONAL | 70.833% sampled hourly coverage; coverage_below_75_percent, negative_lifetime_sensor_summary_review |
| Bhayandar West, Mira-Bhayandar - MPCB | 12238339 | CONDITIONAL | 83.74% sampled hourly coverage; negative_lifetime_sensor_summary_review |
| Mindspace-Malad West, Mumbai - MPCB | 12238348 | CONDITIONAL | 75.203% sampled hourly coverage; negative_lifetime_sensor_summary_review |
| Chembur, Mumbai - MPCB | 12238384 | CONDITIONAL | 79.268% sampled hourly coverage; negative_lifetime_sensor_summary_review |
| Kherwadi_Bandra East, Mumbai - MPCB | 12238411 | CONDITIONAL | 84.654% sampled hourly coverage; negative_lifetime_sensor_summary_review |
| Sanpada, Navi Mumbai - MPCB | 12243949 | CONDITIONAL | 83.74% sampled hourly coverage; negative_lifetime_sensor_summary_review |
| Kandivali West, Mumbai - BMC | 12238585 | CONDITIONAL | 78.76% sampled hourly coverage; negative_lifetime_sensor_summary_review |
| Sewri, Mumbai - BMC | 12238594 | ACCEPT | 81.199% sampled hourly coverage; requires source agreement check |
| Ghatkopar, Mumbai - BMC | 12238603 | ACCEPT | 78.049% sampled hourly coverage; requires source agreement check |

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
- Request caps: 3 location pages, 5 pages per sensor endpoint, 60 sensors. All counts refer to bbox (72.75, 18.85, 73.05, 19.35), not an administrative Mumbai boundary.


## Replay-period spot check

A separate bounded May 2025 query covers the earliest replay period. It sampled only the four existing AirWindow PM2.5 sensors:

| Station | Sensor | May 2025 hourly coverage |
|---|---:|---:|
| Borivali East, Mumbai - IITM | 12236418 | 94.086% |
| Malad West, Mumbai - IITM | 12236426 | 94.086% |
| Byculla, Mumbai - BMC | 12238567 | 94.892% |
| Shivaji Nagar, Mumbai - BMC | 12238576 | 91.801% |

See `historical_2025_05/` for the complete bounded query outputs. Other replay months have not been audited.

## Source documentation

- [OpenAQ API v3](https://docs.openaq.org/api)
- [API key](https://docs.openaq.org/using-the-api/api-key)
- [Rate limits](https://docs.openaq.org/using-the-api/rate-limits)
- [Terms and attribution](https://docs.openaq.org/about/terms)
- [Hourly sensor measurements](https://docs.openaq.org/api/operations/sensor_hourly_measurements_get_v3_sensors__sensors_id__hours_get)
