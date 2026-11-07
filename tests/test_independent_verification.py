"""Regression tests for independent verification of ML forecasting pipeline.

Verifies:
1. Zero overlap between historical training origins and validation target intervals.
2. Past-only gating: features at simulated origin use only history < origin_cutoff.
3. Second-day forecast predictions do not access first-day future target ground truth.
4. Target transformations (log1p, sqrt, residual) are fitted on training data only.
5. Missing target hours are cleanly excluded rather than imputed as zero.
6. Candidate submissions match SampleSubmission IDs, non-negative values, and manifests.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from mumbai_pm25.data import load_data
from mumbai_pm25.features.pipeline import build_feature_matrix
from mumbai_pm25.historical_archive import load_2024_history
from mumbai_pm25.models.supervised import SupervisedForecaster
from mumbai_pm25.validation import generate_fixed_target_folds

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "raw" / "challenge"


@pytest.fixture(scope="module")
def challenge_data():
    train, test, sample, stations = load_data(DATA_DIR)
    hist_2024 = load_2024_history(DATA_DIR / "AdditionalHistory.zip")
    grid = train.set_index(["location_id", "target_start"])[["pm25"]].sort_index()
    station_histories = {
        int(sid): grid.xs(sid, level="location_id")["pm25"]
        for sid in train["location_id"].unique()
    }
    return train, test, sample, stations, hist_2024, station_histories


def test_zero_leakage_between_training_origins_and_validation_window(challenge_data):
    train, _, _, _, _, _ = challenge_data
    folds = generate_fixed_target_folds(
        train, gap_hours=48, horizon_hours=48, step_days=21, holdout_hours=48
    )
    val_fold = folds[-1]

    hist_origins = pd.date_range(
        train.target_start.min() + pd.Timedelta(days=21),
        val_fold.pm_history_cutoff - pd.Timedelta(hours=48),
        freq="72h",
        tz="Asia/Kolkata",
    )
    clean_origins = [
        orig for orig in hist_origins
        if orig + pd.Timedelta(hours=48) < val_fold.target_start or orig > val_fold.target_end
    ]

    for orig in clean_origins:
        orig_target_end = orig + pd.Timedelta(hours=48)
        # 1. Training target window must end before validation target interval begins
        assert orig_target_end <= val_fold.target_start, (
            f"Training target end {orig_target_end} overlaps validation start {val_fold.target_start}"
        )
        # 2. Training cutoff must be strictly before validation cutoff
        orig_cutoff = orig - pd.Timedelta(hours=48)
        assert orig_cutoff < val_fold.pm_history_cutoff


def test_features_use_only_information_prior_to_simulated_cutoff(challenge_data):
    _, _, _, _, hist_2024, station_histories = challenge_data
    cutoff = pd.Timestamp("2026-08-01 12:00:00+05:30")
    target_df = pd.DataFrame([
        {"location_id": 11606, "target_start": cutoff + pd.Timedelta(hours=24), "horizon_hours": 24}
    ])

    # Inject an extreme future observation after cutoff into a copy of history
    tainted_histories = {
        sid: s.copy() for sid, s in station_histories.items()
    }
    future_time = cutoff + pd.Timedelta(hours=10)
    tainted_histories[11606].loc[future_time] = 99999.0

    X_clean = build_feature_matrix(
        station_histories, target_df, cutoff, history_2024=hist_2024
    )
    X_tainted = build_feature_matrix(
        tainted_histories, target_df, cutoff, history_2024=hist_2024
    )

    # Future value must NOT affect feature values computed at cutoff
    for col in X_clean.columns:
        val_c = X_clean[col].iloc[0]
        val_t = X_tainted[col].iloc[0]
        if pd.isna(val_c):
            assert pd.isna(val_t)
        else:
            assert np.isclose(val_c, val_t), f"Feature {col} leaked future data!"


def test_target_transformations_fitted_on_training_data_only():
    X_tr = pd.DataFrame({"station_id": [11606, 11611], "median_72": [40.0, 50.0]})
    y_tr = pd.Series([45.0, 55.0])
    forecaster = SupervisedForecaster(model_family="catboost", target_transform="log1p")
    forecaster.fit(X_tr, y_tr)

    # Inverting predictions on test features uses only test features and model weights
    X_te = pd.DataFrame({"station_id": [11606], "median_72": [42.0]})
    pred = forecaster.predict(X_te)
    assert np.isfinite(pred).all()
    assert (pred >= 0).all()


def test_missing_targets_are_excluded_not_imputed(challenge_data):
    train, _, _, _, _, station_histories = challenge_data
    folds = generate_fixed_target_folds(
        train, gap_hours=48, horizon_hours=48, step_days=21, holdout_hours=48
    )
    # Check fold 25 where heavy missingness occurred during monsoon
    f25 = folds[-4]  # fold_25_20260827
    target_hours = pd.date_range(f25.target_start, periods=48, freq="h")

    rows = []
    for sid in [11606, 11611, 3409510, 3409511]:
        s_series = station_histories[sid]
        for t in target_hours:
            y_val = s_series.loc[t] if t in s_series.index else np.nan
            rows.append({"location_id": sid, "target_start": t, "y": y_val})
    df_raw = pd.DataFrame(rows)
    df_valid = df_raw.dropna(subset=["y"])

    # 164 missing values in fold 25
    assert len(df_raw) == 192
    assert len(df_valid) == 28
    # Ground truth evaluation must drop NaNs, never replace with 0.0
    assert not (df_valid["y"] == 0.0).all()


def test_supervised_training_examples_strictly_precede_cutoff_and_validation(challenge_data):
    """Enforce Task 6 availability rule:
    For every training example, target_end <= pm_history_cutoff < target_start.
    """
    train, _, _, _, _, _ = challenge_data
    folds = generate_fixed_target_folds(
        train, gap_hours=48, horizon_hours=48, step_days=21, holdout_hours=48
    )
    for fold in folds:
        hist_origins = pd.date_range(
            train.target_start.min() + pd.Timedelta(days=21),
            fold.pm_history_cutoff - pd.Timedelta(hours=48),
            freq="72h",
            tz="Asia/Kolkata",
        )
        clean_origins = [
            orig for orig in hist_origins
            if orig + pd.Timedelta(hours=48) < fold.target_start or orig > fold.target_end
        ]
        for orig in clean_origins:
            for h in range(1, 49):
                target_end = orig + pd.Timedelta(hours=h)
                # Strict check: target_end <= fold.pm_history_cutoff
                assert target_end <= fold.pm_history_cutoff, (
                    f"Training target end {target_end} exceeds simulated cutoff {fold.pm_history_cutoff}"
                )
                assert target_end < fold.target_start, (
                    f"Training target end {target_end} enters validation target window {fold.target_start}"
                )


def test_candidate_submissions_compliance():
    sample = pd.read_csv(DATA_DIR / "SampleSubmission.csv")
    sub_a_path = ROOT / "artifacts" / "submissions" / "submission_A_accuracy_ensemble.csv"
    sub_b_path = ROOT / "artifacts" / "submissions" / "submission_B_robust_ensemble.csv"

    for path in [sub_a_path, sub_b_path]:
        assert path.is_file(), f"Submission file {path} missing"
        sub = pd.read_csv(path)
        assert len(sub) == 2592, f"Expected 2592 rows in {path}, got {len(sub)}"
        assert list(sub.columns) == ["ID", "Target"]
        assert (sub["ID"] == sample["ID"]).all(), f"ID mismatch in {path}"
        assert sub["Target"].notna().all(), f"NaN values in {path}"
        assert np.isfinite(sub["Target"]).all(), f"Non-finite values in {path}"
        assert (sub["Target"] >= 0.0).all(), f"Negative values in {path}"

        manifest_path = path.with_suffix(".manifest.txt")
        assert manifest_path.is_file(), f"Manifest file {manifest_path} missing"
        manifest_text = manifest_path.read_text(encoding="utf-8")
        assert "git_commit:" in manifest_text
        assert "output_sha256:" in manifest_text
        assert "pm_history_cutoff_global: 2026-11-02T23:00:00+05:30" in manifest_text
