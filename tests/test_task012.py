from __future__ import annotations

import pandas as pd

from mumbai_pm25.oof_cache import cache_manifest_matches
from scripts.run_task012 import alpha_fit, causal_past_median


def test_station_alpha_is_shrunk_toward_global_when_penalty_increases() -> None:
    rows = pd.DataFrame({
        "location_id": [1, 1, 2, 2],
        "P_fix": [10.0, 10.0, 10.0, 10.0],
        "Pfix_diur50": [20.0, 20.0, 20.0, 20.0],
        "y": [20.0, 20.0, 12.0, 12.0],
    })
    _, unregularized = alpha_fit(rows, -1.0)
    _, regularized = alpha_fit(rows, 1000.0)
    assert unregularized[1] > regularized[1]
    assert unregularized[2] < regularized[2]


def test_past_median_uses_only_values_ended_by_example_origin() -> None:
    train = pd.DataFrame({
        "location_id": [1, 1, 1],
        "target_start": pd.date_range("2025-01-01 00:00", periods=3, freq="h", tz="Asia/Kolkata"),
        "pm25": [10.0, 20.0, 999.0],
    })
    row = pd.Series({"location_id": 1, "prediction_origin": pd.Timestamp("2025-01-01 02:00", tz="Asia/Kolkata"), "P_fix": 5.0})
    assert causal_past_median(train, row) == 15.0


def test_oof_cache_requires_exact_provenance_match() -> None:
    expected = {"train": "a", "source": "b", "folds": [1, 2], "config": {"gap": 15}}
    assert cache_manifest_matches(expected.copy(), expected)
    assert not cache_manifest_matches({**expected, "train": "changed"}, expected)
    assert not cache_manifest_matches({**expected, "source": "changed"}, expected)
    assert not cache_manifest_matches({**expected, "folds": [1]}, expected)
    assert not cache_manifest_matches({**expected, "config": {"gap": 72}}, expected)
    with_artifact = {**expected, "artifact_sha256": {"oof.csv.gz": "c"}}
    assert cache_manifest_matches(with_artifact, {**expected, "artifact_sha256": {"oof.csv.gz": "c"}})
    assert not cache_manifest_matches(with_artifact, {**expected, "artifact_sha256": {"oof.csv.gz": "tampered"}})
