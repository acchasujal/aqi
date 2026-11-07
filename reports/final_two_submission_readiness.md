# Final Two-Submission Operational Readiness and Verification Protocol

**Competition:** Zindi Google Mumbai Data Challenge: Air Quality Mapping & Forecasting  
**Target Evaluation Window:** 11 November 2026 00:00 IST – 12 November 2026 23:00 IST (192 private hourly evaluation rows)  
**Selected Candidate Pair:**  
- **Candidate C:** `artifacts/submissions/submission_C_statistical_seasonal.csv` (100% Statistical Seasonal Climatology Blend)  
- **Candidate B:** `artifacts/submissions/submission_B_robust_ensemble.csv` (50% CatBoost log1p + 50% Statistical Seasonal Blend)  
**Date of Protocol:** 8 November 2026  
**Status:** Operational Deployment Specification  

---

## 1. Scientific Integrity: Disentangling Observations, Physics, and Hypotheses

To maintain strict scientific and regulatory discipline, the pipeline clearly separates four levels of claims:

| Category | Definition | Verified Facts in This Pipeline | Unsupported / Prohibited Hypotheses (Excluded) |
| :--- | :--- | :--- | :--- |
| **1. Measured Observations** | Ground truth present in the competition dataset. | - Station 11606 (Borivali East) exhibits the lowest mean PM2.5 (23.3 $\mu\text{g}/\text{m}^3$ in train).<br>- Station 3409511 (Shivaji Nagar) exhibits four observed spikes $>250 \mu\text{g}/\text{m}^3$ on 11–12 Nov 2025 (max 688.07 $\mu\text{g}/\text{m}^3$). | - Do not assume all stations spike simultaneously.<br>- Do not assume Shivaji Nagar will repeat 688 $\mu\text{g}/\text{m}^3$ on 11 Nov 2026. |
| **2. Statistical Relationships** | Correlational patterns demonstrated across validation folds. | - Tree models share $>0.96$ residual correlation with each other.<br>- Statistical climatology has 0.805 residual correlation with tree models.<br>- Blending 50% climatology (Candidate B) reduces autumn RMSE to 14.75; 100% climatology (Candidate C) achieves 39.28 winter RMSE. | - Do not claim complex neural network models or tree-tree ensembles provide hedging when validation residuals are 0.97 correlated. |
| **3. External Atmospheric Physics** | Established atmospheric literature (IIT Bombay, NEERI, SAFAR, CPCB). | - Mumbai winter transition brings boundary-layer height compression (<300 m nocturnal).<br>- Surface radiative cooling causes early morning (09–11 IST) and late night (21–23 IST) inversion traps.<br>- Shivaji Nagar's proximity to Deonar landfill, Sion-Panvel trucking, and unpaved roads provides high local particulate loading. | - Prohibited: Do not scrape or ingest unapproved external commercial air quality APIs or unverified satellite products. Only the provided `Train.csv`, `Stations.csv`, and `AdditionalHistory.zip` (CPCB CAAQM) are used. |
| **4. Unverified Hypotheses** | Plausible scenarios that cannot be confirmed until private evaluation. | - Hypothesis A: 11–12 Nov 2026 experiences strong winter stagnation.<br>- Hypothesis B: Maritime winds persist, keeping 11–12 Nov 2026 relatively clean.<br>- *Both candidates together hedge across these two hypotheses.* | - Never claim private test scores or leaderboard placement are known in advance. |

---

## 2. Complementary Two-Submission Rationale

Zindi allows two private submission selections. Candidate C and Candidate B were selected because they provide an authentic hedge across contrasting meteorological outcomes:

```
[Private Target Window: 11–12 November 2026]
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
  [Regime 1: Winter Surge]  [Regime 2: Moderate Persistence]
  (Thermal Inversions,     (Maritime Ventilation,
   Post-Diwali Accumulation) Clean Autumn Dispersion)
         │                       │
         ▼                       ▼
   Candidate C Dominates   Candidate B Dominates
   (Winter RMSE: 39.28     (Autumn RMSE: 14.75
    Pooled RMSE: 29.30      Clean RMSE: 11.97
    Mean Bias: -0.54)       Recent Median Sensitive)
```

- **Residual Correlation:** 0.805 (substantially independent errors).
- **Mean Absolute Divergence:** 5.47 $\mu\text{g}/\text{m}^3$ overall, rising to 8.15 $\mu\text{g}/\text{m}^3$ in winter folds and 18.69 $\mu\text{g}/\text{m}^3$ during November transition days.
- **Cluster Bootstrap Win Rate:** In 10,000 fold-level resamples, Candidate C has an 88.6% probability of beating Candidate B, but Candidate B wins in 5 out of 9 individual historical folds (particularly during cleaner periods).

---

## 3. Candidate Artifact Inventory (Archived & Verified)

All submission files exist, have matching `.manifest.txt` records, and have passed compliance tests:

| Candidate | Path | Model Type | Rows | SHA-256 Digest |
| :--- | :--- | :--- | :---: | :--- |
| **Candidate C (Primary)** | `artifacts/submissions/submission_C_statistical_seasonal.csv` | 50% 2024 Climatology + 50% Median72 | 2,592 | `e82ff30bc8867a07fc26fb51e737c73dbca63fc9ad4a2ad528404a3f21d3f237` |
| **Candidate B (Secondary)** | `artifacts/submissions/submission_B_robust_ensemble.csv` | 50% CatBoost log1p + 50% Statistical Seasonal | 2,592 | `01db64673628bb9c072bfef693ef2b8df1c8b36a188be923832cce6bb79c298c` |
| **Candidate A (Archived)** | `artifacts/submissions/submission_A_accuracy_ensemble.csv` | 83% CatBoost log1p + 17% Statistical Seasonal | 2,592 | `0417e435941c48c6e7c10b71329c21147a4f9104043b4fdb3288f4b0d0c36785` |
| **Candidate D (Archived)** | `artifacts/submissions/submission_D_balanced_ensemble.csv` | 20% CatBoost log1p + 80% Statistical Seasonal | 2,592 | `da7e8d626e259b1dc710927e1f4fcbbbb68aa9dbfb4e680d28362ea5317b9666` |

---

## 4. Final Operational Execution Protocol for 10 November 2026

When the competition organizers release the refreshed `Train.csv` file on 10 November 2026:

### Step 1: Data Ingestion and Station Cutoff Verification
Do not assume the cutoff is `2026-11-09 23:00:00`. Inspect the actual refreshed file:
```bash
python -c "
import pandas as pd
df = pd.read_csv('data/raw/challenge/Train.csv')
df['target_start'] = pd.to_datetime(df['target_start_ist'])
print('Latest timestamp per station:')
for sid, g in df.groupby('location_id'):
    print(f'Station {sid}: {g[\"target_start\"].max()}')
"
```

### Step 2: Regenerate Candidate C (Statistical Seasonal)
```bash
python scripts/train_predict.py \
    --model hist24_blend50_median72 \
    --model-run-time 2026-11-10T12:00:00+05:30 \
    --output artifacts/submissions/submission_C_refreshed_20261110.csv
```

### Step 3: Regenerate Candidate B (Robust Ensemble)
```bash
python scripts/train_predict.py \
    --model ensemble_robust \
    --model-run-time 2026-11-10T12:00:00+05:30 \
    --output artifacts/submissions/submission_B_refreshed_20261110.csv
```

### Step 4: Verification Checklist Before Upload
Run the verification test suite:
```bash
pytest -ra
```
Confirm:
1. Both files contain exactly 2,592 rows.
2. The `ID` column matches `data/raw/challenge/SampleSubmission.csv` row-for-row.
3. Every predicted target is strictly finite and non-negative ($Target \ge 0.0$).
4. The `.manifest.txt` files are written with Git commit hashes and output SHA-256 digests.

### Step 5: Final Submission on Zindi Platform
Upload `submission_C_refreshed_20261110.csv` and `submission_B_refreshed_20261110.csv` as the two final official submissions.
