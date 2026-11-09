# EXP-014 November-focused evidence

The fixed validation schedule includes two November 2025 target windows (November 1 and November 8). This is **reused exploratory evidence**, not an unseen confirmation period. There are 430 public-shaped and 426 private-shaped labeled rows per model. No November row in these folds reaches 500 µg/m³; their full-target RMSE is therefore also their ordinary-range diagnostic RMSE.

| Model | Public November RMSE | Private November RMSE |
|---|---:|---:|
| Existing W50 | 35.3695 | **44.2262** |
| LightGBM squared error | 41.5373 | 70.4791 |
| CatBoost RMSE | 60.7442 | 73.8402 |
| CatBoost Huber | **29.3171** | 63.0407 |
| HistGradientBoosting squared error | 31.1403 | 77.1367 |
| LightGBM residual correction | 40.2940 | 86.7622 |

The robust CatBoost model improves the public-style November score by 6.05 RMSE but worsens private-style November by 18.81. The actual competition's final evaluation is the private November 11–12 window, so this transfer risk is decisive against promoting the supervised model. The November windows contain incomplete station-hour coverage, and archive provenance remains unresolved. Detailed rows and prediction ranges are in `NOVEMBER_RESULTS.csv`; fold metrics are in `FOLD_RESULTS.csv`.
