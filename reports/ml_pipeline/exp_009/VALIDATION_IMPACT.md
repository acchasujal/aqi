# EXP-009 Validation impact

Matched on `(fold_id, location_id, target_start)`; existing EXP-007 OOF is control. Labels unchanged. 48-hour windows, 7-day spacing.

| Gap h | Rows | Changed | Old RMSE | New RMSE | Old MAE | New MAE | Max abs Δ |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 48 | 13,528 | 11,056 | 43.117188 | 43.119655 | 12.858444 | 12.853845 | 6.141042 |
| 72 | 13,060 | 10,707 | 490.901000 | 490.902210 | 18.483074 | 18.481174 | 11.716667 |
| 96 | 13,177 | 10,869 | 2348.741105 | 2348.748850 | 48.541170 | 48.588205 | 11.716667 |
| 120 | 13,395 | 11,019 | 2331.454295 | 2331.463624 | 48.674948 | 48.763018 | 11.716667 |

Differences arise from the explicit-cutoff recent median and all-eligible-history median fallback. The old validator anchored to its latest grid hour and fell back to last observation. Production CSVs are byte identical. Station and horizon diagnostics are in adjacent CSVs. Fold construction still skips stations with no prior PM record, so seasonal-only fallback frequency is not estimable from these OOF files; synthetic parity tests cover it.
