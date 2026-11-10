# TASK012 — selective VayuDrishti research transfer

**Date:** 10 November 2026 (IST)
**Branch:** `main`, starting `58fd180a50394b3c595a4d2b75b9fd5e694e3114` (equal to local `origin/main`)
**Result:** Selective experiments completed. No submitted CSV, raw challenge input, or production forecast behavior changed.

## Findings

The transferable ideas were (1) an explicit station-level shrinkage calibration with parameters fit on earlier origins, and (2) a compact residual model around a stable forecast prior. Both were reimplemented in isolated research code, not copied from VayuDrishti. The reference's causal feature cutoff pattern also reinforces our existing fixed-origin design. The reference's training-target cleaner is not transferable: it uses centered windows and bidirectional interpolation, and its cleaned labels are built globally before the multi-cutoff training examples are sliced. Its reported validation scores also fit the ensemble optimizer on the same OOF rows it reports. See [REFERENCE_TECHNIQUE_AUDIT.md](REFERENCE_TECHNIQUE_AUDIT.md).

No weather or spatial candidate was fitted. Historical weather issue-time mapping and source eligibility remain blocked. Auxiliary stations have no verified mapping/coordinates/release clock and the supplied series stop on 16 October, so they do not provide contemporaneous private-inference readings. CAMS/NWP analogs, wind transport, ST-GAT and foundation forecasts remain untested or blocked. The current environment lacks PyTorch, TimesFM 3, Chronos, CatBoost and XGBoost.

## Rebuilt controls

From the final frozen Train snapshot, the runner rebuilt 84 scheduled weekly origins (2 April 2025 through 4 November 2026), 16,128 station-hour rows, 12,731 raw labelled rows, and 83 labelled origins. The first 60 labelled origins were the calibration-development period. The last 23 origins, 3,545 labelled station-hours, were reserved for forward evaluation. Each block is 48 hours with a 15-hour initial gap; fitting at a given origin uses only prior OOF examples whose full target block ended by that origin's PM cutoff. All validation labels remain raw and unchanged.

| Control, all 83 labelled origins | Full-target RMSE | MAE | Bias | Diagnostic RMSE, y < 500 |
|---|---:|---:|---:|---:|
| P_fix | 2391.7163 | 48.5044 | -36.4632 | 17.3970 |
| P_fix + 10% diur7 | 2391.7244 | 48.2705 | -36.6142 | 17.1126 |
| P_fix + 25% diur7 (B25) | 2391.7375 | 48.0024 | -36.8407 | 16.8076 |
| P_fix + 50% diur7 (B50) | 2391.7619 | 47.7965 | -37.2183 | 16.6408 |
| Median168 | 2391.5041 | 48.7220 | -39.7669 | 17.9569 |

The eight labels at or above 1,000 remain in scoring; they dominate squared error. Median168 has the lowest nominal all-origin RMSE by 0.212 over P_fix, while having worse `y < 500` RMSE and MAE. That tiny difference is not a credible reason to replace the better-supported P_fix/B50 controls. Diur7 standalone is unsupported on some rows; its exact missing count is in `control_metrics.csv`. Per-origin, station, lead and station/lead results are in `control_group_metrics.csv`; prediction/residual correlations are in `control_prediction_residual_correlations.csv`.

## Experiment A — station-specific shrinkage

For each station, the tested prediction was `P_fix + alpha_station * (B50 - P_fix)`. One global alpha, four unconstrained station alphas, and station alphas partially pooled toward the global value were estimated only on the development origins. A dimensionless ridge precision grid was selected on those development origins; the selected strength was `lambda = 1`.

| Forward candidate, last 23 origins | Full-target RMSE | MAE | Bias | Paired moving-block delta vs P_fix (95% interval) |
|---|---:|---:|---:|---:|
| P_fix | 11.1934 | 7.7401 | -1.8727 | — |
| B50 | 10.4333 | 6.9754 | -2.5077 | -0.7601 [-1.1878, -0.2621] |
| Global alpha | 11.1934 | 7.7401 | -1.8727 | 0.0000 [0.0000, 0.0000] |
| Unregularized station alpha | 10.6894 | 7.2587 | -1.9593 | -0.5040 [-0.7678, -0.0809] |
| Development-selected regularized station alpha | 10.8791 | 7.4455 | -1.9160 | -0.3143 [-0.4510, -0.0839] |

B50 beat P_fix on 18/23 forward origins. Every forward label is below 500, so this full-target forward score contains no extreme event; the intervals use moving blocks of four origins and do not establish performance under the rare extreme failures. B50's forward improvement is useful complementary evidence, while P_fix remains the broad OOF primary because the full 83-origin raw RMSE is slightly lower and extreme-label risk remains unresolved. The station-shrunk model improves over P_fix, but loses to B50 by 0.4458 RMSE (paired interval `[+0.1373,+0.7541]`); it is rejected as a new promoted candidate.

Station/lead diagnostics show the B50 gain is broad: it is lower in 11 of 12 station/lead groups, with one small Byculla near-lead loss (+0.075 RMSE). Regularized alpha is lower than P_fix in 9 groups and tied in Shivaji Nagar's three groups. Full per-group values and complete 48-hour origin blocks are saved in `station_shrinkage_station_lead_metrics.csv`, `station_shrinkage_fold_metrics.csv`, and `paired_origin_differences.csv`.

## Experiments B/C — causal target treatment and residual model

The compact model predicts `y - P_fix` using existing permitted calendar, station, lead, recent-level, diur7 and archive features. Each fold uses only eligible past OOF training examples. Missing values are imputed inside each training fold. Evaluation labels are never changed.

| Forward candidate | Training treatment | Full-target RMSE | MAE | Bias | Result |
|---|---|---:|---:|---:|---|
| Huber residual | Raw labels, Huber loss | 11.6382 | 7.4760 | -2.8167 | Loses to P_fix and B50 |
| Ridge residual | Raw labels, squared loss | 345.5608 | 143.4888 | +126.9359 | Severe failure from large historical residuals |
| Ridge residual | Training labels >=1,000 replaced by median of 24 prior eligible observations | 11.8761 | 7.6611 | -2.1943 | Loses to P_fix and B50 |

The past-only treatment changed 184 training labels across the 23 repeated forward fits (the 8 high labels reappear in eligible histories); it never changed validation labels. `flag_high_1000` treatment was not fitted because historical prediction-time availability of that flag is unverified. Neither robust loss nor the tested causal replacement earned promotion. Details are in `causal_cleaning_metrics.csv` and `residual_model_metrics.csv`.

## Promotion and eligibility decisions

- **PROMOTE as a complementary forward-regime candidate:** B50 reduces raw full-target RMSE by 0.760 on the 23-origin forward set, 18/23 origin wins, paired moving-block interval excluding zero. Keep P_fix as the broad primary control; do not overwrite or regenerate any official submitted CSV.
- **REJECT:** new station-alpha calibration (does not beat B50), Huber/Ridge residual challengers, reference cleaner, model-zoo stack, and any claim based on the reference's headline scores.
- **BLOCKED:** CAMS/NWP prior, ventilation/wind features and meteorological analogs pending historical run-availability policy and source eligibility.
- **REJECT for final inference:** auxiliary-station spatial transport due to identity, coordinate, interval, release-time and final-snapshot coverage failures.
- **NOT RUN:** foundation/GNN zoo; required packages are absent, weather covariates are blocked, and matched residual-diversity evidence does not exist.

P_fix and B50 remain the most defensible distinct controls for the current task. The complete 83-origin raw metric nominally favors Median168 by 0.212 due to the extreme rows, but that model has worse clean-range RMSE and MAE; the task's previous complete-block pair analysis also favors B50 + P_fix as the two-model pair. No private-period performance is claimed.

## Reproduction and review

```powershell
.venv/Scripts/python.exe scripts/run_task012.py
.venv/Scripts/python.exe -m pytest tests/test_task012.py tests/test_task011.py -q -p no:cacheprovider --basetemp data/processed/task012-focused-tests
.venv/Scripts/python.exe -m ruff check scripts/run_task011.py scripts/run_task012.py src/mumbai_pm25/oof_cache.py tests/test_task012.py
.venv/Scripts/python.exe -m py_compile scripts/run_task011.py scripts/run_task012.py src/mumbai_pm25/oof_cache.py
git diff --check
```

The OOF/config/input fingerprint and exact 84-origin schedule are in `oof_manifest.json` (OOF SHA-256 `d280f06a8bb244b48e5faa12c919a4ff0a8758de4e32a8c45a34a62c0736291e`). Two complete runner executions produced the same OOF and coverage SHA-256 values. The original TASK011 cache is now reused only when a JSON sidecar exactly matches hashes of all five data inputs, relevant source files, model configuration, fold schedule, and the OOF/coverage artifact bytes; a missing, altered, or stale sidecar forces a rebuild. Focused tests passed 6/6; full suite passed **147 tests** with 19 existing Pandas warnings. Scoped Ruff, `py_compile` and `git diff --check` passed. Remote `main` was verified at the starting SHA before the staged diff review; the final read-only `git ls-remote` retry failed because GitHub network access became unavailable. Publication is pending that network gate.

No raw challenge files were modified. P_fix (`f450b682...e34c13`), B25 (`96aff853...a1c6f2d1`), and war-room B50 (`b4d60181...798904`) submission hashes were preserved.
