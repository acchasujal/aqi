# EXP-013 horizon profile

PM interval-end cutoff: `2026-11-02T23:00:00+05:30`; model run time used for this snapshot: `2026-11-07T12:00:00+05:30`.
The two clocks are distinct. Leads use target interval start minus each station's latest eligible PM interval end.

| Station ID | Rows | Minimum h | Median h | Maximum h |
|---:|---:|---:|---:|---:|
| 11606 | 48 | 193 | 216.5 | 240 |
| 11611 | 48 | 193 | 216.5 | 240 |
| 3409510 | 48 | 193 | 216.5 | 240 |
| 3409511 | 48 | 193 | 216.5 | 240 |

| Target date (IST) | Rows | Minimum h | Median h | Maximum h |
|---|---:|---:|---:|---:|
| 2026-11-11 | 96 | 193 | 204.5 | 216 |
| 2026-11-12 | 96 | 217 | 228.5 | 240 |

Overall: 192 private-window target rows; lead 193–240h, median 216.5h.
Each station has one row per lead hour from 193 through 240 on this snapshot. All 192 rows fall in the 193–240h lead bucket. Per-date and per-row detail is in `PRIVATE_HORIZON_ROWS.csv`.
For comparison, the locally documented revised public window (November 3–4) has 192 rows and leads 1–48h on this snapshot. The public-page date differs from the local dictionary; see `COMPETITION_REQUIREMENTS.md`. Older Test dates before the PM cutoff are not treated as live future targets.
