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
