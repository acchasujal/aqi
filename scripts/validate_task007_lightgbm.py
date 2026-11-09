"""Controlled all-label LightGBM comparisons for TASK 007 gap-193 OOF."""
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

DEVELOPMENT_START = pd.Timestamp("2025-04-01 00:00", tz="Asia/Kolkata")
DEVELOPMENT_END = pd.Timestamp("2026-09-30 00:00", tz="Asia/Kolkata")
HOLDOUT_ORIGINS = tuple(
    pd.Timestamp(value, tz="Asia/Kolkata")
    for value in ("2026-10-20 00:00", "2026-10-27 00:00")
)
MODEL_NAMES = ("ratio_cyclic", "ratio_doy", "direct_cyclic", "residual_cyclic", "ratio_huber")
WEIGHT_GRID = (
    (0.125, 0.125, 0.750),
    (0.250, 0.250, 0.500),
    (0.375, 0.125, 0.500),
    (0.125, 0.375, 0.500),
    (0.250, 0.375, 0.375),
)


def origins() -> list[tuple[str, pd.Timestamp]]:
    dev = [("development", d) for d in pd.date_range(
        DEVELOPMENT_START, DEVELOPMENT_END, freq="28D"
    )]
    return dev + [("holdout", d) for d in HOLDOUT_ORIGINS]


def _features_for_origin(
    raw: pd.DataFrame,
    clean: pd.DataFrame,
    origin: pd.Timestamp,
    gap_hours: int,
) -> pd.DataFrame:
    cutoff = origin - pd.Timedelta(hours=gap_hours)
    history = clean.loc[clean.index < cutoff]
    if len(history) < 24 * 8:
        return pd.DataFrame()
    x24, x72, x168, x336 = (history.iloc[-n:] for n in (24, 72, 168, 336))
    global_means = {
        window: float(block.mean().mean()) if block.notna().any().any() else np.nan
        for window, block in ((24, x24), (72, x72), (168, x168))
    }
    profiles = x168.groupby(x168.index.hour).mean()
    records: list[dict[str, object]] = []
    for station in sorted(int(x) for x in raw.columns):
        if int(x72[station].notna().sum()) < 24:
            continue
        level = float(x168[station].mean())
        if not np.isfinite(level) or level <= 1:
            continue
        station_history = history[station]
        last = station_history.dropna()
        if last.empty:
            continue
        profile = profiles[station]
        for k in range(1, 49):
            target_end = origin + pd.Timedelta(hours=k)
            target_start = target_end - pd.Timedelta(hours=1)
            y = raw[station].reindex([target_start]).iloc[0]
            if pd.isna(y):
                continue
            records.append({
                "origin": origin,
                "pm_history_cutoff": cutoff,
                "target_start": target_start,
                "target_end": target_end,
                "location_id": station,
                "hour": target_end.hour,
                "day_of_week": target_end.day_of_week,
                "day_of_year": target_end.day_of_year,
                "forecast_lead_hours": gap_hours + k - 1,
                "m24": float(x24[station].mean()),
                "m72": float(x72[station].mean()),
                "m168": level,
                "m336": float(x336[station].mean()),
                "med72": float(x72[station].median()),
                "sd168": float(x168[station].std()),
                "last": float(last.iloc[-1]),
                "pk168": float(x168[station].max()),
                "p24": global_means[24],
                "p72": global_means[72],
                "p168": global_means[168],
                "prof7": float(profile.get(target_end.hour, np.nan)),
                "level": level,
                "y": float(y),
            })
    return pd.DataFrame.from_records(records)


def build_pseudo_samples(train: pd.DataFrame, gap_hours: int) -> pd.DataFrame:
    """Build past-only weekly pseudo-origin training rows with all labels kept."""
    grid = complete_hourly_grid(train).unstack(0)
    raw = grid["pm25"].copy()
    clean = raw.where(raw < 1000).clip(upper=300)
    min_origin = train.target_start.min().ceil("D") + pd.Timedelta(days=18)
    max_target_origin = max(date for _, date in origins())
    max_origin = max_target_origin - pd.Timedelta(hours=gap_hours + 48)
    pseudo_origins = pd.date_range(min_origin, max_origin, freq="7D")
    parts = [_features_for_origin(raw, clean, origin, gap_hours) for origin in pseudo_origins]
    return pd.concat([part for part in parts if not part.empty], ignore_index=True)


def _matrix(frame: pd.DataFrame, *, cyclic: bool) -> tuple[pd.DataFrame, list[str]]:
    data = frame.copy()
    angle = 2.0 * np.pi * (data.day_of_year - 1) / 365.2425
    data["annual_sin"] = np.sin(angle)
    data["annual_cos"] = np.cos(angle)
    data = pd.get_dummies(data, columns=["location_id"], prefix="station", dtype=float)
    features = [
        "hour", "day_of_week", "forecast_lead_hours", "m24", "m72", "m168",
        "m336", "med72", "sd168", "last", "pk168", "p24", "p72", "p168",
        "prof7", "annual_sin", "annual_cos",
    ]
    if not cyclic:
        features.append("day_of_year")
    features.extend(col for col in data.columns if col.startswith("station_"))
    return data, features


def fit_model(train_rows: pd.DataFrame, valid_rows: pd.DataFrame,
              name: str, *, seed: int = 20261108) -> np.ndarray:
    try:
        from lightgbm import LGBMRegressor
    except ImportError as exc:
        raise RuntimeError("LightGBM is required for TASK 007 candidate evaluation") from exc
    cyclic = name != "ratio_doy"
    tr, features = _matrix(train_rows, cyclic=cyclic)
    va, _ = _matrix(valid_rows, cyclic=cyclic)
    xtr = tr[features].copy()
    xva = va.reindex(columns=features).copy()
    medians = xtr.median(numeric_only=True)
    xtr = xtr.fillna(medians).fillna(-999)
    xva = xva.fillna(medians).fillna(-999)
    y = train_rows.y.to_numpy(dtype=float)
    level = train_rows.level.to_numpy(dtype=float)
    params: dict[str, object] = {
        "n_estimators": 200, "learning_rate": 0.03, "num_leaves": 15,
        "min_child_samples": 150, "subsample": 0.8, "subsample_freq": 1,
        "colsample_bytree": 0.8, "reg_lambda": 5.0, "random_state": seed,
        "n_jobs": 2, "verbosity": -1,
    }
    if name.startswith("ratio"):
        response = np.log(np.maximum(y, 1.0) / level)
        if name == "ratio_huber":
            params.update(objective="huber", alpha=0.5)
    elif name == "direct_cyclic":
        response = np.log1p(y)
    elif name == "residual_cyclic":
        response = y - level
    else:
        raise ValueError(f"Unknown LightGBM candidate {name!r}")
    model = LGBMRegressor(**params).fit(xtr, response)
    prediction = model.predict(xva)
    if name.startswith("ratio"):
        prediction = np.exp(prediction) * valid_rows.level.to_numpy(dtype=float)
    elif name == "direct_cyclic":
        prediction = np.expm1(prediction)
    else:
        prediction = prediction + valid_rows.level.to_numpy(dtype=float)
    prediction = np.maximum(prediction, 0.0)
    if not np.isfinite(prediction).all():
        raise ValueError(f"{name} generated non-finite predictions")
    return prediction


def paired_block_ci(frame: pd.DataFrame, model: str, reference: str,
                    *, seed: int = 20261108, replicates: int = 2000) -> tuple[float, float, float]:
    paired = frame.dropna(subset=[model, reference]).copy()
    folded = paired.assign(
        model_sse=np.square(paired[model] - paired.y),
        ref_sse=np.square(paired[reference] - paired.y),
    ).groupby("fold_id").agg(
        model_sse=("model_sse", "sum"), ref_sse=("ref_sse", "sum"), rows=("y", "size")
    )
    n_folds = len(folded)
    estimate = float(np.sqrt(folded.model_sse.sum() / folded.rows.sum())
                     - np.sqrt(folded.ref_sse.sum() / folded.rows.sum()))
    if n_folds < 4:
        return estimate, np.nan, np.nan
    rng = np.random.default_rng(seed)
    draws = []
    block = 2
    for _ in range(replicates):
        starts = rng.integers(0, n_folds, size=int(np.ceil(n_folds / block)))
        ids = np.concatenate([np.arange(start, start + block) % n_folds for start in starts])[:n_folds]
        rows = folded.rows.to_numpy()[ids]
        rmse_model = np.sqrt(folded.model_sse.to_numpy()[ids].sum() / rows.sum())
        rmse_ref = np.sqrt(folded.ref_sse.to_numpy()[ids].sum() / rows.sum())
        draws.append(rmse_model - rmse_ref)
    low, high = np.percentile(draws, [2.5, 97.5])
    return estimate, float(low), float(high)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data/raw/challenge")
    parser.add_argument("--seasonal-oof", type=Path,
                        default=ROOT / "reports/ml_pipeline/task007/seasonal_repaired_v2/seasonal_oof_gap193.csv.gz")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reports/ml_pipeline/task007/supervised_gap193_v1")
    parser.add_argument("--gap-hours", type=int, default=193)
    parser.add_argument("--min-train-rows", type=int, default=500)
    args = parser.parse_args()
    try:
        import lightgbm
    except ImportError as exc:
        raise SystemExit("Install a compatible LightGBM build to run this experiment") from exc
    train, _test, _sample, _stations = load_data(args.data_dir)
    all_samples = build_pseudo_samples(train, args.gap_hours)
    seasonal = pd.read_csv(args.seasonal_oof, parse_dates=["fold_id", "target_start"])
    grid = complete_hourly_grid(train).unstack(0)
    fold_records: list[pd.DataFrame] = []
    for regime, origin in origins():
        cutoff = origin - pd.Timedelta(hours=args.gap_hours)
        validation = _features_for_origin(
            grid["pm25"].copy(), grid["pm25"].where(grid["pm25"] < 1000).clip(upper=300),
            origin, args.gap_hours,
        )
        if validation.empty:
            continue
        fit_rows = all_samples.loc[
            all_samples.target_end.le(cutoff) & all_samples.origin.lt(origin)
        ].copy()
        if len(fit_rows) < args.min_train_rows:
            print(f"skip {origin.isoformat()}: only {len(fit_rows)} eligible training rows")
            continue
        baseline = []
        diurnal = []
        for row in validation.itertuples(index=False):
            series = grid[("pm25", int(row.location_id))]
            target = pd.DatetimeIndex([row.target_start])
            baseline.append(predict_station_baseline(
                series, target, pm_history_cutoff=cutoff, model="median72"
            )[0])
            diurnal.append(predict_station_baseline(
                series, target, pm_history_cutoff=cutoff, model="diur7"
            )[0])
        validation["median72"] = np.maximum(baseline, 0.0)
        validation["diur7"] = diurnal
        key = seasonal.loc[seasonal.fold_id.eq(origin),
                           ["target_start", "location_id", "P_fix", "original_production", "P_fix_spec"]]
        validation = validation.merge(key, on=["target_start", "location_id"], how="left", validate="one_to_one")
        for name in MODEL_NAMES:
            validation[name] = fit_model(fit_rows, validation, name)
        validation["regime"] = regime
        validation["fold_id"] = origin
        validation["prediction_origin"] = cutoff
        fold_records.append(validation)
        print(f"{regime} origin={origin.isoformat()} train_rows={len(fit_rows)} target_rows={len(validation)}",
              flush=True)

    if not fold_records:
        raise RuntimeError("No LightGBM folds produced predictions")
    oof = pd.concat(fold_records, ignore_index=True)
    # Preserve row-level OOF for every candidate; report metrics on the common support.
    args.output_dir.mkdir(parents=True, exist_ok=True)
    oof.to_csv(args.output_dir / "lightgbm_oof.csv.gz", index=False, compression="gzip")
    dev = oof.loc[oof.regime.eq("development")].dropna(
        subset=[*MODEL_NAMES, "median72", "diur7", "P_fix"]
    ).copy()
    holdout = oof.loc[oof.regime.eq("holdout")].dropna(
        subset=[*MODEL_NAMES, "median72", "diur7", "P_fix"]
    ).copy()
    model_scores = {name: float(np.sqrt(np.mean(np.square(dev[name] - dev.y))))
                    for name in MODEL_NAMES}
    selected = min(model_scores, key=model_scores.get)
    ratio_candidates = ("ratio_cyclic", "ratio_doy", "ratio_huber")
    ratio_scores = {name: model_scores[name] for name in ratio_candidates}
    selected_ratio = min(ratio_scores, key=ratio_scores.get)
    print("Development RMSE by supervised candidate:", model_scores,
          "best individual:", selected, "selected ratio B:", selected_ratio)
    grid_rows = []
    for b_weight, diur_weight, pfix_weight in WEIGHT_GRID:
        name = f"f4w_{b_weight:.3f}_{diur_weight:.3f}_{pfix_weight:.3f}"
        dev[name] = (b_weight * dev[selected_ratio] + diur_weight * dev.diur7
                     + pfix_weight * dev.P_fix)
        grid_rows.append({"model": name, "B_weight": b_weight,
                          "diur7_weight": diur_weight, "P_fix_weight": pfix_weight,
                          "development_rmse": float(np.sqrt(np.mean(np.square(dev[name]-dev.y))))})
    grid_result = pd.DataFrame(grid_rows).sort_values("development_rmse")
    grid_result.to_csv(args.output_dir / "f4_weight_grid_development.csv", index=False)
    best = grid_result.iloc[0]
    b_weight, diur_weight, pfix_weight = (best.B_weight, best.diur7_weight, best.P_fix_weight)
    for frame in (dev, holdout):
        frame["B_ratio_selected"] = frame[selected_ratio]
        frame["F4_fixed"] = 0.25 * frame[selected_ratio] + 0.25 * frame.diur7 + 0.50 * frame.P_fix
        frame["F4_dev_selected"] = b_weight * frame[selected_ratio] + diur_weight * frame.diur7 + pfix_weight * frame.P_fix
    candidates = ["median72", "diur7", "original_production", "P_fix_spec", "P_fix", *MODEL_NAMES,
                  "B_ratio_selected", "F4_fixed", "F4_dev_selected"]
    metric_rows = []
    for regime, frame in (("development", dev), ("holdout", holdout)):
        # Drop any row where one of the required candidates is unavailable.
        matched = frame.dropna(subset=candidates)
        y = matched.y.to_numpy(dtype=float)
        for model in candidates:
            error = matched[model].to_numpy(dtype=float) - y
            fold_extreme = matched.groupby("fold_id").y.max().gt(1000)
            extreme_ids = set(fold_extreme.loc[fold_extreme].index)
            ordinary = matched.loc[~matched.fold_id.isin(extreme_ids)]
            metric_rows.append({
                "regime": regime, "model": model, "rows": len(matched),
                "folds": matched.fold_id.nunique(),
                "full_rmse": float(np.sqrt(np.mean(error ** 2))),
                "clean_rmse_lt500": float(np.sqrt(np.mean(np.square(
                    matched.loc[matched.y < 500, model] - matched.loc[matched.y < 500, "y"]
                )))),
                "mae": float(np.mean(np.abs(error))), "bias": float(np.mean(error)),
                "targets_gt500": int((matched.y > 500).sum()),
                "targets_gt1000": int((matched.y > 1000).sum()),
                "extreme_squared_error_share": float(np.sum(np.square(error[matched.y.to_numpy() > 1000]))
                                                       / np.sum(error ** 2)) if np.sum(error ** 2) else 0.0,
                "rmse_excluding_extreme_folds": float(np.sqrt(np.mean(np.square(
                    ordinary[model] - ordinary.y
                )))) if len(ordinary) else np.nan,
            })
            if regime == "development":
                delta, ci_low, ci_high = paired_block_ci(matched, model, "P_fix")
                metric_rows[-1]["paired_delta_vs_pfix"] = delta
                metric_rows[-1]["paired_ci_low"] = ci_low
                metric_rows[-1]["paired_ci_high"] = ci_high
            else:
                metric_rows[-1]["paired_delta_vs_pfix"] = float(np.sqrt(np.mean(np.square(
                    matched[model] - matched.y
                ))) - np.sqrt(np.mean(np.square(matched.P_fix - matched.y))))
                metric_rows[-1]["paired_ci_low"] = np.nan
                metric_rows[-1]["paired_ci_high"] = np.nan
        matched.to_csv(args.output_dir / f"matched_{regime}_predictions.csv", index=False)
    pd.DataFrame(metric_rows).to_csv(args.output_dir / "model_metrics.csv", index=False)
    for regime, frame in (("development", dev), ("holdout", holdout)):
        matched = frame.dropna(subset=candidates)
        by_station = []
        for station, group in matched.groupby("location_id"):
            for model in candidates:
                by_station.append({"regime": regime, "location_id": station, "model": model,
                                   "rows": len(group), "rmse": float(np.sqrt(np.mean(
                                       np.square(group[model] - group.y)
                                   )))})
        pd.DataFrame(by_station).to_csv(args.output_dir / f"station_metrics_{regime}.csv", index=False)
        matched["forecast_day"] = np.where(
            matched.forecast_lead_hours <= args.gap_hours + 23, "first_day", "second_day"
        )
        by_day = []
        for day, group in matched.groupby("forecast_day"):
            for model in candidates:
                by_day.append({"regime": regime, "forecast_day": day, "model": model,
                               "rows": len(group), "rmse": float(np.sqrt(np.mean(
                                   np.square(group[model] - group.y)
                               )))})
        pd.DataFrame(by_day).to_csv(args.output_dir / f"lead_metrics_{regime}.csv", index=False)
        fold_rows = []
        for fold, group in matched.groupby("fold_id"):
            for model in candidates:
                fold_rows.append({"regime": regime, "fold_id": fold, "model": model,
                                  "rows": len(group), "rmse": float(np.sqrt(np.mean(
                                      np.square(group[model] - group.y)
                                  )))})
        pd.DataFrame(fold_rows).to_csv(args.output_dir / f"fold_metrics_{regime}.csv", index=False)
    print("Best individual:", selected, "selected ratio B:", selected_ratio,
          "F4 development weights:",
          (b_weight, diur_weight, pfix_weight), "fixed F4 remains (0.25,0.25,0.50)")
    print(pd.DataFrame(metric_rows).to_string(index=False))
    print(f"LightGBM {lightgbm.__version__}; output={args.output_dir}")


if __name__ == "__main__":
    main()
