# Architecture and Experiment Decisions

This is an append-only decision log. Do not rewrite old decisions. If a decision is reversed, add a new entry that references the old ID.

## DECISION AIRWINDOW21-P1 (2026-11-12)

- **Decision:** Keep the frozen 77-origin replay support, four-station footprint, and current 1–3-hour event durations. Do not add stations, extend event durations, or claim scheduled refresh/user research from this pass.
- **Evidence:** Existing locked origin support covers 77 of 83 schedules; four early 2025 origins fail the predeclared common-OOF minimum-training-row gate, while two origins have no paired labels. External station listings did not establish a verified identity crosswalk, raw hourly coverage, first-publication clock, reuse terms, or model support. An eight-hour comparison may be illustrated, but there is no safety or validation evidence for longer real event durations. No usability sessions were conducted and the frozen forecast pipeline is issue-specific, not a general refresh system.
- **Confidence:** High for preserving the existing replay and for not overstating evidence; medium on the reason each external listing is unusable because source exports and exact terms were not independently audited.
- **Alternatives considered:** Add apparent Mumbai monitor listings or infer longer-event value from the 248-hour forecast horizon. Rejected because monitor provenance/coverage and event decision validity are not established by those facts.
- **Consequences / revisit trigger:** Current UI and submission state these limits. Revisit with a sourced station crosswalk, prediction-time/terms audit, matched model validation, or a funded and consented usability protocol.

## Decision record format

- **ID:** DEC-YYYYMMDD-NN
- **Date / owner:**
- **Status:** Proposed | Accepted | Rejected | Superseded
- **Context:**
- **Decision:**
- **Evidence:** file, experiment ID, source URL or exact finding
- **Confidence:** High | Medium | Low
- **Alternatives considered:**
- **Consequences / revisit trigger:**

---

## DEC-20261106-01 — Repository structure and raw-data immutability

- **Date / owner:** 2026-11-06 / project owner + AI assistant
- **Status:** Accepted
- **Context:** Multiple AI agents may work in parallel and must share a stable source of truth.
- **Decision:** Keep raw challenge inputs under `data/raw/challenge/`; generated data under `data/processed/`; external downloaded weather under `data/external/weather/`; reusable Python code in `src/mumbai_pm25/`; scripts in `scripts/`; tests in `tests/`; experiments and reports separate. Raw challenge files are immutable.
- **Evidence:** Uploaded challenge files and DataDictionary; see `docs/DATA_AUDIT.md`.
- **Confidence:** High
- **Alternatives considered:** Keeping data and code mixed at repository root; rejected because it complicates reproducibility and agent work.
- **Consequences / revisit trigger:** If the existing repository layout already has a different stable convention, update the path config once rather than duplicating raw files.

## DEC-20261106-02 — Forecasting architecture is baseline-first, not deep-learning-first

- **Date / owner:** 2026-11-06 / project owner + AI assistant
- **Status:** Accepted as initial plan; final model selection remains open
- **Context:** Claude's initial rolling tests found simple recent station profiles competitive with a small LightGBM model; the final evaluation is short and time-dependent.
- **Decision:** Establish recent station level/diurnal baselines first; test a compact LightGBM ratio-to-recent-level model and a simple blend only if matched rolling-origin full-target RMSE supports it. Do not begin with TFT, LSTM, complex stacking or broad static GIS features.
- **Evidence:** `PLAN_Zindi_Mumbai_PM25.md` supplied by Claude; validation scripts in `validation_code.zip`; see `docs/VALIDATION_PROTOCOL.md`. The reported model comparisons remain provisional because primary full-target results and exact reproducibility need review.
- **Confidence:** Medium
- **Alternatives considered:** Immediate neural forecasting or large model zoo; rejected until evidence justifies complexity.
- **Consequences / revisit trigger:** Add model complexity only when multiple identical folds show repeatable incremental benefit.

## DEC-20261106-03 — Full-target RMSE is the primary selection metric

- **Date / owner:** 2026-11-06 / project owner + AI assistant
- **Status:** Accepted
- **Context:** Extremely high recorded PM2.5 values exist; Claude's report uses `y < 500` for some diagnostics.
- **Decision:** Report RMSE on every labelled validation row as the primary metric. `y < 500` RMSE may be reported only as a separate diagnostic. Never select a model solely from filtered RMSE.
- **Evidence:** Competition evaluation uses RMSE; train file includes large values. See `docs/DATA_AUDIT.md` and `docs/VALIDATION_PROTOCOL.md`.
- **Confidence:** High
- **Alternatives considered:** Excluding spikes from the reported primary metric; rejected because it does not match the competition objective.
- **Consequences / revisit trigger:** If organisers confirm an explicit target-cleaning/evaluation rule, update with a new decision.

## DEC-20261106-04 — Weather is a priority experiment, subject to time-valid runs and permission

- **Date / owner:** 2026-11-06 / project owner + AI assistant
- **Status:** Proposed pending data terms and organiser confirmation
- **Context:** Final PM2.5 history may be stale, while a forecast made close to submission can provide a fresh forward-looking signal.
- **Decision:** Test archived individual forecast runs (initially ECMWF IFS HRES) against no-weather baselines. Do not use a stitched historical forecast series as if it were a full multi-day forecast vintage. Include only model runs available by the pseudo-issue time.
- **Evidence:** Open-Meteo Single Runs documentation: https://open-meteo.com/en/docs/single-runs-api ; Historical Forecast documentation: https://open-meteo.com/en/docs/historical-forecast-api . Competition-specific ClimateVerse permission and Open-Meteo API terms require confirmation; see `docs/EXTERNAL_DATA_POLICY.md`.
- **Confidence:** Medium on methodology; Low on expected score benefit and legal/terms clearance.
- **Alternatives considered:** Reanalysis or stitched history as the only weather training signal; rejected as insufficiently representative of actual forecast vintage/availability.
- **Consequences / revisit trigger:** Do not integrate weather into final model until legal/organiser permission and rolling validation support it.

## DEC-20261106-05 — Year-over-year features remain experiments, not assumptions

- **Date / owner:** 2026-11-06 / project owner + AI assistant
- **Status:** Proposed
- **Context:** The same 11–12 November 2025 period contains high Shivaji Nagar observations; a one-year seasonal hint may be informative but one prior year is weak evidence.
- **Decision:** Test previous-year same-hour PM2.5, robust local aggregates and missingness indicators in rolling validation. Do not hardcode a spike or upward offset.
- **Evidence:** Supplied Train.csv and Claude's `spikes.py`/plan; validate from actual row-level labels.
- **Confidence:** Low–Medium
- **Alternatives considered:** Always repeat the previous-year spike; rejected as unjustified.
- **Consequences / revisit trigger:** Keep only if it improves multiple full-target folds without leakage.

## DEC-20261106-06 — Conservative compliance posture while rules conflict

- **Date / owner:** 2026-11-06 / project owner + AI assistant
- **Status:** Accepted pending organiser clarification
- **Context:** Competition info page generic terms and organiser-specific discussion contain conflicting limits and selection language.
- **Decision:** Respect the stricter 10 submissions/day and 140 total limit until confirmed otherwise. Use only challenge files and datasets listed in the named ClimateVerse catalogue, subject to licence and prediction-time checks. Keep the intended final submission clearly recorded; if the interface requires selecting two, select two deliberately, while retaining the latest-valid approach described in the organiser evaluation announcement.
- **Evidence:** Official info page https://zindi.world/competitions/google-mumbai-data-challenge ; organiser discussion https://zindi.world/competitions/google-mumbai-data-challenge/discussions/35761 and https://zindi.world/competitions/google-mumbai-data-challenge/discussions/35663 . See `docs/EVALUATION_AND_RULES.md`.
- **Confidence:** Medium pending direct confirmation.
- **Alternatives considered:** Following the generic 300-submission limit; rejected until the organiser clarifies the stricter competition-specific statement.
- **Consequences / revisit trigger:** Record organiser response verbatim and issue a new decision.

## DEC-20261106-07 — AirWindow consumes a versioned ML artifact

- **Date / owner:** 2026-11-06 / Codex
- **Status:** Accepted for the creative foundation; contract is awaiting owner approval.
- **Context:** The repository has no reusable PM2.5 inference/export command, no committed forecast artifact, no station-level validation table and no interval calibration. The only saved prediction rows are ignored legacy OOF pickles.
- **Decision:** Keep AirWindow as a separate static client that consumes a versioned ML forecast artifact. It will not train an independent model in the browser or publish fabricated forecast values. The artifact contract carries independent model issue time, PM-history cutoff and weather issue time; unavailable freshness/validation values remain explicitly unknown/null; prediction intervals remain null until calibrated.
- **Evidence:** Repository audit in `reports/creative_submission/INTEGRATION_AUDIT.md`; contract in `docs/FORECAST_ARTIFACT_CONTRACT.md`; product constraints in `docs/CREATIVE_PRODUCT_SPEC_AIRWINDOW.md` and `docs/CLAIMS_AND_USER_SAFETY.md`.
- **Confidence:** High on separation and provenance requirements; medium on contract field names pending owner review.
- **Alternatives considered:** Train a second model in the client; rejected because it would duplicate the ML pipeline and lack reproducible validation evidence. Embed sample predictions; rejected because they could be mistaken for real forecasts.
- **Consequences / revisit trigger:** Do not build the full frontend or add a public forecast artifact until the owner approves schema version 1.0.0 and the ML pipeline can generate and validate real artifacts.

## DEC-20261106-08 — Keep a 72-hour station median as the inference control

- **Date / owner:** 2026-11-06 / Codex
- **Status:** Accepted as a simple control; not a final winner
- **Context:** TASK 003 established a leakage-safe baseline ladder on the current four-station release. Rare extreme targets dominate full-target RMSE, while fold-level variability is much larger than the small differences between baselines.
- **Decision:** Use the station-specific median of eligible PM observations in the preceding 72 elapsed hours as the reproducible inference control, with fallback to all eligible station history if that window is empty. Keep last observation and the profile baselines as permanent matched controls. Do not introduce clipping or outlier deletion.
- **Evidence:** `reports/ml_pipeline/evaluation/summary.md`, `EXP-20261106-005`: median72 full-target RMSE was 43.98/490.97/2348.57/2331.27 at nominal gaps 48/72/96/120; last-value was 49.73/491.59/2343.94/2325.63. Fold RMSE standard deviations were 41.97/462.99/2501.12/2564.66 for median72, and extreme targets accounted for 61–100% of its squared error.
- **Confidence:** Medium that this is a robust simple control; low that it is superior for the final unseen window.
- **Alternatives considered:** Last-value; wins at longer gaps but has higher clean-range error. Diurnal and hour-of-week profiles; no reliable full-target advantage. Supervised LightGBM; no compatible binary wheel on the validated Windows ARM64 runtime. Weather; external permission/terms remain unresolved.
- **Consequences / revisit trigger:** Keep the selection provisional. Rerun all baselines on the final advertised Train refresh and retain median72 only if matched full-target OOF evidence remains credible. Never represent this result as private/test performance.

## DEC-20261107-09 — Reject calendar-only ExtraTrees for inference

- **Date / owner:** 2026-11-07 / Codex
- **Status:** Rejected
- **Context:** After the baseline ladder was established, one Windows ARM64-compatible supervised candidate was tested to determine whether station and calendar structure alone could improve the history controls.
- **Decision:** Do not expose the calendar-only ExtraTrees candidate in the production inference command. Keep its code and OOF outputs for reproducibility; the default submission pipeline remains median72.
- **Evidence:** `reports/ml_pipeline/supervised_evaluation/summary.md`, `EXP-20261107-006`: 22 matched folds per gap. ExtraTrees full-target RMSE was 44.98/84.34/4467.34/4547.22 at gaps 48/72/96/120, worse than the best history control at every gap (18.19/20.96/4451.58/4529.99). Clean-range error was also much worse.
- **Confidence:** Medium for rejecting this calendar-only model; low for broader conclusions about supervised residual models that include PM history.
- **Alternatives considered:** Median72/last/EWM controls, which performed better; supervised residual-to-level models, not tested due time and no compatible LightGBM wheel; weather, excluded pending permission.
- **Consequences / revisit trigger:** Keep the inference CLI limited to the validated baseline. Revisit a supervised model only with a specific PM-history residual hypothesis, a compatible environment, and matched full-target OOF evidence.

## DEC-20261107-10 — Adopt 2024 seasonal history blend (hist24_blend50_median72) as production model

- **Date / owner:** 2026-11-07 / Lead ML Researcher & Forecasting Engineer
- **Status:** Accepted (supersedes DEC-20261106-08 median72 as default submission model)
- **Context:** TASK 004 audited `AdditionalHistory.zip` and tested whether 2024 same-station climatology improves forecasts under stale PM history conditions.
- **Decision:** Use a 50:50 blend of the station-specific recent 72-hour median and 2024 same-station, same-hour-of-day seasonal climatology (`hist24_blend50_median72`) as the production forecasting model. Filter `History_Mumbai_2024.csv.gz` to `source == 'cpcb_caaqm'` only. If seasonal data is unavailable, fall back transparently to `median72`. Reject all other archive members from target-station feature generation.
- **Evidence:** `reports/ml_pipeline/seasonal_history/REPORT_EXP_20261107_007.md`, `EXP-20261107-007`:
  - Full-target RMSE at gap 48h improved from 43.98 (median72) to 43.12 (blend).
  - Full-target RMSE at gap 72h improved from 490.97 (median72) to 490.90 (blend).
  - At gap 96h and 120h, full RMSE is virtually tied (2348.74 vs 2348.57, diff 0.17 relative to fold SD >2500).
  - Clean-range RMSE (<500) improved across ALL gaps: 20.94 vs 22.66 (gap 48h), 20.39 vs 22.23 (gap 72h), 21.00 vs 22.74 (gap 96h), 20.29 vs 21.93 (gap 120h).
  - MAE improved across ALL gaps: 12.86 vs 13.79 (gap 48h), 18.48 vs 19.50 (gap 72h), 48.54 vs 49.64 (gap 96h), 48.67 vs 49.90 (gap 120h).
  - At gap 48h, the blend beats median72 across **all 4 stations individually** and across **all 4 forecast horizon buckets**.
- **Confidence:** High for gap 48h and 72h regimes; Medium for longer horizons where rare extreme targets dominate RMSE.
- **Alternatives considered:** Pure `hist24_same_hour` without blend (poorer level tracking at gap 72h: 494.29 vs 490.90); standalone `median72` (fails to exploit diurnal cycle; higher MAE and clean RMSE); calendar-only ExtraTrees (already rejected in DEC-20261107-09).
- **Consequences / revisit trigger:** Update `train_predict.py` to support `hist24_blend50_median72` and explicit PM-history cutoffs. Re-evaluate on final 10 November Train refresh.

## DEC-20261108-11 — Retain P_fix as fallback; do not promote F4 yet

- **Date / owner:** 2026-11-08 / Codex
- **Status:** Provisional for the current Train snapshot; final refresh rerun required.
- **Context:** TASK 007 repaired exact archive-series handling and compared seasonal and LightGBM candidates at the current 193-hour target lead with fixed-origin 48-hour windows.
- **Decision:** Keep P_fix as the provisional fallback and keep F4 as an unpromoted challenger. Exclude Mindspace `xkdr:site_5807` from the Malad P_fix mapping; compare it only as a separately named candidate. P_fix uses Borivali `site_5400`, explicit Malad combination `site_5102` + `site_5402`, Byculla `site_5960`, and Shivaji Nagar `site_5961`.
- **Evidence:** At 193h, P_fix development full RMSE was 30.181 (2,820 rows/20 origins) versus F4 fixed 32.224; paired F4-P_fix delta +1.624, 95% moving-block interval [-0.860, 3.399]. The 318-row/two-origin holdout favored F4 (13.618) over P_fix (20.948), but has no extreme targets and is too small to establish robust promotion. Ratio B was 35.970 on development and 17.429 on holdout. See `reports/ml_pipeline/task007/TASK007_FINAL_REPORT.md` and `EXP-20261108-008`.
- **Confidence:** Medium that F4 should not be promoted on this evidence; Low about final competition ranking until refreshed data and more independent origins.
- **Alternatives considered:** Promote fixed F4 because of holdout gain; use median72. Rejected promotion because F4 loses development and only two held-out origins exist. Median72 remains the fallback if seasonal inputs fail validation.
- **Consequences / revisit trigger:** Use the provisional P_fix artifact only as a current-snapshot candidate. Recompute all cutoffs and validation after the final Train refresh. Reconsider F4 only if full-target RMSE gains replicate across more untouched origins, stations, lead buckets and extreme-event regimes.

## DEC-20261108-12 — TASK008 retains P_fix after common-origin comparison

- **Date / owner:** 2026-11-08 / Codex
- **Status:** Provisional; actual final official Train refresh and submission remain pending.
- **Decision:** Retain the reviewed exact-source P_fix mapping and 50:50 seasonal/recent blend; median72 remains explicit fallback. Keep TASK008 isolated from main and PR #4 unmerged. Do not promote the recent/diurnal, anomaly-decay, residual LightGBM or OOF blend candidates on the current snapshot.
- **Evidence:** `reports/ml_pipeline/task008/TASK008_FINAL_REPORT.md`, run01 matched 69 development origins/11,001 rows and eight later confirmation origins/1,400 rows, nominal PM gap 193h. Development best 50% P_fix + 50% median24 RMSE 757.9741 vs P_fix 757.9880; paired delta -0.01393, moving-block 95% interval [-0.05390,+0.44730], only 31/69 origin and 1/4 station wins. Confirmation improves to 13.7909 vs 15.7963 but has no extreme labels and prior analyst exposure. Source-sensitivity intervals cross zero. LightGBM delta/log-ratio/sqrt all lose development full RMSE. Raw labels and files unchanged; 53 tests pass, scoped lint passes; provisional P_fix output exactly matches Task007 v2.
- **Confidence:** High that promotion is unsupported by these gates; low about private-period ranking. Eight development extreme labels drive 99.846% of P_fix squared error, and the schedule does not include every historical extreme.
- **Alternatives:** Promote median24 blend based on later ordinary-regime gain; promote log-ratio LightGBM based on confirmation alone; switch Malad to one archive source. Rejected because development uncertainty/station stability fail and confirmation is not blind. Weather is NOT TESTED without verified permitted as-issued vintages; Vaibhav remains an unscored black-box reference with unknown issue lineage.
- **Consequences / revisit trigger:** Use `scripts/prepare_task008_submission.py` to freeze refreshed inputs and verify deterministic inference. Recompute actual station cutoffs/leads, check current organiser rules/UI and use legitimately new labels as confirmation of locked candidates. Final-data inference and Zindi processing require the real future release and human platform action/authorisation. Resolve main/PR conflicts separately before integration.

## DEC-20261108-13 — AirWindow 2.0 uses separate forecast/replay artifacts and honest abstention

- **Date / owner:** 2026-11-08 / Codex, parallel frontend/evidence/package contributors
- **Status:** Accepted for the creative prototype; no independent decision calibration or deployment claim.
- **Decision:** Upgrade the existing AirWindow product on the user-requested existing feature branch. Use a deterministic React/Vite/TypeScript event scheduler, retain the original slot, rank only complete consecutive hours, separate live forecast from historical replay, and allow abstention. Preserve schema 1.0 and add forecast 1.1 for exact fractional issue leads plus a separate replay 1.0 contract. No frontend training or ML behavior change.
- **Evidence:** Real TASK008 P_fix artifact and 1,848 predeclared replay cases across 77 origins; 1,469 paired outcomes over 76 origins, 379 missing. Of 1,291 numerical alternatives with paired outcomes, 63.67% were lower afterwards, median realised difference -1.17 µg/m³. Later confirmation is analyst-exposed; the descriptive rate is not a calibrated probability. Full Python integration 60 passed, final focused artifact tests 22 passed after annotation-only regeneration, frontend domain tests 9 passed, Chrome browser tests 5 passed, production build and relevant lint passed. Real screenshots and rendered one-page brief/submission PDF are under `reports/creative_submission/`.
- **Confidence:** High in tested deterministic scheduling, temporal separation and disclosed limits; insufficient evidence for robust live recommendations, probabilities, intervals, health benefits or superiority to established services.
- **Alternatives:** A generic map/lowest-hour dashboard, automatic numerical recommendation, invented confidence, dense spatial interpolation, external real-time weather/LLM/API dependency. Rejected because the four-station evidence and independent calibration do not support those claims. Red-team review documents prior art including existing constrained-window services; the product's defensible contribution is the auditable original-event comparison/replay/abstention workflow.
- **Consequences / revisit trigger:** Live issue lead and PM-information lead must both match evidence before a metric is described as relevant; otherwise show unavailable/insufficient evidence. Expired hours cannot be planned as future activity. No robust recommendation is issued by current artifacts. Firebase Spark configuration and a Colab-compatible notebook are prepared, with authenticated deployment and actual cloud execution unclaimed. Revisit calibrated recommendations only with independently validated chronological decision evidence, and refresh the forecast through the ML export path when genuine new inputs are available.


## 2026-11-08 ? Preserve explicit seasonal policies when integrating main

Decision: retain exact archive-identity P_fix for TASK008 and isolate historical EXP-007--015 calculations in legacy_seasonal.py, selected explicitly by existing experiment/CLI paths. Evidence: 107 tests pass; full W50 and P_fix inference hashes each reproduce their respective reviewed versions. Confidence: high for compatibility and integration, without a new score claim. Alternative: silently replace all legacy pooling/calendar behavior; rejected because it would invalidate prior experiment parity. Consequence: two clearly distinguished source policies remain supported, with regression gates. Reuse main per owner request.


## DEC-20261108-14 - Reject EXP-024 station calibrations for production

- **Date / owner:** 2026-11-08 / Codex
- **Status:** Rejected candidates; retain current provisional P_fix.
- **Context:** Owner requested analysis of five CSVs and pasted research/model suggestions. No B/C/Low generation lineage or new official labels were supplied.
- **Decision:** Keep identity-shrunk offset, affine and Huber calibration as reproducible experiments only. Do not change production inference, upload an unchanged candidate, or integrate black-box forecasts. AIFS-COMPO remains unavailable as an established pipeline input.
- **Evidence:** EXP-20261108-024, reports/ml_pipeline/exp024/REPORT.md and run02/. All three lose development and later full-target RMSE on the same 12,401 rows/77 origins. Later P_fix 15.796318 vs offset 22.110661 / affine 21.946022 / Huber 15.936059; all paired promotion gates fail. Official ECMWF announcement says underlying AIFS-COMPO data will be released in the future. Full suite 114 passed; raw hashes and 2,592-row production output fingerprint unchanged.
- **Confidence:** High that these fixed calibrations lack promotion evidence; low about final private ranking. Historical confirmation remains analyst-exposed.
- **Alternatives considered:** Arbitrary global reduction, selecting B/Low from public scores alone, promoting Huber for station/origin wins despite worse pooled RMSE. Rejected as unsupported by matched primary metrics or reproducible lineage.
- **Consequences / revisit trigger:** Preserve P_fix and the existing final-release guards. Revisit only with eligible B/C/Low provenance or genuinely new official labels and recalculated actual-gap validation. No new external data, targets or event multipliers added.


## DEC-20261108-15 - Retain P_fix after exact source-C reproduction

- **Date / owner:** 2026-11-08 / Codex
- **Status:** Rejected C promotion; B evaluation incomplete.
- **Context:** Owner identified the team B/C branch and the public Low repository, then confirmed B/C's author is on the registered team.
- **Decision:** Preserve production P_fix and keep the name-pooled C reconstruction isolated as an experiment. Do not merge the team's package rewrite or label Low's display builder a forecast trainer. B needs compatible CatBoost execution and actual-gap validation before promotion.
- **Evidence:** EXP-20261108-025, reports/ml_pipeline/exp025/REPORT.md and run02/. Original pinned C source and independent implementation both reproduce all 2,592 supplied values exactly. Matched 69 development/8 later origins give C full RMSE 758.020061/15.849352 vs P_fix 757.988014/15.796318; paired intervals cross zero. B computes its training gap from the earliest Test hour, yielding -287h clamped to48h rather than actual private193h. Low CSV and newline-normalized Train/Test match, but the inspected repo lacks training code. Full suite117 passed; all raw hashes unchanged.
- **Confidence:** High in C reproduction, source-code gap finding and decision against C promotion; no claim about B or Low's unseen-period ranking.
- **Alternatives considered:** Merge the source branch or choose C/B/Low by public score. Rejected because matched C evidence fails and B/Low reproduction remains incomplete. No substitute learner is called B.
- **Consequences / revisit trigger:** Use a compatible CatBoost runtime for B; enforce actual-gap chronological training eligibility. Obtain Low's real generation pipeline and as-issued weather provenance. Repeat frozen evaluation after official data refresh. Main production and creative application remain unchanged.


## DEC-20261109-16 - Retain P_fix; weather research requires a defensible historical issue policy

- **Date / owner:** 2026-11-09 / Codex and project owner
- **Status:** Accepted for current-data work; final release pending.
- **Context:** Actual supplied CAMS/GFS differ from the request's example audit. CAMS has full hourly coverage for five fields but no pressure; fresh NOAA48h ingestion succeeds. Owner explicitly confirms no documented historical model issue-time policy and forbids inventing one.
- **Decision:** Keep P_fix unchanged. Mark all weather corrections and historical model-selection experiments BLOCKED until issue-time mapping, historical as-issued vintages, catalogue eligibility and matched development/later confirmation evidence exist. Allow clearly labelled current-period spatial/units/coverage diagnostics only. Register weather candidates without granting production status. Preserve existing EXP-20261108-025; namespace this collision as EXP-025-WEATHER. Retire unsafe unvalidated Open-Meteo prototype arguments and delegate its entry point to shared audited ingestion.
- **Evidence:** reports/ml_pipeline/weather/WEATHER_EXPERIMENT_REPORT.md, per-message raw audits, NOAA_DOWNLOADED_FILE_AUDITS.json,169-row run manifest and48-row coverage table; owner clarification in this session.139 tests pass; repeated P_fix2592 values match prior TASK008 exactly. Current forecast means do not establish skill.
- **Confidence:** High on ingestion results and need for blocked promotion; no claim about weather improvement/private score.
- **Alternatives:** Infer issue time from PM cutoff or nominal cycle; validate against reanalysis or current private forecast levels; treat ADS/NOAA licence as organiser permission; reject all supplied CAMS hourly data based on the older endpoint request. Rejected for leakage, unsupported eligibility or contradiction with decoded bytes.
- **Consequences / revisit trigger:** Obtain missing pressure only through the exact saved supplement request if needed. Resolve catalogue approval and defensible historical operational clocks, then inspect forecast retention before rerunning unchanged chronological folds. Until then P_fix/final-stage safeguards remain authoritative. Final10 November data retrieval/inference and platform submission are not claimed complete.


### DEC-20261109-17 - AirWindow 2.1 final product audit

- **Decision:** retain the genuine frozen P_fix/replay artifacts and existing scheduler/design; improve forecast-first replay/reveal, candidate inspection, runtime data checks/retry, exact time/provenance, historical lead-specific validation and one-page brief. Work/publish on main under the owner's latest explicit instruction.
- **Evidence:** clean/fetched dba644a baseline; 139 Python tests, 12 domain tests, eight real Chrome tests, production build/static smoke and locally executed notebook. Full task evidence in reports/creative_submission/AIRWINDOW_FINAL_COMPLETION_REPORT.md. No independent calibration or newer official refresh is available.
- **Confidence:** high for deterministic arithmetic/artifact preservation and tested Chrome paths; limited for human usability, accessibility certification and public platform readiness.
- **Alternatives:** rebuild UI, fabricate demonstration/freshness/calibration, add external APIs, or block engineering on Firebase access. Rejected: unnecessary scope or unsupported evidence.
- **Consequences:** original scientific claims/data remain fixed; no probabilities or health guarantees. Firebase needs authenticated existing Spark access; form returned401 and requires human verification/submission. Native URL verification stopped Computer Use, so native zoom/print dialog are not claimed. Local print output and reflow are verified.


### DEC-20261109-18 - Keep exact-calendar P_fix primary; gate the second model

- **Date / owner:** 2026-11-09 / Codex
- **Status:** Accepted for current release planning; final pair remains provisional.
- **Context:** TASK010 audited the fetched 25-commit team branch and supplied 9 November Train/EXP030 files, then ran common midnight-aligned 48-hour folds with each station's actual 41–43h first-target PM gap.
- **Decision:** Retain P_fix / exact month-day Candidate C as the primary. Do not promote Candidate B, D, E, or either EXP030 file from this run. Candidate B can remain a conditional hedge for the 10 November refresh only after compatible CatBoost execution and corrected-gap validation; if that gate cannot be met, use the existing documented P_fix/median72 fallback and disclose its weaker result.
- **Evidence:** `reports/ml_pipeline/task010/TASK010_REPRODUCTION_REPORT.md`, `run06/model_metrics.csv`, `run06/paired_bootstrap.json`, `run06/branch_oof_model_metrics.csv`, `run06/candidate_e_artifact_audit.json`. P_fix/exact C RMSE 27.3948 on 1,475 rows; median72 28.4303; legacy_doy 27.9122. Exact-vs-legacy paired interval [-1.0169,+0.0377] crosses zero. Branch C/B/D figures are from a different fold schedule (1,460 rows); CatBoost B/D not rerun. EXP030 manifests/labels are unavailable. E output authenticates to its manifest after CRLF normalization, but private max 532.54 conflicts with the report's stated 116.72 maximum.
- **Confidence:** High that the supplied current Train matches the fetched 9 November data and that P_fix is the best directly evaluated reproducible candidate here; medium for the calendar alignment advantage; low for the final second-model ranking/private score.
- **Alternatives considered:** Promote B by its prior clean-range result; select EXP030 by forecast mean/divergence; promote E by its reported OOF score; choose median72 as equally accurate. Rejected because the first two lack corrected matched evidence/provenance, E has an unresolved output/report mismatch, and median72 loses primary RMSE.
- **Consequences / revisit trigger:** The 9 November Train is preserved in ignored processed evidence only. The final inference gate rejects it as final and requires a later PM cutoff. Reopen second-model selection only with the actual 10 November official snapshot, verified CatBoost runtime/manifests, and identical station-specific folds. No final submission or platform action occurred.
## DEC-20261110-19 - Keep P_fix primary and use a modest diur7 hedge

- **Date / owner:** 2026-11-10 / Codex
- **Decision:** Generate P_fix as the primary final file and P_fix + 25% diur7 as the second selectable file. Keep the second explicitly labelled as a hedge, not a full-target RMSE win.
- **Evidence:** The frozen final Train is SHA-256 `8adbcf...e70a283`; 84 weekly target origins were scheduled, with 12,731 labelled rows on 83 nonempty origins. Full-target RMSE is 2391.716290 for P_fix, 2391.724402 at 10%, 2391.737515 at 25%, and 2391.761889 at 50%. 25% improves the clean `<250` diagnostic but worsens the primary full-target score slightly. Its recent-origin behavior is a small hedge; no private score is known. Results and limitations are recorded in `reports/ml_pipeline/task011/TASK011_FINAL_REPORT.md`.
- **Confidence:** High in input hash, exact fold/row calculation, baseline arithmetic, overlay and deterministic output; medium-low that the hedge helps the private two-day window.
- **Alternatives:** Choose two P_fix variants; use median72; promote an unverified EXP030 or Candidate B file. Rejected because the requested blend is more distinct but only modestly different, median72 is weaker in prior matched evidence, and EXP030/B do not have comparable final-release validation/manifests here.
- **Consequences / revisit trigger:** Upload and select these two final files manually if the owner accepts the hedge; never claim the blend improved broad primary RMSE. Revisit only with matched, eligible private confirmation evidence.

## DEC-20261110-20 - Retain P_fix/B50; reject calibration and residual promotions

- **Date / owner:** 2026-11-10 / Codex
- **Status:** Accepted for current evidence; no production forecast change.
- **Context:** TASK012 rebuilt the frozen TASK011 84-origin OOF from source and input hashes and evaluated regularized station alpha and causal residual variants on the final 23 chronological origins.
- **Decision:** Keep P_fix as the primary control and B50 as the current complementary hedge. Do not promote station-specific alpha, raw/cleaned Ridge or Huber residual challengers. Keep weather and auxiliary-station predictors blocked.
- **Evidence:** `reports/ml_pipeline/task012_vayudrishti_transfer/TASK012_FINAL_REPORT.md`, `control_metrics.csv`, `station_shrinkage_metrics.csv`, `causal_cleaning_metrics.csv`, and `residual_model_metrics.csv`. Across all 12,731 raw labels/83 origins, P_fix RMSE 2391.716290; B50 2391.761889. On the later 3,545 labels/23 origins, P_fix 11.1934, B50 10.4333, selected global-alpha model 11.1934, unregularized station alpha 10.6894, Huber residual 11.6382. The cleaner from VayuDrishti uses centered rolling windows and bidirectional interpolation and is applied before multi-cutoff target slicing; it is not causal for its historical training labels. Weather issue mapping/permission and auxiliary identity/coverage remain unresolved.
- **Confidence:** High that the frozen artifacts reproduced and tested challengers did not beat the controls on their selected matched rows; limited for private-period ranking and extreme-event behavior.
- **Alternatives considered:** Port the full stack, apply reference cleaner, fit station alpha on all OOF, or add CAMS/auxiliary features. Rejected due same-OOF optimizer bias, target leakage, lack of forward gain, or unavailable/uncleared inputs.
- **Consequences / revisit trigger:** P_fix/B50 production predictions and submitted files remain unchanged. Reopen with new eligible as-issued weather/provenance evidence or a preregistered candidate that passes unchanged raw full-target forward folds.

## DEC-20261110-21 - TASK012 final regularization rerun clarification

- **Date / owner:** 2026-11-10 / Codex
- **Status:** Clarifies DEC-20261110-20; main decision unchanged.
- **Context:** The first TASK012 execution preceded a correction to the dimensionless station-alpha shrinkage grid. The final deterministic run/report supersedes that early alpha detail.
- **Decision:** The development-selected dimensionless ridge strength is `lambda=1`. On the final 23 forward origins, regularized station alpha scores 10.8791 RMSE and unregularized station alpha 10.6894; both improve over P_fix 11.1934 but lose to B50 10.4333. Do not promote either calibration.
- **Evidence:** `reports/ml_pipeline/task012_vayudrishti_transfer/station_shrinkage_metrics.csv`, `station_shrinkage_config.json`, `paired_candidate_metrics.json`; final TASK012 runner SHA-256 `562322c0799724be6483dabc89917eda0773cd6a2fc85855364f49e36f80da7a`.
- **Confidence:** High for these matched forward metrics; no implication about private extremes.
- **Alternatives considered:** Rely on the earlier run's global-only alpha record; rejected because its regularization grid was superseded before final execution.
- **Consequences / revisit trigger:** `TASK012_FINAL_REPORT.md` is authoritative; forecast outputs and submitted files remain unchanged.

## DEC-20261110-22 - TASK012 deterministic artifact fingerprint

- **Date / owner:** 2026-11-10 / Codex
- **Status:** Accepted reproducibility record.
- **Context:** The first full TASK012 rerun changed only the gzip header timestamp. The runner now fixes gzip `mtime` to zero and was executed twice after that change.
- **Decision:** Treat the deterministic OOF artifact SHA-256 as `d280f06a8bb244b48e5faa12c919a4ff0a8758de4e32a8c45a34a62c0736291e`; the two complete reruns matched. Final runner source SHA-256 is `fbd08dfd97c9443d35fd2c5e64150a8e7126b68591543018e1908595bdff329b`.
- **Evidence:** `reports/ml_pipeline/task012_vayudrishti_transfer/oof_manifest.json`; `scripts/run_task012.py` uses gzip `mtime=0`; both runner commands exited zero with the same OOF and coverage hashes.
- **Confidence:** High for byte-identical output under Python 3.12.10/pandas 3.1.1 and the frozen inputs.
- **Alternatives considered:** Record only parsed-row equivalence; fixed gzip metadata provides an exact artifact-level check.
- **Consequences / revisit trigger:** Use this SHA in future comparisons; input/source/fold changes require a fresh OOF manifest.

## DEC-20261111-23 - Publish paired scheduling baselines and freshness-bounded snapshot

- **Date / owner:** 2026-11-11 / Codex
- **Status:** Accepted for creative application and retrospective evidence only.
- **Context:** Final AirWindow execution added baseline comparison and reviewed forecast expiry/provenance before Hosting deployment.
- **Decision:** Display paired selected-window outcomes against past-only usual-cleanest and latest-window baselines, with full replay and later confirmation split and origin-cluster bootstrap intervals. Keep all limitations explicit; do not imply superiority or future guarantee. Preserve TASK008 bytes as fallback and use the validated TASK011 final P_fix artifact only through its declared 21 November validity horizon.
- **Evidence:** Reproducible artifact and calculation in `apps/airwindow/baseline_comparison.py` plus `public/data/baseline_comparison.json`; 2,000 seeded origin-cluster bootstrap samples. Four 95% intervals span zero. Release artifact schema/hash checks and browser tests pass.
- **Confidence:** High in paired calculations and committed artifact integrity; limited in generalization because confirmation has eight origins, cases overlap, historical origins had analyst exposure, and forecast decision calibration is unavailable.
- **Alternatives considered:** Show point estimates alone, infer superiority from negative deltas, extend stale snapshot validity, or rerun after source deadline. Rejected because these would hide uncertainty or misstate provenance.
- **Consequences / revisit trigger:** UI, PDF and demo carry the same results and expiry clocks. Recompute comparisons only when replay bytes/method change. Refresh forecast only from a newly eligible complete pipeline output.

## DEC-20261112-24 — AirWindow unavailable-period scheduling policy

- **Date / owner:** 2026-11-12 / Codex
- **Status:** Accepted for the creative planner; forecast and replay artifacts remain unchanged.
- **Decision:** Allow up to six labelled, same-date IST unavailable periods within the selected date's remaining forecast-hour domain. Treat intervals as half-open, so a window ending exactly when a block starts remains feasible. Count each complete forecast window once even when blocks overlap. Keep a conflicting original booking visible but outside the feasible ranking. If only the original remains, report no feasible alternative. The six-block cap keeps the printable brief on one A4 page.
- **Evidence:** AirWindow domain tests and Chrome browser tests pass (17/17 and 14/14); build passes. Printed briefs with one and six active blocks each have one A4 page by `pdfinfo`. The existing unconstrained scheduler output is unchanged with an empty period list.
- **Confidence:** High for deterministic interval arithmetic, UI/print behavior and retained provenance on the tested artifact; limited for untested browser or printer settings.
- **Alternatives:** Silently remove overlapping blocks, discard a blocked original, or show a blocked window as the best alternative. Rejected because each would hide a scheduling constraint or misstate feasibility. Unlimited blocks were not selected because they could break the one-page brief.
- **Consequences / revisit trigger:** Users can edit/remove blocks or change the date/station, which clears date-specific blocks. Revisit the six-block limit only with a revised printable layout and tests.

## DEC-20261112-25 — Preserve the replay reveal boundary during main integration

- **Date / owner:** 2026-11-12 / Codex
- **Status:** Accepted for the merged AirWindow UI.
- **Decision:** Keep case outcomes, aggregate outcome evidence and paired baseline comparisons behind the existing reveal control. Retain the incoming origin-level baseline statistics, artifact validation and provenance text once revealed. Historical outcome filters remain explicitly labelled as hindsight exploration and reset new case details to forecast-only.
- **Evidence:** The prior P0 reveal regression and merged 17-case browser suite verify forecast-first rendering, hide/reset behavior, the new outcome filters and the incoming baseline sensitivity panel. The merged release audit verifies the baseline and PDF artifacts.
- **Confidence:** High for the tested UI boundary and artifact integrity; historical outcome and baseline comparisons remain retrospective and do not establish future benefit.
- **Alternatives considered:** Show aggregate outcomes immediately, as in incoming commit `e624754`. Rejected for the merged UI because it would reverse the existing forecast-first reveal behavior and its regression coverage.
- **Consequences / revisit trigger:** Keep app documentation aligned with reveal-gated evidence. Reconsider only with an explicit product decision and updated leakage/accessibility tests.
