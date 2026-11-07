# EXP-013 extreme-value sensitivity

Primary metrics retain **all 13,244 labeled rows** and use the unmodified official `pm25` labels. On the matched 193–240h rows, original W50 full-target RMSE is **690.2117**. The diagnostic RMSE on rows with `y < 500` is **23.7411**. The 17 rows with `y ≥ 500` contribute **99.8818%** of W50 squared error. This explains why very small changes to forecasts around extreme events dominate the pooled full-target ranking. The diagnostic cannot replace the full-target metric.

Two Borivali East readings on 2025-08-09 at 13:00 and 14:00 IST have official labels **75,203.525** and **25,007.455 µg/m³**. They contribute **89.5967%** and **9.8979%** of total W50 squared error, respectively, or **99.4946% combined**. Their official Train records are unique station-hours, both from `openaq:12236418`, with `count=4` and `flag_high_1000=True`. Other extreme clusters occur at Shivaji Nagar in October/November 2025 and Byculla in May 2026. All 17 extreme station-hours join one-to-one to Train; the full Train has no duplicate `(location_id, target_start)` keys. These flags and magnitudes warrant source-quality investigation, but they do not establish that the labels are wrong. No label was clipped, excluded, replaced, or used as a predictive flag.

| Locked model | Full RMSE | Diagnostic RMSE, `y < 500` | November full RMSE |
|---|---:|---:|---:|
| Original W50 | 690.2117 | 23.7411 | **62.6158** |
| EXP-012 hybrid | **690.1778** | 23.8298 | 63.1823 |
| Median72 | 690.2467 | 26.1052 | 67.9001 |
| Calendar-corrected W50 | 690.2088 | **23.6938** | 62.7498 |

The hybrid's **0.0339** full-target RMSE gain over W50 is small beside the extreme-event contribution, while its ordinary-range and November diagnostics are worse. In 85 paired folds, hybrid RMSE improves 44 and worsens 41 versus W50. This does not establish reliable superiority at the live November horizon, particularly because all rows were previously inspected. No extreme labels were removed from the primary comparison.
