"""Run matched, non-overlapping rolling-origin baseline validation."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from mumbai_pm25.data import load_data
from mumbai_pm25.validation import metric_tables, rolling_oof


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=root / "data/raw/challenge")
    parser.add_argument("--output-dir", type=Path, default=root / "reports/ml_pipeline/evaluation")
    parser.add_argument("--gaps", type=int, nargs="+", default=[48, 72, 96, 120])
    args = parser.parse_args()
    train, _, _, _ = load_data(args.data_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    model_metrics, station_metrics, horizon_metrics, fold_metrics = [], [], [], []
    oof_files = []
    for gap in args.gaps:
        oof = rolling_oof(train, gap_hours=gap)
        oof.insert(0, "gap_hours", gap)
        path = args.output_dir / f"oof_gap{gap}.csv.gz"
        oof.to_csv(path, index=False, compression="gzip")
        oof_files.append(path.name)
        by_model, by_station, by_horizon, by_fold = metric_tables(oof)
        for frame in (by_model, by_station, by_horizon, by_fold):
            frame.insert(0, "gap_hours", gap)
        model_metrics.append(by_model)
        station_metrics.append(by_station)
        horizon_metrics.append(by_horizon)
        fold_metrics.append(by_fold)
    for name, parts in (("model_metrics.csv", model_metrics), ("station_metrics.csv", station_metrics),
                        ("horizon_metrics.csv", horizon_metrics), ("fold_metrics.csv", fold_metrics)):
        pd.concat(parts, ignore_index=True).to_csv(args.output_dir / name, index=False)
    print(f"Completed gaps {args.gaps}; OOF artifacts: {', '.join(oof_files)}")


if __name__ == "__main__":
    main()
