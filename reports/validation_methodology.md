# Validation Methodology: Chronological Fixed-Origin Protocol

**Date:** 2026-11-08  
**Author:** Senior Data Scientist, ML Engineer, and Software Architect  
**Evaluation Objective:** Minimize original-scale PM2.5 RMSE on unseen private period (11–12 November 2026)  
**Status:** Implemented & Verified in `src/mumbai_pm25/validation.py`

---

## 1. Guiding Philosophy: Simulate the Unseen Test Reality

The competition evaluation tests 48 consecutive forecast hours across 4 Mumbai CAAQMS monitoring stations during **11–12 November 2026**.

To guarantee that validation error estimates accurately predict performance on this private evaluation:
1.  **Fixed-Origin Block Forecasting:** All 48 hourly predictions in a forecast block must be produced simultaneously from a single frozen information snapshot.
2.  **Zero Target Ingestion:** Predictions for hour 25 through hour 48 must **never** ingest observed target values from hours 1 through 24.
3.  **Strict Chronological Boundaries:** All feature transformations, rolling statistics, and model parameters must be fit strictly on data available before the simulated prediction origin.
4.  **No Random Splitting or K-Fold Shuffling:** PM2.5 is auto-correlated, seasonally non-stationary, and subject to meteorological shifts. Random cross-validation causes massive optimistic leakage.

---

## 2. Separation of Information Clocks

The validation protocol rigorously separates four independent temporal clocks:

```text
Time Line:
-----------------[ pm_history_cutoff ] -------- [ forecast_issue_time ] ------ [ target_start ] ======> [ target_end ]
                          |                                                           |                     |
                   Latest available PM                                          Start of 48h          End of 48h
                   Train observation end                                         forecast block        forecast block
```

1.  **Forecast Issue Time / Model Run Time ($T_{\text{issue}}$):**
    The wall-clock timestamp at which the forecast model is executed. Weather forecasts and static metadata are eligible up to this clock.
2.  **PM History Cutoff ($T_{\text{cutoff}}$):**
    The timestamp of the latest available PM2.5 observation in the training release. In live competition conditions, reporting delays may cause $T_{\text{cutoff}}$ to lag $T_{\text{issue}}$ by 48 to 120 hours.
3.  **Target Interval $[T_{\text{start}}, T_{\text{end}})$:**
    The exact hourly interval being forecasted (48 consecutive hours).
4.  **Forecast Horizon ($h \in \{1, 2, \dots, 48\}$):**
    Elapsed hours from $T_{\text{start}}$ to the target hour ($h = (t - T_{\text{start}}) + 1$).

---

## 3. Fixed-Origin Reporting-Gap Experiments

### The Flaw in Legacy Validation
In the initial legacy code, changing `gap_hours` dynamically shifted `target_start = cutoff + gap_hours`. When comparing 48h vs. 72h vs. 96h vs. 120h reporting delays, the model evaluated completely different calendar dates, confusing reporting latency with seasonal weather variations.

### The Corrected Fixed-Target Protocol
Our updated protocol anchors on **fixed 48-hour target windows**:
-   Target Window $[T_{\text{start}}, T_{\text{end}})$ is chosen first and remains constant.
-   For any gap $g \in \{48, 72, 96, 120\}$ hours, the PM history cutoff is set to:
    $$T_{\text{cutoff}} = T_{\text{start}} - g$$
-   All four reporting-gap experiments evaluate **100% identical ground-truth validation rows**.

| Fold ID | Fixed Target Window | Gap 48h Cutoff | Gap 72h Cutoff | Gap 96h Cutoff | Gap 120h Cutoff |
|---|---|---|---|---|---|
| Fold 38 | 2026-09-17 to 2026-09-19 | 2026-09-15 00:00 | 2026-09-14 00:00 | 2026-09-13 00:00 | 2026-09-12 00:00 |
| Fold 39 | 2026-10-01 to 2026-10-03 | 2026-09-29 00:00 | 2026-09-28 00:00 | 2026-09-27 00:00 | 2026-09-26 00:00 |
| Fold 40 | 2026-10-15 to 2026-10-17 | 2026-10-13 00:00 | 2026-10-12 00:00 | 2026-10-11 00:00 | 2026-10-10 00:00 |
| Fold 41 | 2026-10-29 to 2026-10-31 | 2026-10-27 00:00 | 2026-10-26 00:00 | 2026-10-25 00:00 | 2026-10-24 00:00 |

Folds are spaced 14 days apart, guaranteeing non-overlapping evaluation targets across multiple seasonal regimes (monsoon, autumn transition, winter onset).

---

## 4. Supervised Training Simulation & Leakage Prevention

To train supervised models (LightGBM, CatBoost, XGBoost, Random Forest) without leakage:

1.  **Historical Forecast-Origin Training Examples:**
    Training samples are constructed by simulating past forecast origins $t_{\text{train\_orig}}$. Features are computed using only data available strictly before $t_{\text{train\_orig}} - g$.
2.  **Strict Temporal Purging:**
    For each outer validation fold with target window $[T_{\text{start}}, T_{\text{end}}]$:
    -   Only training examples with target blocks ending strictly before $T_{\text{cutoff}}$ are included in model fitting:
        $$t_{\text{train\_target\_end}} \le T_{\text{cutoff}}$$
    -   Any historical training example whose target window overlaps the validation block $[T_{\text{start}}, T_{\text{end}}]$ is **strictly purged**.
3.  **Overlapping Origin Sample Weighting:**
    Generating origins at daily intervals creates overlapping target blocks in the training set. To prevent sample overweighting, origin sampling is controlled (sampled at 72-hour intervals) or inversely weighted by origin overlap count.

---

## 5. Untouched Final Chronological Holdout

To protect against subtle overfitting from hyperparameter tuning and feature selection:
-   **Holdout Window:** `2026-10-31 00:00:00+05:30` to `2026-11-02 00:00:00+05:30` (48 hours $\times$ 4 stations = 192 rows).
-   This window is completely quarantined from model tuning, feature selection, and ensemble weight optimization.
-   It is evaluated only once as a final sanity check prior to private submission generation.

---

## 6. Official Metrics and Diagnostics

Every evaluated model generates an Out-Of-Fold (OOF) prediction record with:
1.  **Pooled Full-Target RMSE (Primary Metric):**
    $$\text{RMSE}_{\text{full}} = \sqrt{\frac{1}{N} \sum_{i=1}^{N} (\hat{y}_i - y_i)^2}$$
    Evaluated over all eligible validation rows. Validation targets are never clipped, winsorized, or deleted.
2.  **Clean-Range Diagnostic RMSE:**
    Computed strictly on $y < 500\ \mu\text{g/m}^3$. Diagnostic only; never used as the primary selection criterion.
3.  **Mean Absolute Error (MAE) & Bias:**
    Tracks systematic under- or over-prediction.
4.  **Per-Station RMSE:**
    Evaluates error independently for Borivali East, Malad West, Byculla, and Shivaji Nagar.
5.  **Per-Horizon-Bucket RMSE:**
    Evaluates performance degradation across forecast horizons:
    -   `h01_12`: Hours 1–12
    -   `h13_24`: Hours 13–24
    -   `h25_36`: Hours 25–36
    -   `h37_48`: Hours 37–48
6.  **High-Pollution Error Analysis:**
    Subgroup RMSE and MAE on $y \ge 100\ \mu\text{g/m}^3$ and $y \ge 300\ \mu\text{g/m}^3$.
7.  **Fold Variability Metrics:**
    Mean, median, and standard deviation of per-fold RMSE to ensure improvements generalize across multiple regimes rather than being driven by a single favorable fold.
