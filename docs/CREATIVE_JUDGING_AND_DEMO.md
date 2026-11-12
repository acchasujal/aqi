# AirWindow Mumbai 2.1 - Judging evidence and demo

Current public static deployment: https://airwindow-99085.web.app/. Verified release and artifact status are recorded in `reports/creative_submission/AIRWINDOW21_FINAL_TASK_RECORD.md`.

## Official criteria

The [official challenge page](https://zindi.world/competitions/google-mumbai-data-challenge) lists impact, novelty and functionality, with bonus consideration for Google tools. Creative deadline: 13 November 2026 18:29 GMT (23:59 IST). No numeric weights are published. Recheck form access and eligibility; the 19 November presentation and separate 20 November closing-event references remain distinct.

## Internal review rubric

This is our review checklist, not the judges' scoring formula.

| Criterion | Evidence |
|---|---|
| Impact | A sports coordinator's original booking, feasible constraints and shareable event brief. No invented interviews or health impact. |
| Novelty | Original-versus-alternative decision, paired OOF replay and abstention, compared with established forecast/map/alert services. |
| Functionality | Real data, correct contiguous-hour calculations, working controls, mobile/keyboard journey, print output and clear missingness. |
| Google tools | Firebase Spark preparation or verified deployment plus executable Colab-compatible evidence notebook. State exactly what ran. |
| Integrity | Issue/cutoff/lead lineage, station-only coverage, unmodified historical truth and no fabricated confidence. |

## 60-second judge journey

The opening asks **Should you move your outdoor event?** Choose a monitored station, existing booking, duration and feasible range. Compare shows the original and lowest forecast alternative with a prominent evidence state. Trust and replay are discoverable secondary routes, not prerequisites to understand the result.

## 90-second demonstration

| Time | Demonstration |
|---|---|
| 0-10s | A school coordinator can move a two-hour event; a city-wide number does not compare those actual options. |
| 10-25s | Select a real station and set original booking/range. Show last observation and frozen snapshot label. |
| 25-45s | Compare original versus alternative mean, peak, hourly path and signed concentration difference. |
| 45-60s | Read the reliability state. Current evidence is uncalibrated: lower prediction alone is not a robust recommendation. Show comparable counts and lead. |
| 60-78s | Open genuine retrospective replay, show later outcomes and all-case results including failed choices. |
| 78-90s | Print the planning brief. Explain four-station limits and the reproducible static architecture. |

Use an ordinary default case, not a hand-picked win. A historically worse choice is an honest demonstration of forecast risk. Do not fabricate a ROBUST state.

## Package and fallback

The creative report folder holds overview, red-team review, detailed demo, checklist, real screenshots, PDF and checks. The PDF covers user/problem, differentiator, workflow, evidence, architecture, Google tools, provenance, limits and verified links, below 10 MB.

For network failure, run the built static app locally with bundled genuine artifacts and use real screenshots. Record a 90-second screen capture after fixing final artifact/build hashes; a recording plan is not a completed video. A public URL must pass signed-out and mobile checks before availability is claimed.

## Submission gate

Reopen the official form and confirm required fields/document size. Use matching Zindi entrant details and keep eligibility documents private. The human submits or explicitly authorises submission and saves confirmation. A ready app/PDF does not prove form submission.

## 9 November verification update

The official challenge page was reopened and still states 13 November 18:29 GMT (23:59 IST), impact/novelty/functionality and a Google-tools bonus. The linked Google Form redirects to a form endpoint that returned 401 to a public read; current response status/fields/upload requirements need a signed-in human check. Earlier supplied form fields are preparation evidence, not a fresh form verification. Show forecasts first in replay, then click **Reveal subsequent observations** and retain a worse outcome. Built-static Chrome QA and a locally executed six-cell notebook support functionality; Firebase and cloud Colab execution remain unclaimed. Main is the current source branch.
