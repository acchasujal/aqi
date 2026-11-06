# Experiment Management Protocol

## Mandatory before running an experiment

Create an ID such as `EXP-20261106-001` and record:
- Question/hypothesis.
- Baseline and proposed change.
- Dataset hashes/version.
- Feature list and cutoff assumptions.
- Fold IDs and gaps.
- Model/parameters/seed.
- Primary metric and diagnostic metrics.
- Expected outcome and decision threshold.

## Required output per experiment

Save under `reports/experiments/<experiment_id>/`:
- `config.yaml` (exact run config)
- `metrics.csv` (fold and station metrics)
- `predictions.parquet` or CSV (row-level OOF predictions)
- `summary.md` (interpretation and decision)
- logs and package versions where practical

Do not save huge intermediate feature matrices by default.

## Experiment log

Append a row to `experiments/EXPERIMENT_LOG.csv`. Never delete failed experiments. Mark them `failed`, `blocked`, `inconclusive` or `completed`.

## Comparing two models

Use exactly the same validation rows. Compare paired per-row squared errors and fold results. Report uncertainty and regime-specific results. A lower single aggregate number on different rows is not a valid comparison.

## Current initial queue

1. Reproduce Claude history baselines using repository-relative paths.
2. Re-run model comparison with full-target RMSE and same folds.
3. Add previous-year same-hour features and local robust aggregation.
4. Test lag-gap sensitivity using 48/72/96/120 hours.
5. Reconstruct archived weather forecast vintages at historical issue times (only after permission).
6. Test weather vs no-weather on exactly the same fold rows.
7. Tune simple blend weights from OOF predictions.
8. Re-evaluate after latest training-data update.
