#!/usr/bin/env python3
"""Fetch leakage-aware ECMWF IFS single-run weather vintages for Mumbai PM2.5.

Historical backtest example (daily pseudo-target starts):
  python fetch_single_run_weather.py --start-target-date 2025-03-12 --end-target-date 2026-11-04 --output weather_vintages.csv

Final private-window example (run this close to the 10 Nov submission time):
  python fetch_single_run_weather.py --start-target-date 2026-11-11 --end-target-date 2026-11-11 --issue-time-local 2026-11-10T23:00:00 --output weather_private_20261110.csv

The archive mode defaults to an issue time 60 minutes before the first target
interval (adjust with --issue-margin-minutes). The final mode lets you specify
the actual local issue time. For each issue time, it selects the latest 6-hour IFS
run whose nominal availability (run + delay hours) is no later than issue time.
It then falls back to earlier cycles if the requested run is not retrievable or
does not cover the complete target window.

IMPORTANT:
- This script does not decide whether Open-Meteo's free API terms permit your
  competition use. Check terms/organiser permission before relying on it.
- `models=ecmwf_ifs` pins ECMWF IFS HRES. Keep this consistent in historical
  validation and final inference.
- Timestamps returned in Asia/Kolkata are interpreted as IST.
- Weather `time` is matched to the start of the PM2.5 target interval.
- The output contains forecast features only; it never fetches PM2.5 targets.
"""

from __future__ import annotations

import argparse
import datetime as dt
import math
import time
from zoneinfo import ZoneInfo

import pandas as pd
import requests

IST = ZoneInfo("Asia/Kolkata")
UTC = dt.timezone.utc
ENDPOINT = "https://single-runs-api.open-meteo.com/v1/forecast"
MODEL = "ecmwf_ifs"

STATIONS = {
    "BOR": (19.232410, 72.868950),
    "MAL": (19.197090, 72.822040),
    "BYC": (18.976700, 72.838000),
    "SHI": (19.060498, 72.923356),
}

HOURLY = ",".join([
    "temperature_2m",
    "relative_humidity_2m",
    "dew_point_2m",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
    "precipitation",
    "surface_pressure",
    "boundary_layer_height",
    "cloud_cover",
    "shortwave_radiation",
])


def parse_issue_time(value: str | None, target_start: dt.datetime) -> dt.datetime:
    if not value:
        return target_start - dt.timedelta(minutes=1)
    parsed = dt.datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=IST)
    return parsed.astimezone(IST)


def latest_cycle_before(available_by_utc: dt.datetime) -> dt.datetime:
    """Latest UTC 00/06/12/18 cycle <= available_by_utc."""
    t = available_by_utc.astimezone(UTC).replace(minute=0, second=0, microsecond=0)
    t = t.replace(hour=(t.hour // 6) * 6)
    return t


def request_run(session: requests.Session, lat: float, lon: float,
                run_utc: dt.datetime, timeout: int = 90) -> dict:
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": HOURLY,
        "timezone": "Asia/Kolkata",
        "timeformat": "iso8601",
        "models": MODEL,
        "run": run_utc.strftime("%Y-%m-%dT%H:%M"),
        "forecast_days": 4,
        "wind_speed_unit": "ms",
        "precipitation_unit": "mm",
    }
    response = session.get(ENDPOINT, params=params, timeout=timeout)
    if response.status_code != 200:
        raise RuntimeError(f"HTTP {response.status_code}: {response.text[:300]}")
    payload = response.json()
    if "hourly" not in payload or "time" not in payload["hourly"]:
        raise RuntimeError(f"Unexpected API response: {str(payload)[:300]}")
    return payload


def make_rows(payload: dict, station: str, lat: float, lon: float,
              target_start: dt.datetime, target_hours: int,
              issue_time: dt.datetime, run_utc: dt.datetime,
              assumed_delay_hours: float, fallback_steps: int) -> pd.DataFrame:
    hourly = pd.DataFrame(payload["hourly"])
    times = pd.to_datetime(hourly.pop("time"), errors="raise")
    # Open-Meteo returns local ISO strings without an offset when timezone is set.
    # `time` comes from a DataFrame column, so handle it as a Series with `.dt`.
    if isinstance(times, pd.Series):
        if times.dt.tz is None:
            times = times.dt.tz_localize(IST)
        else:
            times = times.dt.tz_convert(IST)
    else:
        if times.tz is None:
            times = times.tz_localize(IST)
        else:
            times = times.tz_convert(IST)
    hourly.insert(0, "valid_time_ist", times)

    target_end = target_start + dt.timedelta(hours=target_hours)
    start_ts = pd.Timestamp(target_start)
    end_ts = pd.Timestamp(target_end)
    hourly = hourly[(hourly.valid_time_ist >= start_ts) & (hourly.valid_time_ist < end_ts)].copy()

    expected = pd.date_range(start=start_ts, periods=target_hours, freq="h")
    got = pd.DatetimeIndex(hourly.valid_time_ist)
    if len(hourly) != target_hours or not got.equals(expected):
        raise RuntimeError(
            f"Run does not cover exact target window: got {len(hourly)} rows, "
            f"expected {target_hours}; first={got.min() if len(got) else None}, "
            f"last={got.max() if len(got) else None}"
        )

    direction = pd.to_numeric(hourly["wind_direction_10m"], errors="coerce")
    speed = pd.to_numeric(hourly["wind_speed_10m"], errors="coerce")
    radians = direction * math.pi / 180.0
    hourly["wind_u_ms"] = -speed * radians.map(math.sin)
    hourly["wind_v_ms"] = -speed * radians.map(math.cos)

    hourly.insert(0, "station", station)
    hourly["latitude"] = lat
    hourly["longitude"] = lon
    hourly["api_grid_latitude"] = payload.get("latitude")
    hourly["api_grid_longitude"] = payload.get("longitude")
    hourly["api_grid_elevation_m"] = payload.get("elevation")
    hourly["api_timezone"] = payload.get("timezone")
    hourly["target_start_ist"] = start_ts
    hourly["issue_time_ist"] = pd.Timestamp(issue_time)
    hourly["issue_time_utc"] = pd.Timestamp(issue_time.astimezone(UTC))
    hourly["run_utc"] = pd.Timestamp(run_utc)
    hourly["assumed_run_delay_hours"] = assumed_delay_hours
    hourly["fallback_steps_6h"] = fallback_steps
    hourly["forecast_lead_hours"] = (
        hourly.valid_time_ist.dt.tz_convert("UTC") - pd.Timestamp(run_utc)
    ).dt.total_seconds() / 3600.0
    hourly["model"] = MODEL
    hourly["source"] = "Open-Meteo Single Runs API"
    return hourly


def fetch_target_date(session: requests.Session, date: dt.date, station: str,
                      coords: tuple[float, float], target_hours: int,
                      issue_time_override: dt.datetime | None,
                      issue_margin_minutes: int,
                      delay_hours: float, fallback_cycles: int,
                      pause_seconds: float) -> pd.DataFrame:
    target_start = dt.datetime.combine(date, dt.time(0, 0), tzinfo=IST)
    issue_time = issue_time_override or (target_start - dt.timedelta(minutes=issue_margin_minutes))
    if issue_time >= target_start:
        raise ValueError(
            f"Issue time {issue_time.isoformat()} must be before target start "
            f"{target_start.isoformat()}"
        )

    available_by = issue_time.astimezone(UTC) - dt.timedelta(hours=delay_hours)
    first_run = latest_cycle_before(available_by)
    lat, lon = coords
    last_error = None

    for step in range(fallback_cycles + 1):
        run_utc = first_run - dt.timedelta(hours=6 * step)
        try:
            payload = request_run(session, lat, lon, run_utc)
            rows = make_rows(payload, station, lat, lon, target_start,
                             target_hours, issue_time, run_utc,
                             delay_hours, step)
            print(
                f"OK {date} {station}: run={run_utc:%Y-%m-%dT%H:%MZ}, "
                f"lead={rows.forecast_lead_hours.min():.1f}-"
                f"{rows.forecast_lead_hours.max():.1f}h, rows={len(rows)}"
            )
            return rows
        except Exception as exc:  # fallback for unavailable run / coverage errors
            last_error = exc
            print(f"Fallback {date} {station} run={run_utc:%Y-%m-%dT%H:%MZ}: {exc}")
            time.sleep(pause_seconds)

    raise RuntimeError(
        f"No usable run for {date} {station}; last error: {last_error}"
    )


def date_range(start: dt.date, end: dt.date):
    current = start
    while current <= end:
        yield current
        current += dt.timedelta(days=1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-target-date", required=True,
                        help="Inclusive target-start date in IST, YYYY-MM-DD")
    parser.add_argument("--end-target-date", required=True,
                        help="Inclusive target-start date in IST, YYYY-MM-DD")
    parser.add_argument("--target-hours", type=int, default=48,
                        help="Forecast window length from midnight IST (default 48)")
    parser.add_argument("--issue-time-local", default=None,
                        help="Optional actual issue time, e.g. 2026-11-10T23:00:00; "
                             "omit for historical backtests")
    parser.add_argument("--issue-margin-minutes", type=int, default=60,
                        help="Historical pseudo-issue time = target start minus this many minutes (default 60)")
    parser.add_argument("--delay-hours", type=float, default=6.0,
                        help="Conservative run-output availability delay (default 6h)")
    parser.add_argument("--fallback-cycles", type=int, default=3,
                        help="How many older 6-hour cycles to try if latest is unavailable")
    parser.add_argument("--pause-seconds", type=float, default=0.25)
    parser.add_argument("--output", default="weather_single_runs.csv")
    args = parser.parse_args()

    start = dt.date.fromisoformat(args.start_target_date)
    end = dt.date.fromisoformat(args.end_target_date)
    if end < start:
        parser.error("--end-target-date must be on or after --start-target-date")
    if args.target_hours < 1 or args.target_hours > 96:
        parser.error("--target-hours must be between 1 and 96")

    issue_override = parse_issue_time(args.issue_time_local,
                                      dt.datetime.combine(start, dt.time(0), tzinfo=IST)) \
        if args.issue_time_local else None

    session = requests.Session()
    session.headers.update({"User-Agent": "Mumbai-PM25-forecast-research/1.0"})
    all_frames = []
    for date in date_range(start, end):
        for station, coords in STATIONS.items():
            frame = fetch_target_date(
                session=session,
                date=date,
                station=station,
                coords=coords,
                target_hours=args.target_hours,
                issue_time_override=issue_override,
                issue_margin_minutes=args.issue_margin_minutes,
                delay_hours=args.delay_hours,
                fallback_cycles=args.fallback_cycles,
                pause_seconds=args.pause_seconds,
            )
            all_frames.append(frame)
            time.sleep(args.pause_seconds)

    result = pd.concat(all_frames, ignore_index=True)
    result.to_csv(args.output, index=False)
    print(f"Saved {len(result):,} rows to {args.output}")
    print("Run coverage by station:")
    print(result.groupby("station").agg(
        rows=("valid_time_ist", "size"),
        first_target=("valid_time_ist", "min"),
        last_target=("valid_time_ist", "max"),
        mean_lead_h=("forecast_lead_hours", "mean"),
        max_fallback=("fallback_steps_6h", "max"),
    ).to_string())


if __name__ == "__main__":
    main()
