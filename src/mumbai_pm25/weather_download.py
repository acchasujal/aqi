"""Reproducible research downloads; raw files are immutable and hash-verified."""

from __future__ import annotations

import datetime as dt
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from mumbai_pm25.weather_grib import decode_grib, sha256, validate_run

CAMS_DATASET = "cams-global-atmospheric-composition-forecasts"
CAMS_VARIABLES = (
    "10m_u_component_of_wind",
    "10m_v_component_of_wind",
    "2m_dewpoint_temperature",
    "2m_temperature",
    "particulate_matter_2.5um",
    "surface_pressure",
)
NOMADS = "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl"


def cams_request(date: str, cycle: int, first: int, last: int) -> dict:
    dt.date.fromisoformat(date)
    if cycle not in (0, 12) or not 0 <= first <= last <= 120:
        raise ValueError("CAMS requires 00/12Z and leads in 0..120")
    return {
        "date": date,
        "time": f"{cycle:02d}:00",
        "type": "forecast",
        "variable": list(CAMS_VARIABLES),
        "leadtime_hour": [str(h) for h in range(first, last + 1)],
        "area": [20, 72, 18, 74],
        "data_format": "grib",
    }


def gfs_url(date: str, cycle: int, lead: int) -> str:
    dt.datetime.strptime(date, "%Y%m%d")
    if cycle not in (0, 6, 12, 18) or not 0 <= lead <= 120:
        raise ValueError("GFS requires 00/06/12/18Z and hourly leads in 0..120")
    params = {
        "file": f"gfs.t{cycle:02d}z.pgrb2.0p25.f{lead:03d}",
        "dir": f"/gfs.{date}/{cycle:02d}/atmos/",
        "subregion": "",
        "toplat": 19.6,
        "bottomlat": 18.6,
        "leftlon": 72.4,
        "rightlon": 73.4,
        "lev_surface": "on",
        "lev_2_m_above_ground": "on",
        "lev_10_m_above_ground": "on",
    }
    params.update({f"var_{v}": "on" for v in ("HPBL", "TMP", "RH", "UGRD", "VGRD", "PRATE")})
    return NOMADS + "?" + urllib.parse.urlencode(params)


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _receipt(
    path: Path, source: str, date: int, cycle: int, leads: list[int], request: str | dict
) -> dict:
    audit = decode_grib(path)
    validate_run(audit["messages"], source, date, cycle, leads)
    return {
        "schema_version": "1.0",
        "source": source,
        "request": request,
        "source_sha256": audit["sha256"],
        "raw_path": path.as_posix(),
        "retrieved_at_utc": dt.datetime.now(dt.UTC).isoformat(),
        "publication_time_utc": None,
        "availability_basis": "retrieval upper bound only",
        "eligibility": "BLOCKED_PENDING_CATALOGUE_EVIDENCE",
        "forecast_initialisation_utc": (
            dt.datetime.strptime(str(date), "%Y%m%d").replace(hour=cycle, tzinfo=dt.UTC).isoformat()
        ),
        "leads": leads,
        "audit": audit,
    }


def _verified_existing(
    path: Path, source: str, date: int, cycle: int, leads: list[int], request: str | dict
) -> bool:
    if not path.exists():
        return False
    receipt_path = path.with_suffix(path.suffix + ".receipt.json")
    if not receipt_path.is_file():
        raise ValueError(f"Existing file lacks hash receipt; preserve and audit separately: {path}")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt["source_sha256"] != sha256(path) or receipt["request"] != request:
        raise ValueError(f"Existing hash/request mismatch; refusing overwrite: {path}")
    validate_run(decode_grib(path)["messages"], source, date, cycle, leads)
    return True


def fetch_gfs_file(
    path: Path, date: str, cycle: int, lead: int, *, attempts: int = 3, timeout: int = 60
) -> dict:
    url = gfs_url(date, cycle, lead)
    if _verified_existing(path, "gfs", int(date), cycle, [lead], url):
        return json.loads(path.with_suffix(path.suffix + ".receipt.json").read_text())
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(path.suffix + ".part")
    if partial.exists():
        raise ValueError(f"Stale partial must be inspected before retry: {partial}")
    errors = []
    for attempt in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mumbai-PM25-research/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                if response.status != 200:
                    raise ValueError(f"HTTP {response.status}")
                data = response.read(10_000_001)
            if len(data) > 10_000_000 or not data.startswith(b"GRIB"):
                raise ValueError("Unexpected non-GRIB/oversized response")
            with partial.open("xb") as stream:
                stream.write(data)
            receipt = _receipt(partial, "gfs", int(date), cycle, [lead], url)
            receipt["raw_path"] = path.as_posix()
            if receipt["audit"]["message_count"] > 12:
                raise ValueError("Filter returned excessive unrelated messages")
            os.link(partial, path)  # exclusive atomic publication; never replaces an existing file
            partial.unlink()
            _write_json(path.with_suffix(path.suffix + ".receipt.json"), receipt)
            return receipt
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            errors.append({"attempt": attempt + 1, "error": str(exc), "url": url})
            if partial.exists():
                partial.unlink()
            _write_json(path.with_suffix(path.suffix + ".errors.json"), {"errors": errors})
            if attempt + 1 == attempts:
                raise RuntimeError(f"GFS retrieval failed: {path}; see error receipt") from exc
            time.sleep(2**attempt)
    raise ValueError("attempts must be positive")


def fetch_gfs_block(directory: Path, date: str, cycle: int, first: int, last: int) -> list[dict]:
    if last - first != 47:
        raise ValueError("Expected exactly 48 consecutive GFS hours")
    receipts = []
    for lead in range(first, last + 1):
        # The first file passes decoding/coverage before any subsequent request.
        name = f"gfs_{date}_{cycle:02d}Z_f{lead:03d}_mumbai.grib2"
        receipts.append(fetch_gfs_file(directory / name, date, cycle, lead))
        time.sleep(0.5)
    return receipts


def fetch_cams(path: Path, request: dict) -> dict:
    date = int(request["date"].replace("-", ""))
    cycle = int(request["time"][:2])
    leads = [int(h) for h in request["leadtime_hour"]]
    if _verified_existing(path, "cams", date, cycle, leads, request):
        return json.loads(path.with_suffix(path.suffix + ".receipt.json").read_text())
    config = Path(os.environ.get("CDSAPI_RC", Path.home() / ".cdsapirc"))
    if not config.is_file() and not os.environ.get("CDSAPI_KEY"):
        raise RuntimeError(
            "ADS credentials absent; configure privately, never paste/commit a token"
        )
    try:
        import cdsapi
    except ImportError as exc:
        raise RuntimeError("Install optional cdsapi>=0.7.7 in the decoder environment") from exc
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(path.suffix + ".part")
    if partial.exists():
        raise ValueError("Preserve/inspect existing CAMS partial before retry")
    # Explicit ADS endpoint prevents accidental submission to the CDS service.
    cdsapi.Client(url="https://ads.atmosphere.copernicus.eu/api", timeout=60).retrieve(
        CAMS_DATASET, request, str(partial)
    )
    receipt = _receipt(partial, "cams", date, cycle, leads, request)
    receipt["raw_path"] = path.as_posix()
    os.link(partial, path)
    partial.unlink()
    _write_json(path.with_suffix(path.suffix + ".receipt.json"), receipt)
    return receipt
