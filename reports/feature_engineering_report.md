# Feature Engineering Report and Feature Registry

**Date:** 2026-11-08  
**Author:** Senior Data Scientist, ML Engineer, and Software Architect  
**Modules:** `src/mumbai_pm25/features/` (`calendar.py`, `pm_history.py`, `seasonal.py`, `spatial.py`, `pipeline.py`)  
**Status:** Implemented, Tested, and Verified

---

## 1. Feature Architecture Overview

All features are extracted relative to an **explicit, frozen forecast origin snapshot**:
- `pm_history_cutoff`: latest timestamp permitted into feature computation.
- No feature ever peeks past `pm_history_cutoff`.
- Features are grouped by responsibility into five distinct groups:
  - **Group A:** Recent Pollution State
  - **Group B:** Pollution Dynamics & Trajectory
  - **Group C:** Temporal & Cyclical Structures
  - **Group D:** Historical Seasonal Climatology (2024 Archive)
  - **Group E:** Spatial & Citywide Multi-Station Context

---

## 2. Comprehensive Feature Registry

| Group | Feature Name | Definition / Formula | Source | Forecast Origin Availability | Missing-Value Behavior | Intended Purpose |
|---|---|---|---|---|---|---|
| **A** | `latest_pm25` | Most recent non-null PM2.5 reading | `Train.csv` | Prior to cutoff | Falls back to station historical median | Direct autoregressive level anchor |
| **A** | `obs_age_hours` | Elapsed hours from last observation end to cutoff | `Train.csv` | Prior to cutoff | Set to 999.0 if no history | Quantifies feature staleness |
| **A** | `obs_count_24`, `72`, `168` | Non-null reading counts in past 24h, 72h, 168h | `Train.csv` | Prior to cutoff | 0.0 if empty | Sensor data density / reliability |
| **A** | `coverage_72` | `obs_count_72 / 72.0` | `Train.csv` | Prior to cutoff | 0.0 if empty | Observation coverage ratio |
| **A** | `median_6`, `12`, `24`, `48`, `72`, `168` | Rolling median in elapsed $W$-hour window | `Train.csv` | Prior to cutoff | Falls back to latest available reading | Multi-scale robust baseline level |
| **A** | `mean_24`, `72`, `168` | Rolling mean in elapsed $W$-hour window | `Train.csv` | Prior to cutoff | Falls back to latest available reading | Smoothed particulate concentration |
| **A** | `min_24`, `max_24` | Min and Max PM2.5 in past 24 hours | `Train.csv` | Prior to cutoff | Falls back to latest available reading | Short-term concentration range |
| **A** | `std_24` | Standard deviation in past 24 hours | `Train.csv` | Prior to cutoff | 0.0 if count $\le 1$ | Short-term dispersion |
| **A** | `iqr_72` | 75th percentile minus 25th percentile in 72h | `Train.csv` | Prior to cutoff | 0.0 if count $< 4$ | Robust spread metric |
| **A** | `ewm_24`, `ewm_72` | Exponentially weighted average (half-life 12h / 24h) | `Train.csv` | Prior to cutoff | Falls back to latest available reading | Recency-weighted level tracking |
| **B** | `delta_median_24_48` | `median_24 - median_prev24` | `Train.csv` | Prior to cutoff | 0.0 if insufficient data | Daily rate of change (rising/falling) |
| **B** | `ratio_median_24_168` | `median_24 / (median_168 + 1.0)` | `Train.csv` | Prior to cutoff | 1.0 if empty | Short-term vs. weekly relative anomaly |
| **B** | `volatility_24` | `std_24 / (mean_24 + 1.0)` | `Train.csv` | Prior to cutoff | 0.0 if empty | Coefficient of variation |
| **B** | `is_rising_trend` | $1$ if `median_24 > median_72` else $0$ | `Train.csv` | Prior to cutoff | 0.0 if empty | Directional momentum indicator |
| **B** | `linear_slope_24` | OLS slope $\beta_1$ of PM2.5 over past 24 hours | `Train.csv` | Prior to cutoff | 0.0 if count $< 3$ | Rate of pollution acceleration |
| **C** | `hour` | Target hour of day ($0 \dots 23$) | `Test.csv` / Target index | Exact at prediction time | Deterministic | Diurnal schedule |
| **C** | `weekday` | Day of week ($0 \dots 6$) | `Test.csv` / Target index | Exact at prediction time | Deterministic | Weekly traffic/workday cycle |
| **C** | `month` | Calendar month ($1 \dots 12$) | `Test.csv` / Target index | Exact at prediction time | Deterministic | Macro seasonal position |
| **C** | `day_of_year` | Day of year ($1 \dots 366$) | `Test.csv` / Target index | Exact at prediction time | Deterministic | Annual seasonal cycle |
| **C** | `hour_sin`, `hour_cos` | $\sin(2\pi h / 24)$, $\cos(2\pi h / 24)$ | `Test.csv` / Target index | Exact at prediction time | Deterministic | Continuous 24h cycle |
| **C** | `weekday_sin`, `weekday_cos` | $\sin(2\pi w / 7)$, $\cos(2\pi w / 7)$ | `Test.csv` / Target index | Exact at prediction time | Deterministic | Continuous weekly cycle |
| **C** | `doy_sin`, `doy_cos` | $\sin(2\pi d / 365.25)$, $\cos(2\pi d / 365.25)$ | `Test.csv` / Target index | Exact at prediction time | Deterministic | Continuous annual cycle |
| **C** | `horizon_hours` | Target forecast horizon ($1 \dots 48$) | `Test.csv` / Target index | Exact at prediction time | Deterministic | Decay & uncertainty scaling |
| **C** | `station_id` | Categorical integer station code | `Stations.csv` | Static | Exact match | Station identity for tree algorithms |
| **C** | `station_<ID>` | One-hot indicator per station | `Stations.csv` | Static | Exact match | Linear & tree splits |
| **D** | `hist24_same_hour_mean` | 2024 same-station mean for target hour $\pm 14$ days | `History_Mumbai_2024.csv.gz` | Available at submission | NaN if coverage $< 3$ | Leap-year normalized seasonal prior |
| **D** | `hist24_month_hour_mean` | 2024 same-station mean for target month & hour | `History_Mumbai_2024.csv.gz` | Available at submission | NaN if coverage $< 3$ | Monthly diurnal profile |
| **D** | `hist24_coverage` | Number of unique observed hours in 2024 window | `History_Mumbai_2024.csv.gz` | Available at submission | 0 if missing | Reliability of historical climatology |
| **D** | `hist24_has_prior` | Indicator whether `hist24_same_hour_mean` is finite | `History_Mumbai_2024.csv.gz` | Available at submission | 0.0 if missing | Missingness indicator for tree split |
| **D** | `hist24_ratio_to_recent` | `hist24_same_hour_mean / (median_72 + 1.0)` | Derived | Available at submission | 1.0 if missing | Prior-to-recent calibration ratio |
| **E** | `city_median_pm25` | Median of latest observations across 4 stations | `Train.csv` | Prior to cutoff | Falls back to default 40.0 | Citywide background air quality |
| **E** | `city_mean_pm25` | Mean of latest observations across 4 stations | `Train.csv` | Prior to cutoff | Falls back to default 40.0 | Regional particulate load |
| **E** | `city_dispersion` | `city_std / (city_mean + 1.0)` | `Train.csv` | Prior to cutoff | 0.0 if missing | Cross-city spatial homogeneity |
| **E** | `station_diff_from_city` | `station.latest_pm25 - city_median_pm25` | Derived | Prior to cutoff | 0.0 if missing | Station micro-climate offset |
| **E** | `station_ratio_to_city` | `station.latest_pm25 / (city_median_pm25 + 1.0)` | Derived | Prior to cutoff | 1.0 if missing | Station relative local severity |
| **E** | `other_stations_mean_pm25` | Mean of latest observations of the *other 3* stations | `Train.csv` | Prior to cutoff | Falls back to station level | Leave-one-out spatial background |

---

## 3. Leakage Verification

All features were evaluated against information leakage constraints:
1.  **Future Target Independence:** For every fold, target hour observations from hour 1 to hour 48 are completely excluded from feature generation.
2.  **Explicit Clock Gating:** Features are computed exclusively from `history.loc[history.index < pm_history_cutoff]`.
3.  **Timestamp Reindexing:** Temporal grids are indexed by complete hourly `target_start`. Missing hours remain `NaN` and are never imputed as zero.
