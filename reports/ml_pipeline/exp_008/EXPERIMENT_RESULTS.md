# EXP-008 — Experiment results

**Status: BLOCKED / audit-only.** Phase A identified a non-target station pooled by substring and unresolved duplicate series at the target coordinates for Borivali and Malad. Per task instructions, implementation and forecasting validation stop before changing feature generation when source mapping is not defensible.

## Planned matched comparison

The EXP-007 baseline uses 48-hour target windows, 7-day fold spacing, nominal gaps of 48/72/96/120 hours, with exact station-specific gaps recorded in row-level outputs. Its report contains aggregate metrics. EXP-008 did not recompute or compare any candidate on those folds, so there is no EXP-008 matched metrics table to report.

| Candidate | Result | Reason |
|---|---|---|
| A: median72 | Not rerun | Audit-only gate stopped this task; existing EXP-007 report gives a historical control but not re-evaluated here |
| B: original hist24_blend50_median72 | Not rerun | Original feature generator confirmed to substring-match and pool source series |
| C: source-separated blend | Not evaluated | Borivali and Malad source-series selection cannot be justified from supplied crosswalk evidence |
| D: alternative timestamp alignment | Not evaluated | Interval semantics unknown and source mapping unresolved |
| E: calendar-alignment correction | Not evaluated | Confirmed leap-year key inconsistency; correction has no matched metrics yet |

No full-target RMSE, MAE, station/horizon/fold metrics, November subset, extreme-error contribution, or candidate coverage metrics are claimed for EXP-008. Validation labels remain untouched. No OOF predictions or generated datasets were written. A separate validation/inference fallback discrepancy was confirmed by code inspection and captured in `tests/test_seasonal_history.py`; its focused regression test passes by asserting both sides of the mismatch. Production fallback behavior was not changed.

## Corrective evidence needed to resume

Obtain an authoritative XKDR/source-owner crosswalk or documented canonical-series rule for `site_5113` vs `site_5400` and `site_5102` vs `site_5402`, plus confirmation of interval semantics. If no such evidence is available, a future experiment may compare each series as a separately named sensitivity analysis, but must not label an arbitrary series as the target match or promote it based on validation score.
