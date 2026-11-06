"""Compare calendar ExtraTrees against baselines on identical 28-day-spaced folds."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from mumbai_pm25.data import load_data
from mumbai_pm25.models import rolling_extra_trees
from mumbai_pm25.validation import metric_tables, rolling_oof


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=root / "data/raw/challenge")
    parser.add_argument("--output-dir", type=Path, default=root / "reports/ml_pipeline/supervised_evaluation")
    parser.add_argument("--gaps", type=int, nargs="+", default=[48, 72, 96, 120])
    parser.add_argument("--step-days", type=int, default=28)
    args = parser.parse_args()
    train, _, _, _ = load_data(args.data_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, list[pd.DataFrame]] = {name: [] for name in ("model", "fold", "station", "horizon")}
    for gap in args.gaps:
        baselines = rolling_oof(train, gap_hours=gap, step_days=args.step_days)
        trees = rolling_extra_trees(train, gap_hours=gap, step_days=args.step_days, baseline_oof=baselines)
        combined = pd.concat([baselines, trees], ignore_index=True)
        combined.insert(0, "gap_hours", gap)
        combined.insert(1, "step_days", args.step_days)
        combined.to_csv(args.output_dir / f"oof_gap{gap}.csv.gz", index=False, compression="gzip")
        model, station, horizon, fold = metric_tables(combined)
        for frame in (model, station, horizon, fold):
            frame.insert(0, "gap_hours", gap)
            frame.insert(1, "step_days", args.step_days)
        outputs["model"].append(model)
        outputs["station"].append(station)
        outputs["horizon"].append(horizon)
        outputs["fold"].append(fold)
        print(f"Completed gap {gap}: {trees.fold_id.nunique()} matched folds, {len(trees)} ExtraTrees OOF rows")
    for name, frames in outputs.items():
        pd.concat(frames, ignore_index=True).to_csv(args.output_dir / f"{name}_metrics.csv", index=False)


if __name__ == "__main__":
    main()
