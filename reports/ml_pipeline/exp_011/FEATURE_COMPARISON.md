# EXP-011 Feature comparison

Archive 2024 source, 10:00 IST target hour, current station substring mapping and pooling. Counts are nonmissing source rows; added/removed compare selected archive rows.

| Station | Target | Legacy range | Corrected range | Legacy n | Corrected n | Added | Removed | Δ seasonal mean |
|---|---|---|---|---:|---:|---:|---:|---:|
| Borivali East | 2026-11-11 | 2024-10-27–2024-11-24 | 2024-10-28–2024-11-25 | 58 | 58 | 2 | 2 | 1.1529 |
| Borivali East | 2026-11-12 | 2024-10-28–2024-11-25 | 2024-10-29–2024-11-26 | 58 | 58 | 2 | 2 | 0.8676 |
| Malad West | 2026-11-11 | 2024-10-27–2024-11-24 | 2024-10-28–2024-11-25 | 87 | 87 | 3 | 3 | -0.5401 |
| Malad West | 2026-11-12 | 2024-10-28–2024-11-25 | 2024-10-29–2024-11-26 | 87 | 87 | 3 | 3 | -0.7566 |
| Byculla | 2026-11-11 | 2024-10-27–2024-11-24 | 2024-10-28–2024-11-25 | 29 | 29 | 1 | 1 | -0.5479 |
| Byculla | 2026-11-12 | 2024-10-28–2024-11-25 | 2024-10-29–2024-11-26 | 29 | 29 | 1 | 1 | -1.2310 |
| Shivaji Nagar | 2026-11-11 | 2024-11-24–2024-11-24 | 2024-11-24–2024-11-25 | 1 | 2 | 1 | 0 | nan |
| Shivaji Nagar | 2026-11-12 | 2024-11-24–2024-11-25 | 2024-11-24–2024-11-26 | 2 | 3 | 1 | 0 | nan |

Full numeric values are in `FEATURE_COMPARISON.csv`. The same-hour and ±14-day definitions are preserved. This comparison is descriptive; model validation determines whether the correction helps.
