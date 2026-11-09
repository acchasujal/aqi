"""Causality and schema tests for experimental OOF calibration."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from mumbai_pm25.calibration import METHODS, PRIOR_ROWS, rolling_calibration


def oof_fixture() -> pd.DataFrame:
    parts = []
    for start in pd.date_range("2026-01-15", periods=12, freq="7D", tz="Asia/Kolkata"):
        for station in (11606, 11611):
            times = pd.date_range(start, periods=48, freq="h")
            forecast = 30.0 + times.hour.to_numpy()
            parts.append(pd.DataFrame({"fold_id": start, "prediction_origin": start-pd.Timedelta(hours=193),
                "pm_history_cutoff": start-pd.Timedelta(hours=193), "target_start": times,
                "target_end": times+pd.Timedelta(hours=1), "block_target_end": start+pd.Timedelta(hours=48),
                "location_id": station, "P_fix": forecast, "y": forecast-5,
                "split": "development"}))
    return pd.concat(parts, ignore_index=True)


@pytest.mark.parametrize("method", METHODS)
def test_future_and_current_labels_never_enter_calibration(method):
    rows = oof_fixture()
    original = rows.copy(deep=True)
    first, lineage = rolling_calibration(rows, method)
    pd.testing.assert_frame_equal(rows, original)
    last = rows.fold_id.max()
    cutoff = rows.loc[rows.fold_id.eq(last), "pm_history_cutoff"].iloc[0]
    changed = rows.copy()
    # Includes the prior but not yet fully available target block.
    changed.loc[changed.block_target_end.gt(cutoff), "y"] = 241587.56
    second, _ = rolling_calibration(changed, method)
    np.testing.assert_array_equal(first.loc[rows.fold_id.eq(last)], second.loc[rows.fold_id.eq(last)])
    available = lineage.training_end_max.notna()
    assert lineage.loc[available, "training_end_max"].le(lineage.loc[available, "fitting_cutoff"]).all()
    assert np.isfinite(first).all() and first.ge(0).all()
    assert first.loc[rows.fold_id.eq(rows.fold_id.min())].equals(rows.loc[rows.fold_id.eq(rows.fold_id.min()), "P_fix"])


def test_station_isolation_and_unmodified_extremes():
    rows = oof_fixture()
    base, lineage = rolling_calibration(rows, "cal_offset")
    changed = rows.copy()
    changed.loc[changed.location_id.eq(11611), "y"] = 241587.56
    extreme, _ = rolling_calibration(changed, "cal_offset")
    np.testing.assert_array_equal(base.loc[rows.location_id.eq(11606)], extreme.loc[rows.location_id.eq(11606)])
    assert extreme.loc[rows.location_id.eq(11611)].max() > 1000
    fit = lineage.iloc[-1]
    expected = -5 * fit.training_rows / (fit.training_rows + PRIOR_ROWS)
    assert fit.intercept == pytest.approx(expected)
    assert rows.y.max() < 1000
    assert changed.y.max() == 241587.56


def test_order_invariance_nonnegative_output_and_invalid_schema():
    rows = oof_fixture()
    base, _ = rolling_calibration(rows, "cal_affine")
    shuffled = rows.sample(frac=1, random_state=12)
    result, _ = rolling_calibration(shuffled, "cal_affine")
    np.testing.assert_allclose(base, result.reindex(rows.index), atol=1e-10)
    invalid = rows.copy()
    invalid.loc[0, "P_fix"] = np.inf
    with pytest.raises(ValueError, match="finite"):
        rolling_calibration(invalid, "cal_offset")
    with pytest.raises(ValueError, match="unique"):
        rolling_calibration(pd.concat([rows, rows.iloc[:1]]), "cal_offset")
    invalid = rows.copy()
    invalid["pm_history_cutoff"] = invalid.target_start
    with pytest.raises(ValueError, match="clocks"):
        rolling_calibration(invalid, "cal_offset")
    invalid = rows.copy()
    invalid["target_end"] = invalid.target_end.dt.tz_localize(None)
    with pytest.raises(ValueError, match="timezone-aware"):
        rolling_calibration(invalid, "cal_offset")
    rows["y"] = 0.0
    prediction, _ = rolling_calibration(rows, "cal_affine")
    assert prediction.ge(0).all()


def test_csv_audit_rejects_reordered_submission(tmp_path):
    from scripts.run_exp024 import FILES, audit_supplied

    test = pd.DataFrame({"ID": ["a", "b"], "location_id": [11606, 11606],
        "target_start": pd.date_range("2026-11-11", periods=2, freq="h", tz="Asia/Kolkata")})
    stations = pd.DataFrame({"location_id": [11606], "station_name": ["Borivali East"]})
    for name in FILES:
        pd.DataFrame({"ID": ["a", "b"], "Target": [10., 20.]}).to_csv(tmp_path / name, index=False)
    audit = audit_supplied(tmp_path, test, stations)
    assert audit["pairs"][0]["identical_values"]
    pd.DataFrame({"ID": ["b", "a"], "Target": [20., 10.]}).to_csv(tmp_path / FILES[2], index=False)
    with pytest.raises(ValueError, match="order"):
        audit_supplied(tmp_path, test, stations)


def test_experiment_refuses_to_overwrite(tmp_path):
    from scripts.run_exp024 import run

    with pytest.raises(FileExistsError, match="unused"):
        run(Path("unused"), Path("unused"), tmp_path)
