# Forecast Horizon Audit & Resolution
**Google Mumbai Data Challenge: Air Quality Mapping & Forecasting by Google (Zindi)**

---

## 1. Resolution of the 41–43h vs. 41–90h Discrepancy

There is no mathematical contradiction between the "41–43 hour" and "41–90 hour" figures cited in previous audit reports. They describe two distinct aspects of the identical forecasting timeline:

1. **The 41–43 Hour Figure (Initial Forecast Latency / Onset Gap):**
   - This measures the elapsed time from the **latest available station observation in `Train.csv`** to the **start of the 48-hour private evaluation window** (`2026-11-11 00:00:00 IST`, interval start `2026-11-10 23:00:00 IST`).
   - Depending on the station's last reporting hour on 9 November, this onset gap is exactly:
     - **Station 11611 (Malad West):** `2026-11-09 06:00` start -> **41 hours**
     - **Station 3409511 (Shivaji Nagar):** `2026-11-09 06:00` start -> **41 hours**
     - **Station 11606 (Borivali East):** `2026-11-09 05:00` start -> **42 hours**
     - **Station 3409510 (Byculla):** `2026-11-09 04:00` start -> **43 hours**

2. **The 41–90 Hour Figure (Full Target Horizon Spectrum Across the 48-Hour Block):**
   - The private evaluation window consists of **48 consecutive target hours** (from 11 Nov 00:00 to 12 Nov 23:00 IST).
   - The lead time for each individual forecast row is the duration from the station's latest observation to that specific target hour:
     - **Hour 1 of block (11 Nov 00:00 IST):** Lead time = **41 to 43 hours**.
     - **Hour 24 of block (11 Nov 23:00 IST):** Lead time = **64 to 66 hours**.
     - **Hour 48 of block (12 Nov 23:00 IST):** Lead time = **88 to 90 hours**.
   - Therefore, the complete range of evaluated forecast horizons spans **41 to 90 hours**.

---

## 2. Station-by-Station Exact Timestamps & Horizon Table

| Station ID | Station Name | Latest Train Start (`target_start`) | Latest Train End (Cutoff) | Lead to Private Block Start | Lead to Private Block End | Full Lead Spectrum |
|:---:|---|---|---|:---:|:---:|:---:|
| `11606` | Borivali East, Mumbai - IITM | 2026-11-09 05:00 IST | 2026-11-09 06:00 IST | **42 hours** | **89 hours** | 42h to 89h |
| `11611` | Malad West, Mumbai - IITM | 2026-11-09 06:00 IST | 2026-11-09 07:00 IST | **41 hours** | **88 hours** | 41h to 88h |
| `3409510` | Byculla, Mumbai - BMC | 2026-11-09 04:00 IST | 2026-11-09 05:00 IST | **43 hours** | **90 hours** | 43h to 90h |
| `3409511` | Shivaji Nagar, Mumbai - BMC | 2026-11-09 06:00 IST | 2026-11-09 07:00 IST | **41 hours** | **88 hours** | 41h to 88h |

---

## 3. Clocks & Inference Verification

The pipeline strictly isolates and logs all information clocks:
- **`model_run_time` (Wall Clock):** `2026-11-09T14:30:00+05:30` (recorded in all manifests).
- **`pm_history_cutoff_global`:** `2026-11-09T07:00:00+05:30` (derived strictly from Train contents).
- **Target Intervals:** Derived strictly from `Test.csv`, with zero imputation and zero leakage.
- **In-Distribution Horizon Indexing:** In `predict_test_ensemble`, test targets are mapped to block-hour positions $1 \dots 48$, matching the 48-hour rolling pseudo-forecast training blocks to prevent out-of-distribution tree extrapolation.
