# EXP-009 Final recommendation

**NEEDS REVIEW.** Shared logic removes the confirmed fallback and recent-window discrepancies; actual 2,592-row production predictions are byte identical. Matched OOF metrics shift slightly. The existing fold generator skips stations with no prior PM history, so seasonal-only coverage remains unmeasured in full OOF. Review this limitation and EXP-008 provenance before merge. No push, merge, or Zindi submission occurred.

The final full-suite run had 45 passes and one repeat failure in the pre-existing ExtraTrees exact-equality test, despite an intervening full pass. This instability is outside EXP-009 code but means the final suite gate is not consistently green. Focused parity and seasonal tests pass (21 tests).

## Acceptance update (EXP-010 preflight)

Repeated seeded ExtraTrees fits on base commit `9d3fad0` differed by at most `3.552713678800501e-15` in five direct paired runs, under NumPy 2.3.5, pandas 2.3.3, scikit-learn 1.8.0 and `n_jobs=2`. The exact-equality assertion failed on the base and EXP-009 checkouts. The test now uses `np.testing.assert_allclose` with `rtol=0, atol=1e-12`; ExtraTrees production configuration is unchanged. This is a narrowly justified test correction for pre-existing numerical roundoff.
