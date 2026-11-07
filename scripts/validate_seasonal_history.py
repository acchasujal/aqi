"""Validate 2024 seasonal history features against baseline controls.

EXP-20261107-007: Test whether 2024 same-station same-hour-of-year PM2.5
climatology from AdditionalHistory.zip improves forecasts over the
existing median72 control.

Usage:
    python scripts/validate_seasonal_history.py [--gap-hours 48 72 96 120]

Outputs to reports/ml_pipeline/seasonal_history/
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "raw" / "challenge"
ARCHIVE = DATA_DIR / "AdditionalHistory.zip"
REPORT_DIR = ROOT / "reports" / "ml_pipeline" / "seasonal_history"

import sys  # noqa: E402

sys.path.insert(0, str(ROOT / "src"))

from mumbai_pm25.data import load_data  # noqa: E402
from mumbai_pm25.historical_archive import (  # noqa: E402
    STATION_NAME_MAP,
    build_seasonal_features,
    load_2024_history,
)
from mumbai_pm25.validation import rolling_oof  # noqa: E402
from mumbai_pm25.forecast import combine_forecasts, recent_median72  # noqa: E402

SEASONAL_MODELS = ("hist24_same_hour", "hist24_month_hour", "hist24_blend50_median72")


def _seasonal_baseline_for_fold(
    history_2024: pd.DataFrame,
    fold_targets: pd.DataFrame,
    history_values: dict[int, pd.Series],
    *,
    calendar_mode: str = "legacy_doy",
) -> dict[str, np.ndarray]:
    """Compute seasonal baselines for a fold's target rows."""
    # Build seasonal features using 2024 archive
    target_df = fold_targets[["location_id", "target_start"]].copy()
    seasonal = build_seasonal_features(
        history_2024,
        target_df,
        station_map=STATION_NAME_MAP,
        window_days=14,
        min_obs=3,
        calendar_mode=calendar_mode,
    )

    n = len(fold_targets)
    preds: dict[str, np.ndarray] = {
        "hist24_same_hour": np.full(n, np.nan),
        "hist24_month_hour": np.full(n, np.nan),
        "hist24_blend50_median72": np.full(n, np.nan),
    }

    for i, (_, row) in enumerate(fold_targets.iterrows()):
        loc_id = int(row["location_id"])
        idx = row.name  # original index
        sh = float(seasonal.loc[idx, "hist24_same_hour_mean"]) if idx in seasonal.index else np.nan
        mh = float(seasonal.loc[idx, "hist24_month_hour_mean"]) if idx in seasonal.index else np.nan

        preds["hist24_same_hour"][i] = max(0.0, sh) if np.isfinite(sh) else np.nan
        preds["hist24_month_hour"][i] = max(0.0, mh) if np.isfinite(mh) else np.nan

        station_hist = history_values.get(loc_id)
        m72 = recent_median72(station_hist, row["cutoff"]) if station_hist is not None else None
        seasonal_value = sh if np.isfinite(sh) else None
        try:
            preds["hist24_blend50_median72"][i] = combine_forecasts(m72, seasonal_value)
        except ValueError as exc:
            if "Neither recent PM nor seasonal history" not in str(exc):
                raise


    return preds


def rolling_oof_seasonal(
    train: pd.DataFrame,
    history_2024: pd.DataFrame,
    *,
    gap_hours: int,
    horizon_hours: int = 48,
    step_days: int = 7,
    calendar_mode: str = "legacy_doy",
) -> pd.DataFrame:
    """Rolling OOF evaluation including seasonal 2024 baselines.

    Uses the same fold structure as rolling_oof() and adds seasonal candidates.
    """
    stations = sorted(int(v) for v in train.location_id.unique())
    full_start, full_end = train.target_start.min(), train.target_start.max()
    hours = pd.date_range(full_start, full_end, freq="h")
    grid = train.set_index(["location_id", "target_start"])[["pm25"]].unstack(0).reindex(hours)

    first_origin = full_start.ceil("D") + pd.Timedelta(hours=23)
    last_origin = full_end - pd.Timedelta(hours=gap_hours + horizon_hours)

    rows: list[tuple] = []

    for cutoff in pd.date_range(first_origin, last_origin, freq=f"{step_days}D"):
        target_start_time = cutoff + pd.Timedelta(hours=gap_hours)
        targets = pd.date_range(target_start_time, periods=horizon_hours, freq="h")
        issue_time = target_start_time

        # Build fold targets DataFrame for seasonal feature lookup
        fold_target_rows = []
        history_per_station: dict[int, pd.Series] = {}
        for station in stations:
            s = grid[("pm25", station)]
            history = s.loc[s.index < cutoff]
            last_observed_start = history.last_valid_index()
            history_per_station[station] = history
            truth = s.reindex(targets)
            for horizon, (t, y) in enumerate(zip(targets, truth.to_numpy()), start=1):
                if np.isfinite(y):
                    fold_target_rows.append({
                        "target_start": t,
                        "location_id": station,
                        "y": float(y),
                        "horizon": horizon,
                        "cutoff": cutoff,
                        "issue_time": issue_time,
                        "last_pm_end": last_observed_start + pd.Timedelta(hours=1) if last_observed_start is not None else pd.NaT,
                        "pm_gap_hours": (t - (last_observed_start + pd.Timedelta(hours=1))).total_seconds() / 3600 if last_observed_start is not None else np.nan,
                    })

        if not fold_target_rows:
            continue

        fold_df = pd.DataFrame(fold_target_rows)

        # Compute seasonal predictions for the whole fold at once
        seasonal_preds = _seasonal_baseline_for_fold(
            history_2024, fold_df, history_per_station, calendar_mode=calendar_mode
        )

        # Emit rows for each seasonal model
        for i, fold_row in enumerate(fold_target_rows):
            station = fold_row["location_id"]
            t = fold_row["target_start"]
            y = fold_row["y"]
            last_pm_end = fold_row["last_pm_end"]
            exact_gap = fold_row["pm_gap_hours"]
            horizon = fold_row["horizon"]

            for model_name in SEASONAL_MODELS:
                p = seasonal_preds[model_name][i]
                if np.isfinite(p):
                    rows.append((
                        cutoff, issue_time, cutoff, last_pm_end, exact_gap,
                        t, t + pd.Timedelta(hours=1), station, horizon,
                        float(y), max(0.0, float(p)), model_name,
                    ))

    return pd.DataFrame(rows, columns=[
        "fold_id", "prediction_origin", "pm_history_cutoff", "last_pm_available_at",
        "pm_gap_hours", "target_start", "target_end", "location_id",
        "horizon_hours", "y", "prediction", "model",
    ])


def summarize_comparison(
    baseline_oof: pd.DataFrame,
    seasonal_oof: pd.DataFrame,
    gap_hours: int,
) -> pd.DataFrame:
    """Return a combined model summary sorted by full_target_rmse."""
    combined = pd.concat([baseline_oof, seasonal_oof], ignore_index=True)
    if combined.empty:
        return pd.DataFrame()
    scored = combined.assign(
        error=combined.prediction - combined.y,
        squared=(combined.prediction - combined.y) ** 2,
    )
    result = (
        scored.groupby("model")
        .agg(
            rows=("y", "size"),
            full_target_rmse=("squared", lambda x: float(np.sqrt(x.mean()))),
            mae=("error", lambda x: float(x.abs().mean())),
            bias=("error", "mean"),
            clean_rows=("y", lambda x: int((x < 500).sum())),
        )
        .reset_index()
    )
    clean = (
        scored.loc[scored.y < 500]
        .groupby("model")
        .squared.mean()
        .pow(0.5)
        .rename("clean_rmse")
    )
    result = result.merge(clean.reset_index(), on="model", how="left")
    result["gap_hours"] = gap_hours
    return result.sort_values("full_target_rmse")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate 2024 seasonal history features (EXP-20261107-007)"
    )
    parser.add_argument(
        "--gap-hours",
        nargs="+",
        type=int,
        default=[48, 72],
        help="PM history cutoff-to-target gap(s) in hours",
    )
    parser.add_argument(
        "--step-days",
        type=int,
        default=7,
        help="Fold spacing in days",
    )
    args = parser.parse_args()

    print("EXP-20261107-007: 2024 Seasonal History Evaluation")
    print("=" * 60)

    # Load challenge data
    print("Loading challenge data ...")
    train, test, _sample, _stations = load_data(DATA_DIR)
    print(f"  Train: {len(train):,} rows, Test: {len(test):,} rows")

    # Load 2024 archive history
    print("Loading 2024 archive history ...")
    history_2024 = load_2024_history(ARCHIVE)
    print(f"  Archive rows (cpcb_caaqm only): {len(history_2024):,}")
    for loc_id, name_frag in STATION_NAME_MAP.items():
        matched = history_2024.loc[
            history_2024["station_name"].str.contains(name_frag, case=False)
        ]
        print(f"  {name_frag} (loc {loc_id}): {len(matched):,} archive rows")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    all_summaries: list[pd.DataFrame] = []
    all_seasonal_oofs: list[pd.DataFrame] = []
    all_baseline_oofs: list[pd.DataFrame] = []

    for gap_hours in args.gap_hours:
        print(f"\n--- Gap {gap_hours}h ---")

        # Run baseline rolling OOF (using existing validated MODELS)
        print(f"  Running baseline rolling OOF (gap={gap_hours}h, step={args.step_days}d) ...")
        baseline_oof = rolling_oof(
            train, gap_hours=gap_hours, horizon_hours=48, step_days=args.step_days
        )
        print(f"  Baseline OOF rows: {len(baseline_oof):,}, folds: {baseline_oof.fold_id.nunique()}")

        # Run seasonal rolling OOF
        print("  Running seasonal rolling OOF ...")
        seasonal_oof = rolling_oof_seasonal(
            train,
            history_2024,
            gap_hours=gap_hours,
            horizon_hours=48,
            step_days=args.step_days,
        )
        print(f"  Seasonal OOF rows: {len(seasonal_oof):,}")

        # Summarize
        summary = summarize_comparison(baseline_oof, seasonal_oof, gap_hours)
        print(f"\n  Full-target RMSE comparison (gap={gap_hours}h):")
        print(f"  {'Model':<30} {'RMSE':>10} {'MAE':>10} {'Bias':>10} {'CleanRMSE':>12} {'Rows':>8}")
        print(f"  {'-'*74}")
        for _, row in summary.iterrows():
            clean_rmse = f"{row.get('clean_rmse', float('nan')):.2f}" if pd.notna(row.get('clean_rmse')) else "  N/A  "
            print(
                f"  {row['model']:<30} {row['full_target_rmse']:>10.2f} "
                f"{row['mae']:>10.2f} {row['bias']:>10.2f} "
                f"{clean_rmse:>12} {int(row['rows']):>8}"
            )

        all_summaries.append(summary)
        all_seasonal_oofs.append(seasonal_oof)
        all_baseline_oofs.append(baseline_oof)

        # Save gap-specific files
        baseline_oof.to_csv(
            REPORT_DIR / f"baseline_oof_gap{gap_hours}.csv.gz",
            index=False, compression="gzip",
        )
        seasonal_oof.to_csv(
            REPORT_DIR / f"seasonal_oof_gap{gap_hours}.csv.gz",
            index=False, compression="gzip",
        )

    # Combine and save summary
    full_summary = pd.concat(all_summaries, ignore_index=True)
    full_summary.to_csv(REPORT_DIR / "comparison_summary.csv", index=False)

    # Write Markdown report
    _write_report(full_summary, args.gap_hours)
    print(f"\nReport written to {REPORT_DIR}")


def _write_report(summary: pd.DataFrame, gap_hours_list: list[int]) -> None:
    lines = [
        "# EXP-20261107-007 — 2024 Seasonal History Evaluation",
        "",
        "## Experiment Design",
        "",
        "**Hypothesis**: 2024 same-station same-hour-of-year PM2.5 climatology from",
        "AdditionalHistory.zip provides a useful seasonal prior for November 2025–2026 targets,",
        "particularly when recent PM history is stale (gap ≥ 72h).",
        "",
        "**Archive acceptance gate**:",
        "- `History_Mumbai_2024.csv.gz` filtered to `source == 'cpcb_caaqm'` only.",
        "- Station identity by name fragment matching only (not sensor ID cross-reference).",
        "- PM2.5 values are pre-capped at 1000 µg/m³ in the archive (documented limitation).",
        "- HistoryNotes.txt warns averaging intervals are not fully aligned; cpcb_caaqm",
        "  timestamps at minute=0 treated as hour-start (same as competition target_start).",
        "",
        "**New candidate models**:",
        "- `hist24_same_hour`: same station, same hour-of-day, ±14 calendar days in 2024.",
        "- `hist24_month_hour`: same station, same month + hour-of-day in 2024.",
        "- `hist24_blend50_median72`: 50:50 blend of median72 and hist24_same_hour.",
        "",
        "**Controls**: `median72`, `last`, `mean72_exclude_gt1000` (from EXP-20261106-005).",
        "",
        "**Primary metric**: Full-target RMSE on all labelled validation rows.",
        "",
        "## Results",
        "",
    ]
    for gap in gap_hours_list:
        gap_rows = summary.loc[summary["gap_hours"] == gap]
        lines.append(f"### Gap {gap}h")
        lines.append("")
        lines.append(
            "| Model | Full-target RMSE | MAE | Bias | Clean RMSE (<500) | Rows |"
        )
        lines.append(
            "|---|---:|---:|---:|---:|---:|"
        )
        for _, row in gap_rows.iterrows():
            cr = f"{row.get('clean_rmse', float('nan')):.2f}" if pd.notna(row.get('clean_rmse')) else "N/A"
            lines.append(
                f"| {row['model']} | {row['full_target_rmse']:.2f} | "
                f"{row['mae']:.2f} | {row['bias']:.2f} | {cr} | {int(row['rows'])} |"
            )
        lines.append("")

    lines += [
        "## Archive Acceptance Decisions",
        "",
        "| Archive Member | Decision | Reason |",
        "|---|---|---|",
        "| History_Mumbai_2024.csv.gz | CONDITIONAL PASS (cpcb_caaqm rows only) | Four target station names present; timestamps at :00 for cpcb_caaqm; values capped at 1000 (documented); interval semantics unverified by organiser |",
        "| History_Mumbai_2018_2020.csv.gz | REJECTED | Only Borivali East present; 2018-2020 data too old for 2026 seasonal prior |",
        "| Legacy_Observations_2020_2022.csv.gz | REJECTED | Irregular sub-hourly samples; not qualified hourly labels |",
        "| Other_Mumbai_Stations_2025_2026.csv.gz | REJECTED | Location IDs do not match competition target stations |",
        "| XKDR_All_Stations.csv | N/A | Metadata lookup only |",
        "| Kaggle_All_Stations.csv | N/A | Metadata lookup only |",
        "",
        "## Limitations",
        "",
        "- Sensor identity not verified across archives; name matching only.",
        "- Archive PM2.5 values capped at 1000 µg/m³; competition train has values up to ~241 k.",
        "- Averaging intervals not confirmed identical to competition semantics.",
        "- 2024 is one prior year; seasonal patterns may not repeat exactly.",
        "- Fold RMSE standard deviations are large; small improvements are inconclusive.",
    ]
    (REPORT_DIR / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

