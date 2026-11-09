# EXP-009 Before/after production comparison

Reference: commit `9d3fad0afb25b3247bb564464a5e6a090e107444`, Train snapshot at PM cutoff `2026-11-02T23:00:00+05:30`, model run time `2026-11-07T12:00:00+05:30`, model `hist24_blend50_median72`, weight 0.5. Reference and corrected files are stored only in ignored `data/processed/`; neither is a submitted artifact. The generated manifests record input SHA-256 hashes and environment.

| Item | Before | After |
|---|---:|---:|
| Rows | 2,592 | 2,592 |
| CSV SHA-256 | `55e2fc8c7cad94db22f1358a8715216b0c7fbbb7a50c728c4413890f6a8716bc` | Same |
| Changed row predictions | — | 0 |
| Maximum absolute difference | — | 0 |
| Minimum prediction | 32.96853448275862 | Same |
| Maximum prediction | 93.4375 | Same |

Exact ID order and finite nonnegative values are checked by the inference command. The current snapshot exercises normal cases, so it does not establish behavior for sparse-history fallback; synthetic parity tests cover that case.

Input hashes are in the two ignored inference manifests. They match because the same `Train.csv`, `Test.csv`, and `AdditionalHistory.zip` paths were used for both commands.
