"""EXP-012 diagnostics from matched row-level candidate predictions."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mumbai_pm25.data import load_data  # noqa: E402


def main() -> None:
    data = pd.read_csv(ROOT / "data/processed/exp012_row_predictions.csv.gz")
    data["fold_id"] = pd.to_datetime(data.fold_id, utc=True).dt.tz_convert("Asia/Kolkata")
    data["target_start"] = pd.to_datetime(data.target_start, utc=True).dt.tz_convert("Asia/Kolkata")
    data["square"] = (data.prediction - data.y) ** 2
    train, *_ = load_data(ROOT / "data/raw/challenge")
    station = {int(s): g.set_index("target_start").pm25.sort_index() for s, g in train.groupby("location_id")}
    fallback = {}
    for gap, fold, station_id in data[["gap_hours", "fold_id", "location_id"]].drop_duplicates().itertuples(index=False):
        series = station[int(station_id)]
        eligible = series.loc[series.index < fold].dropna()
        if eligible.empty:
            raise ValueError("Scored row has no eligible station history")
        for hours in (24, 48, 72):
            fallback[(gap, fold, station_id, hours)] = not (eligible.index >= fold-pd.Timedelta(hours=hours)).any()
    def fallback_for(row: pd.Series) -> bool:
        hours = 24 if row.model in ("median24", "hybrid_w50_m24") else 48 if row.model in ("median48", "trend48") else 72
        return fallback[(row.gap_hours, row.fold_id, row.location_id, hours)]
    data["recent_fallback"] = data.apply(fallback_for, axis=1)
    grouped = data.groupby(["partition", "gap_hours", "model"])
    diagnostic = grouped.apply(lambda x: pd.Series({
        "rows": len(x), "extreme_n_ge500": int((x.y >= 500).sum()),
        "extreme_sse_pct": 100 * x.loc[x.y >= 500, "square"].sum() / x.square.sum(),
        "actual_gap_min_h": x.pm_gap_hours.min(), "actual_gap_median_h": x.pm_gap_hours.median(),
        "actual_gap_max_h": x.pm_gap_hours.max(),
        "recent_window_fallback_pct": 100 * x.recent_fallback.mean(),
        "prediction_mean": x.prediction.mean(), "prediction_median": x.prediction.median(),
    }), include_groups=False).reset_index()
    out = ROOT / "reports/ml_pipeline/exp_012"
    diagnostic.to_csv(out / "CANDIDATE_DIAGNOSTICS.csv", index=False)
    # Add the competition-style 192h fold audit to the standard-gap fold audit.
    old = pd.read_csv(out / "FOLD_QUALITY.csv")
    new_rows = []
    q = data[(data.gap_hours.eq(192)) & data.model.eq("legacy_w50")]
    for fold, g in q.groupby("fold_id"):
        y = g.y.to_numpy()
        squared = g.square.to_numpy()
        available = train.loc[train.target_start + pd.Timedelta(hours=1) <= fold]
        new_rows.append({"gap_hours": 192, "fold_id": fold.isoformat(),
                         "target_first": g.target_start.min().isoformat(),
                         "target_last": g.target_start.max().isoformat(),
                         "target_rows": len(g), "station_count": g.location_id.nunique(),
                         "target_min": np.min(y), "target_median": np.median(y),
                         "target_mean": np.mean(y), "target_max": np.max(y),
                         **{f"n_gt_{k}": int((y > k).sum()) for k in (100,250,500,1000,10000)},
                         "sse_gt500_pct": 100*squared[y>500].sum()/squared.sum(),
                         "actual_gap_min_h": g.pm_gap_hours.min(),
                         "actual_gap_median_h": g.pm_gap_hours.median(),
                         "actual_gap_max_h": g.pm_gap_hours.max(),
                         "available_pm_rows": len(available),
                         "november_target_rows": int(g.target_start.dt.month.eq(11).sum()),
                         "private_style_lead": True})
    pd.concat([old, pd.DataFrame(new_rows)], ignore_index=True).to_csv(out / "FOLD_QUALITY.csv", index=False)
    print(f"diagnostics {len(diagnostic)} rows; 192h fold audit {len(new_rows)} folds")


if __name__ == "__main__":
    main()
