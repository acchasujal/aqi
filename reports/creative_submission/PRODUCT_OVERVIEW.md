# AirWindow Mumbai 2.1

**Should you move your outdoor event?** AirWindow helps school sports coordinators and outdoor-event organisers compare an existing booking with feasible one-, two- or three-hour alternatives at four monitored Mumbai stations, then see whether forecast and historical evidence support further consideration. The verified static application is live at <https://airwindow-99085.web.app/>.

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

Live forecast source: audited TASK011 final P_fix, issued 10 November 2026 15:47:52 IST from the 10 November final Train release (SHA-256 `8adbcf55315f166d7dc3dc1d3e4d7400651f26c1d8b95ff387eef38f4e70a283`), with PM history through 09:00 IST and a validity horizon through 21 November 00:00 IST. Forecast CSV SHA-256: `f450b68212463f64bab67adfb0d98e1c4cce7ee83ec118f2564d38d738e34c13`. The earlier 8 November TASK008 artifact is retained as a byte-identical fallback. The 1,848-case historical replay remains the separate TASK008 retrospective simulation described above; it is not evidence of live forecast performance. The live forecast contains no current private actual targets.

## Schedule-baseline comparison

AirWindow's forecast-ranked choice is compared with two simple strategies using paired later-observed PM2.5 means. “Usual cleanest” selects the local start time with the lowest mean observed concentration in earlier origins; for the held-out confirmation split it uses development outcomes only. “Latest window” uses the latest-starting complete candidate. The reported value is AirWindow minus baseline, so negative means the AirWindow-selected window had a lower later-observed mean in that retrospective sample.

| Replay population | Baseline | Paired cases / origins | Mean and median delta | 95% origin-cluster bootstrap interval |
|---|---|---:|---:|---:|
| Full replay, expanding-origin | Usual cleanest | 1,414 / 76 | -2.28; 0.00 | [-5.72, 0.69] |
| Full replay, expanding-origin | Latest window | 1,411 / 77 | -0.16; 0.00 | [-2.34, 2.06] |
| Held-out confirmation | Usual cleanest | 169 / 8 | -0.73; 0.00 | [-2.64, 0.54] |
| Held-out confirmation | Latest window | 170 / 8 | -1.01; 0.00 | [-2.66, 0.16] |

All four pooled intervals span zero. Per-origin mean paired deltas use a 0.01 ug/m^3 tie tolerance. Held-out usual-cleanest origins split 4 favouring AirWindow / 4 the baseline / 0 ties; latest-window origins split 5 / 3 / 0. Equal-origin Student-t intervals are [-3.79, 1.23] and [-3.55, 0.72] ug/m^3; both include zero. Exact two-sided sign-test p-values are 1.000 and 0.727. These small-sample checks are exploratory and do not establish superiority. The held-out sample has only eight origins and was previously inspected by analysts; overlapping scenarios within origins are dependent. Paired coverage excludes cases missing either observed window outcome, and the replay retains those missing cases in its overall counts. The exact calculation and source replay hash are in `apps/airwindow/public/data/baseline_comparison.json` and are reproducible with `apps/airwindow/baseline_comparison.py`.

The four stations are Borivali East, Malad West, Byculla and Shivaji Nagar. Each is a measurement proxy and may not represent a particular school ground or event venue; no station is described as nearest or most representative. They do not support street/building exposure maps or cleanest-route claims. Hourly PM2.5 is not presented as official Indian AQI. No safe/healthy, medical, personal-dose or measured health-benefit claim is made. Official CPCB/government sources remain the place for health guidance.

## Google tools and availability

The static React/Vite application uses bundled artifacts and deterministic logic, with no runtime external API requirement. Firebase Hosting serves the verified public static app at https://airwindow-99085.web.app/. The existing Firebase billing tier has not been independently verified. The reproducibility notebook is Colab-compatible and demonstrates the evidence calculation; its code cells were run locally, not in a verified Google-hosted Colab session. Neither Firebase Hosting nor Colab is a runtime dependency.

Source: [acchasujal/aqi - main branch](https://github.com/acchasujal/aqi/tree/main). Local run and build commands are in the app README. The human must still verify a public link and submit the creative form; this package is not a form-processing confirmation.

## AirWindow 2.1 finish - 9 November

The audit preserved genuine artifact bytes and scheduler behavior while improving forecast-first replay, all-candidate inspection, runtime corruption checks/retry, actual observation-age context, historical lead-specific validation inspection, keyboard result focus and the brief's peak/cutoff details. Supporting mobile text is larger. See AIRWINDOW_FINAL_COMPLETION_REPORT.md for final tests and remaining platform actions. The contribution is an inspectable scheduling decision, with no new-to-world or measured user-impact claim.
