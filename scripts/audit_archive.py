"""Comprehensive audit of AdditionalHistory.zip for TASK 004."""
from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

TARGET_STATIONS = {
    "Borivali East": {"location_id": 11606, "sensor_id": 12236418, "lat": 19.232410, "lon": 72.868950},
    "Malad West": {"location_id": 11611, "sensor_id": 12236426, "lat": 19.197090, "lon": 72.822040},
    "Byculla": {"location_id": 3409510, "sensor_id": 12238567, "lat": 18.976700, "lon": 72.838000},
    "Shivaji Nagar": {"location_id": 3409511, "sensor_id": 12238576, "lat": 19.060498, "lon": 72.923356},
}

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "data/raw/challenge/AdditionalHistory.zip"


def sha256_member(z: zipfile.ZipFile, name: str) -> str:
    with z.open(name) as f:
        return hashlib.sha256(f.read()).hexdigest()


def audit_history_2024(z: zipfile.ZipFile) -> dict:
    with z.open("History_Mumbai_2024.csv.gz") as f:
        df = pd.read_csv(f, compression="gzip")

    result: dict = {
        "file": "History_Mumbai_2024.csv.gz",
        "rows": len(df),
        "columns": list(df.columns),
        "nulls": df.isnull().sum().to_dict(),
    }

    df["ts"] = pd.to_datetime(df["timestamp_ist"])
    result["timestamp_min"] = str(df["ts"].min())
    result["timestamp_max"] = str(df["ts"].max())
    result["minute_values"] = sorted(df["ts"].dt.minute.unique().tolist())
    result["stations"] = df["station_name"].unique().tolist()
    result["station_ids"] = df["station_id"].unique().tolist()
    result["sources"] = df["source"].unique().tolist()
    result["value_min"] = float(df["value"].min())
    result["value_max"] = float(df["value"].max())

    print(f"\n{'='*60}")
    print("History_Mumbai_2024.csv.gz")
    print(f"  Rows: {result['rows']}")
    print(f"  Timestamp range: {result['timestamp_min']} -> {result['timestamp_max']}")
    print(f"  CRITICAL: Minute values in timestamps: {result['minute_values']}")
    print(f"  Sources: {result['sources']}")
    print(f"  Value range: {result['value_min']} - {result['value_max']}")

    print("\n  === Target station mapping ===")
    target_mappings = {}
    for target_name in TARGET_STATIONS:
        matches = df[df["station_name"].str.contains(target_name, case=False, na=False)]
        if len(matches) > 0:
            station_ids = matches["station_id"].unique().tolist()
            station_names = matches["station_name"].unique().tolist()
            ts_sub = pd.to_datetime(matches["timestamp_ist"])
            minutes = sorted(ts_sub.dt.minute.unique().tolist())
            ts_range = (str(ts_sub.min()), str(ts_sub.max()))
            # Count non-null hourly aligned observations
            # timestamps are at :30 so we need to check
            print(f"  {target_name}:")
            print(f"    Archive station ids: {station_ids}")
            print(f"    Archive station names: {station_names}")
            print(f"    Rows: {len(matches)}, Date range: {ts_range[0]} -> {ts_range[1]}")
            print(f"    Minute values: {minutes}")
            # Check coverage per month
            matches2 = matches.copy()
            matches2["month"] = pd.to_datetime(matches2["timestamp_ist"]).dt.to_period("M")
            cov = matches2.groupby("month").size().reset_index(name="n")
            print(f"    Monthly coverage (rows):")
            for _, row in cov.iterrows():
                print(f"      {row['month']}: {row['n']}")
            target_mappings[target_name] = {
                "station_ids": station_ids,
                "names": station_names,
                "rows": len(matches),
                "minutes": minutes,
                "ts_range": ts_range,
            }
        else:
            print(f"  {target_name}: NOT FOUND in 2024 archive")
            target_mappings[target_name] = None

    result["target_mappings"] = target_mappings
    return result


def audit_history_2018_2020(z: zipfile.ZipFile) -> dict:
    with z.open("History_Mumbai_2018_2020.csv.gz") as f:
        df = pd.read_csv(f, compression="gzip")

    print(f"\n{'='*60}")
    print("History_Mumbai_2018_2020.csv.gz")
    print(f"  Rows: {len(df)}")
    print(f"  Columns: {list(df.columns)}")
    print(f"  Station names: {df['StationName'].unique().tolist()}")
    print(f"  Date range: {df['Datetime'].min()} -> {df['Datetime'].max()}")
    print(f"  PM2.5 range: {df['PM2.5'].min()} - {df['PM2.5'].max()}")
    print(f"  PM2.5 nulls: {df['PM2.5'].isnull().sum()}")

    print("\n  === Target station matching ===")
    for target_name in TARGET_STATIONS:
        matches = df[df["StationName"].str.contains(target_name, case=False, na=False)]
        if len(matches) > 0:
            print(f"  {target_name}: {len(matches)} rows, names={matches['StationName'].unique().tolist()}")
        else:
            print(f"  {target_name}: NOT FOUND")

    return {"rows": len(df), "columns": list(df.columns)}


def audit_legacy(z: zipfile.ZipFile) -> dict:
    with z.open("Legacy_Observations_2020_2022.csv.gz") as f:
        df = pd.read_csv(f, compression="gzip")

    print(f"\n{'='*60}")
    print("Legacy_Observations_2020_2022.csv.gz")
    print(f"  Rows: {len(df)}")
    print(f"  Columns: {list(df.columns)}")
    print(f"  location_ids: {df['location_id'].unique().tolist()}")
    print(f"  Date range: {df['datetime'].min()} -> {df['datetime'].max()}")
    return {"rows": len(df)}


def audit_other_stations(z: zipfile.ZipFile) -> dict:
    with z.open("Other_Mumbai_Stations_2025_2026.csv.gz") as f:
        df = pd.read_csv(f, compression="gzip")

    print(f"\n{'='*60}")
    print("Other_Mumbai_Stations_2025_2026.csv.gz")
    print(f"  Rows: {len(df)}")
    print(f"  Columns: {list(df.columns)}")
    print(f"  Station names: {df['station_name'].unique().tolist()}")
    print(f"  location_ids: {df['location_id'].unique().tolist()}")
    print(f"  Date range: {df['timestamp_ist'].min()} -> {df['timestamp_ist'].max()}")
    print(f"  mean range: {df['mean'].min()} - {df['mean'].max()}")
    print(f"  Nulls: {df.isnull().sum().to_dict()}")

    # Check if any target-station names appear  
    print("\n  === Target station matching ===")
    for target_name in TARGET_STATIONS:
        matches = df[df["station_name"].str.contains(target_name, case=False, na=False)]
        if len(matches) > 0:
            lids = matches["location_id"].unique().tolist()
            names = matches["station_name"].unique().tolist()
            print(f"  {target_name}: {len(matches)} rows, location_ids={lids}, names={names}")
            # Note: Competition uses location_ids 11606, 11611, 3409510, 3409511
            comp_id = TARGET_STATIONS[target_name]["location_id"]
            if comp_id in lids:
                print(f"    EXACT COMPETITION location_id MATCH: {comp_id}")
            else:
                print(f"    Competition location_id {comp_id} NOT in archive ids {lids} - different station!")
        else:
            print(f"  {target_name}: NOT FOUND")

    return {"rows": len(df)}


def audit_kaggle_stations(z: zipfile.ZipFile) -> None:
    csv_content = z.read("Kaggle_All_Stations.csv").decode("utf-8", errors="replace")
    lines = csv_content.split("\n")
    print(f"\n{'='*60}")
    print("Kaggle_All_Stations.csv")
    print(f"  Lines: {len(lines)}")
    print(f"  Header: {lines[0][:200]}")
    # Find Mumbai entries
    mumbai_lines = [l for l in lines[1:] if "Mumbai" in l or "Borivali" in l or "Malad" in l or "Byculla" in l or "Shivaji" in l]
    print(f"  Mumbai-related lines ({len(mumbai_lines)}):")
    for line in mumbai_lines[:30]:
        print(f"    {line[:200]}")


def main() -> None:
    print("AdditionalHistory.zip Audit — TASK 004")
    print(f"Archive: {ARCHIVE}")

    z = zipfile.ZipFile(ARCHIVE)
    members = z.namelist()
    print(f"\nArchive members: {members}")

    # Hash each member
    print("\nMember SHA-256 hashes:")
    for name in members:
        h = sha256_member(z, name)
        info = z.getinfo(name)
        print(f"  {name}: {h[:16]}... ({info.file_size:,} bytes compressed: {info.compress_size:,})")

    audit_history_2024(z)
    audit_history_2018_2020(z)
    audit_legacy(z)
    audit_other_stations(z)
    audit_kaggle_stations(z)

    print(f"\n{'='*60}")
    print("AUDIT COMPLETE")


if __name__ == "__main__":
    main()

