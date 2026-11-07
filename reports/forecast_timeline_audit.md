# Forecast Timeline, Clocks, and Horizon Audit

## Executive Summary

This document performs an independent audit of the forecasting information clocks, lead-time horizon definitions, and timestamp independence for the **Google Mumbai Data Challenge: Air Quality Mapping & Forecasting by Google**.

The private evaluation period is fixed: **11 November 00:00 IST to 12 November 23:00 IST (48 consecutive hours $\times$ 4 stations = 192 prediction rows)**.

---

## 1. Information Clocks & Independence

Four distinct clocks govern the forecasting system. They must never be conflated:

```
Timeline (Asia/Kolkata, UTC+05:30):
========================================================================================================================
... [PM History Cutoff] ---------> [Forecast Issue Time / Model Run] ---------> [Private Block Start] ---> [Private Block End]
    2026-11-09 23:00                2026-11-10 12:00                             2026-11-11 00:00          2026-11-12 23:00
    (interval end of                (wall clock at submission                    (target_start h=1)        (target_start h=48)
     latest observed PM)             generation deadline)
========================================================================================================================
       |<---------------- 13 hours --------------->|<--------------- 12 hours -------------->|
       |<--------------------------------- Total PM Reporting Lag: 25 to 72 hours ---------------------------------->|
```

### Definitions:

1. **`pm_history_cutoff` (Data Snapshot Time):**
   - The timestamp marking the **interval end** of the latest eligible ground-truth PM2.5 observation available in `Train.csv`.
   - In the current repository release, `pm_history_cutoff` is strictly **`2026-11-02 23:00:00+05:30`**.
   - Upon the advertised 10 November 09:00 IST training refresh, `pm_history_cutoff` is expected to advance to approximately **`2026-11-09 23:00:00+05:30`** (assuming standard ~24h CPCB CAAQMS publishing lag).
   - **Independence:** Decoupled from the wall clock; determined solely by data provider ingestion latency.

2. **`forecast_issue_time` / `model_run_time`:**
   - The operational decision time and wall clock when the model inference pipeline is executed and the submission file is sealed.
   - For final submission on 10 November, `--model-run-time` is configured as **`2026-11-10T12:00:00+05:30`** (or prior to 23:59:59 IST).
   - **Independence:** Must satisfy `forecast_issue_time >= pm_history_cutoff`.

3. **`target_start` & `target_end` (Target Interval):**
   - Start and end of the hourly PM2.5 measurement interval in `Test.csv`.
   - Private evaluation window: `2026-11-11 00:00:00+05:30` to `2026-11-12 23:00:00+05:30`.
   - Interval end of the final private target hour: `2026-11-13 00:00:00+05:30`.

4. **`horizon_hours` (Forecast Horizon / Lead Time):**
   - In the competition baseline models and feature pipelines, `horizon_hours` represents the **diurnal sequence position within the 48-hour evaluation block ($1 \dots 48$)**.
   - From operational issue time (`2026-11-10 12:00:00+05:30`), the **physical lead time** to target interval starts spans **12.0 to 59.0 hours** (or **13.0 to 60.0 hours** to interval ends).
   - Relative to the expected refreshed `pm_history_cutoff` (`2026-11-09 23:00:00+05:30`), the **effective PM reporting lag** is **25.0 to 72.0 hours**.

---

## 2. Investigation of Horizon Bug in `forecast.py`

### Finding
In `src/mumbai_pm25/forecast.py` line 284, `test_df["horizon_hours"]` was previously calculated as:
```python
test_df["horizon_hours"] = (
    (test_df["target_start"] - test_df["target_start"].min()).dt.total_seconds() / 3600.0 + 1.0
).astype(int)
```
Because `test.target_start.min()` is `2026-10-22 00:00:00+05:30` (the start of the 2,592-row static template), `horizon_hours` for the private window (11–12 November) was computed as **481 to 528**!

Meanwhile, all supervised models during training were trained on fixed 48-hour blocks where `horizon_hours` was **1 to 48**.

Passing out-of-distribution values ($481 \dots 528$) forced decision tree models (CatBoost, LightGBM) to clamp to extreme rightmost leaf nodes, compressing prediction standard deviation (from 4.77 to 3.25).

### Correction
`horizon_hours` must represent the aligned index within the 48-hour target block:
$$\text{horizon\_hours} = \left(\frac{\text{target\_start} - \text{block\_start}}{3600}\right) + 1 \in [1, 48]$$
This guarantees that test-time feature matrices are strictly in-distribution with the training feature distributions.

---

## 3. Complete Horizon & Lead-Time Timeline Table (All 48 Private Hours $\times$ 4 Stations)

*Note: Clocks assume final inference execution at `issue_time = 2026-11-10 12:00:00+05:30` with expected refreshed cutoff `2026-11-09 23:00:00+05:30`. Identical across all 4 stations: Borivali East (11606), Malad West (11611), Byculla (3409510), Shivaji Nagar (3409511).*

| Block Hour ($h$) | Target Start (IST) | Target End (IST) | Operational Lead Time from Issuance (hours) | Effective Lag from PM Cutoff (hours) | Provisional Lag from Current Cutoff (hours) |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | 2026-11-11 00:00 | 2026-11-11 01:00 | 12.0 (end: 13.0) | 25.0 | 193.0 |
| **2** | 2026-11-11 01:00 | 2026-11-11 02:00 | 13.0 (end: 14.0) | 26.0 | 194.0 |
| **3** | 2026-11-11 02:00 | 2026-11-11 03:00 | 14.0 (end: 15.0) | 27.0 | 195.0 |
| **4** | 2026-11-11 03:00 | 2026-11-11 04:00 | 15.0 (end: 16.0) | 28.0 | 196.0 |
| **5** | 2026-11-11 04:00 | 2026-11-11 05:00 | 16.0 (end: 17.0) | 29.0 | 197.0 |
| **6** | 2026-11-11 05:00 | 2026-11-11 06:00 | 17.0 (end: 18.0) | 30.0 | 198.0 |
| **7** | 2026-11-11 06:00 | 2026-11-11 07:00 | 18.0 (end: 19.0) | 31.0 | 199.0 |
| **8** | 2026-11-11 07:00 | 2026-11-11 08:00 | 19.0 (end: 20.0) | 32.0 | 200.0 |
| **9** | 2026-11-11 08:00 | 2026-11-11 09:00 | 20.0 (end: 21.0) | 33.0 | 201.0 |
| **10** | 2026-11-11 09:00 | 2026-11-11 10:00 | 21.0 (end: 22.0) | 34.0 | 202.0 |
| **11** | 2026-11-11 10:00 | 2026-11-11 11:00 | 22.0 (end: 23.0) | 35.0 | 203.0 |
| **12** | 2026-11-11 11:00 | 2026-11-11 12:00 | 23.0 (end: 24.0) | 36.0 | 204.0 |
| **13** | 2026-11-11 12:00 | 2026-11-11 13:00 | 24.0 (end: 25.0) | 37.0 | 205.0 |
| **14** | 2026-11-11 13:00 | 2026-11-11 14:00 | 25.0 (end: 26.0) | 38.0 | 206.0 |
| **15** | 2026-11-11 14:00 | 2026-11-11 15:00 | 26.0 (end: 27.0) | 39.0 | 207.0 |
| **16** | 2026-11-11 15:00 | 2026-11-11 16:00 | 27.0 (end: 28.0) | 40.0 | 208.0 |
| **17** | 2026-11-11 16:00 | 2026-11-11 17:00 | 28.0 (end: 29.0) | 41.0 | 209.0 |
| **18** | 2026-11-11 17:00 | 2026-11-11 18:00 | 29.0 (end: 30.0) | 42.0 | 210.0 |
| **19** | 2026-11-11 18:00 | 2026-11-11 19:00 | 30.0 (end: 31.0) | 43.0 | 211.0 |
| **20** | 2026-11-11 19:00 | 2026-11-11 20:00 | 31.0 (end: 32.0) | 44.0 | 212.0 |
| **21** | 2026-11-11 20:00 | 2026-11-11 21:00 | 32.0 (end: 33.0) | 45.0 | 213.0 |
| **22** | 2026-11-11 21:00 | 2026-11-11 22:00 | 33.0 (end: 34.0) | 46.0 | 214.0 |
| **23** | 2026-11-11 22:00 | 2026-11-11 23:00 | 34.0 (end: 35.0) | 47.0 | 215.0 |
| **24** | 2026-11-11 23:00 | 2026-11-12 00:00 | 35.0 (end: 36.0) | 48.0 | 216.0 |
| **25** | 2026-11-12 00:00 | 2026-11-12 01:00 | 36.0 (end: 37.0) | 49.0 | 217.0 |
| **26** | 2026-11-12 01:00 | 2026-11-12 02:00 | 37.0 (end: 38.0) | 50.0 | 218.0 |
| **27** | 2026-11-12 02:00 | 2026-11-12 03:00 | 38.0 (end: 39.0) | 51.0 | 219.0 |
| **28** | 2026-11-12 03:00 | 2026-11-12 04:00 | 39.0 (end: 40.0) | 52.0 | 220.0 |
| **29** | 2026-11-12 04:00 | 2026-11-12 05:00 | 40.0 (end: 41.0) | 53.0 | 221.0 |
| **30** | 2026-11-12 05:00 | 2026-11-12 06:00 | 41.0 (end: 42.0) | 54.0 | 222.0 |
| **31** | 2026-11-12 06:00 | 2026-11-12 07:00 | 42.0 (end: 43.0) | 55.0 | 223.0 |
| **32** | 2026-11-12 07:00 | 2026-11-12 08:00 | 43.0 (end: 44.0) | 56.0 | 224.0 |
| **33** | 2026-11-12 08:00 | 2026-11-12 09:00 | 44.0 (end: 45.0) | 57.0 | 225.0 |
| **34** | 2026-11-12 09:00 | 2026-11-12 10:00 | 45.0 (end: 46.0) | 58.0 | 226.0 |
| **35** | 2026-11-12 10:00 | 2026-11-12 11:00 | 46.0 (end: 47.0) | 59.0 | 227.0 |
| **36** | 2026-11-12 11:00 | 2026-11-12 12:00 | 47.0 (end: 48.0) | 60.0 | 228.0 |
| **37** | 2026-11-12 12:00 | 2026-11-12 13:00 | 48.0 (end: 49.0) | 61.0 | 229.0 |
| **38** | 2026-11-12 13:00 | 2026-11-12 14:00 | 49.0 (end: 50.0) | 62.0 | 230.0 |
| **39** | 2026-11-12 14:00 | 2026-11-12 15:00 | 50.0 (end: 51.0) | 63.0 | 231.0 |
| **40** | 2026-11-12 15:00 | 2026-11-12 16:00 | 51.0 (end: 52.0) | 64.0 | 232.0 |
| **41** | 2026-11-12 16:00 | 2026-11-12 17:00 | 52.0 (end: 53.0) | 65.0 | 233.0 |
| **42** | 2026-11-12 17:00 | 2026-11-12 18:00 | 53.0 (end: 54.0) | 66.0 | 234.0 |
| **43** | 2026-11-12 18:00 | 2026-11-12 19:00 | 54.0 (end: 55.0) | 67.0 | 235.0 |
| **44** | 2026-11-12 19:00 | 2026-11-12 20:00 | 55.0 (end: 56.0) | 68.0 | 236.0 |
| **45** | 2026-11-12 20:00 | 2026-11-12 21:00 | 56.0 (end: 57.0) | 69.0 | 237.0 |
| **46** | 2026-11-12 21:00 | 2026-11-12 22:00 | 57.0 (end: 58.0) | 70.0 | 238.0 |
| **47** | 2026-11-12 22:00 | 2026-11-12 23:00 | 58.0 (end: 59.0) | 71.0 | 239.0 |
| **48** | 2026-11-12 23:00 | 2026-11-13 00:00 | 59.0 (end: 60.0) | 72.0 | 240.0 |
