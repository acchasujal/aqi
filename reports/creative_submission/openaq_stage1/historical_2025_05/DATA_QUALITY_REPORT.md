# OpenAQ Mumbai data quality report

Status: **LIVE_BOUNDED_DISCOVERY**. Generated 2026-11-13T08:41:37.017643+00:00.

Requested UTC interval: 2025-05-01T00:00:00Z to 2025-06-01T00:00:00Z (end exclusive).

Discovered locations: 43; PM2.5 sensors: 57; 75%+ coverage candidates in sampled interval: 4.

Coverage is measured only in the requested interval. A truncated request cannot establish complete coverage. Values outside the interval are retained in raw data.

## Limitations

- AirWindow source IDs in Stations.csv are local leads until authenticated OpenAQ responses verify them.
- OpenAQ location coordinates may be rounded; coordinate proximity alone cannot prove physical or source identity.
- The requested 2026-10 to 2026-11 window does not cover all replay cases from 2025-05 onward; rerun for additional bounded historical intervals.
- OpenAQ's terms require OpenAQ and underlying-source attribution; review provider terms before any downstream publication or integration.
- OpenAQ precomputed hourly periods may start at :30 UTC; comparisons use their explicit period end against AirWindow's interval-end timestamps.
- Request caps: 3 location pages, 5 pages per sensor endpoint, 4 sensors. All counts refer to bbox (72.75, 18.85, 73.05, 19.35), not an administrative Mumbai boundary.
- Only first 4 PM2.5 sensors downloaded; remaining sensors are cataloged but unassessed.

## Sensor 12236418 — Borivali East, Mumbai - IITM

Hourly records: 701; coverage: 94.086%; hourly duplicates: 0; raw duplicates: 0; median raw interval: 15.0 min; longest internal gap: 24.0 h; usable days: 31; unit: µg/m³; value range: 0.0–71.7.
Flags: none in sampled interval.

## Sensor 12236426 — Malad West, Mumbai - IITM

Hourly records: 701; coverage: 94.086%; hourly duplicates: 0; raw duplicates: 0; median raw interval: 15.0 min; longest internal gap: 25.0 h; usable days: 31; unit: µg/m³; value range: 0.0–112.0.
Flags: none in sampled interval.

## Sensor 12238567 — Byculla, Mumbai - BMC

Hourly records: 707; coverage: 94.892%; hourly duplicates: 0; raw duplicates: 0; median raw interval: 15.0 min; longest internal gap: 25.0 h; usable days: 31; unit: µg/m³; value range: 0.0925–59.3.
Flags: none in sampled interval.

## Sensor 12238576 — Shivaji Nagar, Mumbai - BMC

Hourly records: 684; coverage: 91.801%; hourly duplicates: 0; raw duplicates: 0; median raw interval: 15.0 min; longest internal gap: 48.0 h; usable days: 30; unit: µg/m³; value range: 0.0–347.0.
Flags: negative_lifetime_sensor_summary_review.

OpenAQ does not expose a verified first-publication timestamp in these responses, so measurement reporting latency cannot be calculated reliably.
