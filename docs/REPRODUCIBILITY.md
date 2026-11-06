# Reproducibility and Environment

## Principles

- One command should reproduce each audit, validation experiment and submission.
- No absolute paths or user-specific environment assumptions.
- Use a `pyproject.toml` or lock file with compatible dependency ranges; record exact installed versions in experiment outputs.
- Set seeds centrally and record them.
- Record hashes of raw inputs and external snapshots.
- Keep output names immutable by experiment/run ID.

## Windows ARM64 constraints

The participant uses a Windows Snapdragon X laptop with 16 GB RAM. Check wheel availability in the actual Python architecture before installing specialised libraries. Prefer NumPy/Pandas/scikit-learn and a small XGBoost/LightGBM-compatible setup only after import and smoke tests. Do not assume NPU/GPU acceleration. If a package lacks a native Windows ARM64 wheel, decide explicitly whether x64 emulation or Colab is worth the overhead.

## Suggested environment

Python 3.11 or 3.12 may be used only after verifying compatibility of the selected package versions on the user's installed architecture.

Install basic dependencies first; add model libraries only when the corresponding experiment is ready. Do not add CatBoost, LightGBM, XGBoost, Optuna or large deep-learning frameworks merely because they are common in competitions.

## Reproduction commands (to implement)

```powershell
# Create environment
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip

# After pyproject.toml is maintained
python -m pip install -e ".[dev]"

# Run data audit
python -m mumbai_pm25.audit --config configs/default.yaml

# Run tests
python -m pytest

# Run a configured experiment
python -m mumbai_pm25.validation --config configs/experiments/<experiment>.yaml

# Build and validate submission
python -m mumbai_pm25.submission --config configs/submission.yaml
```

Commands above describe the target interface; do not claim they work until the CLI modules are implemented and smoke-tested.
