from pathlib import Path
import os
import pandas as pd
import numpy as np

# By default, read Train.csv from the same folder as this script.
# Override with the ZINDI_DATA_DIR environment variable if the CSVs live elsewhere.
DATA_DIR = Path(os.environ.get("ZINDI_DATA_DIR", Path(__file__).resolve().parent)).expanduser().resolve()
TRAIN_FILE = DATA_DIR / "Train.csv"

def load():
    if not TRAIN_FILE.exists():
        raise FileNotFoundError(
            f"Could not find {TRAIN_FILE}. Put Train.csv beside these scripts "
            "or set ZINDI_DATA_DIR to the folder containing Train.csv."
        )
    tr = pd.read_csv(TRAIN_FILE)
    required = {"timestamp_ist", "station_name", "pm25"}
    missing = required - set(tr.columns)
    if missing:
        raise ValueError(f"Train.csv is missing required columns: {sorted(missing)}")
    tr["ts"] = pd.to_datetime(tr["timestamp_ist"], format="mixed", utc=True).dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
    st = {
        "Borivali East, Mumbai - IITM": "BOR",
        "Byculla, Mumbai - BMC": "BYC",
        "Malad West, Mumbai - IITM": "MAL",
        "Shivaji Nagar, Mumbai - BMC": "SHI",
    }
    tr["st"] = tr["station_name"].map(st)
    if tr["st"].isna().any():
        unknown = sorted(tr.loc[tr["st"].isna(), "station_name"].dropna().unique().tolist())
        raise ValueError(f"Unmapped station_name values: {unknown}")
    idx = pd.date_range(tr.ts.min(), tr.ts.max(), freq="h")
    W = tr.pivot(index="ts", columns="st", values="pm25").reindex(idx)
    return tr, W
