# Data Quality, Schema, and Outlier Audit Report

**Date:** 2026-11-08  
**Author:** Senior Data Scientist, ML Engineer, and Software Architect  
**Scope:** Raw Challenge Inputs, Historical Archives, and Target Distributions  
**Status:** Complete Forensic Assessment

---

## 1. Challenge Dataset Schema & Integrity

### A. Train.csv
- **Total Rows:** 47,849
- **Columns:** `location_id`, `station_name`, `sensor_id`, `timestamp_ist`, `pm25`, `mean`, `count`, `available_at`, `series_id`, `flag_high_1000`
- **Time Range:** `2025-02-19 03:00:00+05:30` to `2026-11-02 23:00:00+05:30` (622 calendar days)
- **Time Semantics:** `timestamp_ist` represents the **end** of the 1-hour observation interval.
  - Aligned interval start: `target_start = timestamp_ist - pd.Timedelta(hours=1)`.
- **Column Integrity Audits:**
  - `mean`: Confirmed identical to `pm25` on 100.0% of rows (`(train['mean'] == train['pm25']).all() == True`). Duplicate column; dropped.
  - `count`: Integer counts (3 or 4 valid 15-minute readings per hour); absent from `Test.csv`.
  - `available_at`: Ingestion timestamp from source; not verified public release time.
  - `series_id`: Constant identifier per station-source; non-predictive metadata.
  - `flag_high_1000`: Boolean diagnostic flag; non-predictive metadata.

### B. Test.csv
- **Total Rows:** 2,592 (exactly 648 rows $\times$ 4 stations = 27 days $\times$ 24 hours).
- **Columns:** `ID`, `location_id`, `sensor_id`, `target_start_ist`, `target_end_ist`, `scoring_block`, `unit`
- **Time Range:** `2026-10-22 00:00:00+05:30` to `2026-11-20 23:00:00+05:30`.
- **Time Semantics:** `target_start_ist` is already the interval start; interval is exactly 1 hour.
- **Rule Enforcement:** `scoring_block` and `ID` token fragments are administrative metadata; never used as features.

### C. Stations.csv
- **Target Stations (4 CAAQMS Monitors):**
  1. `11606` / sensor `12236418`: Borivali East (Lat: 19.232410, Lon: 72.868950)
  2. `11611` / sensor `12236426`: Malad West (Lat: 19.197090, Lon: 72.822040)
  3. `3409510` / sensor `12238567`: Byculla (Lat: 18.976700, Lon: 72.838000)
  4. `3409511` / sensor `12238576`: Shivaji Nagar (Lat: 19.060498, Lon: 72.923356)

---

## 2. Target Distribution and Extreme Outliers

The PM2.5 distribution in Mumbai exhibits intense right-skewness, typical of severe episodic particulate pollution combined with potential sensor anomalies.

### Quantile Distribution (µg/m³)

| Metric | Overall | Borivali East | Malad West | Byculla | Shivaji Nagar |
|---|---|---|---|---|---|
| **Min** | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| **25th percentile** | 24.30 | 22.00 | 25.00 | 21.00 | 31.00 |
| **50th percentile (Median)** | 42.30 | 38.00 | 44.00 | 37.00 | 54.00 |
| **75th percentile** | 68.10 | 60.00 | 69.00 | 60.00 | 88.00 |
| **95th percentile** | 129.00 | 115.00 | 128.00 | 119.00 | 170.00 |
| **99th percentile** | 265.40 | 224.00 | 247.00 | 239.00 | 385.00 |
| **Max** | 241,587.56 | 1,440.00 | 1,280.00 | 999.00 | 241,587.56 |

### Extreme Outliers (>1,000 µg/m³)
- Exactly **19 observations** in `Train.csv` exceed 1,000 µg/m³.
- The single largest value is **241,587.56 µg/m³** at Shivaji Nagar (`2025-11-04 14:00:00+05:30`).
- Because evaluation uses RMSE:
  - An error on $241,587\ \mu\text{g/m}^3$ squares to $5.8 \times 10^{10}$, completely overwhelming thousands of normal hours.
- **Handling Policy:**
  - **Validation Targets:** MUST NEVER be clipped, winsorized, or removed. Official evaluation includes all rows.
  - **Training Targets:** Supervised models trained on raw target with squared error loss easily destabilize. Target transformations ($\log(1+y)$, $\sqrt{y}$) and robust regression losses (Huber, MAE) are mandatory to prevent gradient explosion.

---

## 3. Station Missingness and Gap Characteristics

Because air quality monitoring stations experience periodic power cuts, calibration cycles, and maintenance, data coverage is not uniform across the 14,924 theoretical hours of the training grid.

### Station Missingness Profile

| Station | Location ID | Valid Hours | Total Hours | Coverage % | Longest Gap (Hours) |
|---|---|---|---|---|---|
| **Borivali East** | 11606 | 12,014 | 14,925 | 80.5% | 286h (~12 days) |
| **Malad West** | 11611 | 11,892 | 14,925 | 79.7% | 241h (~10 days) |
| **Byculla** | 3409510 | 11,987 | 14,925 | 80.3% | 215h (~9 days) |
| **Shivaji Nagar** | 3409511 | 11,956 | 14,925 | 80.1% | 264h (~11 days) |

- **Impact on Forecasting:**
  - When forecasting with reporting gaps of 48h to 120h, missing hours in the recent window exacerbate staleness.
  - Feature engineering must explicitly encode observation age, observation counts within recent windows (6h, 12h, 24h, 72h, 168h), and provide age-aware fallbacks.

---

## 4. Auxiliary Archives in AdditionalHistory.zip

| File Member | Records | Status | Findings |
|---|---|---|---|
| `History_Mumbai_2024.csv.gz` | 216,472 | **Accepted (cpcb_caaqm)** | Contains high-quality 2024 hourly data for all 4 target stations. Pre-aggregated to eliminate dual-sensor duplicate timestamps. |
| `Other_Mumbai_Stations_2025_2026.csv.gz` | 158,320 | **Conditionally Accepted** | 14 auxiliary Mumbai stations through 16 October 2026. Useful for citywide spatial correlation and background pollution levels. Stale for November private period. |
| `History_Mumbai_2018_2020.csv.gz` | ~180,000 | **Rejected** | Pre-2020 CPCB stations. Different sensor models and calibration standards; strong temporal distribution shift. |
| `Legacy_Observations_2020_2022.csv.gz` | ~45,000 | **Rejected** | Irregular OpenAQ readings covering only 2 stations with large multi-month gaps. |
| `XKDR_All_Stations.csv` / `Kaggle_All_Stations.csv` | - | **Reference Metadata** | Metadata lookups for station coordinates and agency ownership. |

---

## 5. Preprocessing and Feature Engineering Directives

1.  **Strict Hourly Timeline Indexing:** Missing hours remain `NaN` during rolling aggregation; never filled with zeros.
2.  **Dual-Sensor IITM Aggregation:** Borivali East IITM (site 5113, site 5400) and Malad West IITM (site 5102, site 5402) are aggregated per station-hour using mean aggregation before computing seasonal profiles.
3.  **Leap-Year Normalization:** 2024 day-of-year is normalized ($d - 1$ post-Feb 28, Feb 29 = 59.5) to align calendar dates with 2026.
4.  **Transformation Pipeline:** Train supervised models on raw, $\log(1+y)$, and $\sqrt{y}$ targets; invert predictions back to original $\mu\text{g/m}^3$ and enforce non-negativity ($\max(0, \hat{y})$).
