# AirWindow Mumbai 2.0 - Product specification

**Product:** the confidence-aware outdoor activity scheduler.

**Audience:** school sports coordinators and outdoor-event organisers.

**Tagline:** Don't just check the air. Make a better-timed plan, and know whether the forecast is reliable enough to justify changing it.

## Product thesis

A coordinator already has a two-hour event booked and can move it within a feasible range. AirWindow compares that original event with complete alternative windows at one of four actual CPCB stations, then explains whether historical evidence supports acting on the difference.

The signature combines constraints, original-versus-alternative comparison, paired historical decision replay and honest abstention. Existing services already provide maps, forecasts and alerts; no first-in-Mumbai or universal superiority claim is justified. This independent challenge prototype complements official services.

## Core workflow

1. Select Borivali East (11606), Malad West (11611), Byculla (3409510) or Shivaji Nagar (3409511). Show exact location and latest eligible observation timestamp.
2. Set the original start and duration of one, two or three hours. Derive the original end and keep it visible.
3. Set earliest feasible start and latest feasible end within the artifact horizon. Enumerate hourly starts only; every hour in each window must be present, consecutive and valid.
4. Compare the original and lowest predicted alternative: mean, maximum, peak hour, individual hourly predictions and signed difference.
5. Inspect the reliability state and other feasible windows. A numerical rank alone never establishes that moving is justified.
6. Explore genuine historical replay and print a one-page event brief with evidence and limitations.

## Decision states and evidence

| State | Meaning |
|---|---|
| ROBUST IMPROVEMENT | Reserved for adequate comparable support and independently validated chronological decision reliability. Current artifacts cannot claim it without that evidence. |
| TENTATIVE IMPROVEMENT | An alternative has lower predicted concentration, but reliable improvement is not established. |
| NO CLEAR WINNER | Complete options are tied or validated evidence cannot distinguish them. |
| INSUFFICIENT EVIDENCE | Comparable station/duration/lead evidence cannot support a reliability estimate. |

Calibration status is separate from case count. Overlapping hourly comparisons are not independent forecast origins. TASK008 supplies genuine retrospective rolling-origin OOF forecasts with fixed PM cutoffs and unmodified truth. Interval-end availability is a proxy, not verified first publication; historical confirmation has prior analyst exposure. Therefore the current app must not display calibrated probabilities or uncertainty intervals or claim independent confirmation.

The deterministic evidence build pairs original and alternative windows from the same origin, station, duration and comparable lead range. It compares predicted with later observed differences and preserves origin dependence in block resampling. Report case and origin counts, relevant station/lead RMSE, calibration status, exclusions and limitations. Document sufficiency criteria and method; do not invent thresholds in UI components.

## Historical Decision Replay

Replay is a separate retrospective artifact. A judge selects an origin, station and duration; sees what the model knew, its original slot, feasible forecasts, the selected lower-forecast window, later observations and whether the choice was actually better.

Aggregate metrics cover all eligible declared decision cases, including failures: lower-observed fraction for numerical selections, median realised difference, hindsight gap to the best observed feasible slot, coverage and origin counts, overall and by station/duration. Distinguish numerical selections from calibrated recommendations. No health benefit or personal exposure reduction is measured.

## Trust centre and missingness

Show model ID/version, code/data fingerprints, generation/issue time, PM cutoff, latest station observation, target intervals and actual leads. Weather fields stay null unless weather was used. Display the actual validation population, sample/fold counts and unmodified-target metrics.

Missing forecasts stay missing. Missing original hours prevent comparison; incomplete alternatives are excluded with a reason. Invalid schemas fail visibly. Historical/stale artifacts are labelled snapshots, not a continuously refreshed service. Never extrapolate beyond available horizon.

## Architecture and contracts

Preserve the existing live forecast contract/validator and temporal invariants; see [the contract](FORECAST_ARTIFACT_CONTRACT.md) for its versioned migration. The separate replay contract retains origin, cutoff, training lineage, target intervals, predictions and subsequent released historical observations. Hidden/private actuals never enter app artifacts.

The Python build step owns artifact export, paired evidence and classification, without training a new model. React + Vite + TypeScript owns interaction and transparent window arithmetic. No account, database, health-data collection, chatbot or runtime external API is required. A station locator may show four actual points; no interpolated heatmap.

Prepare Firebase Hosting Spark without paid billing. A Colab-compatible evidence notebook is reproducible support, not a live dependency. Hosting configuration does not prove deployment; record a public URL only after authorised project access and successful checks.

## Printable brief

Show station/location, original time/duration, alternative when available, forecast means and peaks, difference, reliability state/reason, issue/cutoff/last observation, model version, validation counts and limitations. Preserve abstention. This is a planning comparison, not a statement that an event is safe.

## Acceptance criteria

- Opening question: **Should you move your outdoor event?** The core form and comparison should take a judge under 60 seconds; actual timing is QA, not a user-study claim.
- Real artifact arithmetic and working controls; original and alternative remain visible.
- Live logic cannot use retrospective actuals; replay is explicitly labelled.
- Evidence states are honest, unsupported probability/interval fields remain null and abstention is prominent.
- Four actual stations only; no streets/routes/exposure estimates, hourly-to-AQI conversion, medical advice or safe/healthy labels. Refer health questions to official CPCB/government guidance.
- Missing/invalid/stale data and impossible ranges have actionable states; desktop/mobile, keyboard and print work.
- Tests cover contracts, contiguous hours, bounds, arithmetic, original slot, clocks/leakage and reliability support.
- Judging package uses real screenshots/evidence and a PDF under 10 MB; deployment is verified or explicitly pending with commands.
