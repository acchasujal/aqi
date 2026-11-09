# EXP-012 validation diagnostics

Audited 346 `(gap, fold)` combinations from EXP-011 accepted legacy W50 OOF. All raw target labels were retained. Fold-level detail is in `FOLD_QUALITY.csv`.

November-containing combinations: 18; labelled November rows counted across gaps: 2473. These reuse the same historical dates across gaps and are not independent. November 2026 in Train ends November 2, leaving no comparable November 11–12 2026 labels. The strongest analogous period is November 2025, but one year cannot establish stable seasonal generalization.

Maximum fold target: 241587.563 µg/m³. Folds with targets >500: 21. Maximum extreme squared-error contribution in one fold: 100.00%. The official comparison remains full-target RMSE; ordinary-range RMSE is diagnostic only.

## Competition-style lead addendum

The 192h diagnostic adds 86 `(gap, fold)` combinations, bringing the audit to 432. It has 13,999 matched scored rows per model. Actual station-specific PM observation-to-target gaps are recorded in `FOLD_QUALITY.csv` and `CANDIDATE_DIAGNOSTICS.csv`; the median is 218h on development rows and 216h on reused late-2026 rows. In the 192h development set, 17 targets ≥500 account for 99.88% of W50 squared error. This makes 0.027 RMSE differences between models weak evidence. The 192h November subset has 889 scored rows, drawn from a small number of 2025 dates and reused across the candidate comparison. No November 11–12 2026 labels are available.
