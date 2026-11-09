# Decision Log

This is an append-only decision log. Do not edit or remove existing entries.
Every technical decision must include:
- Date and owner
- Context
- Decision
- Evidence (experiment ID, primary metric, fold setup, sample size, failure modes)
- Confidence (High / Medium / Low)
- Alternatives considered and why rejected
- Consequences and revisit trigger

---

## DEC-20261106-01 — Baseline Metric and Validation Fold Setup

- **Date / owner:** 2026-11-06 / ML Engineering
- **Context:** Establishing the repository validation standard for Mumbai PM2.5 forecasting.
- **Decision:** Primary metric is full-target raw-scale RMSE evaluated across all labelled validation rows. Clean-range ($y < 500$) is diagnostic only. Validation must use chronological, forward-only rolling-origin folds.
- **Evidence:** Documented in `docs/VALIDATION_PROTOCOL.md` and `docs/EVALUATION_AND_RULES.md`.
- **Confidence:** High.
- **Alternatives considered:** Shuffled K-Fold (rejected: severe temporal leakage); MAE as primary (rejected: competition uses RMSE).
- **Consequences / revisit trigger:** All models must report on this standardized protocol.

## DEC-20261107-02 — Exclude `mean` and Unverified Source Flags as Predictors

- **Date / owner:** 2026-11-07 / Data Audit
- **Context:** Auditing `Train.csv` fields for predictive validity and leakage.
- **Decision:** Exclude `mean` (duplicates `pm25`), `count`, `available_at`, `series_id`, and flags from default feature set.
- **Evidence:** `docs/DATA_AUDIT.md`.
- **Confidence:** High.
- **Alternatives considered:** Using `available_at` as publication time (rejected: not verified first publication time).
- **Consequences / revisit trigger:** Feature pipelines must not include these columns without documented prediction-time availability proof.

## DEC-20261107-03 — Adopt `hist24_blend50_median72` as Strong Baseline

- **Date / owner:** 2026-11-07 / ML Engineering
- **Context:** Statistical seasonal baselines across varying forecast gaps (48h, 72h).
- **Decision:** Blend 50% 2024 same-hour historical climatology with 50% recent 72h station median.
- **Evidence:** At gap 48h, the blend beats median72 across all 4 stations individually and across all 4 forecast horizon buckets.
- **Confidence:** High for gap 48h and 72h regimes; Medium for longer horizons where rare extreme targets dominate RMSE.
- **Alternatives considered:** Pure `hist24_same_hour` without blend (poorer level tracking at gap 72h: 494.29 vs 490.90); standalone `median72` (fails to exploit diurnal cycle; higher MAE and clean RMSE); calendar-only ExtraTrees (already rejected in DEC-20261107-09).
- **Consequences / revisit trigger:** Update `train_predict.py` to support `hist24_blend50_median72` and explicit PM-history cutoffs. Re-evaluate on final 10 November Train refresh.

## DEC-20261108-11A [ML-Pipeline] — Select Dual-Ensemble Final Competition Submissions (Accuracy Ensemble A & Robust Ensemble B)

- **Date / owner:** 2026-11-08 / Senior Data Scientist & ML Researcher
- **Status:** Accepted (Selects final competition submission candidates A & B)
- **Context:** Following the comprehensive repository audit, leap-year alignment correction, fixed-origin validation framework, modular feature engineering, multi-model benchmarking (LightGBM, CatBoost, XGBoost, Random Forest, statistical baselines), target transformation analysis, and adversarial validation, two distinct final candidate submission strategies were formulated for private evaluation on 11–12 November 2026.
- **Decision:** Select Candidate A (`submission_A_accuracy_ensemble.csv`) and Candidate B (`submission_B_robust_ensemble.csv`) as the two official private leaderboard evaluations on Zindi.
  - **Candidate A (Accuracy Ensemble):** 83% CatBoost (`log1p` target transform, depth 6, lr 0.05, 150 iterations) + 17% 2024 Seasonal Climatological Blend (`hist24_blend50_median72`).
  - **Candidate B (Robust Ensemble):** 50% CatBoost (`log1p`) + 50% 2024 Seasonal Climatological Blend.
- **Evidence:**
  - Evaluated on 5 fixed-origin historical folds (960 ground-truth labels across all 4 stations, identical 48-hour blocks):
    - Candidate A achieved the lowest overall Full RMSE: **14.24 $\mu\text{g}/\text{m}^3$** (vs. 17.51 for `median72`, 15.65 for `hist24_blend50`, 15.38 for `lightgbm_log1p`, 14.29 for `catboost_log1p`).
    - Candidate A mean bias: $-0.29 \mu\text{g}/\text{m}^3$ (near zero bias).
    - Candidate B achieved Full RMSE: **14.43 $\mu\text{g}/\text{m}^3$**, mean bias $-1.03 \mu\text{g}/\text{m}^3$, providing conservative hedging against deep horizon divergence (up to 648h) or distribution shift.
    - Target transformation experiment proved `log1p` transform reduced CatBoost RMSE from 20.15 (raw) to 14.29 (log1p), and LightGBM from 38.00 (raw) to 15.38 (log1p).
    - Feature ablation showed monotonic reduction from 14.13 (calendar only) -> 12.86 (+PM history) -> 12.33 (+seasonal climatology) -> 11.89 (+cross-station spatial interactions).
    - Both candidates pass 100% of sanity and rule checks: 2,592 rows matching `SampleSubmission.csv` exactly, strictly finite and non-negative values.
- **Confidence:** High. Both candidates outperform single baseline models on strict chronological validation folds and preserve cryptographic reproducibility manifests.
- **Alternatives considered:**
  - Single best GBDT (`CatBoost_log1p` alone): Strong, but ensemble with seasonal climatology slightly improves RMSE (14.24 vs 14.29) and reduces variance across stations.
  - LightGBM `raw` MSE loss: Rejected due to severe distortion by positive tail skew (RMSE 38.00).
  - Pure statistical `median72`: Retained as control, but superseded by seasonal blend (15.65) and CatBoost ensemble (14.24).
- **Consequences / revisit trigger:** Both files are exported to `artifacts/submissions/` with `.manifest.txt` files and are designated for the 2 allowed private submissions on Zindi.

## DEC-20261108-12A [ML-Pipeline] — Validate Dual-Candidate Ensembles Across Multi-Regime Winter Validation and In-Distribution Horizon Alignment

- **Date / owner:** 2026-11-08 / Senior Data Scientist, ML Engineer, and Software Architect
- **Status:** Accepted (Reaffirms and strengthens DEC-20261108-11 with winter empirical evidence)
- **Context:** Following the initial multi-model benchmarking on August–October 2026 folds, a comprehensive generalization audit was conducted to verify performance during the post-monsoon/winter transition (11–12 November) where ambient PM2.5 historically surges (e.g. 11–12 Nov 2025 mean $y = 65.74$, max $688.07 \mu\text{g}/\text{m}^3$).
- **Decision:** Reaffirm Candidate A (83% CatBoost log1p + 17% Statistical Blend) and Candidate B (50% CatBoost log1p + 50% Statistical Blend) as the official pair of final submissions for private evaluation.
  - Fix horizon calculation in test inference to map target offset into aligned in-distribution block horizon $1 \dots 48$.
  - Candidate A is retained as the primary precision candidate for steady autumn/late-monsoon air quality conditions (RMSE 14.24 on monsoon folds).
  - Candidate B is validated as the critical robust hedge candidate against winter meteorological inversions and pollution surges (RMSE 41.66 on winter folds vs 44.72 for Candidate A, cutting under-prediction bias by 5.3 $\mu\text{g}/\text{m}^3$ and dominating all observations with $y \ge 50$).
  - Reject tree-tree blending (CatBoost + LightGBM) as an alternative hedge because gradient boosted trees share 0.9693 residual correlation and fail simultaneously during winter distribution shifts (winter RMSE 46.74).
- **Evidence:**
  - `reports/forecast_timeline_audit.md`: Audited all 4 information clocks and corrected block horizon mapping.
  - `reports/november_seasonal_validation.md`: Evaluated 4 seasonal winter pseudo-forecast folds ($N=626$).
  - `reports/high_pollution_robustness.md`: Binned performance across pollution levels ($<50$, $50-75$, $75-100$, $100-250$, $>250$).
  - `reports/adversarial_validation_decomposition.csv`: Proved ROC-AUC 1.0 is driven purely by calendar seasonality and macro levels, not leakage.
  - `reports/candidate_diversity_reassessment.csv`: Evaluated 8 model configurations across all 9 folds ($N=1316$).
  - `reports/final_generalization_assessment.md`: Complete synthesis and inspection of the 192 private slots.
- **Confidence:** High. Supported by 1,316 evaluated ground-truth observations across 9 chronological folds.
- **Alternatives considered:** Pure tree ensemble (CatBoost + LightGBM; rejected due to 0.9693 error correlation); pure statistical climatology (rejected due to higher autumn error).
- **Consequences / revisit trigger:** Both submissions remain cryptographically archived in `artifacts/submissions/`. On 10 November 2026, re-execute `scripts/train_predict.py` with the refreshed `Train.csv` snapshot.

## DEC-20261108-13A [ML-Pipeline] — Adopt Candidate C (Statistical Seasonal) and Candidate B (Robust Ensemble) as the Final Private Submission Pair

- **Date / owner:** 2026-11-08 / Senior Data Scientist, ML Engineer, and Software Architect
- **Status:** Accepted (Updates DEC-20261108-11 and DEC-20261108-12 with final candidate selection)
- **Context:** A comprehensive model-selection study evaluated Strategies A, B, C, D and their constituents across all 9 validation folds ($N=1,316$). The Statistical Seasonal model alone (Strategy C) achieved the lowest pooled RMSE (29.30) and lowest winter RMSE (39.28) with near-zero bias (-0.54 $\mu\text{g}/\text{m}^3$), strictly outperforming tree-heavy models in winter transitions.
- **Decision:** Designate Candidate C (`submission_C_statistical_seasonal.csv`) and Candidate B (`submission_B_robust_ensemble.csv`) as the primary recommendation for the two official private submission slots on Zindi:
  - **Candidate C (Strategy C: 50% 2024 CAAQMS Climatology + 50% Recent 72h Median):** The optimal solution for the expected winter transition regime. It avoids gradient-boosted tree under-prediction bias, dominates at high-emission industrial stations (Shivaji Nagar RMSE 52.56 vs 58.70 for Candidate A), and delivers the lowest overall pooled RMSE across all 9 folds (29.30).
  - **Candidate B (Strategy B: 50% CatBoost log1p + 50% Statistical Seasonal):** The optimal solution for the alternative regime of late-monsoon atmospheric persistence or rapid local level fluctuations. It achieved the lowest Autumn RMSE among all tested models (14.75) while maintaining strong winter protection (41.66).
  - Candidate A (83% CatBoost) and Candidate D (20% CatBoost) are retained as archived alternatives.
- **Evidence:** `reports/final_candidate_comparison.csv` and `reports/final_submission_selection.md`.
- **Confidence:** High. Supported by 1,316 evaluated ground-truth observations across 9 chronological folds.
- **Consequences / revisit trigger:** Both candidates are generated with cryptographic manifests in `artifacts/submissions/`. On 10 November 2026, execute the refreshed pipeline to generate the final upload pair.

## DEC-20261108-14A [ML-Pipeline] — Reaffirm Robustness of Candidate C and B Under Extreme-Observation Sensitivity and Block Bootstrap

- **Date / owner:** 2026-11-08 / Senior Data Scientist, ML Engineer, and Software Architect
- **Status:** Accepted (Confirms robustness of DEC-20261108-13 selection)
- **Context:** A sensitivity audit investigated whether Candidate C's lower pooled RMSE was an artifact of four extreme Shivaji Nagar observations ($y > 250\ \mu\text{g}/\text{m}^3$) in November 2025, and tested whether Candidate C and Candidate B provide an authentic two-submission hedge under cluster-resampled bootstrap.
- **Decision:** Reaffirm the final submission pairing of Candidate C (`submission_C_statistical_seasonal.csv`) and Candidate B (`submission_B_robust_ensemble.csv`):
  - **Extreme Observation Robustness:** Diagnostic jackknife analysis proves Candidate C achieves lower RMSE than Candidate B both on the complete ground-truth dataset (29.30 vs 30.65) and when all four extreme observations $>250\ \mu\text{g}/\text{m}^3$ are diagnostically excluded (16.34 vs 16.53). Candidate C's performance is not driven by outlier distortion.
  - **Cluster Bootstrap by Forecast Fold:** 10,000 block-resampled bootstrap iterations yield a 95% CI for Candidate C of `[13.58, 47.53]` (mean 27.72) vs Candidate B of `[13.56, 49.88]` (mean 28.94), with an 88.6% probability of Candidate C winning overall.
  - **Hedge Value:** Candidate B provides genuine protection if post-monsoon conditions remain clean ($y < 50$ RMSE: 11.97 vs 15.03 for Candidate C) and wins in 5 out of 9 individual folds. The mean absolute prediction divergence of 18.69 $\mu\text{g}/\text{m}^3$ on November transition days provides a true two-submission hedge across meteorological regimes.
- **Evidence:** `reports/extreme_event_sensitivity.md`, `reports/november_2025_2026_comparison.md`, `reports/candidate_C_B_paired_analysis.csv`, and `reports/final_two_submission_readiness.md`.
- **Confidence:** High. Supported by 1,316 observations across 9 chronological folds.
- **Consequences / revisit trigger:** On 10 November 2026, execute the verified readiness protocol to ingest the refreshed `Train.csv` and regenerate both final submission files.

## DEC-20261108-11B [Task007-Track] — Retain P_fix as fallback; do not promote F4 yet

- **Date / owner:** 2026-11-08 / Codex
- **Status:** Provisional for the current Train snapshot; final refresh rerun required.
- **Context:** TASK 007 repaired exact archive-series handling and compared seasonal and LightGBM candidates at the current 193-hour target lead with fixed-origin 48-hour windows.
- **Decision:** Keep P_fix as the provisional fallback and keep F4 as an unpromoted challenger. Exclude Mindspace `xkdr:site_5807` from the Malad P_fix mapping; compare it only as a separately named candidate. P_fix uses Borivali `site_5400`, explicit Malad combination `site_5102` + `site_5402`, Byculla `site_5960`, and Shivaji Nagar `site_5961`.
- **Evidence:** At 193h, P_fix development full RMSE was 30.181 (2,820 rows/20 origins) versus F4 fixed 32.224; paired F4-P_fix delta +1.624, 95% moving-block interval [-0.860, 3.399]. The 318-row/two-origin holdout favored F4 (13.618) over P_fix (20.948), but has no extreme targets and is too small to establish robust promotion. Ratio B was 35.970 on development and 17.429 on holdout. See `reports/ml_pipeline/task007/TASK007_FINAL_REPORT.md` and `EXP-20261108-008`.
- **Confidence:** Medium that F4 should not be promoted on this evidence; Low about final competition ranking until refreshed data and more independent origins.
- **Alternatives considered:** Promote fixed F4 because of holdout gain; use median72. Rejected promotion because F4 loses development and only two held-out origins exist. Median72 remains the fallback if seasonal inputs fail validation.
- **Consequences / revisit trigger:** Use the provisional P_fix artifact only as a current-snapshot candidate. Recompute all cutoffs and validation after the final Train refresh. Reconsider F4 only if full-target RMSE gains replicate across more untouched origins, stations, lead buckets and extreme-event regimes.

## DEC-20261108-12B [Task008-Track] — TASK008 retains P_fix after common-origin comparison

- **Date / owner:** 2026-11-08 / Codex
- **Status:** Provisional; actual final official Train refresh and submission remain pending.
- **Decision:** Retain the reviewed exact-source P_fix mapping and 50:50 seasonal/recent blend; median72 remains explicit fallback. Keep TASK008 isolated from main and PR #4 unmerged. Do not promote the recent/diurnal, anomaly-decay, residual LightGBM or OOF blend candidates on the current snapshot.
- **Evidence:** `reports/ml_pipeline/task008/TASK008_FINAL_REPORT.md`, run01 matched 69 development origins/11,001 rows and eight later confirmation origins/1,400 rows, nominal PM gap 193h. Development best 50% P_fix + 50% median24 RMSE 757.9741 vs P_fix 757.9880; paired delta -0.01393, moving-block 95% interval [-0.05390,+0.44730], only 31/69 origin and 1/4 station wins. Confirmation improves to 13.7909 vs 15.7963 but has no extreme labels and prior analyst exposure. Source-sensitivity intervals cross zero. LightGBM delta/log-ratio/sqrt all lose development full RMSE. Raw labels and files unchanged; 53 tests pass, scoped lint passes; provisional P_fix output exactly matches Task007 v2.
- **Confidence:** High that promotion is unsupported by these gates; low about private-period ranking. Eight development extreme labels drive 99.846% of P_fix squared error, and the schedule does not include every historical extreme.
- **Alternatives:** Promote median24 blend based on later ordinary-regime gain; promote log-ratio LightGBM based on confirmation alone; switch Malad to one archive source. Rejected because development uncertainty/station stability fail and confirmation is not blind. Weather is NOT TESTED without verified permitted as-issued vintages; Vaibhav remains an unscored black-box reference with unknown issue lineage.
- **Consequences / revisit trigger:** Use `scripts/prepare_task008_submission.py` to freeze refreshed inputs and verify deterministic inference. Recompute actual station cutoffs/leads, check current organiser rules/UI and use legitimately new labels as confirmation of locked candidates. Final-data inference and Zindi processing require the real future release and human platform action/authorisation. Resolve main/PR conflicts separately before integration.

## DEC-20261108-13B [AirWindow] — AirWindow 2.0 uses separate forecast/replay artifacts and honest abstention

- **Date / owner:** 2026-11-08 / Codex, parallel frontend/evidence/package contributors
- **Status:** Accepted for the creative prototype; no independent decision calibration or deployment claim.
- **Decision:** Upgrade the existing AirWindow product on the user-requested existing feature branch. Use a deterministic React/Vite/TypeScript event scheduler, retain the original slot, rank only complete consecutive hours, separate live forecast from historical replay, and allow abstention. Preserve schema 1.0 and add forecast 1.1 for exact fractional issue leads plus a separate replay 1.0 contract. No frontend training or ML behavior change.
- **Evidence:** Real TASK008 P_fix artifact and 1,848 predeclared replay cases across 77 origins; 1,469 paired outcomes over 76 origins, 379 missing. Of 1,291 numerical alternatives with paired outcomes, 63.67% were lower afterwards, median realised difference -1.17 µg/m³. Later confirmation is analyst-exposed; the descriptive rate is not a calibrated probability. Full Python integration 60 passed, final focused artifact tests 22 passed after annotation-only regeneration, frontend domain tests 9 passed, Chrome browser tests 5 passed, production build and relevant lint passed. Real screenshots and rendered one-page brief/submission PDF are under `reports/creative_submission/`.
- **Confidence:** High in tested deterministic scheduling, temporal separation and disclosed limits; insufficient evidence for robust live recommendations, probabilities, intervals, health benefits or superiority to established services.
- **Alternatives:** A generic map/lowest-hour dashboard, automatic numerical recommendation, invented confidence, dense spatial interpolation, external real-time weather/LLM/API dependency. Rejected because the four-station evidence and independent calibration do not support those claims. Red-team review documents prior art including existing constrained-window services; the product's defensible contribution is the auditable original-event comparison/replay/abstention workflow.
- **Consequences / revisit trigger:** Live issue lead and PM-information lead must both match evidence before a metric is described as relevant; otherwise show unavailable/insufficient evidence. Expired hours cannot be planned as future activity. No robust recommendation is issued by current artifacts. Firebase Spark configuration and a Colab-compatible notebook are prepared, with authenticated deployment and actual cloud execution unclaimed. Revisit calibrated recommendations only with independently validated chronological decision evidence, and refresh the forecast through the ML export path when genuine new inputs are available.

## DEC-20261108-14B [Integration] — Preserve explicit seasonal policies when integrating main

- **Decision:** retain exact archive-identity P_fix for TASK008 and isolate historical EXP-007--015 calculations in `legacy_seasonal.py`, selected explicitly by existing experiment/CLI paths.
- **Evidence:** 107 tests pass; full W50 and P_fix inference hashes each reproduce their respective reviewed versions.
- **Confidence:** high for compatibility and integration, without a new score claim.
- **Alternative:** silently replace all legacy pooling/calendar behavior; rejected because it would invalidate prior experiment parity.
- **Consequence:** two clearly distinguished source policies remain supported, with regression gates. Reuse main per owner request.

## DEC-20261108-15B [Calibration] — Reject EXP-024 station calibrations for production

- **Date / owner:** 2026-11-08 / Codex
- **Status:** Rejected candidates; retain current provisional P_fix.
- **Context:** Owner requested analysis of five CSVs and pasted research/model suggestions. No B/C/Low generation lineage or new official labels were supplied.
- **Decision:** Keep identity-shrunk offset, affine and Huber calibration as reproducible experiments only. Do not change production inference, upload an unchanged candidate, or integrate black-box forecasts. AIFS-COMPO remains unavailable as an established pipeline input.
- **Evidence:** EXP-20261108-024, reports/ml_pipeline/exp024/REPORT.md and run02/. All three lose development and later full-target RMSE on the same 12,401 rows/77 origins. Later P_fix 15.796318 vs offset 22.110661 / affine 21.946022 / Huber 15.936059; all paired promotion gates fail. Official ECMWF announcement says underlying AIFS-COMPO data will be released in the future. Full suite 114 passed; raw hashes and 2,592-row production output fingerprint unchanged.
- **Confidence:** High that these fixed calibrations lack promotion evidence; low about final private ranking. Historical confirmation remains analyst-exposed.
- **Alternatives considered:** Arbitrary global reduction, selecting B/Low from public scores alone, promoting Huber for station/origin wins despite worse pooled RMSE. Rejected as unsupported by matched primary metrics or reproducible lineage.
- **Consequences / revisit trigger:** Preserve P_fix and the existing final-release guards. Revisit only with eligible B/C/Low provenance or genuinely new official labels and recalculated actual-gap validation. No new external data, targets or event multipliers added.

## DEC-20261108-16B [Audit] — Retain P_fix after exact source-C reproduction

- **Date / owner:** 2026-11-08 / Codex
- **Status:** Rejected C promotion; B evaluation incomplete.
- **Context:** Owner identified the team B/C branch and the public Low repository, then confirmed B/C's author is on the registered team.
- **Decision:** Preserve production P_fix and keep the name-pooled C reconstruction isolated as an experiment. Do not merge the team's package rewrite or label Low's display builder a forecast trainer. B needs compatible CatBoost execution and actual-gap validation before promotion.
- **Evidence:** EXP-20261108-025, reports/ml_pipeline/exp025/REPORT.md and run02/. Original pinned C source and independent implementation both reproduce all 2,592 supplied values exactly. Matched 69 development/8 later origins give C full RMSE 758.020061/15.849352 vs P_fix 757.988014/15.796318; paired intervals cross zero. B computes its training gap from the earliest Test hour, yielding -287h clamped to 48h rather than actual private 193h. Low CSV and newline-normalized Train/Test match, but the inspected repo lacks training code. Full suite 117 passed; all raw hashes unchanged.
- **Confidence:** High in C reproduction, source-code gap finding and decision against C promotion; no claim about B or Low's unseen-period ranking.
- **Alternatives considered:** Merge the source branch or choose C/B/Low by public score. Rejected because matched C evidence fails and B/Low reproduction remains incomplete. No substitute learner is called B.
- **Consequences / revisit trigger:** Use a compatible CatBoost runtime for B; enforce actual-gap chronological training eligibility. Obtain Low's real generation pipeline and as-issued weather provenance. Repeat frozen evaluation after official data refresh. Main production and creative application remain unchanged.

## DEC-20261109-17B [Weather] — Retain P_fix; weather research requires a defensible historical issue policy

- **Date / owner:** 2026-11-09 / Codex and project owner
- **Status:** Accepted for current-data work; final release pending.
- **Context:** Actual supplied CAMS/GFS differ from the request's example audit. CAMS has full hourly coverage for five fields but no pressure; fresh NOAA48h ingestion succeeds. Owner explicitly confirms no documented historical model issue-time policy and forbids inventing one.
- **Decision:** Keep P_fix unchanged. Mark all weather corrections and historical model-selection experiments BLOCKED until issue-time mapping, historical as-issued vintages, catalogue eligibility and matched development/later confirmation evidence exist. Allow clearly labelled current-period spatial/units/coverage diagnostics only. Register weather candidates without granting production status. Preserve existing EXP-20261108-025; namespace this collision as EXP-025-WEATHER. Retire unsafe unvalidated Open-Meteo prototype arguments and delegate its entry point to shared audited ingestion.
- **Evidence:** reports/ml_pipeline/weather/WEATHER_EXPERIMENT_REPORT.md, per-message raw audits, NOAA_DOWNLOADED_FILE_AUDITS.json, 169-row run manifest and 48-row coverage table; owner clarification in this session. 139 tests pass; repeated P_fix 2,592 values match prior TASK008 exactly. Current forecast means do not establish skill.
- **Confidence:** High on ingestion results and need for blocked promotion; no claim about weather improvement/private score.
- **Alternatives:** Infer issue time from PM cutoff or nominal cycle; validate against reanalysis or current private forecast levels; treat ADS/NOAA licence as organiser permission; reject all supplied CAMS hourly data based on the older endpoint request. Rejected for leakage, unsupported eligibility or contradiction with decoded bytes.
- **Consequences / revisit trigger:** Obtain missing pressure only through the exact saved supplement request if needed. Resolve catalogue approval and defensible historical operational clocks, then inspect forecast retention before rerunning unchanged chronological folds. Until then P_fix/final-stage safeguards remain authoritative. Final 10 November data retrieval/inference and platform submission are not claimed complete.

## DEC-20261109-18B [AirWindow] — AirWindow 2.1 final product audit

- **Decision:** retain the genuine frozen P_fix/replay artifacts and existing scheduler/design; improve forecast-first replay/reveal, candidate inspection, runtime data checks/retry, exact time/provenance, historical lead-specific validation and one-page brief. Work/publish on main under the owner's latest explicit instruction.
- **Evidence:** clean/fetched dba644a baseline; 139 Python tests, 12 domain tests, eight real Chrome tests, production build/static smoke and locally executed notebook. Full task evidence in reports/creative_submission/AIRWINDOW_FINAL_COMPLETION_REPORT.md. No independent calibration or newer official refresh is available.
- **Confidence:** high for deterministic arithmetic/artifact preservation and tested Chrome paths; limited for human usability, accessibility certification and public platform readiness.
- **Alternatives:** rebuild UI, fabricate demonstration/freshness/calibration, add external APIs, or block engineering on Firebase access. Rejected: unnecessary scope or unsupported evidence.
- **Consequences:** original scientific claims/data remain fixed; no probabilities or health guarantees. Firebase needs authenticated existing Spark access; form returned 401 and requires human verification/submission. Native URL verification stopped Computer Use, so native zoom/print dialog are not claimed. Local print output and reflow are verified.

## DEC-20261109-19 [Task009-Selection] — Adopt Candidate C and Candidate B as Final Challenge Submissions on Refreshed 9 November Data

- **Date / owner:** 2026-11-09 / Senior Data Scientist, ML Engineer, and Software Architect
- **Status:** Adopted for final submission to Zindi Google Mumbai Data Challenge.
- **Context:** Refreshed official data release (`Train.csv`, 48,133 rows with observations up to 9 Nov 07:00 IST) shortens the forecast lead time from 193h to 41–43h before the private evaluation window (11–12 Nov 2026, 192 target hours). All teammate branches were audited and merged on `feat/competition-ml-pipeline`.
- **Decision:** Select **Submission 1 (Primary): Candidate C** (`submission_1_primary_candidate_C.csv` / `hist24_blend50_median72`) and **Submission 2 (Robust Hedge): Candidate B** (`submission_2_hedge_candidate_B.csv` / `ensemble_robust`). Maintain **Candidate E (Residual Blend)** (`submission_refined_blend_E.csv` / `ensemble_residual_blend`) as diagnostic benchmark. Implement training-target clipping safeguard (>500 µg/m³) in `SupervisedForecaster` for linear residual models.
- **Evidence:** 9-fold chronological validation ($N=1,460$ across all 4 stations):
  - Candidate C: Pooled RMSE 28.20, Winter RMSE 40.07 (lowest individual winter error), Mean Bias -3.47.
  - Candidate B: Pooled RMSE 29.18, Autumn RMSE 12.41, Clean-regime ($y < 50$) RMSE 8.35 (lowest among all candidates).
  - Pure GBDT models (CatBoost log1p, LightGBM log1p, Tree-Tree blends) suffer severe winter underprediction (bias < -10.5, winter RMSE > 46.5) due to high residual correlation (0.969) and lack of winter inversion training examples.
  - Raw `Train.csv` contains an extreme sensor corruption spike of 241,587 µg/m³; `log1p` organically dampens it, while `residual_median72` requires training target clipping to prevent leaf distortion.
  - Full test suite passes: 166 passing tests, 0 failures. All generated submissions strictly comply with 2,592-row, non-negative, finite, and ID format constraints with cryptographic manifests.
- **Confidence:** High for leak-free reproducibility, lead-time alignment, and dual-regime protection; private leaderboard will reflect mid-November winter atmospheric progression.
- **Alternatives considered:** Pure tree-tree blending (rejected: residual correlation 0.969, fails in winter); single CatBoost log1p (rejected: underpredicts winter levels by >10 µg/m³); arbitrary public-LB multiplier tuning (rejected: overfits clean 2-day public window and catastrophic on private winter inversion).
- **Consequences:** Submissions 1 and 2 are cryptographically sealed in `artifacts/submissions/` with complete `.manifest.txt` records ready for the 10 November 23:59:59 IST deadline.

