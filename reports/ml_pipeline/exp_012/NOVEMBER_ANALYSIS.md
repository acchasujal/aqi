# EXP-012 November analysis

Historical November rows come from the official Train release, chiefly November 2025. The same dates recur across nominal gaps, so the rows are not independent replications. No November 11–12 2026 labels are available. Full-target RMSE includes every labelled row; no extreme target is edited or removed.

| Model | 48h | 72h | 96h | 120h | 192h |
|---|---:|---:|---:|---:|---:|
| Original W50 | 64.365 | 67.486 | 72.918 | 75.818 | **62.252** |
| Median72 | 65.377 | 68.783 | 74.265 | 78.468 | 67.566 |
| Median24 | 64.009 | 67.902 | 73.432 | 77.676 | 64.639 |
| Median48 | 65.053 | 68.424 | 73.839 | 77.948 | 65.146 |
| Trend48 | 64.951 | 68.305 | 73.743 | 77.857 | 65.082 |
| Hybrid W50/M24 | **63.713** | **67.353** | 72.789 | 76.297 | 62.865 |
| Calendar W50 | 64.513 | 67.610 | **71.991** | **75.029** | 62.387 |

The hybrid improves 48/72/96h November RMSE but worsens 120h and the competition-style 192h gap. The original W50 is best at 192h, the most relevant lead diagnostic. This prevents calling the hybrid a validated private-window challenger. Exact rows, MAE and diagnostics are in `NOVEMBER_METRICS.csv`.
