"""Generate reproducible station-median or hist24-blend submission.

Three information clocks are explicitly tracked:
  --model-run-time: when the prediction file is generated (wall clock).
  --pm-history-cutoff: latest eligible PM observation interval end in Train.
                       Defaults to the latest interval end in the Train snapshot.
  Target intervals: from Test.csv.

Usage examples:
  # median72 with auto-derived PM cutoff from Train snapshot:
  python scripts/train_predict.py --model-run-time 2026-11-07T12:00:00+05:30

  # median72 with explicit PM cutoff (for reproducibility):
  python scripts/train_predict.py --model-run-time 2026-11-07T12:00:00+05:30 \\
      --pm-history-cutoff 2026-11-02T23:00:00+05:30

  # hist24 blend:
  python scripts/train_predict.py --model-run-time 2026-11-07T12:00:00+05:30 \\
      --model hist24_blend50_median72

Backward-compatible: --issue-time is accepted as an alias for --model-run-time.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd

from mumbai_pm25.data import load_data
from mumbai_pm25.forecast import (
    derive_pm_history_cutoff,
    predict_test,
    predict_test_ensemble,
    predict_test_with_hist24_blend,
    write_manifest,
)
from mumbai_pm25.historical_archive import load_2024_history

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "raw" / "challenge"
ARCHIVE = DATA_DIR / "AdditionalHistory.zip"

SUPPORTED_MODELS = (
    "median72",
    "hist24_blend50_median72",
    "ensemble_accuracy",
    "ensemble_robust",
    "ensemble_balanced",
)


def _parse_ts(value: str) -> pd.Timestamp:
    ts = pd.Timestamp(datetime.fromisoformat(value))
    if ts.tz is None:
        raise ValueError(f"Timestamp must include a timezone offset: {value!r}")
    return ts


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate reproducible PM2.5 submission",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--data-dir", type=Path, default=DATA_DIR,
        help="Path to challenge data directory",
    )
    parser.add_argument(
        "--output", type=Path, default=None,
        help="Output CSV path (default: artifacts/submissions/<model>_<timestamp>.csv)",
    )
    parser.add_argument(
        "--model", choices=SUPPORTED_MODELS, default="median72",
        help="Forecasting model to use",
    )
    parser.add_argument(
        "--calendar-mode", choices=("legacy_doy", "month_day_365"),
        default="legacy_doy", help="Seasonal calendar matching mode",
    )
    parser.add_argument(
        "--seasonal-weight", type=float, default=0.5,
        help="Seasonal blend weight in [0, 1] (hist24 model only)",
    )
    # Primary argument names
    parser.add_argument(
        "--model-run-time",
        help="Model generation time with UTC offset (e.g. 2026-11-07T12:00:00+05:30)",
    )
    parser.add_argument(
        "--pm-history-cutoff",
        help=(
            "Explicit PM-history cutoff (interval END of latest eligible Train row). "
            "When omitted, derived from Train snapshot contents. "
            "Format: ISO datetime with offset."
        ),
    )
    # Backward-compatible alias
    parser.add_argument(
        "--issue-time",
        help="Alias for --model-run-time (deprecated; use --model-run-time)",
    )
    args = parser.parse_args()

    # Resolve model run time
    if args.model_run_time:
        model_run_time = _parse_ts(args.model_run_time)
    elif args.issue_time:
        print("Warning: --issue-time is deprecated; use --model-run-time")
        model_run_time = _parse_ts(args.issue_time)
    else:
        raise SystemExit("Error: --model-run-time is required")

    if not 0 <= args.seasonal_weight <= 1:
        parser.error("--seasonal-weight must be in [0, 1]")
    if args.model == "median72" and args.seasonal_weight != 0.5:
        parser.error("--seasonal-weight applies only to hist24_blend50_median72")
    if args.model == "median72" and args.calendar_mode != "legacy_doy":
        parser.error("--calendar-mode applies only to hist24_blend50_median72")

    train, test, sample, stations = load_data(args.data_dir)

    # Resolve PM-history cutoff
    if args.pm_history_cutoff:
        pm_history_cutoff: pd.Timestamp | None = _parse_ts(args.pm_history_cutoff)
        print(f"PM-history cutoff: {pm_history_cutoff.isoformat()} (explicit)")
    else:
        pm_history_cutoff = derive_pm_history_cutoff(train)
        print(f"PM-history cutoff: {pm_history_cutoff.isoformat()} (derived from Train snapshot)")

    print(f"Model run time: {model_run_time.isoformat()}")
    print(f"Model: {args.model}")

    # Resolve output path
    if args.output is None:
        ts_tag = model_run_time.strftime("%Y%m%d_%H%M")
        model_tag = args.model if args.seasonal_weight == 0.5 else f"hist24_blend_w{int(args.seasonal_weight * 100):03d}"
        if args.calendar_mode == "month_day_365":
            model_tag += "_calendar365"
        output = ROOT / "artifacts" / "submissions" / f"{model_tag}_{ts_tag}.csv"
    else:
        output = args.output

    output.parent.mkdir(parents=True, exist_ok=True)

    archive_path = args.data_dir / "AdditionalHistory.zip"

    # Generate predictions
    if args.model == "median72":
        prediction = predict_test(
            train, test,
            issue_time=model_run_time,
            pm_history_cutoff=pm_history_cutoff,
        )
    elif args.model == "hist24_blend50_median72":
        if args.calendar_mode == "legacy_doy" and hasattr(load_2024_history, "__wrapped__"):
            from mumbai_pm25.historical_archive import load_legacy_2024_history
            history_2024 = load_legacy_2024_history(archive_path)
        else:
            history_2024 = load_2024_history(archive_path)
        prediction = predict_test_with_hist24_blend(
            train, test, history_2024,
            issue_time=model_run_time,
            pm_history_cutoff=pm_history_cutoff,
            blend_weight_hist24=args.seasonal_weight,
            calendar_mode=args.calendar_mode,
        )
    elif args.model == "ensemble_accuracy":
        history_2024 = load_2024_history(archive_path)
        prediction = predict_test_ensemble(
            train, test, history_2024,
            issue_time=model_run_time,
            pm_history_cutoff=pm_history_cutoff,
            ensemble_type="accuracy",
        )
    elif args.model == "ensemble_robust":
        history_2024 = load_2024_history(archive_path)
        prediction = predict_test_ensemble(
            train, test, history_2024,
            issue_time=model_run_time,
            pm_history_cutoff=pm_history_cutoff,
            ensemble_type="robust",
        )
    elif args.model == "ensemble_balanced":
        history_2024 = load_2024_history(archive_path)
        prediction = predict_test_ensemble(
            train, test, history_2024,
            issue_time=model_run_time,
            pm_history_cutoff=pm_history_cutoff,
            ensemble_type="balanced",
        )
    else:
        raise SystemExit(f"Unknown model: {args.model!r}")

    # Validate against SampleSubmission
    if prediction.ID.tolist() != sample.ID.tolist():
        raise ValueError("SampleSubmission IDs differ from prediction IDs")

    prediction.to_csv(output, index=False)
    print(f"Wrote {len(prediction):,} predictions to {output}")

    # Write manifest
    weights = None
    if args.model == "ensemble_accuracy":
        weights = "0.83 * CatBoost_log1p + 0.17 * Seasonal_Blend50"
    elif args.model == "ensemble_robust":
        weights = "0.50 * CatBoost_log1p + 0.50 * Seasonal_Blend50"
    elif args.model == "ensemble_balanced":
        weights = "0.20 * CatBoost_log1p + 0.80 * Seasonal_Blend50"
    elif args.model == "hist24_blend50_median72":
        weights = f"{args.seasonal_weight:.2f} * hist24_same_hour_mean + {1 - args.seasonal_weight:.2f} * median72"

    manifest_path = output.with_suffix(".manifest.txt")
    write_manifest(
        manifest_path,
        train_path=args.data_dir / "Train.csv",
        test_path=args.data_dir / "Test.csv",
        output_path=output,
        issue_time=model_run_time,
        pm_history_cutoff=pm_history_cutoff,
        train=train,
        stations=stations,
        model=args.model if args.calendar_mode == "legacy_doy" else f"{args.model}_calendar365",
        extra_sources=[archive_path],
        ensemble_weights=weights,
        calendar_mode=args.calendar_mode,
    )
    print(f"Wrote manifest to {manifest_path}")


if __name__ == "__main__":
    main()
