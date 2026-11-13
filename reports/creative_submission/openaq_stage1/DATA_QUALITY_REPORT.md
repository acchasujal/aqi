# OpenAQ Mumbai data quality report

Status: **LIVE_BOUNDED_DISCOVERY**. Generated 2026-11-13T08:42:17.338152+00:00.

Requested UTC interval: 2026-10-01T00:00:00Z to 2026-11-11T00:00:00Z (end exclusive).

Discovered locations: 43; PM2.5 sensors: 57; 75%+ coverage candidates in sampled interval: 24.

Coverage is measured only in the requested interval. A truncated request cannot establish complete coverage. Values outside the interval are retained in raw data.

## Limitations

- AirWindow source IDs in Stations.csv are local leads until authenticated OpenAQ responses verify them.
- OpenAQ location coordinates may be rounded; coordinate proximity alone cannot prove physical or source identity.
- The requested 2026-10 to 2026-11 window does not cover all replay cases from 2025-05 onward; rerun for additional bounded historical intervals.
- OpenAQ's terms require OpenAQ and underlying-source attribution; review provider terms before any downstream publication or integration.
- OpenAQ precomputed hourly periods may start at :30 UTC; comparisons use their explicit period end against AirWindow's interval-end timestamps.
- Request caps: 3 location pages, 5 pages per sensor endpoint, 60 sensors. All counts refer to bbox (72.75, 18.85, 73.05, 19.35), not an administrative Mumbai boundary.

## Sensor 12236418 — Borivali East, Mumbai - IITM

Hourly records: 837; coverage: 85.061%; hourly duplicates: 0; raw duplicates: 0; median raw interval: 15.0 min; longest internal gap: 84.0 h; usable days: 38; unit: µg/m³; value range: 12.3–303.0.
Flags: none in sampled interval.

## Sensor 12236426 — Malad West, Mumbai - IITM

Hourly records: 839; coverage: 85.163%; hourly duplicates: 0; raw duplicates: 0; median raw interval: 15.0 min; longest internal gap: 85.0 h; usable days: 38; unit: µg/m³; value range: 7.76–735.0.
Flags: none in sampled interval.

## Sensor 12238567 — Byculla, Mumbai - BMC

Hourly records: 836; coverage: 84.858%; hourly duplicates: 0; raw duplicates: 0; median raw interval: 15.0 min; longest internal gap: 84.0 h; usable days: 38; unit: µg/m³; value range: 5.73–405.0.
Flags: none in sampled interval.

## Sensor 12238576 — Shivaji Nagar, Mumbai - BMC

Hourly records: 838; coverage: 85.061%; hourly duplicates: 0; raw duplicates: 0; median raw interval: 15.0 min; longest internal gap: 84.0 h; usable days: 38; unit: µg/m³; value range: 19.9–795.0.
Flags: negative_lifetime_sensor_summary_review.

## Sensor 39428 — Borivali East, Mumbai - IITM

Hourly records: 0; coverage: 0.0%; hourly duplicates: 0; raw duplicates: 0; median raw interval: None min; longest internal gap: None h; usable days: 0; unit: µg/m³; value range: None–None.
Flags: coverage_below_75_percent.

## Sensor 39454 — Malad West, Mumbai - IITM

Hourly records: 0; coverage: 0.0%; hourly duplicates: 0; raw duplicates: 0; median raw interval: None min; longest internal gap: None h; usable days: 0; unit: µg/m³; value range: None–None.
Flags: coverage_below_75_percent.

## Sensor 20079 — Powai, Mumbai - MPCB

Hourly records: 0; coverage: 0.0%; hourly duplicates: 0; raw duplicates: 0; median raw interval: None min; longest internal gap: None h; usable days: 0; unit: µg/m³; value range: None–None.
Flags: coverage_below_75_percent.

## Sensor 12235896 — Powai, Mumbai - MPCB

Hourly records: 438; coverage: 44.512%; hourly duplicates: 0; raw duplicates: 0; median raw interval: 15.0 min; longest internal gap: 236.0 h; usable days: 23; unit: µg/m³; value range: 2.58–141.0.
Flags: coverage_below_75_percent.

## Sensor 20033 — Siddharth Nagar-Worli, Mumbai - IITM

Hourly records: 0; coverage: 0.0%; hourly duplicates: 0; raw duplicates: 0; median raw interval: None min; longest internal gap: None h; usable days: 0; unit: µg/m³; value range: None–None.
Flags: coverage_below_75_percent, negative_lifetime_sensor_summary_review.

## Sensor 12236435 — Siddharth Nagar-Worli, Mumbai - IITM

Hourly records: 782; coverage: 79.37%; hourly duplicates: 0; raw duplicates: 0; median raw interval: 15.0 min; longest internal gap: 84.0 h; usable days: 36; unit: µg/m³; value range: 0.815–258.0.
Flags: none in sampled interval.

## Sensor 39404 — Bandra Kurla Complex, Mumbai - IITM

Hourly records: 0; coverage: 0.0%; hourly duplicates: 0; raw duplicates: 0; median raw interval: None min; longest internal gap: None h; usable days: 0; unit: µg/m³; value range: None–None.
Flags: coverage_below_75_percent.

## Sensor 39416 — Deonar, Mumbai - IITM

Hourly records: 0; coverage: 0.0%; hourly duplicates: 0; raw duplicates: 0; median raw interval: None min; longest internal gap: None h; usable days: 0; unit: µg/m³; value range: None–None.
Flags: coverage_below_75_percent.

## Sensor 389761 — Siddharth Nagar-Worli, Mumbai - IITM

Hourly records: 0; coverage: 0.0%; hourly duplicates: 0; raw duplicates: 0; median raw interval: None min; longest internal gap: None h; usable days: 0; unit: µg/m³; value range: None–None.
Flags: coverage_below_75_percent.

## Sensor 12235914 — Worli, Mumbai - MPCB

Hourly records: 756; coverage: 76.728%; hourly duplicates: 0; raw duplicates: 0; median raw interval: 15.0 min; longest internal gap: 84.0 h; usable days: 37; unit: µg/m³; value range: 13.5–357.0.
Flags: none in sampled interval.

## Sensor 12708246 — Bandra Kurla Complex, Mumbai - IITM

Hourly records: 566; coverage: 57.419%; hourly duplicates: 0; raw duplicates: 0; median raw interval: 15.0 min; longest internal gap: 84.0 h; usable days: 37; unit: µg/m³; value range: 1.0–640.0.
Flags: coverage_below_75_percent.

## Sensor 12236385 — Deonar, Mumbai - IITM

Hourly records: 792; coverage: 80.386%; hourly duplicates: 0; raw duplicates: 0; median raw interval: 15.0 min; longest internal gap: 84.0 h; usable days: 38; unit: µg/m³; value range: 1.81–586.0.
Flags: none in sampled interval.

## Sensor 12238375 — Bandra Kurla Complex, Mumbai - MPCB

Hourly records: 700; coverage: 71.037%; hourly duplicates: 0; raw duplicates: 0; median raw interval: 15.0 min; longest internal gap: 88.0 h; usable days: 35; unit: µg/m³; value range: 16.9–617.0.
Flags: coverage_below_75_percent, negative_lifetime_sensor_summary_review.

## Sensor 5404 — Navi Mumbai Municipal Corporation Airoli

Hourly records: 0; coverage: 0.0%; hourly duplicates: 0; raw duplicates: 0; median raw interval: None min; longest internal gap: None h; usable days: 0; unit: µg/m³; value range: None–None.
Flags: coverage_below_75_percent.

## Sensor 14806 — Pimpleshwar Mandir, Thane - MPCB

Hourly records: 0; coverage: 0.0%; hourly duplicates: 0; raw duplicates: 0; median raw interval: None min; longest internal gap: None h; usable days: 0; unit: µg/m³; value range: None–None.
Flags: coverage_below_75_percent.

## Sensor 20143 — Colaba, Mumbai - MPCB

Hourly records: 0; coverage: 0.0%; hourly duplicates: 0; raw duplicates: 0; median raw interval: None min; longest internal gap: None h; usable days: 0; unit: µg/m³; value range: None–None.
Flags: coverage_below_75_percent, negative_lifetime_sensor_summary_review.

## Sensor 12235926 — Colaba, Mumbai - MPCB

Hourly records: 732; coverage: 74.39%; hourly duplicates: 0; raw duplicates: 0; median raw interval: 15.0 min; longest internal gap: 84.0 h; usable days: 34; unit: µg/m³; value range: 7.0–91.0.
Flags: coverage_below_75_percent.

## Sensor 20046 — Mahape, Navi Mumbai - MPCB

Hourly records: 0; coverage: 0.0%; hourly duplicates: 0; raw duplicates: 0; median raw interval: None min; longest internal gap: None h; usable days: 0; unit: µg/m³; value range: None–None.
Flags: coverage_below_75_percent.

## Sensor 12235905 — Mahape, Navi Mumbai - MPCB

Hourly records: 800; coverage: 81.199%; hourly duplicates: 0; raw duplicates: 0; median raw interval: 15.0 min; longest internal gap: 84.0 h; usable days: 37; unit: µg/m³; value range: 8.47–104.0.
Flags: none in sampled interval.

## Sensor 19978 — Kurla, Mumbai - MPCB

Hourly records: 0; coverage: 0.0%; hourly duplicates: 0; raw duplicates: 0; median raw interval: None min; longest internal gap: None h; usable days: 0; unit: µg/m³; value range: None–None.
Flags: coverage_below_75_percent.

## Sensor 12235834 — Kurla, Mumbai - MPCB

Hourly records: 793; coverage: 80.488%; hourly duplicates: 0; raw duplicates: 0; median raw interval: 15.0 min; longest internal gap: 84.0 h; usable days: 37; unit: µg/m³; value range: 20.9–155.0.
Flags: none in sampled interval.

## Sensor 19981 — Chhatrapati Shivaji Intl. Airport (T2), Mumbai - MPCB

Hourly records: 0; coverage: 0.0%; hourly duplicates: 0; raw duplicates: 0; median raw interval: None min; longest internal gap: None h; usable days: 0; unit: µg/m³; value range: None–None.
Flags: coverage_below_75_percent.

## Sensor 12235860 — Chhatrapati Shivaji Intl. Airport (T2), Mumbai - MPCB

Hourly records: 211; coverage: 21.341%; hourly duplicates: 0; raw duplicates: 0; median raw interval: 15.0 min; longest internal gap: 10.0 h; usable days: 10; unit: µg/m³; value range: 18.0–54.9.
Flags: coverage_below_75_percent.

## Sensor 20087 — Borivali East, Mumbai - MPCB

Hourly records: 0; coverage: 0.0%; hourly duplicates: 0; raw duplicates: 0; median raw interval: None min; longest internal gap: None h; usable days: 0; unit: µg/m³; value range: None–None.
Flags: coverage_below_75_percent.

## Sensor 12252658 — Borivali East, Mumbai - MPCB

Hourly records: 689; coverage: 70.02%; hourly duplicates: 0; raw duplicates: 0; median raw interval: 15.0 min; longest internal gap: 89.0 h; usable days: 34; unit: µg/m³; value range: 16.4–98.7.
Flags: coverage_below_75_percent.

## Sensor 20096 — Sion, Mumbai - MPCB

Hourly records: 0; coverage: 0.0%; hourly duplicates: 0; raw duplicates: 0; median raw interval: None min; longest internal gap: None h; usable days: 0; unit: µg/m³; value range: None–None.
Flags: coverage_below_75_percent, negative_lifetime_sensor_summary_review.

## Sensor 12243930 — Sion, Mumbai - MPCB

Hourly records: 774; coverage: 78.557%; hourly duplicates: 0; raw duplicates: 0; median raw interval: 15.0 min; longest internal gap: 84.0 h; usable days: 36; unit: µg/m³; value range: 11.9–208.0.
Flags: none in sampled interval.

## Sensor 20251 — Vile Parle West, Mumbai - MPCB

Hourly records: 0; coverage: 0.0%; hourly duplicates: 0; raw duplicates: 0; median raw interval: None min; longest internal gap: None h; usable days: 0; unit: µg/m³; value range: None–None.
Flags: coverage_below_75_percent, negative_lifetime_sensor_summary_review.

## Sensor 12235851 — Vile Parle West, Mumbai - MPCB

Hourly records: 0; coverage: 0.0%; hourly duplicates: 0; raw duplicates: 0; median raw interval: None min; longest internal gap: None h; usable days: 0; unit: µg/m³; value range: None–None.
Flags: coverage_below_75_percent.

## Sensor 36447 — Bandra, Mumbai - MPCB

Hourly records: 0; coverage: 0.0%; hourly duplicates: 0; raw duplicates: 0; median raw interval: None min; longest internal gap: None h; usable days: 0; unit: µg/m³; value range: None–None.
Flags: coverage_below_75_percent.

## Sensor 23320 — Mumbai

Hourly records: 814; coverage: 82.724%; hourly duplicates: 0; raw duplicates: 0; median raw interval: 60.0 min; longest internal gap: 32.0 h; usable days: 41; unit: µg/m³; value range: 0.0–982.0.
Flags: negative_lifetime_sensor_summary_review.

## Sensor 39460 — Sector-19A Nerul, Navi Mumbai - IITM

Hourly records: 0; coverage: 0.0%; hourly duplicates: 0; raw duplicates: 0; median raw interval: None min; longest internal gap: None h; usable days: 0; unit: µg/m³; value range: None–None.
Flags: coverage_below_75_percent.

## Sensor 40571 — Chakala-Andheri East, Mumbai - IITM

Hourly records: 0; coverage: 0.0%; hourly duplicates: 0; raw duplicates: 0; median raw interval: None min; longest internal gap: None h; usable days: 0; unit: µg/m³; value range: None–None.
Flags: coverage_below_75_percent.

## Sensor 12442196 — Chakala-Andheri East, Mumbai - IITM

Hourly records: 793; coverage: 80.488%; hourly duplicates: 0; raw duplicates: 0; median raw interval: 15.0 min; longest internal gap: 84.0 h; usable days: 38; unit: µg/m³; value range: 10.3–558.0.
Flags: none in sampled interval.

## Sensor 40608 — Khindipada-Bhandup West, Mumbai - IITM

Hourly records: 0; coverage: 0.0%; hourly duplicates: 0; raw duplicates: 0; median raw interval: None min; longest internal gap: None h; usable days: 0; unit: µg/m³; value range: None–None.
Flags: coverage_below_75_percent.

## Sensor 12236394 — Khindipada-Bhandup West, Mumbai - IITM

Hourly records: 788; coverage: 79.98%; hourly duplicates: 0; raw duplicates: 0; median raw interval: 15.0 min; longest internal gap: 84.0 h; usable days: 38; unit: µg/m³; value range: 2.13–148.0.
Flags: none in sampled interval.

## Sensor 40641 — Mulund West, Mumbai - MPCB

Hourly records: 0; coverage: 0.0%; hourly duplicates: 0; raw duplicates: 0; median raw interval: None min; longest internal gap: None h; usable days: 0; unit: µg/m³; value range: None–None.
Flags: coverage_below_75_percent.

## Sensor 12236481 — Mulund West, Mumbai - MPCB

Hourly records: 764; coverage: 77.541%; hourly duplicates: 0; raw duplicates: 0; median raw interval: 15.0 min; longest internal gap: 84.0 h; usable days: 37; unit: µg/m³; value range: 10.3–222.0.
Flags: none in sampled interval.

## Sensor 40650 — Kandivali East, Mumbai - MPCB

Hourly records: 0; coverage: 0.0%; hourly duplicates: 0; raw duplicates: 0; median raw interval: None min; longest internal gap: None h; usable days: 0; unit: µg/m³; value range: None–None.
Flags: coverage_below_75_percent.

## Sensor 12236472 — Kandivali East, Mumbai - MPCB

Hourly records: 0; coverage: 0.0%; hourly duplicates: 0; raw duplicates: 0; median raw interval: None min; longest internal gap: None h; usable days: 0; unit: µg/m³; value range: None–None.
Flags: coverage_below_75_percent.

## Sensor 12235644 — Pimpleshwar Mandir, Thane - MPCB

Hourly records: 439; coverage: 44.614%; hourly duplicates: 0; raw duplicates: 0; median raw interval: 15.0 min; longest internal gap: 85.0 h; usable days: 36; unit: µg/m³; value range: 0.875–159.0.
Flags: coverage_below_75_percent.

## Sensor 12238258 — Kasarvadavali, Thane - MPCB

Hourly records: 818; coverage: 83.028%; hourly duplicates: 0; raw duplicates: 0; median raw interval: 15.0 min; longest internal gap: 84.0 h; usable days: 38; unit: µg/m³; value range: 1.31–412.0.
Flags: negative_lifetime_sensor_summary_review.

## Sensor 12238285 — Upvan Fort, Thane - MPCB

Hourly records: 734; coverage: 74.492%; hourly duplicates: 0; raw duplicates: 0; median raw interval: 15.0 min; longest internal gap: 84.0 h; usable days: 36; unit: µg/m³; value range: 3.19–927.0.
Flags: coverage_below_75_percent, negative_lifetime_sensor_summary_review.

## Sensor 12238321 — CBD Belapur, Belapur - MPCB

Hourly records: 840; coverage: 85.264%; hourly duplicates: 0; raw duplicates: 0; median raw interval: 15.0 min; longest internal gap: 84.0 h; usable days: 38; unit: µg/m³; value range: 0.06–378.0.
Flags: negative_lifetime_sensor_summary_review.

## Sensor 12238330 — Kopripada-Vashi, Navi Mumbai - MPCB

Hourly records: 698; coverage: 70.833%; hourly duplicates: 0; raw duplicates: 0; median raw interval: 15.0 min; longest internal gap: 84.0 h; usable days: 36; unit: µg/m³; value range: 2.93–535.0.
Flags: coverage_below_75_percent, negative_lifetime_sensor_summary_review.

## Sensor 12238339 — Bhayandar West, Mira-Bhayandar - MPCB

Hourly records: 825; coverage: 83.74%; hourly duplicates: 0; raw duplicates: 0; median raw interval: 15.0 min; longest internal gap: 84.0 h; usable days: 38; unit: µg/m³; value range: 2.47–228.0.
Flags: negative_lifetime_sensor_summary_review.

## Sensor 12238348 — Mindspace-Malad West, Mumbai - MPCB

Hourly records: 741; coverage: 75.203%; hourly duplicates: 0; raw duplicates: 0; median raw interval: 15.0 min; longest internal gap: 84.0 h; usable days: 38; unit: µg/m³; value range: 1.11–650.0.
Flags: negative_lifetime_sensor_summary_review.

## Sensor 12238384 — Chembur, Mumbai - MPCB

Hourly records: 781; coverage: 79.268%; hourly duplicates: 0; raw duplicates: 0; median raw interval: 15.0 min; longest internal gap: 84.0 h; usable days: 36; unit: µg/m³; value range: 3.01–948.0.
Flags: negative_lifetime_sensor_summary_review.

## Sensor 12238411 — Kherwadi_Bandra East, Mumbai - MPCB

Hourly records: 834; coverage: 84.654%; hourly duplicates: 0; raw duplicates: 0; median raw interval: 15.0 min; longest internal gap: 84.0 h; usable days: 38; unit: µg/m³; value range: 18.4–860.0.
Flags: negative_lifetime_sensor_summary_review.

## Sensor 12243949 — Sanpada, Navi Mumbai - MPCB

Hourly records: 824; coverage: 83.74%; hourly duplicates: 0; raw duplicates: 0; median raw interval: 15.0 min; longest internal gap: 84.0 h; usable days: 38; unit: µg/m³; value range: 0.01–495.0.
Flags: negative_lifetime_sensor_summary_review.

## Sensor 12238585 — Kandivali West, Mumbai - BMC

Hourly records: 776; coverage: 78.76%; hourly duplicates: 0; raw duplicates: 0; median raw interval: 15.0 min; longest internal gap: 84.0 h; usable days: 37; unit: µg/m³; value range: 0.43–673.0.
Flags: negative_lifetime_sensor_summary_review.

## Sensor 12238594 — Sewri, Mumbai - BMC

Hourly records: 800; coverage: 81.199%; hourly duplicates: 0; raw duplicates: 0; median raw interval: 15.0 min; longest internal gap: 84.0 h; usable days: 38; unit: µg/m³; value range: 3.53–593.0.
Flags: none in sampled interval.

## Sensor 12238603 — Ghatkopar, Mumbai - BMC

Hourly records: 769; coverage: 78.049%; hourly duplicates: 0; raw duplicates: 0; median raw interval: 15.0 min; longest internal gap: 84.0 h; usable days: 38; unit: µg/m³; value range: 2.5–449.0.
Flags: none in sampled interval.

OpenAQ does not expose a verified first-publication timestamp in these responses, so measurement reporting latency cannot be calculated reliably.
