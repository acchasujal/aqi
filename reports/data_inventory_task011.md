# Task 011 Data Inventory & Forecast Horizon Audit

## 1. Challenge Dataset Overview

- **Train.csv Rows:** 48,133
- **Train Range:** `2025-02-19T03:00:00+05:30` to `2026-11-09T07:00:00+05:30`
- **Test.csv Rows:** 2,592
- **SampleSubmission.csv Rows:** 2,592 (ID Order Matches Test 100%: `True`)

## 2. Station-by-Station Hourly Coverage & Missingness in Train.csv

| location_id | station_name | row_count | expected_hours | missing_hours | coverage_pct | longest_gap_hours | latest_train_end | pm25_min | pm25_mean | pm25_median | pm25_std | pm25_p90 | pm25_max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 11606 | Borivali East, Mumbai - IITM | 12172 | 15076 | 2904 | 80.74 | 243 | 2026-11-09T06:00:00+05:30 | 0.00 | 48.05 | 26.61 | 878.79 | 63.87 | 75203.52 |
| 11611 | Malad West, Mumbai - IITM | 12276 | 15077 | 2801 | 81.42 | 243 | 2026-11-09T07:00:00+05:30 | 0.00 | 25.96 | 16.43 | 28.65 | 61.78 | 718.23 |
| 3409510 | Byculla, Mumbai - BMC | 11620 | 15075 | 3455 | 77.08 | 243 | 2026-11-09T05:00:00+05:30 | 0.00 | 26.95 | 17.96 | 44.08 | 59.16 | 3320.63 |
| 3409511 | Shivaji Nagar, Mumbai - BMC | 12065 | 15077 | 3012 | 80.02 | 243 | 2026-11-09T07:00:00+05:30 | 0.00 | 74.80 | 24.68 | 2457.94 | 64.60 | 241587.56 |

## 3. Exact Private Target Leads (Interval-End Convention)

Lead defined as `lead_hours = target_end_ist - last_eligible_train_timestamp`:

| location_id | station_name | last_train_end | earliest_target_end | latest_target_end | min_lead_hours | max_lead_hours | private_target_count |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 11606 | Borivali East, Mumbai - IITM | 2026-11-09T06:00:00+05:30 | 2026-11-11T00:00:00+05:30 | 2026-11-12T23:00:00+05:30 | 42.00 | 89.00 | 48 |
| 11611 | Malad West, Mumbai - IITM | 2026-11-09T07:00:00+05:30 | 2026-11-11T00:00:00+05:30 | 2026-11-12T23:00:00+05:30 | 41.00 | 88.00 | 48 |
| 3409510 | Byculla, Mumbai - BMC | 2026-11-09T05:00:00+05:30 | 2026-11-11T00:00:00+05:30 | 2026-11-12T23:00:00+05:30 | 43.00 | 90.00 | 48 |
| 3409511 | Shivaji Nagar, Mumbai - BMC | 2026-11-09T07:00:00+05:30 | 2026-11-11T00:00:00+05:30 | 2026-11-12T23:00:00+05:30 | 41.00 | 88.00 | 48 |

### Lead Summary:
- Minimum lead to first private interval end: **41 hours**
- Maximum lead to last private interval end: **90 hours**
