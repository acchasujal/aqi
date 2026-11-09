# Updated Data Audit: 9 November 2026 Official Challenge Release

**Audit Date:** 2026-11-09  
**Auditor:** Senior Data Scientist, ML Engineer, and Software Architect  
**Dataset:** Zindi Google Mumbai Data Challenge: Air Quality Mapping & Forecasting  
**Commit Reference:** `0735651` / `efa053a`  

---

## 1. Executive Summary

On 9 November 2026, the challenge organizers published an updated training release adding 284 new hourly observations across Mumbai monitoring stations.
This audit analyzes the new data, confirms absence of target leakage, establishes updated information horizons, and validates temporal alignment for the upcoming 11–12 November 2026 private evaluation period.

| Metric | Previous Snapshot (EXP-013 / Task 007) | Refreshed Snapshot (9 Nov Release) | Change |
|---|---:|---:|---:|
| **Train Row Count** | 47,849 | **48,133** | +284 |
| **Train Min Timestamp (End of Hour)** | 2025-02-19 03:00 IST | 2025-02-19 03:00 IST | Unchanged |
| **Train Max Timestamp (End of Hour)** | 2026-11-02 23:00 IST | **2026-11-09 07:00 IST** | +152 hours |
| **Test Row Count** | 2,592 | 2,592 | Fixed & verified |
| **SampleSubmission Row Count** | 2,592 | 2,592 | Fixed & verified |
| **Target Stations** | 4 | 4 | Unchanged |
| **Active Public Window** | 5–6 November 2026 | **7–8 November 2026** (171 valid) | Excluded from Train |
| **Private Evaluation Window** | 11–12 November 2026 | 11–12 November 2026 | Excluded from Train |
| **Lead to Private Window Start** | ~193 hours | **41–43 hours** | Reduced by 150h |
| **Lead to Private Window End** | ~240 hours | **88–90 hours** | Reduced by 150h |

---

## 2. File Hashes and Immutability Verification

All core files in `data/raw/challenge/` were cryptographically audited via SHA-256:

| File | SHA-256 Digest | Status |
|---|---|---|
| `Train.csv` | `e107dda18670583c333be0966530fc444c18fdb30c870156ac25688a2c152210` | Refreshed (+284 rows) |
| `Test.csv` | `05232d3625f69f8c6792da0b00c3b0eb688c2279b94ce5187e5bba8f4c281dfd` | Immutable |
| `SampleSubmission.csv` | `1021469e8bb43588ef5bc0dbba84df6124564c7eaae396a8fc17a780faaa67a7` | Immutable |
| `Stations.csv` | `f59735d4fa5cff863b14dca21815598129e925ea031666ff0590c5c308c352ef` | Immutable |
| `DataDictionary.txt` | `17e5aa599554bfd50cb681be93f538356a59600e12d6a5c102c7e0766288863f` | Updated with 9 Nov notes |
| `AdditionalHistory.zip` | `df1ef1fa7fb877eeea5a88e0ec04ee1e18826d9cfd11634b07f877ca43b1c93a` | Immutable |

---

## 3. Station Coverage & Information Cutoffs

In `Train.csv`, each timestamp denotes the **end** of the 1-hour interval, while in `Test.csv`, `target_start_ist` denotes the **start** of the target hour.

| Station ID | Station Name | Network | Sensor ID | Rows in Train | Max Timestamp (Interval End) | Lead to Private Start (11 Nov 00:00) | Lead to Private End (12 Nov 23:00) |
|---|---|---|---|---:|---|---:|---:|
| **11606** | Borivali East, Mumbai - IITM | IITM | 5400 | 12,172 | 2026-11-09 06:00 IST | 42 hours | 89 hours |
| **11611** | Malad West, Mumbai - IITM | IITM | 5402 | 12,276 | 2026-11-09 07:00 IST | 41 hours | 88 hours |
| **3409510** | Byculla, Mumbai - BMC | BMC | 5960 | 11,620 | 2026-11-09 05:00 IST | 43 hours | 90 hours |
| **3409511** | Shivaji Nagar, Mumbai - BMC | BMC | 5961 | 12,065 | 2026-11-09 07:00 IST | 41 hours | 88 hours |

### Observation on Recent Train Rows:
- 5 November 2026: 88 valid readings across the 4 stations.
- 6 November 2026: 87 valid readings across the 4 stations.
- 7–8 November 2026: **0 readings** in `Train.csv`. As confirmed in `DataDictionary.txt`, these 171 valid labels form the current active public leaderboard scoring window and are intentionally omitted from `Train.csv` to prevent leakage.
- 9 November 2026: 17 fresh readings up to 07:00 IST.

---

## 4. Methodological Implications for Final Private Forecasting

The reduction of the forecast lead time from **193 hours** (under the 2 November snapshot) down to **41–43 hours** (under the 9 November snapshot) fundamentally impacts model dynamics:

1. **Auto-regressive & Persistence Relevance:**
   - At 193 hours (8 days), recent PM2.5 levels had decayed significantly in predictive autocorrelation, making the historical 2024 seasonal climatology the dominant signal.
   - At 41–43 hours (<2 days), recent station levels (recent 24h/72h medians, recent diurnal profile, and local pollution anomalies) carry substantial predictive signal.
2. **Supervised GBDT and Residual Models:**
   - Shorter horizons (41–90 hours) are precisely where gradient boosted decision trees (CatBoost, LightGBM) trained on recent-level features, cyclic calendar features, and seasonal interaction features demonstrate peak predictive performance.
   - A residual or ensemble approach that combines recent-level autoregression with seasonal climatology is theoretically and empirically optimal.
3. **Absence of Leakage:**
   - No 7–8 November public labels or 11–12 November private labels are present in `Train.csv`.
   - All feature generation strictly respects the `pm_history_cutoff` derived from the station's latest eligible observation.
