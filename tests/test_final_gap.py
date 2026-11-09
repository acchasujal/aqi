"""Leakage, availability and coverage gates for TASK008."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from mumbai_pm25.final_gap import (
    BASE_MODELS,
    FEATURES,
    ForecastBlock,
    baseline_predictions,
    block_features,
    eligible_training_rows,
    labelled_blocks,
    paired_bootstrap,
    score_predictions,
)
from mumbai_pm25.forecast import predict_test_with_hist24_blend
from mumbai_pm25.historical_archive import build_seasonal_features


def fixture():
    times = pd.date_range("2026-06-01", periods=24*45, freq="h", tz="Asia/Kolkata")
    train = pd.DataFrame({"target_start": times, "location_id": 11606,
                          "pm25": 20.0 + times.hour.to_numpy()})
    cutoff = times[24*35]
    block = ForecastBlock(cutoff+pd.Timedelta(hours=193), cutoff, cutoff)
    hours = pd.date_range("2024-01-01", "2024-12-31 23:00", freq="h", tz="Asia/Kolkata")
    archive = pd.DataFrame({"hour_start": hours, "series_id": "xkdr:site_5400",
                            "pm25": 25.0 + hours.hour.to_numpy()})
    return train, archive, block


def test_fixed_origin_future_perturbation_and_feature_allowlist():
    train, archive, block = fixture()
    original = baseline_predictions(block_features(train, archive, block, (11606,)))
    changed = train.copy()
    changed.loc[changed.target_start.ge(block.pm_cutoff), "pm25"] = 999999.0
    altered = baseline_predictions(block_features(changed, archive, block, (11606,)))
    pd.testing.assert_frame_equal(original, altered)
    assert original.prediction_origin.nunique() == 1
    assert original.forecast_lead_hours.tolist() == list(range(193, 241))
    assert original.actual_pm_lead_hours.tolist() == list(range(193, 241))
    assert original.last_pm_end.le(original.pm_history_cutoff).all()
    assert not {"y", "ID", "scoring_block", "series_id", "available_at"}.intersection(FEATURES)


def test_cutoff_boundary_exact_lags_missing_hours_and_extreme_history():
    train, archive, block = fixture()
    boundary = block.pm_cutoff-pd.Timedelta(hours=1)
    train.loc[train.target_start.eq(boundary), "pm25"] = 12345.0
    train = train.loc[train.target_start.ne(block.pm_cutoff-pd.Timedelta(hours=2))]
    rows = block_features(train, archive, block, (11606,))
    assert rows.lag1.eq(12345).all()
    assert rows.lag2.isna().all()
    assert rows.last_pm.eq(12345).all()
    assert rows.missing72.eq(1/72).all() or np.allclose(rows.missing72, 1/72)
    assert rows.age_hours.eq(0).all()
    assert rows.last_pm_end.eq(block.pm_cutoff).all()


def test_validation_inference_parity_and_all_history_fallback():
    train, archive, block = fixture()
    # No observations in the recent window: use all eligible station median.
    train = train.loc[train.target_start.lt(block.pm_cutoff-pd.Timedelta(hours=100))]
    rows = baseline_predictions(block_features(train, archive, block, (11606,)))
    targets = rows[["location_id", "target_start"]].assign(ID=[f"t{i}" for i in range(48)])
    pred = predict_test_with_hist24_blend(train, targets, archive,
                                         issue_time=block.issue_time, pm_history_cutoff=block.pm_cutoff)
    np.testing.assert_allclose(rows.P_fix, pred.Target)
    assert rows.median72.eq(train.pm25.median()).all()


def test_complete_block_training_eligibility_and_truth_retention():
    train, archive, block = fixture()
    rows, coverage = labelled_blocks(train, archive, [block])
    assert coverage.expected_rows.iloc[0] == 192
    truth_rows = rows.loc[rows.location_id.eq(11606) & rows.y.notna()]
    assert len(truth_rows) == 47  # Last target is outside fixture; missing stays missing.
    assert eligible_training_rows(rows, block.target_end-pd.Timedelta(hours=1)).empty
    assert len(eligible_training_rows(rows, block.target_end)) == len(truth_rows)
    rows.loc[truth_rows.index[0], "y"] = 241587.56
    metric = score_predictions(rows.loc[rows.location_id.eq(11606)], ["median72"]).iloc[0]
    assert metric.extreme_rows == 1
    assert metric.rows == len(truth_rows)


def test_missing_candidate_never_wins_by_dropping_rows():
    rows = pd.DataFrame({"fold_id": [1, 2], "y": [20, 10000],
                         "P_fix": [20., 30.], "candidate": [20., np.nan]})
    scores = score_predictions(rows, ["P_fix", "candidate"])
    candidate = scores.loc[scores.model.eq("candidate")].iloc[0]
    assert candidate.rows == 2 and candidate.missing_predictions == 1
    assert np.isnan(candidate.full_target_rmse)
    assert paired_bootstrap(rows, "candidate")["status"] == "incomplete_predictions"


def test_archive_missing_source_preserves_sum_metadata():
    _, archive, block = fixture()
    target = pd.DataFrame({"location_id": [11606], "target_start": [block.target_start]})
    features = build_seasonal_features(archive, target,
        series_map={11606: ("missing", "xkdr:site_5400")})
    assert features["hist24_series::missing::sum"].iloc[0] == 0
    assert features["hist24_series::xkdr:site_5400::sum"].iloc[0] > 0
    assert features.hist24_coverage.iloc[0] == 29


def test_invalid_clocks_rejected_and_candidates_nonnegative():
    train, archive, block = fixture()
    with pytest.raises(ValueError, match="cutoff"):
        ForecastBlock(block.target_start, block.pm_cutoff, block.pm_cutoff-pd.Timedelta(hours=1))
    rows = baseline_predictions(block_features(train, archive, block, (11606,)))
    complete = [m for m in BASE_MODELS if m != "diur7"]
    assert np.isfinite(rows[complete].to_numpy()).all()
    assert (rows[complete] >= 0).all().all()


def test_supervised_block_availability_and_determinism():
    from mumbai_pm25.final_gap_supervised import SUPERVISED_MODELS, fit_predict

    cutoff = pd.Timestamp("2026-07-01", tz="Asia/Kolkata")
    training = pd.DataFrame({name: np.arange(600) % 24 for name in FEATURES})
    training["median72"] = 25.0
    training["y"] = (np.arange(600) % 70).astype(float)
    training.loc[0, "y"] = 241587.56
    training["block_target_end"] = cutoff
    validation = training.iloc[:48].copy()
    for model in SUPERVISED_MODELS:
        first = fit_predict(training, validation, model, fitting_cutoff=cutoff)
        second = fit_predict(training, validation, model, fitting_cutoff=cutoff)
        np.testing.assert_array_equal(first, second)
        assert np.isfinite(first).all() and (first >= 0).all()
    with pytest.raises(ValueError, match="complete available"):
        fit_predict(training, validation, "lgbm_delta", fitting_cutoff=cutoff-pd.Timedelta(hours=1))
    assert training.y.max() == 241587.56 and training.y.min() == 0


def test_submission_final_stage_rejects_initial_release_and_overwrite(tmp_path):
    from pathlib import Path

    from scripts.prepare_task008_submission import prepare

    data = Path(__file__).resolve().parents[1] / "data/raw/challenge"
    with pytest.raises(ValueError, match="9 November Train snapshot"):
        prepare(data, tmp_path / "final.csv", stage="final",
                issue_time=pd.Timestamp("2026-11-10 12:00+05:30"),
                release_time=pd.Timestamp("2026-11-10 09:00+05:30"))
    occupied = tmp_path / "old.csv"
    occupied.write_text("preserved", encoding="utf-8")
    with pytest.raises(FileExistsError, match="immutable"):
        prepare(data, occupied, issue_time=pd.Timestamp("2026-11-08 12:00+05:30"))
    assert occupied.read_text(encoding="utf-8") == "preserved"
