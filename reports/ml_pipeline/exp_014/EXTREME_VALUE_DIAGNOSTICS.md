# EXP-014 extreme-label diagnostics

The two fixed stress days, 2025-08-09 and 2026-05-09, contain **five** `y ≥ 500` station-hours in each public/private regime. The same labels are evaluated under different historical cutoff states; they are not ten independent events. Their official values include Borivali East **75,203.525** and **25,007.455** µg/m³ and three Byculla values of **1,762.91**, **3,320.6333**, and **1,643.1375**. The Borivali and Byculla records are unique in Train and were already flagged/inspected in EXP-013. No record is automatically called erroneous. All raw labels remain in primary RMSE and training.

The five extreme rows contribute **99.9862%** of public W50 squared error and **99.9797%** of private W50 squared error on these 11-day comparisons. Full-target pooled RMSE is therefore about 1,914 in public and 1,918 in private, even though ordinary-range RMSE is around 19–34. The CatBoost Huber training objective reduces runaway predictions, but it does not remove or relabel any target.

| Model | Public full RMSE | Public `y < 500` RMSE | Private full RMSE | Private `y < 500` RMSE |
|---|---:|---:|---:|---:|
| W50 | 1913.7996 | 22.5466 | 1918.1655 | **27.3418** |
| CatBoost Huber | **1913.6724** | **18.6724** | **1918.1244** | 34.0943 |
| LightGBM squared error | 1925.8700 | 217.2678 | 1934.3400 | 252.8469 |
| CatBoost RMSE | 1917.4185 | 122.2710 | 1928.9699 | 208.4481 |
| HistGradientBoosting | 1916.6220 | 108.5759 | 1921.1263 | 114.7640 |
| LightGBM residual | 1917.6424 | 124.0888 | 1926.2135 | 178.8743 |

With the **stress dates** removed as a diagnostic only, W50 versus CatBoost Huber RMSE is **23.3504 versus 19.1268** for public-shaped rows and **29.0587 versus 37.0120** for private-shaped rows. This confirms that the robust model has a real public ordinary-range signal but substantial private-horizon regression. Diagnostic filtering never replaces the full-label comparison. Squared-error models' validation prediction maxima range from about 1,258 to 2,973 µg/m³, while W50 remains below 88 in these folds; the large learned outputs are a practical reliability concern.
