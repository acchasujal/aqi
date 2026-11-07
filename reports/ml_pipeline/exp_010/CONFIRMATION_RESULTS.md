# EXP-010 confirmation results

Chronological confirmation begins at fold cutoff `2026-06-25T23:00:00+05:30` (last 20% of distinct fold dates). It was held out from weight selection. All five weights share row keys within each gap. W0 was the provisional challenger from pooled development full-target RMSE, compared with W50 and the recent-only control (W0 itself). The confirmation period contains **zero** targets ≥500, so it cannot establish performance on extreme-value regimes.

| Gap | W0 RMSE | W50 RMSE | W0 rows | W0 fallback % |
|---:|---:|---:|---:|---:|
| 48h | 8.751106 | 9.355311 | 2,675 | 0.00 |
| 72h | 8.940241 | 9.465675 | 2,759 | 0.00 |
| 96h | 10.148410 | 10.505046 | 2,877 | 0.35 |
| 120h | 12.482781 | 12.721731 | 2,935 | 1.06 |

Pooled confirmation RMSE: W0 10.239058, W50 10.642804 (11,246 rows). W0 has lower squared error on 12 of 18 confirmation fold dates when pooling gaps, but cross-gap targets can overlap, so those are not 18 independent experiments. Station-wise confirmation RMSE: Borivali 9.656 vs 11.322; Malad 11.110 vs 11.035; Byculla 9.984 vs 9.852; Shivaji Nagar 10.150 vs 10.367 (W0 vs W50). Thus W0 has small regressions at Malad and Byculla even in confirmation.

Development pooled RMSE was W0 1883.266538 versus W50 1883.387394, a 0.121 difference. The same 2025-12-03 extreme observations appear in both 96h and 120h comparisons. The top two `(gap, fold)` gains from the 2025-11-27 fold exceed the total pooled gain, while non-extreme rows collectively *favor W50* by 4,267,925 squared-error units. Hence W0's development advantage is driven entirely by extreme observations in one historical window, repeated across gaps. The confirmation set has no comparable extremes. W0 fails the predeclared robustness condition and is rejected.

Development November-focused RMSE favored W50 at all four gaps (48h 64.365 vs W0 65.377; 72h 67.486 vs 68.783; 96h 72.918 vs 74.265; 120h 75.818 vs 78.468). No November confirmation rows were available. This is diagnostic, not a substitute for full-target RMSE.
