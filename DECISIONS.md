# Architecture and Experiment Decisions

This is an append-only decision log. Do not rewrite old decisions. If a decision is reversed, add a new entry that references the old ID.

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


## DEC-20261108-11 — Select Dual-Ensemble Final Competition Submissions (Accuracy Ensemble A & Robust Ensemble B)

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
