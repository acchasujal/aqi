# TASK007 Output Artifact Status

`TASK007_FINAL_REPORT.md` identifies the authoritative outputs. Intermediate runs were retained unchanged so their progression is auditable; they are not all suitable for comparing scores.

## Authoritative current-snapshot outputs

- Seasonal 193-hour comparison and OOF: `seasonal_repaired_v4/`
- Seasonal gap sensitivity at 48/72/73/96 hours: `seasonal_final_gap48/`, `seasonal_final_gap72/`, `seasonal_final_gap73/`, `seasonal_final_gap96/`
- Corrected supervised model and F4 comparison: `supervised_gap193_v5/`
- Final current-snapshot candidate CSV and manifest are under `artifacts/submissions/`; the CSV is explicitly provisional.

These use the approved exact source policy (Mindspace excluded from P_fix) and corrected forecast-lead clock.

## Superseded exploratory outputs

- `seasonal_repaired_v2/` and root `seasonal_oof_gap193.csv.gz`: early attempt; not final.
- `seasonal_repaired_v3/`: corrected lead calculation, but its development selection still allowed Mindspace into the Malad P_fix mapping.
- `supervised_gap193_v2/`, `supervised_gap193_v3/`, and `supervised_gap193_v4/`: model-comparison iterations before the final approved Malad source restriction; v2 also had F4 selection-labeling corrected in later runs.
- `seasonal_gap48/`, `seasonal_gap72/`, `seasonal_gap73/`, `seasonal_gap96/` and their `_v2` variants: earlier source/lead iterations; use `seasonal_final_gap*` instead.
- `seasonal_repaired_v2/` and `seasonal_repaired_v3/` are retained for audit only; do not use their P_fix metrics in final comparisons.

The first provisional CSV `artifacts/submissions/task007_provisional_pfix_current_train.csv` was generated before the Malad source restriction. It is preserved unchanged with a `.superseded.txt` warning and must not be submitted. Use the `_v2.csv` artifact only as a provisional current-snapshot candidate pending final Train refresh.
