# EXP-014 bounded model configurations

All configurations use the same 34 numeric features in `FEATURE_CATALOG.csv`, including four one-hot station fields. Numeric station and sensor identifiers are not passed as continuous values. Each validation issue fits on eligible examples from both regimes, while public and private issues for a target day are fitted separately because their PM cutoffs differ. `lead_hours` and `actual_lead_hours` allow regime interactions. One fixed configuration per family was evaluated; no leaderboard feedback or broad hyperparameter search was used. All models run on CPU with explicit seed 42 where supported.

| Model | Objective | Fixed configuration |
|---|---|---|
| W50 | Existing deterministic baseline | 0.5 recent median72 + 0.5 legacy 2024 seasonal feature, existing fallback |
| LightGBM | Squared error | 120 trees, learning rate 0.05, 7 leaves, depth 4, minimum child 100, L2 20, 2 threads |
| CatBoost | RMSE | 120 iterations, depth 4, learning rate 0.05, L2 leaf 20, 2 threads |
| CatBoost Huber | `Huber:delta=50` | Same CatBoost tree settings; robust training only, raw-label RMSE evaluation |
| HistGradientBoostingRegressor | Squared error | 120 iterations, learning rate 0.05, 7 leaves, minimum leaf 100, L2 20 |
| LightGBM residual | Squared error on `y − W50` | Same LightGBM settings; final prediction is W50 plus predicted residual |

All supervised predictions are floored at zero to meet the submission contract; training labels are unmodified. There is no upper clipping. The 2024 seasonal feature is computed with the existing legacy mapping and calendar mode, and W50 values in live public/private feature rows exactly match production inference on all 384 checked rows. Squared-error models can produce very large predictions after fitting the official extreme labels; the robust objective is reported separately rather than silently changing those labels.

An ignored `.venv` in the isolated worktree uses Python 3.11, pandas **2.3.3**, NumPy 2.4.6, scikit-learn 1.9.1, LightGBM 4.7.0 and CatBoost 1.2.10 on Windows AMD64. The installation did not alter the global Python environment or project lockfiles. The initial pandas 3.1.1 environment failed an existing empty-history production test; pinning pandas 2.3.3, the version used in accepted runs, restored the full suite without production edits. This conflicts with `pyproject.toml`'s stated pandas lower bound and needs a separate dependency-compatibility cleanup. `pyproject.toml` already has an optional LightGBM dependency; CatBoost is an EXP-014 environment dependency only. Model binaries are not committed.

Recreate this experiment environment in the isolated worktree with `py -3.11 -m venv .venv` followed by `.\.venv\Scripts\python.exe -m pip install numpy==2.4.6 pandas==2.3.3 scipy==1.17.1 scikit-learn==1.9.1 lightgbm==4.7.0 catboost==1.2.10 pytest==9.2.0 ruff==0.17.4 jsonschema==4.26.0`. Then set `$env:PYTHONPATH='src'` and run `.\.venv\Scripts\python.exe scripts/validate_supervised.py`. No external dataset download is needed.
