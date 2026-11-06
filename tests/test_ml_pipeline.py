from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from mumbai_pm25.data import _parse_ist, complete_hourly_grid, load_data
from mumbai_pm25.forecast import predict_test, validate_submission
from mumbai_pm25.models import calendar_features, fit_extra_trees, rolling_extra_trees
from mumbai_pm25.validation import _baseline, metric_tables, rolling_oof


def synthetic_train() -> pd.DataFrame:
    starts = pd.date_range("2026-01-01", periods=24 * 35, freq="h", tz="Asia/Kolkata")
    rows = []
    for station in (1, 2):
        for i, start in enumerate(starts):
            if station == 1 and i in (10, 11, 12, 400):
                continue
            rows.append({"location_id": station, "target_start": start,
                         "timestamp_ist": start + pd.Timedelta(hours=1), "pm25": float(10 + i % 24)})
    return pd.DataFrame(rows)


def test_load_aligns_train_hour_and_checks_station_mapping():
    data = __import__("pathlib").Path("data/raw/challenge")
    train, test, sample, stations = load_data(data)
    assert train.target_start.iloc[0] == train.timestamp_ist.iloc[0] - pd.Timedelta(hours=1)
    assert len(test) == len(sample) == 2592
    assert len(stations) == 4


def test_timestamp_parser_requires_explicit_ist_offset():
    parsed = _parse_ist(pd.Series(["2026-01-01T00:00:00+05:30"]), field_name="test")
    assert parsed.iloc[0] == pd.Timestamp("2026-01-01T00:00:00+05:30")
    with pytest.raises(ValueError, match=r"explicit \+05:30"):
        _parse_ist(pd.Series(["2026-01-01T00:00:00"]), field_name="test")


def test_grid_keeps_missing_hours_missing():
    train = synthetic_train()
    grid = complete_hourly_grid(train)
    assert pd.isna(grid.loc[(1, pd.Timestamp("2026-01-01 10:00", tz="Asia/Kolkata")), "pm25"])
    assert grid.loc[(2, pd.Timestamp("2026-01-01 10:00", tz="Asia/Kolkata")), "pm25"] == 20


def test_rolling_oof_records_clocks_and_preserves_extreme_labels():
    train = synthetic_train()
    train.loc[train.index[-1], "pm25"] = 10000.0
    oof = rolling_oof(train, gap_hours=48, step_days=7)
    assert not oof.empty
    assert (oof.pm_history_cutoff < oof.target_start).all()
    assert (oof.prediction_origin >= oof.pm_history_cutoff).all()
    assert (oof.target_start - oof.prediction_origin).dt.total_seconds().div(3600).add(1).eq(oof.horizon_hours).all()
    assert (oof.pm_gap_hours >= 48).all()
    assert (oof.last_pm_available_at <= oof.pm_history_cutoff).all()
    eligible_models = oof.groupby(["fold_id", "location_id", "target_start"]).model.nunique()
    assert eligible_models.eq(9).all()
    assert set(oof.model) == {"last", "mean72", "median72", "ewm72", "diurnal7", "hour_week4",
                              "mean72_clip300", "mean72_exclude_gt1000", "year_ago"}
    assert train.pm25.max() == 10000.0
    by_model, by_station, by_horizon, by_fold = metric_tables(oof)
    assert set(by_model.columns) >= {"full_target_rmse", "clean_rmse", "bias", "fold_rmse_sd", "fold_count", "rows", "extreme_squared_error_share"}
    assert not by_station.empty and not by_horizon.empty and not by_fold.empty
    for (_, station, model), fold in oof.groupby(["fold_id", "location_id", "model"]):
        ordered = fold.target_start.sort_values()
        assert ordered.diff().dropna().min() >= pd.Timedelta(hours=1)
        assert fold.target_start.nunique() == fold.target_end.nunique()
    spans = oof.groupby(["location_id", "model", "fold_id"]).target_start.agg(["min", "max"])
    for _, station_model in spans.groupby(level=[0, 1]):
        ordered_spans = station_model.sort_index(level="fold_id")
        assert (ordered_spans["min"].iloc[1:].reset_index(drop=True) >
                ordered_spans["max"].iloc[:-1].reset_index(drop=True)).all()


def test_metric_values_are_full_target_and_aggregations_are_explicit():
    oof = pd.DataFrame({"model": ["m", "m"], "location_id": [1, 2], "horizon_hours": [1, 2],
                        "fold_id": [pd.Timestamp("2026-01-01", tz="Asia/Kolkata")]*2,
                        "y": [0.0, 1000.0], "prediction": [0.0, 0.0]})
    by_model, by_station, by_horizon, by_fold = metric_tables(oof)
    assert by_model.full_target_rmse.iloc[0] == pytest.approx(np.sqrt(500000))
    assert by_model.mae.iloc[0] == 500.0
    assert by_model.extreme_rows.iloc[0] == 0  # Strictly greater than 1,000.
    assert len(by_station) == len(by_horizon) == 2
    assert len(by_fold) == 1


def test_previous_year_baseline_uses_only_exact_past_same_calendar_hour():
    index = pd.date_range("2025-01-01 00:00", periods=3, freq="h", tz="Asia/Kolkata")
    history = pd.Series([8.0, 9.0, 10.0], index=index)
    targets = pd.date_range("2026-01-01 00:00", periods=2, freq="h", tz="Asia/Kolkata")
    assert _baseline(history, targets, "year_ago").tolist() == [8.0, 9.0]


def test_historical_extreme_ablations_do_not_change_inclusion_threshold():
    index = pd.date_range("2026-01-01", periods=72, freq="h", tz="Asia/Kolkata")
    values = np.full(72, 10.0)
    values[-2:] = [1000.0, 1001.0]
    history = pd.Series(values, index=index)
    target = pd.DatetimeIndex([index[-1] + pd.Timedelta(hours=72)])
    assert _baseline(history, target, "mean72_exclude_gt1000")[0] == pytest.approx((70 * 10 + 1000) / 71)
    assert _baseline(history, target, "mean72_clip300")[0] == pytest.approx((70 * 10 + 300 + 300) / 72)


def test_extra_trees_uses_station_one_hot_and_is_deterministic():
    train = synthetic_train()
    cutoff = pd.Timestamp("2026-01-05 00:00", tz="Asia/Kolkata")
    available = train.loc[train.target_start + pd.Timedelta(hours=1) <= cutoff].copy()
    available["pm_history_cutoff"] = cutoff
    targets = pd.DataFrame({"target_start": pd.date_range(cutoff, periods=2, freq="h", tz="Asia/Kolkata"),
                            "location_id": [1, 2]})
    features = calendar_features(targets.target_start, targets.location_id, [1, 2])
    assert {"station_1", "station_2"} <= set(features.columns)
    assert features.station_1.tolist() == [1, 0]
    first = fit_extra_trees(available, targets, station_ids=[1, 2], seed=42)
    second = fit_extra_trees(available, targets, station_ids=[1, 2], seed=42)
    assert np.isfinite(first).all() and (first >= 0).all()
    assert np.array_equal(first, second)
    leaked = available.copy()
    leaked.loc[leaked.index[0], "target_start"] = cutoff
    with pytest.raises(ValueError, match="exceed"):
        fit_extra_trees(leaked, targets, station_ids=[1, 2])


def test_extra_trees_oof_shares_baseline_target_rows_and_folds():
    train = synthetic_train()
    baseline = rolling_oof(train, gap_hours=24, step_days=14)
    model = rolling_extra_trees(train, gap_hours=24, step_days=14, baseline_oof=baseline)
    unique_baseline = baseline.drop_duplicates(["fold_id", "location_id", "target_start"])
    assert len(model) == len(unique_baseline)
    assert model.fold_id.nunique() == unique_baseline.fold_id.nunique()
    assert (model.pm_history_cutoff < model.target_start).all()
    assert (model.prediction_origin <= model.target_start).all()
    assert (model.model == "extra_trees_calendar").all()


def test_inference_excludes_labels_unavailable_at_issue_time():
    train = synthetic_train()
    # This label's interval ends after issue time and must not enter the PM history.
    train.loc[len(train)] = {"location_id": 1, "target_start": pd.Timestamp("2026-02-05 00:00", tz="Asia/Kolkata"),
                             "timestamp_ist": pd.Timestamp("2026-02-05 01:00", tz="Asia/Kolkata"), "pm25": 9999.0}
    test = pd.DataFrame({"ID": ["a", "b"], "location_id": [1, 2],
                         "target_start": pd.date_range("2026-02-05", periods=2, freq="h", tz="Asia/Kolkata")})
    issue = pd.Timestamp("2026-02-05 00:30", tz="Asia/Kolkata")
    prediction = predict_test(train, test, issue_time=issue)
    # The 00:00 interval ends at 01:00, after issue, so only data through 23:00 can be used.
    expected = 21.5
    assert np.isfinite(prediction.Target).all()
    assert prediction.Target.iloc[0] == expected
    assert prediction.equals(predict_test(train, test, issue_time=issue))


def test_submission_requires_exact_order_and_finite_nonnegative_values():
    test = pd.DataFrame({"ID": ["x", "y"]})
    good = pd.DataFrame({"ID": ["x", "y"], "Target": [0.0, 4.0]})
    validate_submission(good, test)
    with pytest.raises(ValueError, match="original order"):
        validate_submission(good.iloc[::-1].reset_index(drop=True), test)
    bad = good.copy()
    bad.loc[0, "Target"] = np.inf
    with pytest.raises(ValueError, match="finite"):
        validate_submission(bad, test)
