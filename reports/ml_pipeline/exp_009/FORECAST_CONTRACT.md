# EXP-009 Forecast contract

At an explicit, timezone-aware PM interval-end cutoff, eligible station PM observations have `target_start < cutoff` and nonmissing PM. The recent estimate is the median of eligible observations with `target_start >= cutoff - 72 hours`; if that window is empty, use the median of all eligible station history. Missing PM is never zero. The 2024 seasonal feature retains the EXP-007 archive loader, station mapping, ±14 DOY window, and hour-of-day computation.

- Both estimates available: 50% recent median + 50% seasonal mean.
- Recent only: recent median.
- Seasonal only: seasonal mean. This is a source-derived prior, not an invented constant.
- Neither: explicit `ValueError`; no prediction can be submitted. Historical OOF cannot score that row and must report coverage.
- Invalid negative/nonfinite component: explicit `ValueError`. Extreme but finite nonnegative observations remain eligible; no clipping or target editing.

`recent_median72` and `combine_forecasts` in `forecast.py` implement the shared policy. Validation and production call both. The public `median72` baseline is unchanged.
