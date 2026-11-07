# November 2025 vs. November 2026 Validation Comparability Audit

**Date of Audit:** 8 November 2026  
**Reference Periods:**  
- Historical Pseudo-Forecast Window: 11 November 2025 00:00 IST – 12 November 2025 23:00 IST  
- Competition Private Forecast Window: 11 November 2026 00:00 IST – 12 November 2026 23:00 IST  
**Status:** Verification and Methodological Specification  

---

## 1. Protocol Verification of Historical Winter Pseudo-Folds

To verify that the four winter pseudo-forecast folds (`fold_nov_2025_calendar_match`, `fold_dec_2025_winter`, `fold_jan_2026_early`, `fold_jan_2026_late`) realistically replicate the competition inference setup:

1. **Historical Forecast Origins ($T_{\text{orig}}$):**
   - In each pseudo-fold, $T_{\text{orig}}$ is anchored exactly at the target window start ($T_{\text{target\_start}}$).
   - In `fold_nov_2025_calendar_match`: $T_{\text{target\_start}} = \text{2025-11-11 00:00:00+05:30}$.
2. **PM-History Cutoffs ($T_{\text{cutoff}}$):**
   - Simulated cutoff is strictly set prior to the target window:
     $$T_{\text{cutoff}} = T_{\text{target\_start}} - 48\text{ hours} = \text{2025-11-09 00:00:00+05:30}$$
   - No observations at or after $T_{\text{cutoff}}$ are accessible to feature extraction or model training.
3. **Frozen Information Across the 48-Hour Block:**
   - All 48 hourly predictions for each station use the **exact same frozen features** generated at $T_{\text{cutoff}}$.
   - No rolling intermediate updates or future target ground truth are used during the 48 hours.
4. **Lead-Time and Block Horizon Definitions:**
   - Each hourly target in the 48-hour block receives in-distribution block horizon $\text{block\_hour} \in [1, 48]$, identical to the test inference mapping.

---

## 2. Comparison of 11–12 November 2025 vs. 11–12 November 2026

We explicitly state: **November 2025 and November 2026 are NOT identical.** While they occupy the same calendar day-of-year, their atmospheric, calendar, and operational contexts exhibit important differences:

### 2.1 Identical Calendar and Feature Properties

| Feature / Property | 11–12 November 2025 | 11–12 November 2026 | Equivalence Status |
| :--- | :---: | :---: | :--- |
| **Target Window Length** | 48 hours ($2 \times 24$h) | 48 hours ($2 \times 24$h) | **Identical** |
| **Day of Year (DOY)** | Day 315 & 316 | Day 315 & 316 | **Identical** (both non-leap years) |
| **Normalized DOY** | 315.0 & 316.0 | 315.0 & 316.0 | **Identical** |
| **2024 CAAQMS Climatological Prior** | 54.55 $\mu\text{g}/\text{m}^3$ (Borivali East) | 54.55 $\mu\text{g}/\text{m}^3$ (Borivali East) | **Identical** (same lookup key) |
| **Block Horizon (`block_hour`)** | $1, 2, \dots, 48$ | $1, 2, \dots, 48$ | **Identical** |
| **Working Day Status** | Mid-week working days | Mid-week working days | **Equivalent** |

---

### 2.2 Key Differences and Non-Equivalence

| Aspect | 11–12 November 2025 | 11–12 November 2026 | Significance / Impact |
| :--- | :--- | :--- | :--- |
| **Day of Week** | **Tuesday & Wednesday** (`weekday = 1, 2`) | **Wednesday & Thursday** (`weekday = 2, 3`) | Minor day-of-week shift. Both are non-weekend working days, but cyclical weekday features (`weekday_sin`, `weekday_cos`) differ slightly. |
| **Festival Timing (Diwali)** | Diwali was on **20 October 2025** (3 weeks prior to target window). | Diwali is on **8 November 2026** (3 days prior to target window). | **Substantial Difference:** 11–12 November 2026 falls in the immediate post-Diwali recovery window (Bhai Dooj). Depending on festival emissions and meteorological dispersion, residual particulate loading could be elevated or activity patterns modified. |
| **Operational Cutoff Gap** | Evaluated with a fixed **48-hour gap** ($T_{\text{cutoff}} = \text{09 Nov 00:00}$). | The expected refreshed cutoff is **09 Nov 23:00** (a **25-hour gap** to 11 Nov 00:00). | **Freshness Advantage in 2026:** Final inference will have slightly fresher PM history (25h vs 48h), providing a more recent 72-hour median baseline. |
| **Meteorological Variability** | Specific synoptic weather (winds, boundary-layer height, humidity) of Nov 2025. | Unobserved actual weather of Nov 2026. | Inter-annual weather variability means actual boundary-layer dynamics on 11–12 Nov 2026 will not match Nov 2025 hour-for-hour. |

---

## 3. Methodological Implications for Model Selection

Because November 2026 will not mirror November 2025 identically:
1. **Never Hardcode Spikes:** The pipeline must not hardcode an artificial upward spike of 600+ $\mu\text{g}/\text{m}^3$ into 11–12 November 2026 predictions simply because Shivaji Nagar spiked on that date in 2025.
2. **Value of Dual Ensembling:**
   - If post-Diwali 2026 conditions experience rapid boundary-layer shallowing and particulate trapping, **Candidate C (Statistical Seasonal)** protects the entry because its seasonal climatology is already calibrated to typical November levels.
   - If favorable marine winds disperse pollutants and keep ambient concentrations lower, **Candidate B (50% CatBoost + 50% Statistical)** anchors predictions closer to the recent observed 72-hour level.
3. This divergence justifies selecting Candidate C and Candidate B as complementary solutions.
