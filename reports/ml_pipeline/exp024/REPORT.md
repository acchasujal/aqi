# EXP-024: supplied forecast audit and station calibration

Date: 2026-11-08. Base: main at `d44e02cb87634db1c2685b946a88d10587e6d702`.
Status: current-input experiment complete; **no demonstrated score improvement**.
Retain P_fix. Experimental code is not connected to production inference or AirWindow.

## Scope and evidence interpretation

The owner's request authorised analysis, research, and safe code/model experiments.
The pasted chat was treated as a set of claims and hypotheses, not as instructions
to change Zindi selections, upload submissions, copy another participant's model,
or automatically scale predictions down. No platform action was performed.

Read the mandatory repository context and current code/diff first. Starting tree
was clean. Work remains on main. No new dependencies, raw-input edits, production
model changes, frontend changes, commit or push.

## Five supplied CSVs

Every CSV has exactly 2,592 rows, ordered `ID,Target` matching official Test and
SampleSubmission, finite nonnegative values and unique IDs. Full fingerprints,
pairwise maximum differences, correlations and station/window summaries are in
`run02/supplied_audit.json`. Originals were read directly from the supplied directory.

TASK007 and TASK008 are byte-identical; both SHA-256:
`3d79cffcca78cea1ad6f5e24d2568bf931bbba8c3b15fcd7db1728462050ab1d`.
That explains their identical score without assuming a leaderboard fault.

| Forecast | Full-grid mean | 3-4 Nov mean | 11-12 Nov mean |
| --- | ---: | ---: | ---: |
| P_fix (both TASK files) | 51.464 | 48.804 | 56.466 |
| Submission B | 45.747 | 43.232 | 48.669 |
| Submission C | 48.695 | 46.092 | 53.450 |
| Low | 36.993 | 41.150 | 32.876 |

These are predictions, not target values or RMSEs. Each two-day summary includes
all 192 possible station-hours; it does not identify the actual scored rows.
Windows use official Test `target_start_ist`, not observation-end timestamps.
Several pasted chat averages differ slightly from these recomputed values.

The full-grid P_fix/Low correlation is 0.009332. Low is not a simple downward
multiplier of P_fix. C leaves Byculla and Shivaji predictions unchanged over
3-4 Nov, whereas B changes all four stations in that window. Neither the filename
nor smoothness establishes the algorithm or information set behind B/C/Low.

The screenshot explicitly associates TASK008 with 14.86260121. It also displays
7.441197896, 10.18562279 and 13.42234351 for other submissions; their association
with Low/B/C comes from the pasted chat, not an independently verified platform
download/manifest. No public score was reproduced. Lower forecast means and lower
public RMSE do not prove a transferable station bias without matched target errors.

B/C/Low generation code, input hashes, issue times and registered-team lineage
were requested and remain unavailable in this session. They are descriptive
references only, excluded from fitting, OOF blends and model promotion.

## Research checked against primary sources

- [Forecasting: Principles and Practice](https://otexts.com/fpp3/toolbox.html#time-series-cross-validation)
  supports rolling-origin evaluation with training observations preceding each
  forecast. We apply the stricter complete-block PM-cutoff rule already in TASK008.
- [CAMS forecast calibration study](https://www.mdpi.com/2072-4292/12/22/3813)
  reports Random Forest bias correction. Search-index abstract verified; full
  publisher retrieval returned HTTP 429. Its detailed chronological protocol and
  transfer to this sparse 193h station task were not established. It motivates a
  controlled local test, not a claimed expected gain or model replacement.
- [ECMWF AIFS-COMPO announcement, 16 October 2026](https://www.ecmwf.int/en/about/media-centre/news/2026/aifs-compo-ai-atmospheric-composition-forecasting)
  confirms experimental ten-day composition forecasts and PM charts. Crucially,
  it says underlying data will become available in the future. It also describes
  missing time-varying emission forcing. This is not an established downloadable
  feature source or a justified fireworks-response predictor for our pipeline.
- [ECMWF open-data documentation](https://www.ecmwf.int/en/forecasts/datasets/open-data)
  covers a subset of IFS/AIFS products under CC-BY-4.0 and ECMWF terms, with a
  rolling twelve-run archive. Do not transfer that access claim to AIFS-COMPO.
  Permitted catalogue membership and historical as-issued vintages remain unverified.
- [Official Zindi page](https://zindi.world/competitions/google-mumbai-data-challenge)
  currently states latest-valid evaluation on 11-12 Nov and the 10 Nov 23:59:59 IST
  deadline. Specific rules list 10/day, 140 total and ClimateVerse sources, while
  generic text still differs. Discussion URLs returned the same general page,
  not authenticated discussion content. ClimateVerse catalogue retrieval failed;
  no new data permission or selection-rule resolution is claimed.

No weather, reanalysis, realised event observations, satellite data or new external
model data entered the experiment. No event multiplier was added.

## Predeclared calibration experiment

Config: `experiments/EXP-20261108-024.yaml`. Module:
`src/mumbai_pm25/calibration.py`. Runner: `scripts/run_exp024.py`.

Reuse the fingerprint-verified TASK008 matched OOF file and original labels:
69 development origins/11,001 rows, eight later origins/1,400 rows, 193-240h
PM leads, weekly nonoverlapping 48h blocks. Confirmation has prior analyst exposure
and is not blind. No new independent labels are available in the current snapshot.

For each station and forecast block, fit only earlier OOF target blocks whose
**entire block ends by the current PM-history cutoff**. Freeze those coefficients
across all 48 target hours. Past confirmation labels can enter later confirmation
fits only after this availability test, simulating the fixed online procedure.
No current validation outcome enters its own calibration.

Three fixed candidates, no tuning grid:

1. Offset: sum of station residuals divided by `n + 500`.
2. Affine: least-squares residual correction `a + c * P_fix/50`, ridge prior
   `500 * (a² + c²)` toward identity.
3. Huber affine: same design and identity prior, fixed residual threshold 20
   micrograms/m3. Explicit robust-loss ablation; all training and validation
   labels retained unchanged.

Fewer than four eligible station origins falls back to identity. Output floor zero
enforces the submission contract; no target clipping or upper forecast cap occurs.
Clocks, unique station-hours, complete-block availability, finite values and original
truth are checked. Fitting lineage records rows/origins/max target end and coefficients.

## Results on identical rows

| Model | Development full RMSE | Later full RMSE | Development clean diagnostic |
| --- | ---: | ---: | ---: |
| P_fix | 757.988014 | 15.796318 | 23.252452 |
| Offset | 758.363755 | 22.110661 | 33.468252 |
| Affine | 758.413549 | 21.946022 | 34.626221 |
| Huber affine | 757.989715 | 15.936059 | 23.302889 |
| median24 control | 757.996398 | 13.585679 | 24.938952 |
| Existing 50% median24/P_fix control | 757.974083 | 13.790862 | 23.533783 |

Development-only choice among identity and the new calibrations is **P_fix**.
Eight development extremes account for 99.846% of P_fix squared error; later
confirmation has none. Mean residual corrections carry historical extremes into
ordinary periods: later bias increases from +0.938 (P_fix) to +9.619/+9.492
(offset/affine). Huber limits that sensitivity but does not improve primary RMSE.

Moving-block bootstrap: four consecutive origins, 2,000 repetitions, seed 20261108.
Development calibration delta intervals vs P_fix: offset [+0.154,+8.954], affine
[+0.164,+9.880], Huber [-0.101,+0.132]. Later intervals: offset [+4.419,+10.084],
affine [+2.895,+11.759], Huber [-0.751,+1.514]. None passes the fixed gate.
Later Huber improves three stations and six origins, but its pooled RMSE is worse;
station wins cannot replace the primary metric. Existing median24 blend has the
same previously reported later gain and inconclusive development interval; it
provides no new independent evidence for promotion.

`run02/` includes complete row counts, bias, MAE, clean diagnostics, station and
lead scores, per-fold spread, paired bootstrap, fitting lineage, row-level OOF and
source/output manifests. `run01/` preserves the initial execution; run02 adds
explicit gate summaries. Both runs' OOF, lineage, audit, aggregate metrics and
bootstrap bytes match. No improved leaderboard score is claimed.

## Commands and verification

Run from repository root (supplied directory is an explicit CLI parameter):

```powershell
.venv/Scripts/python.exe -m pytest tests/test_calibration.py -q -p no:cacheprovider --basetemp data/processed/exp024-tests
.venv/Scripts/python.exe scripts/run_exp024.py --supplied-dir C:/Users/sujal/Downloads --output reports/ml_pipeline/exp024/run01
.venv/Scripts/python.exe scripts/run_exp024.py --supplied-dir C:/Users/sujal/Downloads --output reports/ml_pipeline/exp024/run02
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --basetemp data/processed/exp024-full-tests
.venv/Scripts/python.exe -m ruff check src/mumbai_pm25/calibration.py scripts/run_exp024.py tests/test_calibration.py
.venv/Scripts/python.exe scripts/prepare_task008_submission.py --issue-time 2026-11-08T15:58:00+05:30 --output data/processed/exp024_pfix_regression.csv
git diff --check
```

Focused tests: 7 passed. Full Python suite: **114 passed**, 19 existing pandas
deprecation warnings in legacy seasonal code, 19.29 seconds. Scoped Ruff and diff
check pass. Smoke is a historical regression replay, not a newly issued forecast:
2,592 ordered finite nonnegative outputs, deterministic internal rerun, unchanged
P_fix SHA-256 `3d79cffcca78cea1ad6f5e24d2568bf931bbba8c3b15fcd7db1728462050ab1d`.
All seven raw source hashes still match TASK008. Frontend unchanged; its tests
were not rerun for this isolated ML experiment.

## Remaining work requiring new evidence

Obtain B/C/Low code and lawful reproducible input lineage before model integration.
Preserve actual official refreshed data in a new directory; never overwrite raw.
Use `reports/ml_pipeline/task008/FINAL_REFRESH_RUNBOOK.md` to recompute actual
cutoffs/private leads and rerun the frozen comparison for that information regime.
The existing EXP-024 runner deliberately rejects a different raw snapshot; new-gap
OOF must be rebuilt and reviewed rather than relabelled as this 193h experiment.
The real final release and private outcomes cannot be produced on 8 November.
