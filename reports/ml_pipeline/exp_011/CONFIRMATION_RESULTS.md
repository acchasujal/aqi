# EXP-011 confirmation results

The last 20% of fold dates, beginning `2026-06-25T23:00:00+05:30`, were held out from candidate design. This chronological split was also used for EXP-010 reporting, but no EXP-010 outcome was used to choose the calendar rule. All three models use identical matched rows within each gap; archive 2024 observations end before the earliest 2025 validation fold. No confirmation target is ≥500 and there are no November confirmation targets.

| Gap | Rows | Legacy W50 RMSE | Calendar W50 RMSE | Improvement | Calendar folds better / worse |
|---:|---:|---:|---:|---:|---:|
| 48h | 2,675 | 9.355311 | 9.218785 | +0.136526 | 7 / 10 |
| 72h | 2,759 | 9.465675 | 9.412620 | +0.053055 | 6 / 12 |
| 96h | 2,877 | 10.505046 | 10.466760 | +0.038286 | 8 / 10 |
| 120h | 2,935 | 12.721731 | 12.667543 | +0.054188 | 9 / 9 |

Station-wise pooled confirmation RMSE (legacy → corrected): Borivali 11.322 → 11.208, Malad 11.035 → 10.875, Byculla 9.852 → 9.855, Shivaji Nagar 10.367 → 10.374. The last two are small regressions. Aggregate improvements are small and occur while more individual folds worsen at three gaps. Thus confirmation does not establish stable superiority.

November development folds are mixed: corrected versus legacy RMSE at 48h 64.513 vs 64.365 (worse), 72h 67.610 vs 67.486 (worse), 96h 71.991 vs 72.918 (better), 120h 75.029 vs 75.818 (better). This fails the criterion of no material November-relevant regression only weakly, but together with fold instability argues against promotion. November confirmation is unavailable.
