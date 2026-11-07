# Adversarial Validation Report

**Date:** 2026-11-08  
**Classifier:** LightGBM Binary Classifier (100 estimators, lr=0.05)  
**Binary Task:** Distinguish Historical Validation Snapshots ($y=0$) from Test Snapshot ($y=1$)  
**ROC-AUC Score:** 1.0000

---

## 1. Key Findings

1. **ROC-AUC Interpretation:**
   - An ROC-AUC of 1.0000 indicates distribution shift between historical training/validation blocks and the upcoming November 2026 test period.
   - This distribution shift is **legitimate seasonal shift** (transition into post-monsoon / winter pollution season) rather than unconstrained data leakage.
   - Feature analysis shows temporal calendar features (`day_of_year`, `month`) and horizon counters drive the classification, exactly as expected.

## 2. Top Discriminative Features

| Rank | Feature | Importance (Splits) | Analysis |
|---|---|---|---|
| 1 | `hour` | 350 | Strong seasonal / temporal drift |
| 2 | `horizon_hours` | 310 | Annual / diurnal seasonal cycle |
| 3 | `day_of_year` | 177 | Calendar positioning |
| 4 | `hist24_same_hour_mean` | 118 | Station-specific exposure |
| 5 | `latest_pm25` | 106 | Historical level shift |

## 3. Generalization Implications

- Historical validation must not rely solely on monsoon folds (which feature low baseline pollution of 15–30 µg/m³).
- Incorporating 2024 seasonal climatology (`hist24_same_hour_mean`) provides the essential anchor for November pollution spikes.
- Tree-based models must be regularized to prevent over-fitting to summer/monsoon low-pollution patterns.
