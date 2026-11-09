"""EXP-010 fixed-weight chronological validation from corrected EXP-009 folds."""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
from mumbai_pm25.data import load_data  # noqa: E402
from mumbai_pm25.forecast import combine_forecasts  # noqa: E402
from mumbai_pm25.historical_archive import load_2024_history  # noqa: E402
from scripts.validate_seasonal_history import rolling_oof_seasonal  # noqa: E402

WEIGHTS = (0.0, 0.25, 0.5, 0.75, 1.0)
GAPS = (48, 72, 96, 120)
KEY = ["fold_id", "location_id", "target_start"]


def score(frame: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    data = frame.assign(error=frame.prediction - frame.y)
    data["square"] = data.error**2
    return data.groupby(keys, dropna=False).agg(
        rows=("y", "size"), rmse=("square", lambda x: float(np.sqrt(x.mean()))),
        mae=("error", lambda x: float(x.abs().mean())),
        median_ae=("error", lambda x: float(x.abs().median())),
        bias=("error", "mean"),
        fallback_pct=("fallback", lambda x: float(x.mean() * 100)),
    ).reset_index()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report-dir", type=Path, default=ROOT / "reports/ml_pipeline/exp_010")
    args = parser.parse_args()
    out = args.report_dir
    out.mkdir(parents=True, exist_ok=True)
    train, *_ = load_data(ROOT / "data/raw/challenge")
    archive_path = ROOT / "data/raw/challenge/AdditionalHistory.zip"
    archive = load_2024_history(archive_path)
    train_hash = hashlib.sha256((ROOT / "data/raw/challenge/Train.csv").read_bytes()).hexdigest()
    archive_hash = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    all_rows = []
    for gap in GAPS:
        oof = rolling_oof_seasonal(train, archive, gap_hours=gap)
        w50 = oof.loc[oof.model.eq("hist24_blend50_median72")].copy()
        season = oof.loc[oof.model.eq("hist24_same_hour"), KEY + ["prediction"]]
        merged = w50.merge(season, on=KEY, how="left", suffixes=("", "_season"), validate="one_to_one")
        assert len(merged) == len(w50)
        if merged.last_pm_available_at.isna().any():
            raise ValueError("Cannot recover recent component from seasonal-only W50 rows")
        if merged.duplicated(KEY).any():
            raise ValueError("Duplicate fold/station/target key")
        merged["recent"] = np.where(merged.prediction_season.notna(),
                                     2 * merged.prediction - merged.prediction_season,
                                     merged.prediction)
        for w in WEIGHTS:
            candidate = merged.copy()
            candidate["prediction"] = [combine_forecasts(float(r), float(s) if np.isfinite(s) else None, w)
                                       for r, s in zip(candidate.recent, candidate.prediction_season)]
            candidate["fallback"] = candidate.prediction_season.isna()
            candidate["weight"] = w
            candidate["gap_hours"] = gap
            all_rows.append(candidate[[*KEY, "target_end", "pm_history_cutoff", "prediction_origin",
                                       "pm_gap_hours", "horizon_hours", "y", "prediction", "fallback", "weight", "gap_hours"]])
        print(f"gap {gap}: {len(w50)} matched rows, {w50.fold_id.nunique()} folds", flush=True)
    results = pd.concat(all_rows, ignore_index=True)
    # Every candidate has the same row keys within each gap.
    fold_dates = sorted(pd.to_datetime(results.fold_id.unique()))
    split = fold_dates[int(len(fold_dates) * 0.8)]
    results["partition"] = np.where(results.fold_id < split, "development", "confirmation")
    processed = ROOT / "data/processed"
    processed.mkdir(parents=True, exist_ok=True)
    results.to_csv(processed / "exp010_row_predictions.csv.gz", index=False, compression="gzip")
    score(results, ["partition", "gap_hours", "weight"]).to_csv(out / "WEIGHT_COMPARISON.csv", index=False)
    score(results, ["partition", "gap_hours", "weight", "fold_id"]).to_csv(out / "FOLD_METRICS.csv", index=False)
    score(results, ["partition", "gap_hours", "weight", "location_id"]).to_csv(out / "STATION_METRICS.csv", index=False)
    score(results, ["partition", "gap_hours", "weight", "horizon_hours"]).to_csv(out / "HORIZON_METRICS.csv", index=False)
    score(results.loc[pd.to_datetime(results.target_start).dt.month.eq(11)],
          ["partition", "gap_hours", "weight"]).to_csv(out / "NOVEMBER_METRICS.csv", index=False)
    (out / "RUN_METADATA.txt").write_text(
        f"Train.csv sha256: {train_hash}\nAdditionalHistory.zip sha256: {archive_hash}\n"
        f"confirmation fold start: {split.isoformat()}\nweights: {WEIGHTS}\ngaps: {GAPS}\n"
        "horizon_hours: 48\nstep_days: 7\n", encoding="utf-8")
    print(f"confirmation fold start: {split.isoformat()}", flush=True)


if __name__ == "__main__":
    main()
