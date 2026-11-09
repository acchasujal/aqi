"""Cutoff, station, origin and residual invariants for EXP-014."""
import pickle

import numpy as np
import pandas as pd
import pytest

from mumbai_pm25.data import load_data
from mumbai_pm25.forecast import predict_test_with_hist24_blend
from mumbai_pm25.historical_archive import load_2024_history
from mumbai_pm25.supervised import (
    FEATURE_COLUMNS,
    Origin,
    add_seasonal_and_baseline,
    build_examples,
    candidate_model,
    fit_predict,
    make_origin,
    origin_features,
)


def _train() -> pd.DataFrame:
    start = pd.Timestamp("2026-01-01", tz="Asia/Kolkata")
    rows = []
    for station, level in ((11606, 10.0), (11611, 100.0)):
        for hour in range(100):
            if station == 11606 and hour == 80:
                continue
            rows.append({"location_id": station, "target_start": start + pd.Timedelta(hours=hour),
                         "pm25": level + hour % 24})
    return pd.DataFrame(rows)


def test_public_private_origin_clocks_and_timezone():
    day = pd.Timestamp("2026-11-11", tz="Asia/Kolkata")
    public = make_origin(day, "public")
    private = make_origin(day, "private")
    assert day - public.pm_cutoff == pd.Timedelta(hours=1)
    assert day - private.pm_cutoff == pd.Timedelta(hours=193)
    assert private.issue_time - private.pm_cutoff == pd.Timedelta(hours=109)
    assert private.issue_time == day - pd.Timedelta(hours=84)
    with pytest.raises(ValueError, match="timezone-aware"):
        make_origin(pd.Timestamp("2026-11-11"), "private")


def test_features_ignore_future_pm_and_preserve_station_isolation():
    train = _train()
    day = pd.Timestamp("2026-01-05", tz="Asia/Kolkata")
    cutoff = day-pd.Timedelta(hours=1)
    origin = Origin(day, cutoff, cutoff-pd.Timedelta(minutes=1), "public")
    targets = pd.DataFrame({"location_id": [11606, 11611], "target_start": [day, day]})
    with pytest.raises(ValueError, match="Invalid issue"):
        origin_features(train, targets, origin, (11606, 11611))
    origin = Origin(day, cutoff, cutoff, "public")
    first = origin_features(train, targets, origin, (11606, 11611)).sort_values("location_id")
    modified = train.copy()
    modified.loc[modified.target_start >= day, "pm25"] = 100000.0
    second = origin_features(modified, targets, origin, (11606, 11611)).sort_values("location_id")
    pd.testing.assert_frame_equal(first.reset_index(drop=True), second.reset_index(drop=True))
    assert first.last_pm.iloc[0] < first.last_pm.iloc[1]
    assert first.station_11606.tolist() == [1, 0]
    assert first.available72.iloc[0] == 71  # One missing elapsed hour.
    assert first.missing_fraction72.iloc[0] == pytest.approx(1/72)
    assert first.pm_history_cutoff.eq(cutoff).all()
    assert first.target_end.eq(day+pd.Timedelta(hours=1)).all()


def test_exact_cutoff_excludes_interval_ending_later_and_duplicate_rejected():
    train = _train()
    day = pd.Timestamp("2026-01-05", tz="Asia/Kolkata")
    cutoff = day-pd.Timedelta(hours=1)
    target = pd.DataFrame({"location_id": [11606], "target_start": [day]})
    before = origin_features(train, target, Origin(day, cutoff, cutoff, "public"), (11606,))
    after = train.copy()
    after.loc[after.location_id.eq(11606) & after.target_start.eq(cutoff), "pm25"] = 99999.0
    unchanged = origin_features(after, target, Origin(day, cutoff, cutoff, "public"), (11606,))
    pd.testing.assert_frame_equal(before, unchanged)
    duplicate = pd.concat([train, train.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="Duplicate station-hour"):
        origin_features(duplicate, target, Origin(day, cutoff, cutoff, "public"), (11606,))


def test_residual_prediction_adds_w50_and_rejects_future_label(monkeypatch):
    class ConstantModel:
        def fit(self, features, y):
            self.mean = float(np.mean(y))
            return self

        def predict(self, features):
            return np.full(len(features), self.mean)

    monkeypatch.setattr("mumbai_pm25.supervised.candidate_model", lambda _: ConstantModel())
    cutoff = pd.Timestamp("2026-01-05", tz="Asia/Kolkata")
    columns = {name: [1.0, 1.0] for name in FEATURE_COLUMNS}
    training = pd.DataFrame(columns)
    training["y"] = [15.0, 25.0]
    training["w50"] = [10.0, 20.0]
    training["target_end"] = cutoff-pd.Timedelta(hours=1)
    validation = pd.DataFrame(columns)
    validation["w50"] = [30.0, 40.0]
    validation["pm_history_cutoff"] = cutoff
    np.testing.assert_array_equal(fit_predict("lightgbm_residual", training, validation),
                                  [35.0, 45.0])
    training["y"] = [0.0, 0.0]
    np.testing.assert_array_equal(fit_predict("lightgbm_residual", training, validation),
                                  [15.0, 25.0])
    validation["w50"] = [0.0, 0.0]
    np.testing.assert_array_equal(fit_predict("lightgbm_residual", training, validation),
                                  [0.0, 0.0])
    training.loc[0, "target_end"] = cutoff+pd.Timedelta(hours=1)
    with pytest.raises(ValueError, match="unavailable"):
        fit_predict("lightgbm_residual", training, validation)


def test_hist_gradient_model_serializes_and_is_seeded():
    first = candidate_model("hist_gradient_boosting")
    features = pd.DataFrame({name: np.linspace(0, 1, 220) for name in FEATURE_COLUMNS})
    labels = np.linspace(10, 30, 220)
    first.fit(features, labels)
    second = pickle.loads(pickle.dumps(first))
    np.testing.assert_array_equal(first.predict(features), second.predict(features))
    assert first.random_state == 42


def test_live_public_private_w50_feature_matches_production():
    from pathlib import Path

    raw = Path(__file__).resolve().parents[1] / "data/raw/challenge"
    train, test, _, stations = load_data(raw)
    archive = load_2024_history(raw / "AdditionalHistory.zip")
    station_ids = tuple(sorted(int(v) for v in stations.location_id))
    selected = test.loc[test.target_start.isin([
        pd.Timestamp("2026-11-03T00:00:00+05:30"),
        pd.Timestamp("2026-11-11T00:00:00+05:30")])].copy()
    assert len(selected) == 8
    parts = []
    for day, regime in (("2026-11-03", "public"), ("2026-11-11", "private")):
        start = pd.Timestamp(day, tz="Asia/Kolkata")
        targets = selected.loc[selected.target_start.eq(start)]
        features = origin_features(train, targets, make_origin(start, regime), station_ids)
        parts.append(add_seasonal_and_baseline(features, archive).merge(
            targets[["location_id", "target_start", "ID"]],
            on=["location_id", "target_start"], validate="one_to_one"))
    built = pd.concat(parts).sort_values("ID")
    production = predict_test_with_hist24_blend(
        train, selected, archive,
        calendar_mode="legacy_doy",
        issue_time=pd.Timestamp("2026-11-07T12:00:00+05:30"),
        pm_history_cutoff=pd.Timestamp("2026-11-02T23:00:00+05:30"),
    ).sort_values("ID")
    np.testing.assert_array_equal(built.w50.to_numpy(), production.Target.to_numpy())


def test_training_label_join_does_not_change_features():
    start = pd.Timestamp("2026-01-01", tz="Asia/Kolkata")
    rows = [{"location_id": 11606, "target_start": start+pd.Timedelta(hours=i),
             "pm25": float(10+i % 24)} for i in range(300)]
    train = pd.DataFrame(rows)
    archive = pd.DataFrame(columns=["station_name", "hour_start", "pm25"])
    day = pd.DatetimeIndex([pd.Timestamp("2026-01-10", tz="Asia/Kolkata")])
    first = build_examples(train, archive, day, (11606,))
    changed = train.copy()
    changed.loc[changed.target_start >= day[0], "pm25"] += 1000.0
    second = build_examples(changed, archive, day, (11606,))
    pd.testing.assert_frame_equal(first.drop(columns="y"), second.drop(columns="y"))
    assert (second.y > first.y).all()
    assert set(first.regime) == {"public", "private"}
