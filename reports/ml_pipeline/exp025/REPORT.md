# EXP-025: trace supplied B/C/Low sources and reproduce C

2026-11-08. Base main: `d44e02cb87634db1c2685b946a88d10587e6d702`.
Owner confirmed that B/C's author is on the same registered Zindi team during
this audit. Earlier EXP-024 provenance limitations are superseded only where
the evidence below establishes them; old records have not been rewritten.

## Outcome

**Candidate C is exactly reproduced**, with zero difference on all 2,592 supplied
prediction values. Its source policy does not beat P_fix on matched 193h folds.
Keep production unchanged. B's source is identified but not executed because
CatBoost is absent from the available Windows ARM64 environment. Low's published
CSV and input data match; the supplied repository does not contain its training
pipeline. These are distinct levels of reproducibility, not a blanket compliance
or performance endorsement.

## Source freeze and execution isolation

- [Team branch](https://github.com/acchasujal/aqi/tree/a191dbaf89f3324e8d8fe77542bf8cc70a848b4e):
  `a191dbaf89f3324e8d8fe77542bf8cc70a848b4e`.
- [Low repository](https://github.com/vaibhavgupta9876/mumbai-air-outlook/tree/a4afdc56c757ce4138113b423a001275e38c0dff):
  `a4afdc56c757ce4138113b423a001275e38c0dff`.
- GitHub connector inspected both recursive trees and relevant files. The team
  branch's pinned commit was also already present in the local object database;
  `git show` read it without checkout, fetch, merge or changes to main.
- `SOURCE_INVENTORY.json` records published paths and Git blob IDs. Each run's
  manifest records SHA-256 of extracted branch Python files, local experiment
  code, config, raw inputs, original OOF and outputs.
- The reviewed branch package was extracted to ignored
  `data/processed/exp025/run01` and `run02`, then invoked in separate Python
  processes. No branch module was substituted into the current package.
- Only deterministic offline C inference was executed. The Low app's build code,
  weather requests, workflow and notebook were read, not run. No new external
  predictor data, API calls, secrets or private targets entered validation.

All seven raw input files on the team branch match current inputs after line-ending
normalisation (the archive matches byte-for-byte). Originals remain untouched.
No broad merge of the branch's conflicting model/package architecture was attempted.

## Candidate C: exact reproduction and cause of differences

The branch's C blends 50% recent median72 with 50% seasonal same-hour mean.
Its archive loader first averages concurrent readings under the exact canonical
station name for each timestamp. This pools Borivali site_5113 and site_5400.
Malad pools site_5102/site_5402 and excludes Mindspace. P_fix uses site_5400 alone
for Borivali and explicitly weights the eligible Malad source observations.
Those different aggregation policies explain the changed forecasts without
assuming C learned a public-label bias correction.

Reproduced defaults include circular normalized-day-of-year distance <=14,
at least three unique archived station-hours, and 72h median -> 168h median ->
last-observation fallback. The branch's archive hour alignment remains an
unverified hypothesis; matching a CSV does not establish physical sensor identity.

The original branch's C inference and the new independent, vectorized
`source_candidates.py` reconstruction both match all supplied C predictions
exactly (max absolute difference 0.0). Supplied file SHA-256:
`d1fcc73e4a068bcf5a923f9d9867fac5ece5c3f5b85c5b01b844cf9115e748fb`.
The reproduction timestamp is the branch's documented 8 Nov 12:00 IST, replayed
with PM cutoff 2 Nov 23:00. This is a historical reproduction, not a new issuance.

The isolated reconstruction is not exposed through production inference. It
preserves complete past-only target intervals and rejects fractional PM cutoffs,
duplicate training station-hours and invalid values. Tests cover missing elapsed
hours, cutoff inclusion, future perturbation, pooled-sensor weighting, leap dates,
source coverage, fallback and immutable run output.

## Matched evaluation

Predeclared config: `experiments/EXP-20261108-025.yaml`; no hyperparameter or weight
search. Reused fingerprint-verified TASK008 OOF keys and unmodified official truth:
69 development origins/11,001 rows and eight later origins/1,400 rows. Every block
has one fixed cutoff, a 48-hour target window, and nominal leads 193-240h.
Confirmation was previously inspected and is not fresh independent evidence.

| Model | Development full RMSE | Later full RMSE | Development clean diagnostic |
| --- | ---: | ---: | ---: |
| P_fix | 757.988014 | 15.796318 | 23.252452 |
| Reproduced C policy | 758.020061 | 15.849352 | 23.119108 |
| median72 control | 758.056357 | 15.578586 | 25.787054 |
| Existing median24/P_fix 50:50 control | 757.974083 | 13.790862 | 23.533783 |

C's development RMSE delta +0.032048 has four-origin moving-block 95% interval
[-0.173315,+0.066202], with 26/69 origin wins. Later delta +0.053034 has interval
[-0.080189,+0.558850], with 4/8 origin wins. Seed 20261108, 2,000 repetitions.
The later Borivali RMSE worsens 13.087700  -> 13.411859; Malad improves slightly
18.670139  -> 18.612226; Byculla and Shivaji are numerically unchanged.
No primary metric or uncertainty gate supports replacement. Cleaner-range MAE/RMSE
gains remain diagnostics. Eight development extremes are retained, not cleaned;
they account for approximately 99.85% of baseline squared error.

Both runs produce identical OOF and metric/bootstrap bytes. Run02 adds explicit
line-ending equivalence evidence. Complete station/lead/fold scores, bias, MAE,
spread, coverage and row counts are retained under each run directory.

## Candidate B: identified model and important mismatch

[Source inference](https://github.com/acchasujal/aqi/blob/a191dbaf89f3324e8d8fe77542bf8cc70a848b4e/src/mumbai_pm25/forecast.py)
defines B as 50% CatBoost log1p + 50% the C statistical component. CatBoost uses
150 iterations, depth 6, learning rate 0.05, L2 leaf 3, seed 42 and one thread.
Features combine station-category/calendar, fixed-cutoff PM summaries, seasonal
profiles and past-only citywide station context. No model artifact is tracked.

A concrete inference mismatch exists in `predict_test_ensemble`:

```text
gap = clamp(int((min(Test.target_start) - PM_cutoff) / 1h), 48, 120)
```

For the actual frozen files, `min(Test.target_start)` is 22 Oct 00:00, cutoff
is 2 Nov 23:00, raw gap is **-287h**, and the clamp makes the training gap **48h**.
The real private lead starts at **193h**. Features encode block position 1..48
but do not carry actual PM lead. Mapping block position back into the training
range does not correct stale-history distribution mismatch. The branch's model
selection study likewise uses 48h-gap folds. Its headline scores cannot be
compared directly with TASK008's 193h results.

Corrected B evaluation must choose the target block and explicit PM cutoff, use
the actual gap without clipping it, fit only whole labels available by the outer
cutoff, and use the same chronological folds/rows as the control. Existing main
`final_gap.py` already provides these clocks and complete-block training gates.
Do not replace it with the branch's earliest-Test-date gap calculation.

**B execution remains NOT RUN.** `catboost` is absent from this repository's
Python 3.12 Windows ARM64 environment. [Official PyPI release files](https://pypi.org/project/catboost/#files)
for 1.2.10 include Windows AMD64 binaries, with no native Windows ARM64 wheel.
The system `python` and `py` aliases cannot execute, and there is no second local
worktree/runtime discovered. No dependency or global runtime was changed. On a
compatible environment, the runner can perform original-source B reproduction
when CatBoost is installed; corrected matched-gap model validation remains a
separate required step. No other learner was silently labelled as B.

Branch reports give differing historical B/C SHA-256 values and refer to ignored
local artifacts. Those report hashes alone do not authenticate the supplied B.
C is authenticated through direct rerun; B's supplied values remain unverified
against actual training execution. No public leaderboard score was reproduced.

## Low: artifact traced, training still absent

[Published forecast](https://github.com/vaibhavgupta9876/mumbai-air-outlook/blob/a4afdc56c757ce4138113b423a001275e38c0dff/forecast/low.csv)
has Git blob ID `72061108e958a1ad23b90d523f215df7d47357ee`, exactly matching the
owner's supplied bytes (SHA-256 is in EXP-024's supplied audit). Low's Train/Test
blob IDs match the current official files after converting LF to CRLF **in
memory only**. Thus their data content matches, though their original file hashes
differ due to line endings. This does not establish which inputs trained Low.

[README](https://github.com/vaibhavgupta9876/mumbai-air-outlook/blob/a4afdc56c757ce4138113b423a001275e38c0dff/README.md)
describes a Chronos-2/weather/gradient-boosting ensemble. But
[build_data.py](https://github.com/vaibhavgupta9876/mumbai-air-outlook/blob/a4afdc56c757ce4138113b423a001275e38c0dff/build_data.py)
reads existing Low/High files and derives a display centre as Low/0.95. It does
not train that ensemble. The notebook clones the repository and invokes the same
page builder. The complete inspected tree contains no model-training module,
checkpoint, saved ensemble components, archived weather vintages or OOF predictions.
Its MIT code licence does not establish forecast-input availability or model lineage.

The page builder filters PM>1000 and uses centered rolling spike detection for
its retrospective display. Those operations are not evidence that the unpublished
forecast trainer did so. They were not copied into this forecasting pipeline.
Likewise, current/stitched weather shown by the product is not proof of as-issued
predictors used to train Low. Low remains excluded from fitting/blending pending
the actual generation repository, model settings, issue time and input manifests.

## Verification and task state

```powershell
.venv/Scripts/python.exe -m pytest tests/test_source_candidates.py -q -p no:cacheprovider --basetemp data/processed/exp025-tests
.venv/Scripts/python.exe scripts/audit_exp025.py --supplied-dir C:/Users/sujal/Downloads --output reports/ml_pipeline/exp025/run01
.venv/Scripts/python.exe scripts/audit_exp025.py --supplied-dir C:/Users/sujal/Downloads --output reports/ml_pipeline/exp025/run02
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --basetemp data/processed/exp025-full-tests
.venv/Scripts/python.exe -m ruff check src/mumbai_pm25/source_candidates.py scripts/audit_exp025.py tests/test_source_candidates.py
git diff --check
```

Focused tests 3 passed; full suite **117 passed in 21.44s**, with 19 existing pandas
deprecation warnings in legacy seasonal code. Scoped Ruff and diff check passed.
Both source reruns and matched evaluations completed. All seven raw hashes unchanged.
No production ML file, raw data, AirWindow artifact or frontend changed. Existing
EXP-024 work remains intact. No commit, push, merge, dependency install, platform
selection or upload was performed.

Run manifests were generated before the owner's team-status reply; their
unknown-team note records that earlier state. The owner's later reply confirms
registered-team eligibility for B/C and supersedes that note, not the test results.

Next: reproduce B on a compatible runtime, test its corrected actual-gap version
against frozen controls, obtain Low's real training pipeline, then repeat the
predeclared comparison on genuine official refreshed data. No score gain is claimed.
