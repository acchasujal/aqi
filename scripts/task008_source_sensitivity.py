"""Diagnostic exact-source ablations on frozen TASK008 rows; no reselection."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mumbai_pm25.final_gap import paired_bootstrap, score_predictions
from mumbai_pm25.historical_archive import P_FIX_SERIES, build_seasonal_features, load_2024_history


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data/raw/challenge")
    args = parser.parse_args()
    output = args.run_dir / "source_sensitivity"
    if output.exists():
        raise FileExistsError("Source sensitivity output already exists")
    output.mkdir()
    rows = pd.read_csv(args.run_dir / "matched_oof.csv.gz")
    for column in ("target_start", "fold_id"):
        rows[column] = pd.to_datetime(rows[column], utc=True).dt.tz_convert("Asia/Kolkata")
    archive = load_2024_history(args.data_dir / "AdditionalHistory.zip")
    policies = {
        "borivali_5113": {**P_FIX_SERIES, 11606: ("xkdr:site_5113",)},
        "malad_5102": {**P_FIX_SERIES, 11611: ("xkdr:site_5102",)},
        "malad_5402": {**P_FIX_SERIES, 11611: ("xkdr:site_5402",)},
    }
    all_sources = {**P_FIX_SERIES, 11606: ("xkdr:site_5113", "xkdr:site_5400")}
    features = build_seasonal_features(archive, rows, series_map=all_sources)
    candidates = ["P_fix"]
    for name, policy in policies.items():
        sums = pd.Series(0., index=rows.index)
        counts = pd.Series(0., index=rows.index)
        for station, sources in policy.items():
            mask = rows.location_id.eq(station)
            for source in sources:
                sums.loc[mask] += features.loc[mask, f"hist24_series::{source}::sum"]
                counts.loc[mask] += features.loc[mask, f"hist24_series::{source}::coverage"]
        seasonal = (sums/counts).where(counts >= 3)
        rows[name] = .5*rows.median72 + .5*seasonal.fillna(rows.median72)
        candidates.append(name)
    score_predictions(rows, candidates, ("split",)).to_csv(output / "model_metrics.csv", index=False)
    score_predictions(rows, candidates, ("split", "location_id")).to_csv(output / "station_metrics.csv", index=False)
    pairs = [{"split": split, **paired_bootstrap(part, name)}
             for split, part in rows.groupby("split") for name in candidates if name != "P_fix"]
    pd.DataFrame(pairs).to_csv(output / "paired_bootstrap.csv", index=False)
    rows[["fold_id", "split", "location_id", "target_start", "y", *candidates]].to_csv(output / "oof.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
    (output / "policies.json").write_text(json.dumps(policies, indent=2)+"\n", encoding="utf-8")
    print("Exact-source sensitivity completed; diagnostic only, no source reselection.")


if __name__ == "__main__":
    main()
