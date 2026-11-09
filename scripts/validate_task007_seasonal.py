"""TASK 007 exact-source seasonal evaluation at the current/final PM gap."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mumbai_pm25.data import complete_hourly_grid, load_data
from mumbai_pm25.forecast import predict_station_baseline
from mumbai_pm25.historical_archive import (
    ARCHIVE_SERIES,
    build_seasonal_features,
    load_2024_history,
    source_coverage_report,
)

DEVELOPMENT_START = pd.Timestamp("2025-04-01 00:00", tz="Asia/Kolkata")
DEVELOPMENT_END = pd.Timestamp("2026-09-30 00:00", tz="Asia/Kolkata")
HOLDOUT_ORIGINS = tuple(
    pd.Timestamp(value, tz="Asia/Kolkata")
    for value in ("2026-10-20 00:00", "2026-10-27 00:00")
)
SOURCE_OPTIONS: dict[int, dict[str, tuple[str, ...]]] = {
    11606: {
        "site_5113": ("xkdr:site_5113",),
        "site_5400": ("xkdr:site_5400",),
        "combined_5113_5400": ("xkdr:site_5113", "xkdr:site_5400"),
    },
    11611: {
        "site_5102": ("xkdr:site_5102",),
        "site_5402": ("xkdr:site_5402",),
        "combined_5102_5402": ("xkdr:site_5102", "xkdr:site_5402"),
    },
    3409510: {"site_5960": ("xkdr:site_5960",)},
    3409511: {"site_5961": ("xkdr:site_5961",)},
}
ORIGINAL_POOL = {
    11606: ("xkdr:site_5113", "xkdr:site_5400"),
    11611: ("xkdr:site_5102", "xkdr:site_5402", "xkdr:site_5807"),
    3409510: ("xkdr:site_5960",),
    3409511: ("xkdr:site_5961",),
}
P_FIX_SPEC = {
    11606: ("xkdr:site_5400",),
    11611: ORIGINAL_POOL[11611],
    3409510: ("xkdr:site_5960",),
    3409511: ("xkdr:site_5961",),
}


def build_origins() -> list[tuple[str, pd.Timestamp]]:
    origins = [("development", d) for d in pd.date_range(
        DEVELOPMENT_START, DEVELOPMENT_END, freq="28D"
    )]
    origins.extend(("holdout", d) for d in HOLDOUT_ORIGINS)
    return origins


def seasonal_value(features: pd.DataFrame, row_index: int, sources: tuple[str, ...]) -> tuple[float, int]:
    total_sum = 0.0
    total_count = 0
    for source in sources:
        count = int(features.iloc[row_index][f"hist24_series::{source}::coverage"])
        value_sum = float(features.iloc[row_index][f"hist24_series::{source}::sum"])
        total_sum += value_sum
        total_count += count
    return (total_sum / total_count if total_count >= 3 else np.nan, total_count)


def make_oof(train: pd.DataFrame, history_2024: pd.DataFrame, gap_hours: int,
             windows: tuple[int, ...], offsets: tuple[int, ...]) -> pd.DataFrame:
    grid = complete_hourly_grid(train).unstack(0)
    stations = sorted(int(value) for value in train.location_id.unique())
    origins = build_origins()
    target_rows: list[tuple[int, pd.Timestamp]] = []
    for _, origin in origins:
        target_rows.extend((station, target) for station in stations
                           for target in pd.date_range(origin, periods=48, freq="h"))
    seasonal: dict[tuple[int, int], pd.DataFrame] = {}
    target_df = pd.DataFrame(target_rows, columns=["location_id", "target_start"])
    target_df = target_df.drop_duplicates().reset_index(drop=True)
    all_sources = {station: ARCHIVE_SERIES[station] for station in stations}
    for window in windows:
        for offset in offsets:
            seasonal[(window, offset)] = build_seasonal_features(
                history_2024, target_df, series_map=all_sources,
                window_days=window, min_obs=3, offset_hours=offset,
            )
    seasonal_index = {
        (int(row.location_id), row.target_start): idx
        for idx, row in target_df.iterrows()
    }

    records: list[dict[str, object]] = []
    for regime, origin in origins:
        cutoff = origin - pd.Timedelta(hours=gap_hours)
        target_starts = pd.date_range(origin, periods=48, freq="h")
        for station in stations:
            series = grid[("pm25", station)]
            truth = series.reindex(target_starts).to_numpy(dtype=float)
            median = predict_station_baseline(
                series, target_starts, pm_history_cutoff=cutoff, model="median72"
            )
            diur7 = predict_station_baseline(
                series, target_starts, pm_history_cutoff=cutoff, model="diur7"
            )
            for j, target_start in enumerate(target_starts):
                if not np.isfinite(truth[j]):
                    continue
                row: dict[str, object] = {
                    "fold_id": origin,
                    "regime": regime,
                    "prediction_origin": cutoff,
                    "pm_history_cutoff": cutoff,
                    "target_start": target_start,
                    "target_end": target_start + pd.Timedelta(hours=1),
                    "forecast_lead_hours": gap_hours + j,
                    "pm_gap_hours": (target_start - (series.loc[series.index < cutoff].last_valid_index()
                        + pd.Timedelta(hours=1))).total_seconds() / 3600
                        if series.loc[series.index < cutoff].notna().any() else np.nan,
                    "location_id": station,
                    "y": float(truth[j]),
                    "median72": max(0.0, float(median[j])),
                    "diur7": float(diur7[j]) if np.isfinite(diur7[j]) else np.nan,
                }
                ti = seasonal_index[(station, target_start)]
                for window in windows:
                    feature = seasonal[(window, 0)]
                    for name, source_ids in SOURCE_OPTIONS[station].items():
                        value, coverage = seasonal_value(feature, ti, source_ids)
                        row[f"hist_{window}_{name}"] = value
                        row[f"hist_{window}_{name}_coverage"] = coverage
                        row[f"P50_{window}_{name}"] = (
                            0.5 * row["median72"] + 0.5 * value
                            if np.isfinite(value) else row["median72"]
                        )
                original, original_n = seasonal_value(
                    seasonal[(14, 0)], ti, ORIGINAL_POOL[station]
                )
                row["original_production"] = (
                    0.5 * row["median72"] + 0.5 * original
                    if np.isfinite(original) else row["median72"]
                )
                row["original_pool_coverage"] = original_n
                pfix_spec, _ = seasonal_value(seasonal[(14, 0)], ti, P_FIX_SPEC[station])
                row["P_fix_spec"] = (
                    0.5 * row["median72"] + 0.5 * pfix_spec
                    if np.isfinite(pfix_spec) else row["median72"]
                )
                for offset in offsets:
                    value, _ = seasonal_value(seasonal[(14, offset)], ti, ORIGINAL_POOL[station])
                    row[f"original_production_offset{offset:+d}"] = (
                        0.5 * row["median72"] + 0.5 * value
                        if np.isfinite(value) else row["median72"]
                    )
                records.append(row)
    return pd.DataFrame.from_records(records)


def select_sources(dev: pd.DataFrame) -> dict[int, tuple[str, ...]]:
    selected: dict[int, tuple[str, ...]] = {}
    for station, options in SOURCE_OPTIONS.items():
        scored = []
        subset = dev.loc[dev.location_id.eq(station)]
        for name in options:
            p = subset[f"P50_14_{name}"].to_numpy(dtype=float)
            y = subset.y.to_numpy(dtype=float)
            score = float(np.sqrt(np.mean(np.square(p - y))))
            coverage = float(subset[f"hist_14_{name}_coverage"].mean() / (
                29 * len(options[name])
            ))
            scored.append((score, name, coverage))
        score, name, coverage = min(scored)
        selected[station] = options[name]
        print(f"DEV source choice station={station}: {name}, RMSE={score:.3f}, coverage={coverage:.3f}")
    return selected


def attach_selected(oof: pd.DataFrame, source_map: dict[int, tuple[str, ...]]) -> pd.DataFrame:
    result = oof.copy()
    values = []
    for row in result.itertuples(index=False):
        station = int(row.location_id)
        # Find the source option selected for the station and use the fixed ±14-day profile.
        name = next(key for key, source in SOURCE_OPTIONS[station].items()
                    if source == source_map[station])
        values.append(float(getattr(row, f"P50_14_{name}")))
    result["P_fix"] = values
    return result


def metrics(frame: pd.DataFrame, candidates: list[str]) -> pd.DataFrame:
    rows = []
    for model in candidates:
        part = frame.dropna(subset=[model]).copy()
        error = part[model] - part.y
        squares = error.pow(2)
        clean = part.loc[part.y < 500]
        no_extreme_folds = part.loc[~part.fold_id.isin(
            part.groupby("fold_id").y.max().loc[lambda x: x > 1000].index
        )]
        rows.append({
            "model": model, "rows": len(part), "folds": part.fold_id.nunique(),
            "full_rmse": float(np.sqrt(squares.mean())),
            "clean_rmse_lt500": float(np.sqrt(np.mean(np.square(clean[model] - clean.y)))),
            "mae": float(error.abs().mean()), "bias": float(error.mean()),
            "rmse_excluding_extreme_folds": float(np.sqrt(np.mean(np.square(
                no_extreme_folds[model] - no_extreme_folds.y
            )))) if len(no_extreme_folds) else np.nan,
            "targets_gt500": int((part.y > 500).sum()),
            "targets_gt1000": int((part.y > 1000).sum()),
            "extreme_squared_error_share": float(squares.loc[part.y > 1000].sum() / squares.sum())
            if squares.sum() else 0.0,
        })
    return pd.DataFrame(rows)


def paired_block_ci(frame: pd.DataFrame, model: str, reference: str,
                    *, seed: int = 20261108, replicates: int = 2000) -> tuple[float, float, float]:
    paired = frame.dropna(subset=[model, reference]).copy()
    by_fold = paired.assign(
        a=np.square(paired[model] - paired.y),
        b=np.square(paired[reference] - paired.y),
    ).groupby("fold_id").agg(a=("a", "sum"), b=("b", "sum"), n=("y", "size"))
    k = len(by_fold)
    point = float(np.sqrt(by_fold.a.sum() / by_fold.n.sum())
                  - np.sqrt(by_fold.b.sum() / by_fold.n.sum()))
    if k < 4:
        return point, np.nan, np.nan
    rng = np.random.default_rng(seed)
    draws = []
    block = 2
    for _ in range(replicates):
        starts = rng.integers(0, k, size=int(np.ceil(k / block)))
        ids = np.concatenate([(np.arange(start, start + block) % k) for start in starts])[:k]
        counts = by_fold.n.to_numpy()[ids]
        rmse_a = np.sqrt(by_fold.a.to_numpy()[ids].sum() / counts.sum())
        rmse_b = np.sqrt(by_fold.b.to_numpy()[ids].sum() / counts.sum())
        draws.append(rmse_a - rmse_b)
    lo, hi = np.percentile(draws, [2.5, 97.5])
    return point, float(lo), float(hi)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data/raw/challenge")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reports/ml_pipeline/task007")
    parser.add_argument("--gap-hours", type=int, default=193)
    parser.add_argument("--windows", type=int, nargs="+", default=[7, 14, 21])
    parser.add_argument("--offsets", type=int, nargs="+", default=[-1, 0, 1])
    args = parser.parse_args()
    if args.gap_hours < 1:
        raise SystemExit("--gap-hours must be positive")

    train, _test, _sample, _stations = load_data(args.data_dir)
    history_2024 = load_2024_history(args.data_dir / "AdditionalHistory.zip")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    source_coverage_report(history_2024).to_csv(
        args.output_dir / "archive_source_coverage.csv", index=False
    )
    oof = make_oof(train, history_2024, args.gap_hours,
                   tuple(args.windows), tuple(args.offsets))
    oof.to_csv(args.output_dir / f"seasonal_oof_gap{args.gap_hours}.csv.gz",
               index=False, compression="gzip")

    dev = oof.loc[oof.regime.eq("development")]
    holdout = oof.loc[oof.regime.eq("holdout")]
    selected_sources = select_sources(dev)
    oof = attach_selected(oof, selected_sources)
    oof.to_csv(args.output_dir / f"seasonal_oof_gap{args.gap_hours}.csv.gz",
               index=False, compression="gzip")

    candidates = ["median72", "diur7", "original_production", "P_fix_spec", "P_fix"]
    summary_rows = []
    for regime in ("development", "holdout"):
        part = oof.loc[oof.regime.eq(regime)]
        # All reported comparisons use the same rows.
        matched = part.dropna(subset=candidates)
        summary = metrics(matched, candidates)
        summary["regime"] = regime
        summary["matched_rows"] = len(matched)
        summary_rows.append(summary)
        if regime == "development":
            for model in candidates:
                if model == "P_fix":
                    continue
                point, low, high = paired_block_ci(matched, model, "P_fix")
                print(f"DEV paired diff {model} - P_fix: {point:.3f} [{low:.3f}, {high:.3f}]")
    pd.concat(summary_rows, ignore_index=True).to_csv(
        args.output_dir / f"summary_gap{args.gap_hours}.csv", index=False
    )
    paired_rows = []
    matched_dev = oof.loc[oof.regime.eq("development")].dropna(subset=candidates)
    for model in candidates:
        if model == "P_fix":
            continue
        point, low, high = paired_block_ci(matched_dev, model, "P_fix")
        paired_rows.append({"model": model, "reference": "P_fix", "delta_rmse": point,
                            "ci_low": low, "ci_high": high,
                            "folds": matched_dev.fold_id.nunique(), "block_length_folds": 2})
    pd.DataFrame(paired_rows).to_csv(args.output_dir / f"paired_dev_gap{args.gap_hours}.csv", index=False)

    by_station = []
    matched = oof.dropna(subset=candidates).copy()
    for (regime, station), group in matched.groupby(["regime", "location_id"]):
        for model in candidates:
            by_station.append({"regime": regime, "location_id": station, "model": model,
                               "rows": len(group), "rmse": float(np.sqrt(np.mean(np.square(group[model]-group.y))))})
    pd.DataFrame(by_station).to_csv(args.output_dir / f"station_metrics_gap{args.gap_hours}.csv", index=False)
    matched["forecast_day"] = np.where(matched.forecast_lead_hours <= args.gap_hours + 23,
                                         "first_day", "second_day")
    by_day = []
    for (regime, day), group in matched.groupby(["regime", "forecast_day"]):
        for model in candidates:
            by_day.append({"regime": regime, "forecast_day": day, "model": model,
                           "rows": len(group), "rmse": float(np.sqrt(np.mean(np.square(group[model]-group.y))))})
    pd.DataFrame(by_day).to_csv(args.output_dir / f"lead_metrics_gap{args.gap_hours}.csv", index=False)

    # Sensitivity of original explicit source pools to 2024 calendar-window and hour offsets.
    offset_rows = []
    for window in args.windows:
        if window == 14:
            for offset in args.offsets:
                col = f"original_production_offset{offset:+d}"
                for regime, part in oof.groupby("regime"):
                    matched_offset = part.dropna(subset=[col, "median72", "diur7"])
                    offset_rows.append({"window_days": window, "offset_hours": offset,
                                        "regime": regime, "rows": len(matched_offset),
                                        "rmse": float(np.sqrt(np.mean(np.square(
                                            matched_offset[col] - matched_offset.y
                                        ))))})
    pd.DataFrame(offset_rows).to_csv(args.output_dir / f"alignment_sensitivity_gap{args.gap_hours}.csv", index=False)
    print(f"OOF rows={len(oof)} development folds={dev.fold_id.nunique()} holdout folds={holdout.fold_id.nunique()}")
    print(pd.concat(summary_rows, ignore_index=True).to_string(index=False))
    print(f"Outputs: {args.output_dir}")


if __name__ == "__main__":
    main()
