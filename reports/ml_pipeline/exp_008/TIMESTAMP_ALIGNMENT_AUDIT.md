# EXP-008 — Timestamp alignment audit

## Evidence

The 2024 archive uses `timestamp_ist` strings with `+05:30`; the `cpcb_caaqm` rows examined are all at minute `:00` and have predominantly one-hour adjacent timestamp spacing. The `us_embassy` rows use `:30` timestamps and are not part of the current seasonal feature source. `collected_at` and `timestamp_ist` represent source timestamps in IST. Neither the archive nor `HistoryNotes.txt` defines whether a `:00` timestamp labels the start, end, or instant of a one-hour measurement. `HistoryNotes.txt` explicitly says averaging intervals have not been fully aligned to current OpenAQ hour-ending targets.

The challenge dictionary defines Train `timestamp_ist` as the **end** of its hourly interval; test `target_start_ist` is the **start**, and `target_end_ist` is the end. Thus the current seasonal code's use of archive timestamp hour as target hour is an assumption, not a verified alignment.

## Findings and disposition

- Timestamp frequency: hourly modal frequency, with missing hours; exact counts are in `STATION_PROVENANCE_AUDIT.md`.
- Timezone: IST (`+05:30`) explicitly represented; the loader converts to `Asia/Kolkata`.
- Interval semantics: **UNKNOWN**. A minute-zero timestamp distribution does not distinguish start/end/instantaneous semantics.
- One-hour offset: plausible unresolved hypothesis. −1h, 0h, and +1h require controlled matched validation only after mapping ambiguity is resolved. No shift is adopted.
- Leakage: a seasonal lookup over a fixed 2024 archive has no future-within-2026 leakage, but an interval shift must preserve the target's calendar/hour key and must not use target-year observations. This cannot validate source identity.
- Leap handling: existing code uses raw day-of-year and 365-day modular arithmetic on 2024 (leap) vs targets (mostly 2026 non-leap). This is a confirmed calendar-key inconsistency: after Feb 29, equivalent month/day dates differ by one DOY. November dates are not directly affected by the Feb 29 insertion (same month/day is one DOY higher in leap 2024), but a ±14 DOY window shifts its calendar edges by one day. This is a testable correction, not evidence of score improvement.

No alignment alternative was run because the source-to-target series mapping is unresolved. Historical timestamp intervals remain an explicit blocker to asserting exact hourly alignment.
