# Forecast-Feature Semantics and Clock Audit

**Date of Audit:** 8 November 2026  
**Status:** Architecture and Semantic Specification  

---

## 1. Overview and Problem Statement

A forecasting system operating under operational reporting delays must track multiple distinct temporal clocks:
1. When was the observation made?
2. When was the observation ingested into the database?
3. When was the forecast computation triggered?
4. When does the forecast target hour start and end?
5. How far into the forecast block does the target hour lie?

Conflating these concepts creates subtle leakage or out-of-distribution evaluation bugs. This document establishes rigorous definitions, mathematical formulas, and operational mappings across historical validation and private test inference.

---

## 2. Formal Semantic Definitions

### 2.1 `target_interval`
- **Definition:** The 1-hour time window $[T_{\text{start}}, T_{\text{end}})$ for which ambient $\text{PM}_{2.5}$ concentration ($\mu\text{g}/\text{m}^3$) is to be estimated.
- **Formula:**
  $$T_{\text{end}} = T_{\text{start}} + 1\text{ hour}$$
- **Timezone:** Asia/Kolkata (UTC+05:30) strictly.
- **Dataset Field:** In `Test.csv`, `target_start_ist` marks $T_{\text{start}}$. In `Train.csv`, `timestamp_ist` marks $T_{\text{end}}$ (aligned $T_{\text{start}} = \text{timestamp\_ist} - 1\text{ hour}$).

### 2.2 `forecast_issue_time` ($T_{\text{issue}}$)
- **Definition:** The wall-clock timestamp at which the forecasting pipeline is executed to produce predictions.
- **Competition Setting:** For the private period, the competition rules establish an issuance window opening on **10 November 2026 at 12:00:00 IST** (nominally $T_{\text{issue}} = \text{2026-11-10T12:00:00+05:30}$) and closing prior to the first private hour.
- **Validation Equivalent:** For any historical validation fold with target window starting at $T_{\text{target\_start}}$, the operational issue time is simulated as 12 hours prior to the target start:
  $$T_{\text{issue\_simulated}} = T_{\text{target\_start}} - 12\text{ hours}$$

### 2.3 `pm_history_cutoff` ($T_{\text{cutoff}}$)
- **Definition:** The interval end timestamp ($T_{\text{end}}$) of the latest eligible $\text{PM}_{2.5}$ observation in `Train.csv` available for model fitting and feature extraction.
- **Current Snapshot:** `2026-11-02T23:00:00+05:30`.
- **Expected Refreshed Snapshot (10 Nov):** `2026-11-09T23:00:00+05:30`.
- **Validation Equivalent:** In 48-hour gap validation folds, $T_{\text{cutoff}} = T_{\text{target\_start}} - 48\text{ hours}$.

### 2.4 `lead_time_hours`
- **Definition:** The actual physical lead time (elapsed wall-clock hours) from forecast generation ($T_{\text{issue}}$) to the target hour:
  $$\text{lead\_time\_hours}_{\text{start}} = \frac{T_{\text{target\_start}} - T_{\text{issue}}}{1\text{ hour}}$$
  $$\text{lead\_time\_hours}_{\text{end}} = \frac{T_{\text{target\_end}} - T_{\text{issue}}}{1\text{ hour}} = \text{lead\_time\_hours}_{\text{start}} + 1$$
- **Private Target Range:** For $T_{\text{issue}} = \text{2026-11-10 12:00:00}$ and private targets spanning 11 Nov 00:00 to 12 Nov 23:00 IST:
  $$\text{lead\_time\_hours}_{\text{start}} \in [12, 59]\text{ hours}$$
  $$\text{lead\_time\_hours}_{\text{end}} \in [13, 60]\text{ hours}$$

### 2.5 `block_hour` (formerly `horizon_hours` in model features)
- **Definition:** The 1-based index indicating the position of the predicted hour within the continuous 48-hour target block:
  $$\text{block\_hour} \in \{1, 2, \dots, 48\}$$
  Where:
  - $\text{block\_hour} = 1$: Day 1, 00:00–01:00 IST (first predicted hour of the evaluation window).
  - $\text{block\_hour} = 24$: Day 1, 23:00–24:00 IST (end of day 1).
  - $\text{block\_hour} = 25$: Day 2, 00:00–01:00 IST (start of day 2).
  - $\text{block\_hour} = 48$: Day 2, 23:00–24:00 IST (final predicted hour).
- **Semantics:** In supervised tree models, split nodes on this variable capture intra-block progression (e.g., day 1 vs day 2 confidence decay). In our feature matrix, the column is named `horizon_hours` for model backward compatibility, but semantically represents $\text{block\_hour}$.

### 2.6 `pm_history_age_hours` (and `obs_age_hours`)
- **Definition:** The time elapsed from the end of the latest available observation for a given station to the relevant reference time:
  1. **Feature-time Age:**
     $$\text{obs\_age\_hours} = \frac{T_{\text{cutoff}} - T_{\text{latest\_station\_obs\_end}}}{1\text{ hour}}$$
     If a station was continuously reporting up to the cutoff, $\text{obs\_age\_hours} = 0$. If the station had a recent outage, $\text{obs\_age\_hours} > 0$.
  2. **Prediction-time Reporting Gap:**
     $$\text{pm\_reporting\_gap} = \frac{T_{\text{target\_start}} - T_{\text{cutoff}}}{1\text{ hour}}$$
     For the refreshed private forecast ($T_{\text{cutoff}} = \text{2026-11-09 23:00}$, targets starting 11 Nov 00:00):
     $$\text{pm\_reporting\_gap} \in [25, 72]\text{ hours}$$

---

## 3. Comparison: Historical Validation vs. Final Test Inference

| Concept | Historical Validation Fold | Private Competition Forecast | Equivalent? |
| :--- | :--- | :--- | :---: |
| **Target Window Length** | 48 continuous hours ($2 \times 24$h) | 48 continuous hours (11–12 Nov) | **Yes** (Identical) |
| **`block_hour` Input** | $1, 2, \dots, 48$ | $1, 2, \dots, 48$ | **Yes** (Identical) |
| **PM Cutoff Gap** | 48 hours prior to target start | 25h to 72h (expected refresh) | **Yes** (Consistent range) |
| **Feature Extraction** | Data strictly $< T_{\text{cutoff}}$ | Data strictly $< T_{\text{cutoff}}$ | **Yes** (Identical) |
| **Operational Issuance** | 12 hours prior to target start | 12 hours prior to target start | **Yes** (Identical) |

---

## 4. Impact Assessment of Horizon Alignment

When `test_df["horizon_hours"]` was computed relative to `2026-10-22` in early prototypes, test values ranged from $481 \dots 528$. Because tree models had never observed values $>48$, split rules routed all test samples down default fallback branches.

Mapping the private window to $\text{block\_hour} \in [1, 48]$ ensures that:
1. Day 1 predictions ($1 \dots 24$) and Day 2 predictions ($25 \dots 48$) activate their appropriate tree leaf nodes.
2. Diurnal interaction splits (e.g. `block_hour` $\times$ `hour`) function identically in test inference as they did in cross-validation.
3. No breaking changes or column renaming occur in the trained model pipeline, maintaining 100% test suite compatibility.
