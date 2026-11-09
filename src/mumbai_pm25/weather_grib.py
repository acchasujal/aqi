"""Verified ecCodes decoding; no inference from filenames or binary value offsets."""

from __future__ import annotations

import datetime as dt
import hashlib
from pathlib import Path
from typing import Any

import numpy as np

AUDIT_KEYS = [
    "edition",
    "centre",
    "subCentre",
    "dataDate",
    "dataTime",
    "validityDate",
    "validityTime",
    "forecastTime",
    "startStep",
    "endStep",
    "stepUnits",
    "stepType",
    "stepRange",
    "table2Version",
    "indicatorOfParameter",
    "paramId",
    "discipline",
    "parameterCategory",
    "parameterNumber",
    "shortName",
    "name",
    "units",
    "productDefinitionTemplateNumber",
    "typeOfLevel",
    "level",
    "gridType",
    "Ni",
    "Nj",
    "latitudeOfFirstGridPointInDegrees",
    "longitudeOfFirstGridPointInDegrees",
    "latitudeOfLastGridPointInDegrees",
    "longitudeOfLastGridPointInDegrees",
    "iDirectionIncrementInDegrees",
    "jDirectionIncrementInDegrees",
    "scanningMode",
    "iScansNegatively",
    "jScansPositively",
    "jPointsAreConsecutive",
    "alternativeRowScanning",
    "bitmapPresent",
    "numberOfMissing",
    "numberOfValues",
    "numberOfDataPoints",
    "packingType",
    "localTablesVersion",
    "tablesVersion",
]
HPBL_REFERENCE = "https://www.nco.ncep.noaa.gov/pmb/docs/grib2/grib2_doc/grib2_table4-2-0-3.shtml"


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def validate_grib_envelope(path: Path) -> int:
    """Validate WMO edition1/2 message framing only; ecCodes decodes content."""
    data = path.read_bytes()
    offset = count = 0
    while offset < len(data):
        if data[offset : offset + 4] != b"GRIB" or offset + 8 > len(data):
            raise ValueError(f"{path}: malformed GRIB signature at {offset}")
        edition = data[offset + 7]
        if edition == 1:
            size = int.from_bytes(data[offset + 4 : offset + 7], "big")
        elif edition == 2 and offset + 16 <= len(data):
            size = int.from_bytes(data[offset + 8 : offset + 16], "big")
        else:
            raise ValueError(f"{path}: unsupported/truncated GRIB edition {edition}")
        if size < (12 if edition == 1 else 20) or offset + size > len(data):
            raise ValueError(f"{path}: truncated/invalid message length")
        if data[offset + size - 4 : offset + size] != b"7777":
            raise ValueError(f"{path}: missing GRIB end marker")
        offset += size
        count += 1
    if not count:
        raise ValueError(f"{path}: empty GRIB")
    return count


def decode_grib(path: Path, *, include_grid: bool = False) -> dict[str, Any]:
    """Decode all messages, retaining unknown units and explicit missing values."""
    expected = validate_grib_envelope(path)
    try:
        import eccodes as ec
    except ImportError as exc:
        raise RuntimeError("ecCodes required; see weather/DECODER_SETUP.md") from exc
    rows = []
    with path.open("rb") as stream:
        while (handle := ec.codes_grib_new_from_file(stream)) is not None:
            try:
                row = {
                    key: ec.codes_get(handle, key)
                    if ec.codes_is_defined(handle, key) and not ec.codes_is_missing(handle, key)
                    else None
                    for key in AUDIT_KEYS
                }
                values = ec.codes_get_values(handle)
                lat = ec.codes_get_array(handle, "latitudes")
                lon = ec.codes_get_array(handle, "longitudes")
                valid = np.isfinite(values) & (values != ec.codes_get(handle, "missingValue"))
                if row["gridType"] != "regular_ll":
                    raise ValueError("Only audited regular_ll grids supported")
                if len(values) != row["Ni"] * row["Nj"] or len(lat) != len(values):
                    raise ValueError("Grid dimensions/value count mismatch")
                row.update(
                    message=len(rows) + 1,
                    finite_count=int(valid.sum()),
                    minimum=float(values[valid].min()) if valid.any() else None,
                    maximum=float(values[valid].max()) if valid.any() else None,
                    mean=float(values[valid].mean()) if valid.any() else None,
                    latitude_extent=[float(lat.min()), float(lat.max())],
                    longitude_extent=[float(lon.min()), float(lon.max())],
                )
                # Preserve native unknown metadata; resolve only this exact NCEP local code.
                hpbl = (
                    row["centre"],
                    row["discipline"],
                    row["parameterCategory"],
                    row["parameterNumber"],
                ) == ("kwbc", 0, 3, 196)
                row["resolved_units"] = "m" if hpbl else row["units"]
                row["unit_reference"] = HPBL_REFERENCE if hpbl else "ecCodes metadata"
                if include_grid:
                    row.update(
                        latitudes=lat.tolist(),
                        longitudes=lon.tolist(),
                        values=[float(v) if ok else None for v, ok in zip(values, valid)],
                    )
                rows.append(row)
            finally:
                ec.codes_release(handle)
    if len(rows) != expected:
        raise ValueError("ecCodes message count differs from framing count")
    return {
        "schema_version": "1.0",
        "decoder": "ecCodes " + ec.codes_get_api_version(),
        "filename": path.name,
        "sha256": sha256(path),
        "size_bytes": path.stat().st_size,
        "message_count": len(rows),
        "messages": rows,
    }


def field_name(row: dict, source: str) -> str | None:
    """Exact identifier AND level selection; averages never replace instantaneous fields."""
    if row["stepType"] != "instant" or row["startStep"] != row["endStep"]:
        return None
    if source == "cams" and row["centre"] == "ecmf" and row["edition"] == 1:
        if (row["typeOfLevel"], row["level"]) != ("surface", 0):
            return None
        return {
            (128, 165): "cams_u10_ms",
            (128, 166): "cams_v10_ms",
            (128, 167): "cams_temperature_2m_c",
            (128, 168): "cams_dewpoint_2m_c",
            (128, 134): "cams_surface_pressure_pa",
            (210, 73): "cams_pm25_ug_m3",
        }.get((row["table2Version"], row["indicatorOfParameter"]))
    if source == "gfs" and row["centre"] == "kwbc" and row["edition"] == 2:
        return {
            (0, 3, 196, "surface", 0): "gfs_hpbl_m",
            (0, 0, 0, "heightAboveGround", 2): "gfs_temperature_2m_c",
            (0, 1, 1, "heightAboveGround", 2): "gfs_relative_humidity_2m_pct",
            (0, 2, 2, "heightAboveGround", 10): "gfs_u10_ms",
            (0, 2, 3, "heightAboveGround", 10): "gfs_v10_ms",
            (0, 1, 7, "surface", 0): "gfs_prate_native",
        }.get(
            (
                row["discipline"],
                row["parameterCategory"],
                row["parameterNumber"],
                row["typeOfLevel"],
                row["level"],
            )
        )
    return None


def required_fields(source: str) -> tuple[str, ...]:
    return {
        "cams": (
            "cams_u10_ms",
            "cams_v10_ms",
            "cams_temperature_2m_c",
            "cams_dewpoint_2m_c",
            "cams_surface_pressure_pa",
            "cams_pm25_ug_m3",
        ),
        "gfs": (
            "gfs_hpbl_m",
            "gfs_temperature_2m_c",
            "gfs_relative_humidity_2m_pct",
            "gfs_u10_ms",
            "gfs_v10_ms",
            "gfs_prate_native",
        ),
    }[source]


def validate_run(
    messages: list[dict], source: str, date: int, cycle: int, leads: list[int]
) -> list[dict]:
    """Fail closed on incomplete fields, duplicate keys, wrong/mixed runs or units."""
    selected = []
    keys = set()
    for row in messages:
        if (row["dataDate"], row["dataTime"]) != (date, cycle * 100):
            raise ValueError("Wrong run or run mixing")
        if row["stepUnits"] != 1:
            raise ValueError("Forecast steps must be hours")
        name = field_name(row, source)
        if name is None or row["endStep"] not in leads:
            continue
        run = dt.datetime.strptime(f"{date}{cycle:02d}00", "%Y%m%d%H%M")
        valid = dt.datetime.strptime(
            f"{row['validityDate']}{row['validityTime']:04d}", "%Y%m%d%H%M"
        )
        if valid != run + dt.timedelta(hours=row["endStep"]):
            raise ValueError("Valid time disagrees with forecast lead")
        unit = row.get("resolved_units", row["units"])
        expected_unit = (
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
        )
        if unit != expected_unit:
            raise ValueError(f"Unverified units for {name}: {unit}")
        key = (name, row["endStep"])
        if key in keys:
            raise ValueError(f"Duplicate parameter/lead {key}")
        keys.add(key)
        if row["finite_count"] != row["Ni"] * row["Nj"]:
            raise ValueError(f"Missing grid values for {key}")
        selected.append(row)
    expected = {(name, lead) for name in required_fields(source) for lead in leads}
    if keys != expected:
        raise ValueError(f"Incomplete {source} coverage; missing {sorted(expected - keys)[:8]}")
    return selected
