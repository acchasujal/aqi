# AirWindow 2.1 final gap audit

Task AIRWINDOW21, 9 November 2026. Baseline main and fetched origin/main both
`dba644a1d0e7394794335dc2d98c2d64c548633c`; working tree clean before work.
Scope: existing creative app, tests and award documents only. No model/data refresh.

| Area | Existing state | Remaining problem | Required action | Priority | Evidence |
|---|---|---|---|---|---|
| Scheduling | COMPLETE | Original and complete consecutive candidates already implemented | Preserve arithmetic, rerun checks | P0 | domain.ts; 9 baseline domain tests pass |
| Scientific integrity | COMPLETE | Frozen P_fix, no calibrated recommendations | Preserve artifact bytes and separate replay | P0 | manifest.json; 139 baseline Python tests pass |
| First minute | IMPROVE | Audience and observation-age context could be clearer | State coordinator audience and actual elapsed PM age | P1 | main.tsx hero and station detail |
| Replay | IMPROVE | Actuals immediately visible; ranked candidate list absent | Forecast-first view, reveal outcomes, complete ranked candidates | P1 | ReplayCaseView; artifact already has windows |
| Runtime boundary | IMPROVE | Replay metadata check cannot reject malformed cases | Validate runtime case structure and arithmetic before rendering | P0 | shallow fetch check in main.tsx |
| Trust and brief | IMPROVE | Brief lacks explicit PM cutoff and peak time; trust lacks horizon | Add exact clocks, horizon and peak time | P1 | EventBrief; EvidenceView |
| Accessibility/error paths | IMPROVE | Existing checks omit replay failure and narrow/zoom keyboard paths | Add browser regressions and review captures | P1 | five baseline browser tests |
| Branch documentation | IMPROVE | Active source links and repository plan reference feature branch | Point active instructions to main; preserve historical logs | P1 | source footer; CREATIVE_TRACK_REPO_PLAN.md |
| PDF | IMPROVE | Audited five-page 157,195-byte PDF has old branch link | Rebuild only after final captures; inspect all pages | P1 | PDF audit and builder |
| Firebase | BLOCKED | Config exists; CLI, .firebaserc and saved CLI login absent | Exact existing-Spark-project handoff; no project creation | P0 | local command/path presence checks |
| Colab | IMPROVE | Local notebook exists; requires checkout | Execute cells, add direct Colab link/setup instructions | P1 | Decision_Replay.ipynb |
| Official requirements | PENDING HUMAN ACTION | Official page confirms 13 Nov 18:29 GMT; short form inaccessible to web tool | Recheck form via available route; human completes identity/submission | P0 | https://zindi.world/competitions/google-mumbai-data-challenge |
| New forecast / calibration | NOT REQUIRED | No authorised refreshed official input or independent calibration | Retain frozen issue/cutoff and abstention | P0 | owner instructions |

Baseline commands: root `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --basetemp data/processed/airwindow21-python-tests`: 139 passed, 19 existing pandas warnings, 20.24s. App `npm.cmd test`: 9 passed. `npm.cmd run build`: passed. Browser host unavailable through CUA; user-requested installed-Chrome Playwright QA remains available. Final outcomes and resolved gaps are recorded in AIRWINDOW_FINAL_COMPLETION_REPORT.md.

## Final disposition

| Area | Final status | Resolution / remaining gate |
|---|---|---|
| First minute, replay, runtime boundary, trust, brief | COMPLETE | Implemented and verified; exact changes in completion report |
| Local accessibility/usability | COMPLETE | Keyboard, labels, larger supporting text, 320/390px and 720px reflow; native zoom/dialog and screen-reader certification not verified |
| Main links and active instructions | COMPLETE | Reconciled; older integration records remain historical |
| PDF and local notebook | COMPLETE | Five A4 pages/162376 bytes; every page inspected; six notebook cells reproduce metrics |
| Public deployment | BLOCKED | No CLI/project/login; actual Spark plan cannot be verified |
| Official form | PENDING HUMAN ACTION | Endpoint returned401; owner checks current fields/response status and submits |
| New forecast/calibration | NOT REQUIRED | Frozen artifact bytes preserved; no new scientific claims |

Full exact commands, hashes, review limits and publication record are in
AIRWINDOW_FINAL_COMPLETION_REPORT.md. Git publication is separate from cloud
hosting and human award submission.
