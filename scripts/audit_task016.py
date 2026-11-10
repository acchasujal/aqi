"""TASK 016 Comprehensive Dataset Audit and Pipeline Verification."""

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "challenge"

def get_hashes(path: Path):
    content = path.read_bytes()
    raw_sha = hashlib.sha256(content).hexdigest()
    try:
        text = content.decode("utf-8", errors="replace")
        lf_sha = hashlib.sha256(text.replace("\r\n", "\n").encode("utf-8")).hexdigest()
    except (UnicodeDecodeError, ValueError):
        lf_sha = None
    return raw_sha, lf_sha, len(content)

def audit_datasets():
    print("=================== DATASET INVENTORY ===================")
    for p in sorted(RAW_DIR.iterdir()):
        if not p.is_file():
            continue
        raw_sha, lf_sha, size = get_hashes(p)
        print(f"\nFile: {p.name}")
        print(f"  Path: {p}")
        print(f"  Size: {size:,} bytes")
        print(f"  Raw SHA-256: {raw_sha}")
        print(f"  LF  SHA-256: {lf_sha}")
        if p.suffix == ".csv":
            df = pd.read_csv(p)
            print(f"  Rows: {len(df):,}, Cols: {len(df.columns)}")
            print(f"  Columns: {list(df.columns)}")
        elif p.suffix == ".txt":
            lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
            print(f"  Lines: {len(lines)}")
            print(f"  First 3 lines: {lines[:3]}")

def audit_train():
    print("\n=================== TRAIN.CSV DEEP AUDIT ===================")
    train_path = RAW_DIR / "Train.csv"
    df = pd.read_csv(train_path)
    print(f"Total rows: {len(df):,}")
    print(f"Columns and dtypes:\n{df.dtypes}")
    print(f"Missing values:\n{df.isna().sum()}")
    
    # Station and sensor breakdown
    print(f"Unique location_id: {sorted(df['location_id'].unique().tolist())}")
    if "sensor_id" in df.columns:
        print(f"Unique sensor_id: {sorted(df['sensor_id'].unique().tolist())}")
        loc_sensor = df.groupby(["location_id", "sensor_id"]).size().reset_index(name="count")
        print(f"Location-Sensor pairs:\n{loc_sensor}")

    # Duplicates check
    dup_cols = ["location_id", "timestamp_ist"]
    if "sensor_id" in df.columns:
        dup_3 = df.duplicated(subset=["location_id", "sensor_id", "timestamp_ist"]).sum()
        print(f"Duplicates on (location_id, sensor_id, timestamp_ist): {dup_3}")
    dup_station_hour = df.duplicated(subset=dup_cols).sum()
    print(f"Duplicates on (location_id, timestamp_ist): {dup_station_hour}")

    # Values check
    pm = df["pm25"]
    print(f"PM2.5 min: {pm.min()}, max: {pm.max()}, mean: {pm.mean():.4f}, median: {pm.median():.4f}")
    neg_pm = (pm < 0).sum()
    zero_pm = (pm == 0).sum()
    print(f"Negative PM2.5 count: {neg_pm}, Zero PM2.5 count: {zero_pm}")
    
    # High values and flag
    print(f"PM2.5 > 250 count: {(pm > 250).sum()}")
    print(f"PM2.5 > 500 count: {(pm > 500).sum()}")
    print(f"PM2.5 > 1000 count: {(pm > 1000).sum()}")
    if "flag_high_1000" in df.columns:
        print(f"flag_high_1000 value counts:\n{df['flag_high_1000'].value_counts(dropna=False)}")

    # Time ranges overall and per station
    df["ts"] = pd.to_datetime(df["timestamp_ist"])
    print(f"Overall min timestamp: {df['ts'].min()}, max timestamp: {df['ts'].max()}")
    
    per_station = []
    for loc_id, g in df.groupby("location_id"):
        per_station.append({
            "location_id": loc_id,
            "count": len(g),
            "min_ts": str(g["ts"].min()),
            "max_ts": str(g["ts"].max()),
            "pm25_min": g["pm25"].min(),
            "pm25_max": g["pm25"].max(),
            "pm25_median": g["pm25"].median(),
        })
    per_station_df = pd.DataFrame(per_station)
    print("Per-station summary:\n", per_station_df.to_string(index=False))

    # Inspect the newly added rows (Nov 7 - Nov 10)
    nov_new = df[df["ts"] >= "2026-11-07 00:00:00+05:30"]
    print(f"\nObservations on or after 2026-11-07 00:00 IST: {len(nov_new)}")
    print("Counts by date and location for new rows:")
    nov_new["date"] = nov_new["ts"].dt.date
    pivot_new = nov_new.groupby(["date", "location_id"]).size().unstack(fill_value=0)
    print(pivot_new)

def audit_test_and_sample():
    print("\n=================== TEST & SAMPLESUBMISSION AUDIT ===================")
    test_path = RAW_DIR / "Test.csv"
    sub_path = RAW_DIR / "SampleSubmission.csv"
    
    test = pd.read_csv(test_path)
    sub = pd.read_csv(sub_path)
    
    print(f"Test rows: {len(test):,}, unique IDs: {test['ID'].nunique():,}")
    print(f"SampleSubmission rows: {len(sub):,}, unique IDs: {sub['ID'].nunique():,}")
    
    # Exact ordering
    exact_match = (test["ID"] == sub["ID"]).all()
    print(f"Test IDs match SampleSubmission IDs exactly in order: {exact_match}")
    
    # Test details
    print(f"Test columns: {list(test.columns)}")
    print(f"Unique location_id in Test: {sorted(test['location_id'].unique().tolist())}")
    
    test["t_start"] = pd.to_datetime(test["target_start_ist"])
    test["t_end"] = pd.to_datetime(test["target_end_ist"])
    
    # Duration check
    duration_hours = (test["t_end"] - test["t_start"]).dt.total_seconds() / 3600.0
    print(f"All target durations are exactly 1 hour: {(duration_hours == 1.0).all()}")
    
    # Scoring block breakdown
    if "scoring_block" in test.columns:
        print(f"scoring_block distribution:\n{test['scoring_block'].value_counts(dropna=False)}")
        for sb, g in test.groupby("scoring_block"):
            print(f"  Block '{sb}': rows={len(g)}, min_start={g['t_start'].min()}, max_end={g['t_end'].max()}, stations={sorted(g['location_id'].unique())}")
    
    # Private evaluation candidate rows (Block 'private')
    b_rows = test[test["scoring_block"] == "private"] if "scoring_block" in test.columns else test
    print(f"\nPrivate evaluation candidate rows (scoring_block == 'private'): {len(b_rows)}")
    print(f"  Min start: {b_rows['t_start'].min()}")
    print(f"  Max end: {b_rows['t_end'].max()}")
    print(f"  Rows per station:\n{b_rows.groupby('location_id').size()}")

def audit_lead_times():
    print("\n=================== FORECAST LEAD TIMES & GAPS ===================")
    train = pd.read_csv(RAW_DIR / "Train.csv")
    test = pd.read_csv(RAW_DIR / "Test.csv")
    
    train["ts"] = pd.to_datetime(train["timestamp_ist"])
    test["t_start"] = pd.to_datetime(test["target_start_ist"])
    test["t_end"] = pd.to_datetime(test["target_end_ist"])
    
    # Latest observation per station in Train
    latest_train = train.groupby("location_id")["ts"].max().to_dict()
    
    # Filter for private evaluation window: 11-12 Nov (scoring_block == 'private')
    private_test = test[test["scoring_block"] == "private"].copy()
    
    lead_records = []
    for loc_id, g in private_test.groupby("location_id"):
        cutoff = latest_train[loc_id]
        min_start = g["t_start"].min()
        max_start = g["t_start"].max()
        min_end = g["t_end"].min()
        max_end = g["t_end"].max()
        
        # Lead time from cutoff to target interval start:
        min_lead_start = (min_start - cutoff).total_seconds() / 3600.0
        max_lead_start = (max_start - cutoff).total_seconds() / 3600.0
        
        # Lead time from cutoff to target interval end:
        min_lead_end = (min_end - cutoff).total_seconds() / 3600.0
        max_lead_end = (max_end - cutoff).total_seconds() / 3600.0
        
        # In recent 72 hours before cutoff:
        recent_window_start = cutoff - pd.Timedelta(hours=72)
        station_train = train[train["location_id"] == loc_id]
        recent_obs = station_train[(station_train["ts"] > recent_window_start) & (station_train["ts"] <= cutoff)]
        
        lead_records.append({
            "location_id": loc_id,
            "station_cutoff_ist": str(cutoff),
            "first_private_target_start_ist": str(min_start),
            "last_private_target_start_ist": str(max_start),
            "min_lead_start_hours": min_lead_start,
            "max_lead_start_hours": max_lead_start,
            "min_lead_end_hours": min_lead_end,
            "max_lead_end_hours": max_lead_end,
            "private_target_count": len(g),
            "recent_72h_obs_count": len(recent_obs),
            "recent_72h_median_pm25": recent_obs["pm25"].median() if len(recent_obs) > 0 else np.nan,
        })
    leads_df = pd.DataFrame(lead_records)
    print(leads_df.to_string(index=False))

if __name__ == "__main__":
    audit_datasets()
    audit_train()
    audit_test_and_sample()
    audit_lead_times()
