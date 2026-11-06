# Risk Register

| ID | Risk | Severity | Current confidence | Mitigation / trigger |
|---|---|---|---|---|
| R-01 | PM history cutoff at final forecast differs from expected 2–4 day gap | Critical | Medium | Recompute actual station cutoffs after 10 Nov release; gap sensitivity 48/72/96/120h |
| R-02 | Rare extreme observations dominate RMSE | Critical | High that extremes exist; low recurrence predictability | Full-target scoring, source-quality audit, spike stress tests, no unvalidated hardcoded hedge |
| R-03 | Weather historical features are more favourable than real forecast vintages | High | High | Use individual archived forecast runs and issue-time availability |
| R-04 | External dataset/API terms conflict with competition/prize rights | High | Unresolved | Written organiser and provider clarification before final use |
| R-05 | Competition-specific vs generic submission rules conflict | High | Unresolved | Follow stricter limits and obtain written answer |
| R-06 | Static `scoring_block` misleads current public/private selection | High | High | Follow dated organizer active windows and final private announcement |
| R-07 | Train update changes station distributions/last timestamp | High | Expected | Version every Train update; rerun audit and model selection |
| R-08 | Overlapping validation folds exaggerate effective sample count | Medium | High | Use non-overlapping core folds; report dependence/noise |
| R-09 | Year-over-year spike feature overfits one prior year | High | High | Shrinkage, multiple folds, ablation; no hard-coded spike |
| R-10 | Timestamp off-by-one-hour or timezone error | High | Medium | Canonical target-start key, explicit timezone, unit tests |
| R-11 | Windows ARM64 package incompatibility | Medium | Medium | Verify `platform.machine()` and dependency install; Colab fallback |
| R-12 | Agents overwrite raw data or silently change assumptions | High | Medium | AGENTS.md, immutable raw data, decisions/progress logs, PR review |
