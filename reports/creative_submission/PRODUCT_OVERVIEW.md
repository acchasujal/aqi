# AirWindow Mumbai 2.0

**Should you move your outdoor event?** AirWindow helps a school sports coordinator compare an existing booking with feasible one-, two- or three-hour alternatives at four monitored Mumbai stations, then see whether the forecast evidence is strong enough to justify a change.

The product combines a constraint-aware scheduler, original-versus-alternative comparison, honest reliability/abstention, genuine Historical Decision Replay and a printable event brief. Its contribution is a reproducible decision workflow. It does not claim to be Mumbai's first air-quality forecast or map; see `RED_TEAM_REPORT.md` for the prior-art comparison.

## What the decision means

The scheduler ranks complete consecutive forecast hours by mean PM2.5 and shows the maximum, peak hour, individual predictions and difference from the original. The original always remains visible. Missing hours stay missing; an incomplete original cannot be compared, and an incomplete alternative cannot rank.

Reliability is separate from numerical ranking. The four supported states are ROBUST IMPROVEMENT, TENTATIVE IMPROVEMENT, NO CLEAR WINNER and INSUFFICIENT EVIDENCE. Current evidence is **not calibrated**; no current artifact earns calibrated recommendation probabilities, uncertainty intervals or a robust recommendation. An explicit inability to distinguish the options is a valid result.

## Genuine retrospective evidence

The frozen replay uses TASK008 P_fix rolling-origin OOF predictions. Every case uses forecasts from one recorded simulated origin, with PM history frozen before its cutoff. Outcomes are later released historical observations. Forecasts were generated retrospectively on 8 November 2026 under an interval-end availability proxy; they are not archived real-time vintages. Historical confirmation has prior analyst exposure and does not establish independent calibration.

The declared school scenario uses a 09:00 original booking and feasible 08:00-18:00 range, each duration 1/2/3 hours, both target days, four stations and all 77 matched origins:

| Evidence | Result |
|---|---:|
| Declared decision cases | 1,848 |
| Forecast origins | 77 |
| Cases with paired original/selected observed outcomes | 1,469 across 76 origins |
| Cases retaining missing outcomes | 379 |
| Numerically lower alternatives with paired outcomes | 1,291 |
| Those alternatives with lower subsequently observed PM2.5 | 63.67% |
| Median selected minus original observed mean, for those 1,291 numerical alternatives | -1.17 µg/m³ |
| Median hindsight gap when every feasible window's observed comparison is complete | 2.06 µg/m³ across 1,221 cases |
| Paired cases without complete hindsight comparison | 248 |
| Calibrated recommendations | 0 |

The 63.67% is a descriptive historical fraction, **not a confidence probability for a current event**. It also shows that roughly 36% of numerical alternatives were not lower in the later observations. Missing outcomes stay in the coverage denominator rather than disappearing. Overlapping duration/day cases are dependent; origin counts are reported and exploratory resampling uses contiguous origin blocks. Source: `apps/airwindow/public/data/replay.json`, `manifest.json` and `apps/airwindow/evidence/replay_diagnostics.json`.

Later confirmation comprises eight origins and 192 declared cases, 180 paired outcomes and 158 numerical alternatives; 60.76% of those alternatives had lower observed concentration. This is an analyst-exposed chronological diagnostic, not independent probability validation.

Underlying P_fix full-target, raw-scale RMSE is 757.9880 on 11,001 development rows/69 origins and 15.7963 on 1,400 later rows/eight origins. Eight extreme development labels contribute 99.846% of squared error; later rows contain no such extremes. These populations are not interchangeable, and ordinary-regime replay does not demonstrate reliable extreme-event forecasting. Station/lead results remain visible in the trust evidence.

## Provenance and limits

Forecast source: current-snapshot TASK008 P_fix, issue 8 November 2026 15:58 IST, latest PM interval end 2 November 23:00 IST. Training hash: `fcee20ebf7bd9c4a4e2487bab0a4f81339d6c820a53862b14443031db1f18ad6`. Original prediction CSV hash: `3d79cffcca78cea1ad6f5e24d2568bf931bbba8c3b15fcd7db1728462050ab1d`. The live artifact exports only future forecast hours at issue time, with genuine timestamps and explicit model/source fingerprints. It contains no current private actual targets.

The four stations are Borivali East, Malad West, Byculla and Shivaji Nagar. They do not support street/building exposure maps or cleanest-route claims. Hourly PM2.5 is not presented as official Indian AQI. No safe/healthy, medical, personal-dose or measured health-benefit claim is made. Official CPCB/government sources remain the place for health guidance.

## Google tools and availability

The static React/Vite application uses bundled artifacts and deterministic logic, with no runtime external API requirement. Firebase Hosting Spark configuration and commands are prepared; deployment is blocked by absent authenticated CLI/project access, so no public hosting URL is claimed. The reproducibility notebook is Colab-compatible and demonstrates the evidence calculation; that does not imply execution on Google-hosted compute.

Source branch: [acchasujal/aqi - existing feature branch](https://github.com/acchasujal/aqi/tree/feature/task008-final-gap-execution). Local run and build commands are in the app README. The human must still verify a public link and submit the creative form; this package is not a form-processing confirmation.
