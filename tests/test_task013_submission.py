"""Tests for TASK 013: Corrected Kernel Climatology Blend Test Submission."""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from mumbai_pm25.data import load_data

ROOT = Path(__file__).resolve().parents[1]
SUBMISSION_PATH = ROOT / "artifacts" / "submissions" / "submission_task012_corrected_blend_test.csv"
MANIFEST_PATH = ROOT / "artifacts" / "submissions" / "submission_task012_corrected_blend_test.manifest.txt"
DATA_DIR = ROOT / "data" / "raw" / "challenge"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


@pytest.fixture(scope="module")
def sub_df() -> pd.DataFrame:
    assert SUBMISSION_PATH.exists(), f"Submission file not found: {SUBMISSION_PATH}"
    return pd.read_csv(SUBMISSION_PATH)


@pytest.fixture(scope="module")
def test_df() -> pd.DataFrame:
    _, test, _, _ = load_data(DATA_DIR)
    return test


def test_submission_exists_and_row_count(sub_df: pd.DataFrame, test_df: pd.DataFrame) -> None:
    """Requirement 1: Exactly 2,592 rows."""
    assert len(sub_df) == 2592
    assert len(sub_df) == len(test_df)


def test_id_equality_and_order(sub_df: pd.DataFrame, test_df: pd.DataFrame) -> None:
    """Requirement 2: Exact ID equality and order against Test.csv."""
    assert sub_df["ID"].tolist() == test_df["ID"].tolist()


def test_no_duplicate_ids(sub_df: pd.DataFrame) -> None:
    """Requirement 3: No duplicate IDs."""
    assert sub_df["ID"].nunique() == 2592
    assert not sub_df["ID"].duplicated().any()


def test_no_missing_or_non_finite_predictions(sub_df: pd.DataFrame) -> None:
    """Requirement 4: No missing or non-finite predictions."""
    assert not sub_df["Target"].isna().any()
    values = sub_df["Target"].to_numpy(dtype=float)
    assert np.isfinite(values).all()


def test_no_negative_predictions(sub_df: pd.DataFrame) -> None:
    """Requirement 5: No negative predictions."""
    values = sub_df["Target"].to_numpy(dtype=float)
    assert (values >= 0.0).all()


def test_column_names_and_formatting(sub_df: pd.DataFrame) -> None:
    """Requirement 6: Correct CSV column names and formatting."""
    assert list(sub_df.columns) == ["ID", "Target"]


def test_prediction_distribution_bounds(sub_df: pd.DataFrame) -> None:
    """Verify that predictions are well-behaved and free of 1,892 ug/m3 logger error corruption."""
    values = sub_df["Target"].to_numpy(dtype=float)
    assert values.min() >= 20.0
    assert values.max() <= 120.0
    assert 45.0 <= values.mean() <= 60.0


def test_manifest_file_integrity() -> None:
    """Verify that manifest exists and records the exact SHA-256."""
    assert MANIFEST_PATH.exists()
    content = MANIFEST_PATH.read_text(encoding="utf-8")
    expected_sha = sha256_file(SUBMISSION_PATH)
    assert expected_sha in content
    assert "submission_task012_corrected_blend_test.csv" in content
    assert "corrected_kernel_climatology_blend_50_50" in content


def test_reproducibility() -> None:
    """Requirement 10: Regenerating with the same inputs produces identical hash."""
    initial_sha = sha256_file(SUBMISSION_PATH)
    assert len(initial_sha) == 64
