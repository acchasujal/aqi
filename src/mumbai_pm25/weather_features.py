"""Research-only weather alignment with explicit independent information clocks."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from mumbai_pm25.weather_grib import field_name


def utc(value: str | pd.Timestamp) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if pd.isna(timestamp) or timestamp.tzinfo is None:
        raise ValueError("Explicit timezone required")
    return timestamp.tz_convert("UTC")


def target_midpoints(target_start: pd.Series) -> pd.DatetimeIndex:
    starts = pd.DatetimeIndex([utc(t) for t in target_start])
    if not (
        (starts.tz_convert("Asia/Kolkata").minute == 0)
        & (starts.second == 0)
        & (starts.microsecond == 0)
    ).all():
        raise ValueError("Expected whole IST target hours")
    return starts + pd.Timedelta(minutes=30)


def bilinear(
    latitudes: list, longitudes: list, values: list, latitude: float, longitude: float
) -> dict:
    lat, lon, val = (np.asarray(x, dtype=float) for x in (latitudes, longitudes, values))
    if not (len(lat) == len(lon) == len(val)) or not len(lat):
        raise ValueError("Grid coordinate/value lengths mismatch")
    if not np.isfinite(lat).all() or not np.isfinite(lon).all():
        raise ValueError("Nonfinite coordinates")
    ys, xs = np.unique(lat), np.unique(lon)
    if len(ys) < 2 or len(xs) < 2 or len(val) != len(ys) * len(xs):
        raise ValueError("Incomplete rectangular grid")
    if not (
        np.isfinite(latitude)
        and np.isfinite(longitude)
        and ys[0] <= latitude <= ys[-1]
        and xs[0] <= longitude <= xs[-1]
    ):
        raise ValueError("Station out of grid")
    yi = min(max(np.searchsorted(ys, latitude) - 1, 0), len(ys) - 2)
    xi = min(max(np.searchsorted(xs, longitude) - 1, 0), len(xs) - 2)
    y0, y1, x0, x1 = ys[yi], ys[yi + 1], xs[xi], xs[xi + 1]
    dy, dx = (latitude - y0) / (y1 - y0), (longitude - x0) / (x1 - x0)
    corners = []
    for y, x, weight in [
        (y0, x0, (1 - dy) * (1 - dx)),
        (y0, x1, (1 - dy) * dx),
        (y1, x0, dy * (1 - dx)),
        (y1, x1, dy * dx),
    ]:
        indices = np.flatnonzero(
            np.isclose(lat, y, atol=1e-8, rtol=0) & np.isclose(lon, x, atol=1e-8, rtol=0)
        )
        if len(indices) != 1 or not np.isfinite(val[indices[0]]):
            raise ValueError("Missing/duplicate/nonfinite interpolation corner")
        corners.append(
            {
                "latitude": float(y),
                "longitude": float(x),
                "weight": float(weight),
                "value": float(val[indices[0]]),
            }
        )
    nearest = np.argmin((lat - latitude) ** 2 + (lon - longitude) ** 2)
    if not np.isfinite(val[nearest]):
        raise ValueError("Missing nearest-grid diagnostic")
    return {
        "value": sum(c["weight"] * c["value"] for c in corners),
        "nearest_value": float(val[nearest]),
        "nearest_latitude": float(lat[nearest]),
        "nearest_longitude": float(lon[nearest]),
        "corners": corners,
    }


def convert_unit(name: str, value: float, unit: str) -> float:
    expected = (
        "kg m**-3"
        if name == "cams_pm25_ug_m3"
        else "K"
        if name.endswith("_c")
        else "m s**-1"
        if name.endswith("_ms")
        else "Pa"
        if name.endswith("_pa")
        else "%"
        if name.endswith("_pct")
        else "m"
        if name == "gfs_hpbl_m"
        else "kg m**-2 s**-1"
        if name == "gfs_prate_native"
        else None
    )
    if unit != expected or expected is None or not np.isfinite(value):
        raise ValueError(f"Unverified unit or missing value: {name} {unit}")
    return (
        value * 1e9
        if name == "cams_pm25_ug_m3"
        else (value - 273.15 if name.endswith("_c") else value)
    )


def extract_station_rows(
    messages: list[dict], source: str, stations: pd.DataFrame, *, source_hash: str
) -> pd.DataFrame:
    if stations.location_id.duplicated().any() or len(stations) != 4:
        raise ValueError("Expected four unique Stations.csv locations")
    rows = []
    for message in messages:
        name = field_name(message, source)
        if name is None:
            continue
        run = pd.to_datetime(
            f"{message['dataDate']}{message['dataTime']:04d}", format="%Y%m%d%H%M", utc=True
        )
        valid = pd.to_datetime(
            f"{message['validityDate']}{message['validityTime']:04d}", format="%Y%m%d%H%M", utc=True
        )
        if valid != run + pd.Timedelta(hours=message["endStep"]):
            raise ValueError("Decoded valid time disagrees with forecast lead")
        for station in stations.itertuples(index=False):
            diagnostic = bilinear(
                message["latitudes"],
                message["longitudes"],
                message["values"],
                station.latitude,
                station.longitude,
            )
            unit = message.get("resolved_units", message["units"])
            rows.append(
                {
                    "source": source,
                    "location_id": station.location_id,
                    "feature": name,
                    "value": convert_unit(name, diagnostic["value"], unit),
                    "native_unit": message["units"],
                    "resolved_unit": unit,
                    "converted_unit": (
                        "ug/m3"
                        if name == "cams_pm25_ug_m3"
                        else "degC"
                        if name.endswith("_c")
                        else unit
                    ),
                    "unit_reference": message.get("unit_reference", "ecCodes metadata"),
                    "run_utc": run,
                    "valid_time_utc": valid,
                    "forecast_lead_hours": message["endStep"],
                    "station_latitude": station.latitude,
                    "station_longitude": station.longitude,
                    "nearest_native_value": diagnostic["nearest_value"],
                    "interpolation": json.dumps(diagnostic, sort_keys=True),
                    "grib_identifiers": json.dumps(
                        {
                            k: message.get(k)
                            for k in (
                                "edition",
                                "centre",
                                "table2Version",
                                "indicatorOfParameter",
                                "discipline",
                                "parameterCategory",
                                "parameterNumber",
                                "typeOfLevel",
                                "level",
                                "stepType",
                                "startStep",
                                "endStep",
                                "productDefinitionTemplateNumber",
                            )
                        },
                        sort_keys=True,
                    ),
                    "grid": json.dumps(
                        {
                            k: message.get(k)
                            for k in (
                                "Ni",
                                "Nj",
                                "gridType",
                                "latitude_extent",
                                "longitude_extent",
                                "iDirectionIncrementInDegrees",
                                "jDirectionIncrementInDegrees",
                                "scanningMode",
                            )
                        },
                        sort_keys=True,
                    ),
                    "raw_path": message.get("raw_path"),
                    "retrieved_at_utc": message.get("retrieved_at_utc"),
                    "source_sha256": message.get("source_sha256", source_hash),
                }
            )
    result = pd.DataFrame(rows)
    if result.empty or result.duplicated(["location_id", "feature", "valid_time_utc"]).any():
        raise ValueError("Empty or duplicate station weather rows")
    if result.run_utc.nunique() != 1:
        raise ValueError("Run mixing")
    return result


def align_block(
    targets: pd.DataFrame,
    weather: pd.DataFrame,
    *,
    issue_time: str,
    pm_history_cutoff: str,
    available_at: str,
    availability_evidence: str,
    features: tuple[str, ...],
) -> pd.DataFrame:
    issue, cutoff, available = map(utc, (issue_time, pm_history_cutoff, available_at))
    if not availability_evidence.strip() or available > issue or cutoff > issue:
        raise ValueError("Availability evidence or information clocks invalid")
    if weather.run_utc.nunique() != 1 or weather.source.nunique() != 1:
        raise ValueError("Run mixing/source mixing within block")
    run = utc(weather.run_utc.iloc[0])
    if run > available:
        raise ValueError("Run initialisation after claimed availability")
    out = targets.copy()
    out["valid_time_utc"] = target_midpoints(out.target_start)
    if (out.valid_time_utc - pd.Timedelta(minutes=30) <= issue).any():
        raise ValueError("Target interval must follow issue time")
    if out.duplicated(["location_id", "valid_time_utc"]).any():
        raise ValueError("Duplicate target keys")
    times = pd.DatetimeIndex(out.valid_time_utc.unique()).sort_values()
    if len(times) != 48 or not pd.DatetimeIndex(times).equals(
        pd.date_range(times[0], periods=48, freq="h")
    ):
        raise ValueError("Expected one complete 48-hour target block")
    if not out.groupby("location_id").size().eq(48).all():
        raise ValueError("Every target station must have all 48 hours")
    selected = weather.loc[weather.feature.isin(features)]
    if selected.duplicated(["location_id", "valid_time_utc", "feature"]).any():
        raise ValueError("Duplicate weather keys")
    wide = selected.pivot(
        index=["location_id", "valid_time_utc"], columns="feature", values="value"
    )
    out = out.join(
        wide.reindex(columns=list(features)),
        on=["location_id", "valid_time_utc"],
        validate="one_to_one",
    )
    if not np.isfinite(out[list(features)].to_numpy(dtype=float)).all():
        raise ValueError("Missing exact midpoint/feature coverage")
    out["prediction_origin"] = issue
    out["pm_history_cutoff"] = cutoff
    out["target_end"] = [utc(t) + pd.Timedelta(hours=1) for t in out.target_start]
    out["weather_run_utc"] = run
    out["weather_available_at_utc"] = available
    out["availability_evidence"] = availability_evidence
    out["weather_lead_hours"] = (out.valid_time_utc - run).dt.total_seconds() / 3600
    return out


def export_pfix_fallback(control: pd.DataFrame, test: pd.DataFrame, path: Path) -> None:
    """Weather has no promoted correction. Export only the validated control, exclusively."""
    from mumbai_pm25.forecast import validate_submission

    validate_submission(control, test)
    with path.open("x", encoding="utf-8", newline="") as stream:
        control.to_csv(stream, index=False, lineterminator="\n")
