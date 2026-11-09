# Task 011 Historical Archive Source-Series & Alignment Audit

## 1. 2024 Archive Structure

- **Total Rows:** 216,472
- **CPCB CAAQS Rows:** 208,043
- **Unique Series Count:** 29
- **Timestamp Convention:** All CPCB CAAQS observations are cleanly aligned at minute `:00` IST.

## 2. Overlapping Source Series Analysis

### Borivali East (`site_5113` vs. `site_5400`):
- **Co-occurring Hours:** 6,738
- **Median Absolute Difference:** 14.39 µg/m³
- **Mean Absolute Difference:** 22.14 µg/m³
- **Observation:** Both series monitor Borivali East simultaneously but exhibit substantial sensor level offsets (median 15.9 vs. 35.0 µg/m³). They cannot be treated as independent measurements.

### Malad West (`site_5102` vs. `site_5402`):
- **Co-occurring Hours:** 5,145
- **Median Absolute Difference:** 14.50 µg/m³
- **Mean Absolute Difference:** 23.90 µg/m³
- **Observation:** Significant variance exists between collocated monitors. `site_5807` (Mindspace-Malad) is strictly excluded as an MPCB station in a different microclimate.
