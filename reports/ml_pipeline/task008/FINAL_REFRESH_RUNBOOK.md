# TASK008 refresh and submission runbook

As of 8 November, the 9/10 November releases are pending. Preserve official downloads in a new directory under `data/processed/official_releases/`, retaining the six official filenames; never overwrite `data/raw/challenge/`. Record the official source URL and actual download/release time. Keep the original downloaded bytes and do not normalise line endings.

## On the 9 November release

1. Recheck the official Data page and current submission UI. Confirm the active public window and which released labels it contains. Keep the DataDictionary discrepancy in the record.
2. Audit schema, hashes, station cutoffs and missingness with the loader and prepare command below using `--stage provisional` and a new output filename. The command preserves a hash-addressed input copy and emits row-level cutoff/lead metadata.
3. Evaluate earlier dated predictions only on newly released public labels if their issue-time lineage is established. Vaibhav's supplied lineage is unknown, so public scoring remains blocked without evidence. Preserve new labels for confirmation of locked candidates; do not retune repeatedly on leaderboard feedback.

## On the final 10 November 09:00 IST release

Use a new directory such as `data/processed/official_releases/20261110_0900/` containing all six files. Verify the download is the official final release; `--release-time` is operator-asserted metadata, not proof supplied by the script. Use the actual generation time, no later than 23:59:59 IST. Example (replace time with the actual run time):

```powershell
.venv\Scripts\python.exe scripts/prepare_task008_submission.py --data-dir data/processed/official_releases/20261110_0900 --stage final --release-time 2026-11-10T09:00:00+05:30 --issue-time 2026-11-10T12:00:00+05:30 --model P_fix --output artifacts/submissions/task008_final_pfix_20261110_1200.csv
```

The command rejects known initial Train hashes, snapshots with no newer eligible PM history, future observations relative to issue time, incorrect schema/order, missing/nonfinite/negative outputs, and reused output names. It hashes and preserves all inputs, computes actual station leads, runs inference twice and compares predictions/CSV exactly. It emits `.audit.json` and `.rows.csv` beside the output. If the archive is unavailable or its audit fails, explicitly run `--model median72` under a different filename and document the fallback; do not conceal an input error.

P_fix is the provisional retained model; no supervised retraining is needed for it. To rerun the predeclared experiment on a new snapshot, use a new report directory:

```powershell
.venv\Scripts\python.exe scripts/run_task008.py --data-dir data/processed/official_releases/20261110_0900 --output reports/ml_pipeline/task008/final_refresh_run
```

Its default PM gap is recalculated from the snapshot and the private target start. Station observation ages and actual leads are recorded independently. Historical PM availability uses interval end as a proxy; actual first-publication times remain unverified. Changing the gap creates a new information regime; retain P_fix until matched evidence passes the promotion gate.

## Manual platform step

- Inspect the actual submission UI and preserve the challenge-specific latest-valid versus generic choose-two conflict. If a choose-two control appears, obtain organiser clarification.
- Stay within 10/day and 140 overall. Review the output hash, exact ID order, all 2,592 predictions, latest PM cutoffs, actual private leads and deterministic audit.
- Human login/submission or explicit authorisation is required. Confirm successful processing in Zindi and that the intended final file is the latest valid submission; record filename, hash, processing status and timestamp. Do not infer success from local generation.
- Final-data inference and Zindi processing are **PENDING**. Current provisional artifacts are not final-refresh artifacts.

## TASK010 update — 9 November audit and final-stage guard

The supplied 9 November release has 48,133 rows and station interval-end cutoffs of 9 Nov 06:00, 07:00, 05:00 and 07:00 IST. Do not use it as the final release. The final-stage preparation script rejects both known LF/CRLF hashes of that release and any final snapshot without PM history newer than the 9 Nov 07:00 IST global cutoff. The source download and hashes must still be preserved under the official-release path; do not copy it into `data/raw/challenge/`.

TASK010's corrected matched baseline comparison retains P_fix / Candidate C exact month/day as primary (27.3948 full-target RMSE on 1,475 rows). Candidate C with `legacy_doy` scores 27.9122; the paired interval for the calendar difference crosses zero. Candidate B is not re-run at station-specific 41–43h gaps because CatBoost is unavailable in the current Windows ARM64 environment. Its older branch OOF makes it a provisional hedge only, not a confirmed second winner. EXP030 predictions have no supplied manifests or labels and must not be selected by their filenames or forecast means.

After the verified 10 November release, run Candidate C/P_fix on main using the final command above. Candidate B can be evaluated/generated only in the compatible CatBoost 1.2.10 environment with the reviewed team inference code and a new output name. The branch's prior inference syntax is:

```powershell
python scripts/train_predict.py --model hist24_blend50_median72 --model-run-time <actual-run-time-IST> --output artifacts/submissions/task010_final_candidate_C.csv
python scripts/train_predict.py --model ensemble_robust --model-run-time <actual-run-time-IST> --output artifacts/submissions/task010_final_candidate_B.csv
```

Those are branch-code commands, not commands verified in the current main checkout. Do not upload automatically. If the B environment or validation gate fails, retain the P_fix primary and disclose that a supported second model was not established; do not substitute EXP030 or Candidate E without provenance and matched validation.
