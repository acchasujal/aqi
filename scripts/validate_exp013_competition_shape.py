"""Locked 193h PM-gap, midnight-start, 48h competition-shaped comparison."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
from mumbai_pm25.data import load_data  # noqa: E402
from mumbai_pm25.historical_archive import STATION_NAME_MAP, load_2024_history  # noqa: E402
from mumbai_pm25.november_candidates import recent_median  # noqa: E402
from scripts.validate_seasonal_history import rolling_oof_seasonal  # noqa: E402

KEY = ["fold_id", "location_id", "target_start"]
MODELS = ("legacy_w50", "hybrid_w50_m24", "median72", "calendar365_w50")


def summarize(data: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    d = data.assign(error=data.prediction-data.y)
    d["squared"] = d.error**2
    return d.groupby(keys, dropna=False).agg(
        rows=("y", "size"), rmse=("squared", lambda x: float(np.sqrt(x.mean()))),
        mae=("error", lambda x: float(x.abs().mean())),
        median_ae=("error", lambda x: float(x.abs().median())),
        clean_rmse=("squared", lambda x: float(np.sqrt(x[d.loc[x.index, "y"] < 500].mean()))
                    if (d.loc[x.index, "y"] < 500).any() else np.nan),
        extreme_rows=("y", lambda x: int((x >= 500).sum())),
        fallback_pct=("fallback", lambda x: float(100*x.mean())),
        prediction_min=("prediction", "min"), prediction_median=("prediction", "median"),
        prediction_mean=("prediction", "mean"), prediction_max=("prediction", "max"),
        prediction_variance=("prediction", "var"),
    ).reset_index()


def main() -> None:
    train, *_ = load_data(ROOT / "data/raw/challenge")
    archive = load_2024_history(ROOT / "data/raw/challenge/AdditionalHistory.zip")
    archive = archive.loc[archive.station_name.str.contains(
        "|".join(STATION_NAME_MAP.values()), case=False, regex=True)].copy()
    if archive.hour_start.max() >= train.target_start.min():
        raise ValueError("Archive does not predate all historical folds")
    versions = {}
    for mode in ("legacy_doy", "month_day_365"):
        oof = rolling_oof_seasonal(train, archive, gap_hours=193,
                                   horizon_hours=48, step_days=7, calendar_mode=mode)
        w50 = oof[oof.model.eq("hist24_blend50_median72")].copy()
        season = oof[oof.model.eq("hist24_same_hour")][KEY+["prediction"]]
        versions[mode] = w50.merge(season, on=KEY, how="left",
                                   suffixes=("", "_season"), validate="one_to_one")
    old, new = versions.values()
    paired = old.merge(new, on=KEY, suffixes=("_old", "_new"), validate="one_to_one")
    if len(paired) != len(old) or len(paired) != len(new):
        raise ValueError("Comparison has mismatched scoring rows")
    if not np.array_equal(paired.y_old.to_numpy(), paired.y_new.to_numpy()):
        raise ValueError("Comparison labels differ")
    if not np.array_equal(paired.pm_gap_hours_old.to_numpy(), paired.pm_gap_hours_new.to_numpy()):
        raise ValueError("Comparison station-specific PM leads differ")
    # The current private task has one row at each 193–240h lead per station.
    # Exclude historical station-hours with a longer observation outage from
    # the primary matched comparison; account for coverage in the report.
    paired = paired.loc[paired.pm_gap_hours_old.between(193, 240)].reset_index(drop=True)
    paired["fold_id"] = pd.to_datetime(paired.fold_id, utc=True).dt.tz_convert("Asia/Kolkata")
    paired["target_start"] = pd.to_datetime(paired.target_start, utc=True).dt.tz_convert("Asia/Kolkata")
    if not (paired.target_start.dt.hour == paired.horizon_hours_old.sub(1).mod(24)).all():
        raise ValueError("Fold targets do not begin at midnight")
    if paired.last_pm_available_at_old.isna().any():
        raise ValueError("A scored row lacks PM history")
    station_series = {int(s): g.set_index("target_start").pm25.sort_index()
                      for s, g in train.groupby("location_id")}
    recent72 = np.where(paired.prediction_season_old.notna(),
                        2*paired.prediction_old-paired.prediction_season_old,
                        paired.prediction_old)
    m24 = np.empty(len(paired))
    fallback24 = np.empty(len(paired), dtype=bool)
    for (fold, station), indexes in paired.groupby(["fold_id", "location_id"]).groups.items():
        series = station_series[int(station)]
        value = recent_median(series, fold, 24)
        if value is None:
            raise ValueError("Matched scoring row lacks eligible station PM")
        m24[list(indexes)] = value
        eligible = series.loc[series.index < fold].dropna()
        fallback24[list(indexes)] = not (eligible.index >= fold-pd.Timedelta(hours=24)).any()
    if not np.isfinite(m24).all():
        raise ValueError("Non-finite median24")
    frames = []
    for model, prediction, fallback in (
        ("legacy_w50", paired.prediction_old, paired.prediction_season_old.isna()),
        ("hybrid_w50_m24", 0.5*paired.prediction_old.to_numpy()+0.5*m24,
         paired.prediction_season_old.isna() | fallback24),
        ("median72", recent72, np.zeros(len(paired), dtype=bool)),
        ("calendar365_w50", paired.prediction_new, paired.prediction_season_new.isna()),
    ):
        f = paired[KEY+["target_end_old", "pm_gap_hours_old", "horizon_hours_old", "y_old"]].copy()
        f.columns = KEY+["target_end", "pm_gap_hours", "horizon_hours", "y"]
        f["model"] = model
        f["prediction"] = prediction
        f["fallback"] = fallback
        frames.append(f)
    data = pd.concat(frames, ignore_index=True)
    if set(data.model.unique()) != set(MODELS):
        raise ValueError("Model count mismatch")
    prior_path = ROOT / "data/processed/exp012_row_predictions.csv.gz"
    if not prior_path.exists():
        raise FileNotFoundError("Generate the EXP-012 row audit with scripts/validate_november_candidates.py first")
    prior = pd.read_csv(prior_path, usecols=["location_id", "target_start"]).drop_duplicates()
    prior["target_start"] = pd.to_datetime(prior.target_start, utc=True).dt.tz_convert("Asia/Kolkata")
    prior_keys = pd.MultiIndex.from_frame(prior[["location_id", "target_start"]])
    data["previously_scored_row"] = pd.MultiIndex.from_frame(data[["location_id", "target_start"]]).isin(prior_keys)
    data["november"] = data.target_start.dt.month.eq(11)
    data["partition"] = np.where(data.fold_id < pd.Timestamp("2026-06-25T23:00:00+05:30"),
                                  "historical_development", "previously_inspected_late_2026")
    # Use the audited live release/issue offset for one issue time per fold.
    snapshot = json.loads((ROOT / "reports/ml_pipeline/exp_013/SNAPSHOT.json").read_text())
    issue_offset = pd.Timestamp(snapshot["model_run_time"]) - pd.Timestamp(snapshot["pm_cutoff"])
    data["prediction_origin"] = data.fold_id + issue_offset
    data["pm_history_cutoff"] = data.fold_id
    data["pseudo_issue_time"] = data.prediction_origin
    if not (data.pseudo_issue_time >= data.fold_id).all():
        raise ValueError("Pseudo issue precedes PM cutoff")
    if not (data.target_start >= data.pseudo_issue_time).all():
        raise ValueError("A scored target precedes its pseudo issue time")
    out = ROOT / "reports/ml_pipeline/exp_013"
    out.mkdir(parents=True, exist_ok=True)
    processed = ROOT / "data/processed"
    data.to_csv(processed / "exp013_row_predictions.csv.gz", index=False, compression="gzip")
    all_rows = summarize(data.assign(partition="all_matched_rows"), ["partition", "model"])
    by_partition = summarize(data, ["partition", "model"])
    pd.concat([all_rows, by_partition], ignore_index=True).to_csv(
        out / "MODEL_COMPARISON.csv", index=False)
    summarize(data, ["model", "fold_id"]).to_csv(out / "FOLD_METRICS.csv", index=False)
    summarize(data, ["model", "location_id"]).to_csv(out / "STATION_METRICS.csv", index=False)
    summarize(data, ["model", "horizon_hours"]).to_csv(out / "HORIZON_METRICS.csv", index=False)
    summarize(data, ["model", "pm_gap_hours"]).to_csv(out / "LEAD_METRICS.csv", index=False)
    summarize(data[data.november], ["model"]).to_csv(out / "NOVEMBER_METRICS.csv", index=False)
    print(f"folds {data.fold_id.nunique()}, rows/model {len(paired)}, prior-row-overlap {data.previously_scored_row.mean():.3f}")


if __name__ == "__main__":
    main()
