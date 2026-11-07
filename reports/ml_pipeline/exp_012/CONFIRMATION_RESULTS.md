# EXP-012 reused late-2026 comparison

The split at `2026-06-25T23:00:00+05:30` was set before EXP-012 candidate scores were inspected. These late-2026 folds have already appeared in EXP-010/011 analyses, so they are **not independent confirmation**. The hybrid was the provisional development candidate at the 192h competition-style lead; its development RMSE was 747.126 versus W50 747.153, a 0.027 difference with 99.88% of W50 squared error from 17 targets ≥500. Development non-extreme 192h rows collectively favor W50, and 39 of 69 development folds worsen under the hybrid.

| Gap | W50 RMSE | Hybrid RMSE | Hybrid fold wins / losses |
|---:|---:|---:|---:|
| 48h | 9.355 | 8.374 | 15 / 2 |
| 72h | 9.466 | 8.555 | 15 / 3 |
| 96h | 10.505 | 9.426 | 14 / 4 |
| 120h | 12.722 | 11.445 | 15 / 3 |
| 192h | 12.479 | 11.130 | 12 / 5 |

At 192h the hybrid improves all four stations on reused late-2026 folds: Borivali 11.225→10.245, Malad 14.809→13.162, Byculla 11.879→10.011, Shivaji Nagar 11.737→10.856. This is a promising signal for ordinary pollution levels; that set has no ≥500 targets and no November targets. It cannot independently validate transfer to the private November period or extreme regime. Do not infer leaderboard improvement from these offline results.
