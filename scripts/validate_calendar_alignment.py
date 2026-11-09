"""EXP-011 matched chronological comparison of legacy and calendar-aligned W50."""
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
from scripts.validate_seasonal_history import rolling_oof_seasonal  # noqa: E402

KEY = ["fold_id", "location_id", "target_start"]
GAPS = (48, 72, 96, 120)


def score(frame: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    data = frame.assign(error=frame.prediction - frame.y)
    data["squared"] = data.error**2
    return data.groupby(keys).agg(
        rows=("y", "size"), rmse=("squared", lambda x: float(np.sqrt(x.mean()))),
        mae=("error", lambda x: float(x.abs().mean())),
        median_ae=("error", lambda x: float(x.abs().median())),
        fallback_pct=("fallback", lambda x: float(100 * x.mean())),
        extreme_rows=("y", lambda x: int((x >= 500).sum())),
    ).reset_index()


def main() -> None:
    out = ROOT / "reports/ml_pipeline/exp_011"
    out.mkdir(parents=True, exist_ok=True)
    train, *_ = load_data(ROOT / "data/raw/challenge")
    archive = load_2024_history(ROOT / "data/raw/challenge/AdditionalHistory.zip")
    relevant = archive.station_name.str.contains(
        "|".join(STATION_NAME_MAP.values()), case=False, regex=True
    )
    archive = archive.loc[relevant].copy()
    if archive.hour_start.max() >= train.target_start.min():
        raise ValueError("2024 archive is not wholly prior to validation period")
    archive["calendar_day"] = pd.to_datetime(
        "2025-" + archive.hour_start.dt.strftime("%m-%d"), errors="coerce"
    ).dt.dayofyear
    frames = []
    for gap in GAPS:
        versions = {}
        for mode in ("legacy_doy", "month_day_365"):
            oof = rolling_oof_seasonal(train, archive, gap_hours=gap, calendar_mode=mode)
            blend = oof[oof.model.eq("hist24_blend50_median72")].copy()
            season = oof[oof.model.eq("hist24_same_hour")][KEY + ["prediction"]]
            blend = blend.merge(season, on=KEY, how="left", suffixes=("", "_season"), validate="one_to_one")
            versions[mode] = blend
        old, new = versions.values()
        pair = old.merge(new, on=KEY, suffixes=("_old", "_new"), validate="one_to_one")
        if len(pair) != len(old) or len(pair) != len(new):
            raise ValueError("Calendar modes have different eligible rows")
        if not np.array_equal(pair.y_old.to_numpy(), pair.y_new.to_numpy()):
            raise ValueError("Calendar modes have different target labels")
        if pair.last_pm_available_at_old.isna().any():
            raise ValueError("Recent baseline cannot be recovered for a no-history row")
        recent = np.where(pair.prediction_season_old.notna(),
                          2 * pair.prediction_old - pair.prediction_season_old,
                          pair.prediction_old)
        for model, prediction, fallback in (
            ("median72", recent, np.zeros(len(pair), dtype=bool)),
            ("legacy_w50", pair.prediction_old, pair.prediction_season_old.isna()),
            ("calendar365_w50", pair.prediction_new, pair.prediction_season_new.isna()),
        ):
            frame = pair[[*KEY, "target_end_old", "pm_gap_hours_old", "horizon_hours_old", "y_old"]].copy()
            frame.columns = [*KEY, "target_end", "pm_gap_hours", "horizon_hours", "y"]
            frame["prediction"] = prediction
            frame["fallback"] = fallback
            frame["model"] = model
            frame["gap_hours"] = gap
            frames.append(frame)
        print(f"gap {gap}: {len(pair)} matched rows; changed {(pair.prediction_old != pair.prediction_new).sum()}", flush=True)
    data = pd.concat(frames, ignore_index=True)
    folds = sorted(pd.to_datetime(data.fold_id.unique()))
    split = folds[int(len(folds) * 0.8)]
    data["partition"] = np.where(data.fold_id < split, "development", "confirmation")
    processed = ROOT / "data/processed"
    processed.mkdir(parents=True, exist_ok=True)
    data.to_csv(processed / "exp011_row_predictions.csv.gz", index=False, compression="gzip")
    summary = score(data, ["partition", "gap_hours", "model"])
    overall = score(data, ["gap_hours", "model"])
    overall.insert(0, "partition", "all")
    pd.concat([summary, overall], ignore_index=True).to_csv(
        out / "MATCHED_VALIDATION.csv", index=False
    )
    score(data, ["partition", "gap_hours", "model", "location_id"]).to_csv(out / "STATION_METRICS.csv", index=False)
    score(data, ["partition", "gap_hours", "model", "fold_id"]).to_csv(out / "FOLD_METRICS.csv", index=False)
    score(data, ["partition", "gap_hours", "model", "horizon_hours"]).to_csv(out / "HORIZON_METRICS.csv", index=False)
    print(f"confirmation starts {split.isoformat()}", flush=True)


if __name__ == "__main__":
    main()
