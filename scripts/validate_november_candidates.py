"""EXP-012 matched history-only candidate evaluation."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
from mumbai_pm25.data import load_data  # noqa: E402
from mumbai_pm25.historical_archive import STATION_NAME_MAP, load_2024_history  # noqa: E402
from mumbai_pm25.november_candidates import bounded_trend48, recent_median  # noqa: E402
from scripts.validate_seasonal_history import rolling_oof_seasonal  # noqa: E402

KEY = ["gap_hours", "fold_id", "location_id", "target_start"]
MODELS = ("legacy_w50", "median72", "median24", "median48", "trend48", "hybrid_w50_m24", "calendar365_w50")


def build_192(train: pd.DataFrame) -> pd.DataFrame:
    archive = load_2024_history(ROOT / "data/raw/challenge/AdditionalHistory.zip")
    archive = archive.loc[archive.station_name.str.contains(
        "|".join(STATION_NAME_MAP.values()), case=False, regex=True)].copy()
    if archive.hour_start.max() >= train.target_start.min():
        raise ValueError("Archive must precede validation targets")
    frames = []
    for mode in ("legacy_doy", "month_day_365"):
        oof = rolling_oof_seasonal(train, archive, gap_hours=192, calendar_mode=mode)
        w50 = oof[oof.model.eq("hist24_blend50_median72")].copy()
        season = oof[oof.model.eq("hist24_same_hour")][["fold_id", "location_id", "target_start", "prediction"]]
        w50 = w50.merge(season, on=["fold_id", "location_id", "target_start"],
                        how="left", suffixes=("", "_season"), validate="one_to_one")
        w50["gap_hours"] = 192
        w50["mode"] = mode
        frames.append(w50)
    pair = frames[0].merge(frames[1], on=KEY, suffixes=("_old", "_new"), validate="one_to_one")
    if len(pair) != len(frames[0]) or len(pair) != len(frames[1]):
        raise ValueError("Calendar 192h rows differ")
    if pair.last_pm_available_at_old.isna().any():
        raise ValueError("No-history row prevents recent baseline reconstruction")
    recent = np.where(pair.prediction_season_old.notna(),
                      2 * pair.prediction_old - pair.prediction_season_old,
                      pair.prediction_old)
    rows = []
    for model, pred in (("legacy_w50", pair.prediction_old),
                        ("calendar365_w50", pair.prediction_new), ("median72", recent)):
        f = pair[KEY + ["y_old", "horizon_hours_old", "pm_gap_hours_old"]].copy()
        f.columns = KEY + ["y", "horizon_hours", "pm_gap_hours"]
        f["prediction"] = pred
        f["model"] = model
        rows.append(f)
    return pd.concat(rows, ignore_index=True)


def score(frame: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    d = frame.assign(error=frame.prediction-frame.y)
    d["square"] = d.error**2
    return d.groupby(keys).agg(rows=("y", "size"),
                               rmse=("square", lambda x: float(np.sqrt(x.mean()))),
                               mae=("error", lambda x: float(x.abs().mean())),
                               median_ae=("error", lambda x: float(x.abs().median())),
                               clean_rmse=("square", lambda x: float(np.sqrt(x[d.loc[x.index, "y"] < 500].mean())) if (d.loc[x.index, "y"] < 500).any() else np.nan),
                               prediction_min=("prediction", "min"),
                               prediction_max=("prediction", "max"),
                               prediction_variance=("prediction", "var")).reset_index()


def main() -> None:
    cache = ROOT / "data/processed/exp011_row_predictions.csv.gz"
    if not cache.exists():
        raise FileNotFoundError("Copy or regenerate accepted EXP-011 row predictions")
    train, *_ = load_data(ROOT / "data/raw/challenge")
    existing = pd.read_csv(cache)
    existing = existing[existing.model.isin(["legacy_w50", "calendar365_w50", "median72"])].copy()
    extended = build_192(train)
    base = pd.concat([existing, extended], ignore_index=True)
    base["fold_id"] = pd.to_datetime(base.fold_id, utc=True).dt.tz_convert("Asia/Kolkata")
    base["target_start"] = pd.to_datetime(base.target_start, utc=True).dt.tz_convert("Asia/Kolkata")
    if base.duplicated(KEY + ["model"]).any():
        raise ValueError("Duplicate candidate rows")
    wide = base.pivot(index=KEY, columns="model", values="prediction").reset_index()
    truth = base[base.model.eq("legacy_w50")][KEY + ["y", "horizon_hours", "pm_gap_hours"]]
    wide = wide.merge(truth, on=KEY, validate="one_to_one")
    station_hist = {int(s): g.set_index("target_start").pm25.sort_index()
                    for s, g in train.groupby("location_id")}
    outputs = []
    for (gap, fold, station), g in wide.groupby(["gap_hours", "fold_id", "location_id"], sort=False):
        history = station_hist[int(station)]
        m24 = recent_median(history, fold, 24)
        m48 = recent_median(history, fold, 48)
        m72 = recent_median(history, fold, 72)
        if m24 is None or m48 is None or m72 is None:
            raise ValueError("Missing recent history on matched scored row")
        if not np.allclose(g.median72, m72, rtol=0, atol=1e-10):
            raise ValueError("Recent median differs from accepted EXP-009 baseline")
        trend = bounded_trend48(history, fold, pd.DatetimeIndex(g.target_start))
        predictions = {"median24": np.full(len(g), m24),
                       "median48": np.full(len(g), m48), "trend48": trend,
                       "hybrid_w50_m24": 0.5 * g.legacy_w50.to_numpy() + 0.5 * m24}
        for model, pred in predictions.items():
            f = g[KEY + ["y", "horizon_hours", "pm_gap_hours"]].copy()
            f["model"] = model
            f["prediction"] = pred
            outputs.append(f)
    for model in ("legacy_w50", "median72", "calendar365_w50"):
        f = wide[KEY + ["y", "horizon_hours", "pm_gap_hours"]].copy()
        f["model"] = model
        f["prediction"] = wide[model]
        outputs.append(f)
    result = pd.concat(outputs, ignore_index=True)
    counts = result.groupby(["gap_hours", "model"]).size().unstack()
    if not counts.nunique(axis=1).eq(1).all() or set(counts.columns) != set(MODELS):
        raise ValueError("Candidate scoring rows differ")
    result["partition"] = np.where(result.fold_id < pd.Timestamp("2026-06-25T23:00:00+05:30"),
                                   "development", "reused_late_2026")
    result["november"] = result.target_start.dt.month.eq(11)
    processed = ROOT / "data/processed"
    result.to_csv(processed / "exp012_row_predictions.csv.gz", index=False, compression="gzip")
    out = ROOT / "reports/ml_pipeline/exp_012"
    score(result, ["partition", "gap_hours", "model"]).to_csv(out / "CANDIDATE_COMPARISON.csv", index=False)
    score(result, ["partition", "gap_hours", "model", "fold_id"]).to_csv(out / "FOLD_METRICS.csv", index=False)
    score(result, ["partition", "gap_hours", "model", "location_id"]).to_csv(out / "STATION_METRICS.csv", index=False)
    score(result, ["partition", "gap_hours", "model", "horizon_hours"]).to_csv(out / "HORIZON_METRICS.csv", index=False)
    score(result[result.november], ["gap_hours", "model"]).to_csv(out / "NOVEMBER_METRICS.csv", index=False)
    print(counts.to_string(), flush=True)


if __name__ == "__main__":
    main()
