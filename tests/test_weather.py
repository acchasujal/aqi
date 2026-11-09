from __future__ import annotations

import copy
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import numpy as np
import pandas as pd
import pytest

from mumbai_pm25.weather_download import cams_request, fetch_gfs_file, gfs_url
from mumbai_pm25.weather_features import (
    align_block,
    bilinear,
    convert_unit,
    export_pfix_fallback,
    target_midpoints,
)
from mumbai_pm25.weather_grib import field_name, validate_grib_envelope, validate_run


def test_supplied_grib_framing_and_corruption(tmp_path):
    for filename, count in [
        ("f65626933fa022c9da340289d7db86e7.grib", 605),
        ("gfs.t06z.pgrb2.0p25.f061", 8),
    ]:
        audit = json.loads(
            (Path("reports/ml_pipeline/weather") / (filename + ".audit.json")).read_text()
        )
        raw = Path("data/external/weather/incoming") / filename
        if raw.exists():
            assert validate_grib_envelope(raw) == count == audit["message_count"]
            broken = tmp_path / "broken.grib"
            broken.write_bytes(raw.read_bytes()[:-1])
            with pytest.raises(ValueError):
                validate_grib_envelope(broken)


@pytest.mark.parametrize(
    "content", [b"", b"<html>Error</html>", b"GRIB\0\0\0\3", b"GRIB\0\0\x0c\x017778"]
)
def test_reject_malformed_grib(tmp_path, content):
    path = tmp_path / "bad"
    path.write_bytes(content)
    with pytest.raises(ValueError):
        validate_grib_envelope(path)


def test_request_completeness_and_filter_names():
    request = cams_request("2026-11-08", 0, 67, 114)
    assert request["leadtime_hour"] == [str(h) for h in range(67, 115)]
    assert len(request["variable"]) == 6 and request["area"] == [20, 72, 18, 74]
    final = cams_request("2026-11-10", 0, 19, 66)
    assert len(final["leadtime_hour"]) == 48
    query = parse_qs(urlparse(gfs_url("20261108", 6, 61)).query)
    assert query["dir"] == ["/gfs.20261108/06/atmos/"]
    assert query["lev_2_m_above_ground"] == ["on"]
    assert len([k for k in query if k.startswith("var_")]) == 6
    assert not {"all_var", "all_lev"} & query.keys()


def gfs_messages():
    payload = json.loads(
        Path("reports/ml_pipeline/weather/gfs.t06z.pgrb2.0p25.f061.audit.json").read_text()
    )
    for row in payload["messages"]:
        if row["parameterNumber"] == 196:
            row["resolved_units"] = "m"
    return payload["messages"]


def test_exact_parameters_levels_and_separate_prate():
    messages = gfs_messages()
    selected = validate_run(messages, "gfs", 20261108, 6, [61])
    assert len(selected) == 6
    assert field_name(messages[0], "gfs") is None  # surface TMP
    assert field_name(messages[6], "gfs") is None  # interval-average PRATE
    assert field_name(messages[5], "gfs") == "gfs_prate_native"
    with pytest.raises(ValueError, match="Incomplete"):
        validate_run(messages, "gfs", 20261108, 6, list(range(61, 109)))
    with pytest.raises(ValueError, match="Duplicate"):
        validate_run(messages + [selected[0]], "gfs", 20261108, 6, [61])
    wrong = copy.deepcopy(messages)
    wrong[0]["dataDate"] = 20261109
    with pytest.raises(ValueError, match="run"):
        validate_run(wrong, "gfs", 20261108, 6, [61])
    wrong = copy.deepcopy(messages)
    wrong[1]["units"] = "C"
    with pytest.raises(ValueError, match="units"):
        validate_run(wrong, "gfs", 20261108, 6, [61])


def test_cams_rejects_missing_field_despite_full_hour_coverage():
    payload = json.loads(
        Path(
            "reports/ml_pipeline/weather/f65626933fa022c9da340289d7db86e7.grib.audit.json"
        ).read_text()
    )
    assert len({m["endStep"] for m in payload["messages"]}) == 121
    with pytest.raises(ValueError, match="cams_surface_pressure_pa"):
        validate_run(payload["messages"], "cams", 20261108, 0, list(range(67, 115)))


def test_bilinear_scanning_weights_and_missing():
    # Reversed scanning order still recovers f(y,x)=2y+3x exactly.
    result = bilinear([1, 1, 0, 0], [1, 0, 1, 0], [5, 2, 3, 0], 0.25, 0.75)
    assert result["value"] == pytest.approx(2.75)
    assert sum(c["weight"] for c in result["corners"]) == pytest.approx(1)
    assert bilinear([0, 0, 1, 1], [0, 1, 0, 1], [0, 3, 2, 5], 1, 1)["value"] == 5
    with pytest.raises(ValueError, match="out of grid"):
        bilinear([0, 0, 1, 1], [0, 1, 0, 1], [0, 3, 2, 5], 2, 1)
    with pytest.raises(ValueError, match="corner"):
        bilinear([0, 0, 1, 1], [0, 1, 0, 1], [0, None, 2, 5], 0.5, 0.5)
    with pytest.raises(ValueError, match="rectangular"):
        bilinear([0, 0, 1], [0, 1, 0], [0, 3, 2], 0.5, 0.5)


def test_units_do_not_impute_missing_as_zero():
    assert convert_unit("cams_pm25_ug_m3", 4e-8, "kg m**-3") == 40
    assert convert_unit("cams_temperature_2m_c", 300, "K") == pytest.approx(26.85)
    assert convert_unit("gfs_prate_native", 0, "kg m**-2 s**-1") == 0
    for value, unit in [(np.nan, "kg m**-3"), (40, "ug/m3")]:
        with pytest.raises(ValueError):
            convert_unit("cams_pm25_ug_m3", value, unit)


def block():
    starts = pd.date_range("2026-11-11", periods=48, freq="h", tz="Asia/Kolkata")
    targets = pd.DataFrame({"location_id": 1, "target_start": starts})
    weather = pd.DataFrame(
        {
            "location_id": 1,
            "valid_time_utc": target_midpoints(targets.target_start),
            "feature": "gfs_hpbl_m",
            "value": 100.0,
            "source": "gfs",
            "run_utc": pd.Timestamp("2026-11-08T06:00Z"),
        }
    )
    clocks = {
        "issue_time": "2026-11-08T23:00+05:30",
        "pm_history_cutoff": "2026-11-02T23:00+05:30",
        "available_at": "2026-11-08T12:00Z",
        "availability_evidence": "retrieval receipt",
        "features": ("gfs_hpbl_m",),
    }
    return targets, weather, clocks


def test_exact_ist_utc_midpoint_alignment_and_independent_clocks():
    targets, weather, clocks = block()
    midpoint = target_midpoints(targets.target_start)
    assert midpoint[0] == pd.Timestamp("2026-11-10T19:00Z")
    assert midpoint[-1] == pd.Timestamp("2026-11-12T18:00Z")
    aligned = align_block(targets, weather, **clocks)
    assert aligned.weather_lead_hours.tolist() == list(range(61, 109))
    assert (aligned.pm_history_cutoff < aligned.prediction_origin).all()
    with pytest.raises(ValueError, match="timezone"):
        target_midpoints(pd.Series(["2026-11-11T00:00"]))


@pytest.mark.parametrize("failure", ["late", "mix", "gap", "nan", "shift", "duplicate", "evidence"])
def test_alignment_leakage_and_coverage_gates(failure):
    targets, weather, clocks = block()
    if failure == "late":
        clocks["available_at"] = "2026-11-09T00:00Z"
    elif failure == "mix":
        weather.loc[0, "run_utc"] += pd.Timedelta(hours=6)
    elif failure == "gap":
        targets = targets.iloc[:-1]
    elif failure == "nan":
        weather.loc[0, "value"] = np.nan
    elif failure == "shift":
        weather["valid_time_utc"] += pd.Timedelta(minutes=30)
    elif failure == "duplicate":
        weather = pd.concat([weather, weather.iloc[[0]]])
    else:
        clocks["availability_evidence"] = ""
    with pytest.raises(ValueError):
        align_block(targets, weather, **clocks)


def test_deterministic_control_export_and_existing_file_protection(tmp_path):
    test = pd.DataFrame({"ID": ["a", "b"]})
    control = pd.DataFrame({"ID": ["a", "b"], "Target": [1.25, 2.0]})
    for name in ["one.csv", "two.csv"]:
        export_pfix_fallback(control, test, tmp_path / name)
    assert (tmp_path / "one.csv").read_bytes() == (tmp_path / "two.csv").read_bytes()
    with pytest.raises(FileExistsError):
        export_pfix_fallback(control, test, tmp_path / "one.csv")
    with pytest.raises(ValueError):
        export_pfix_fallback(control.iloc[::-1], test, tmp_path / "bad.csv")


def test_download_never_overwrites_unverified_existing_file(tmp_path):
    path = tmp_path / "existing.grib2"
    path.write_bytes(b"preserve")
    with pytest.raises(ValueError, match="hash receipt"):
        fetch_gfs_file(path, "20261108", 6, 61)
    assert path.read_bytes() == b"preserve"


def test_full_gfs_block_rejects_internal_missing_hour():
    template = [m for m in gfs_messages() if field_name(m, "gfs") is not None]
    records = []
    for lead in range(61, 109):
        for message in copy.deepcopy(template):
            message["startStep"] = message["endStep"] = lead
            valid = pd.Timestamp("2026-11-08T06:00Z") + pd.Timedelta(hours=lead)
            message["validityDate"] = int(valid.strftime("%Y%m%d"))
            message["validityTime"] = int(valid.strftime("%H%M"))
            records.append(message)
    assert len(validate_run(records, "gfs", 20261108, 6, list(range(61, 109)))) == 288
    missing_internal = [m for m in records if m["endStep"] != 77]
    with pytest.raises(ValueError, match="Incomplete"):
        validate_run(missing_internal, "gfs", 20261108, 6, list(range(61, 109)))


def test_http_html_error_is_recorded_without_raw_file(tmp_path, monkeypatch):
    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self, limit):
            return b"<html>Upstream unavailable</html>"

    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: Response())
    target = tmp_path / "noaa.grib2"
    with pytest.raises(RuntimeError, match="retrieval failed"):
        fetch_gfs_file(target, "20261108", 6, 61, attempts=1)
    assert not target.exists() and not target.with_suffix(".grib2.part").exists()
    assert "non-GRIB" in target.with_suffix(".grib2.errors.json").read_text()
