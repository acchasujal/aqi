# Challenge Specification

**Snapshot date:** 2026-11-06. Verify the live official page before final submission; this is a versioned working spec, not a substitute for organiser instructions.

## Objective

Forecast hourly PM2.5 concentration in µg/m³ at four Mumbai CPCB CAAQMS stations. The competition metric is RMSE (lower is better).

## Required output

- `ID`: exactly the IDs and row order from `Test.csv`.
- `Target`: finite, numeric, non-negative PM2.5 predictions.
- One prediction for every one of the 2,592 test rows, including rows not currently included in public/private scoring.
- Do not modify IDs or infer labels from ID formatting.

## Target stations

Coordinates and identifiers are recorded in `data/raw/challenge/Stations.csv`. The audited station names and coordinates are:

| Station | Location ID | Sensor ID | Latitude | Longitude |
|---|---:|---:|---:|---:|
| Borivali East | 11606 | 12236418 | 19.232410 | 72.868950 |
| Malad West | 11611 | 12236426 | 19.197090 | 72.822040 |
| Byculla | 3409510 | 12238567 | 18.976700 | 72.838000 |
| Shivaji Nagar | 3409511 | 12238576 | 19.060498 | 72.923356 |

Timezone: Asia/Kolkata (IST, UTC+05:30).

## Data timeline in the uploaded 5 November dictionary

- Train release audited: 47,849 observations, spanning 2025-02-19 through 2026-11-02 23:00 IST.
- Test grid: 27 days × 24 hours × 4 stations = 2,592 rows.
- Uploaded dictionary says the current public window after the 5 November update is 3–4 November (revised); next public window 5–6 November; private evaluation 11–12 November.
- The live Info page has also described the 5 November public window as 1–2 November. Treat this as unresolved until organiser clarification; see `EVALUATION_AND_RULES.md`.
- Final Train update was advertised for 10 November 2026 at 09:00 IST; final submission deadline was advertised as 10 November 2026 23:59:59 IST.

## Evaluation focus

The organiser evaluation discussion states that the latest valid submission is evaluated on the private period 11–12 November. The supplied dictionary says 192 private rows. Verify whether all 192 rows (48 per station) are the exact final prize-scoring rows.

## Important distinction

The 2,592-row file is a fixed submission grid, not a claim that all 2,592 targets are used in a particular leaderboard score. Never train on hidden target values or use post-deadline observations.
