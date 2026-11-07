# EXP-009 Parity audit

Starting commit: `9d3fad0afb25b3247bb564464a5e6a090e107444`; isolated branch `feature/exp-009-forecast-parity`. EXP-008 changes remain uncommitted in a different worktree. Current production flow is `predict_test_with_hist24_blend` in `forecast.py`; validation flow is `_seasonal_baseline_for_fold` and `rolling_oof_seasonal` in `validate_seasonal_history.py`.

| Component | Before correction | Classification / impact |
|---|---|---|
| Station IDs and seasonal lookup | Both call the same name-fragment based `build_seasonal_features` | Same behavior; provenance ambiguity from EXP-008 remains |
| PM cutoff | Production gates by issue time and feature cutoff; validation uses fold cutoff | Intentional issue-time distinction, but both must use interval end <= PM cutoff |
| Recent median | Production uses a 72-hour window anchored to explicit cutoff, with all-history median fallback; validation anchors to latest grid hour and uses last value fallback | Confirmed defect in sparse histories; potentially different estimates |
| Missing recent history | Production raises before seasonal lookup; validation can emit seasonal only | Confirmed defect; missing-station rows may be excluded from OOF |
| Missing seasonal history | Both use median72 | Consistent |
| Both missing | Production fails; validation omits prediction | Different handling; shared contract now raises, OOF leaves row unscored when no prediction exists |
| Blend | Both nominally 50:50 | Consistent for valid nonnegative finite estimates |
| Negative/nonfinite estimates | Production clips output, validation skips nonfinite and clips output | Confirmed processing difference; shared helper rejects invalid inputs explicitly |
| Timestamp interpretation | Both use same archive loader and seasonal features | Same unresolved archive interval and leap-year assumptions |

No station mapping, archive timestamp, or leap-year correction is made in EXP-009.
