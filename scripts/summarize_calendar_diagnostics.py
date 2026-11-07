"""Summarize EXP-011 matched row predictions without rerunning folds."""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/ml_pipeline/exp_011"
KEY = ["partition", "gap_hours", "fold_id", "location_id", "target_start"]


def main() -> None:
    data = pd.read_csv(ROOT / "data/processed/exp011_row_predictions.csv.gz")
    data["squared"] = (data.prediction - data.y) ** 2
    diagnostic = data.groupby(["partition", "gap_hours", "model"]).apply(
        lambda x: pd.Series({
            "rows": len(x), "actual_gap_median_h": x.pm_gap_hours.median(),
            "actual_gap_min_h": x.pm_gap_hours.min(), "actual_gap_max_h": x.pm_gap_hours.max(),
            "extreme_rows_ge500": int((x.y >= 500).sum()),
            "extreme_sse_pct": 100 * x.loc[x.y >= 500, "squared"].sum() / x.squared.sum(),
            "fallback_pct": 100 * x.fallback.mean(),
        }), include_groups=False,
    ).reset_index()
    diagnostic.to_csv(OUT / "DIAGNOSTICS.csv", index=False)
    november = data.loc[pd.to_datetime(data.target_start).dt.month.eq(11)]
    november.groupby(["partition", "gap_hours", "model"]).apply(
        lambda x: pd.Series({"rows": len(x), "rmse": np.sqrt(np.mean((x.prediction - x.y) ** 2)),
                             "mae": np.mean(np.abs(x.prediction - x.y))}),
        include_groups=False,
    ).reset_index().to_csv(OUT / "NOVEMBER_METRICS.csv", index=False)
    old = data[data.model.eq("legacy_w50")][KEY + ["prediction"]]
    new = data[data.model.eq("calendar365_w50")][KEY + ["prediction"]]
    paired = old.merge(new, on=KEY, suffixes=("_old", "_new"), validate="one_to_one")
    paired.groupby(["partition", "gap_hours"]).apply(
        lambda x: pd.Series({"rows": len(x),
                             "changed_pct": 100 * (x.prediction_old != x.prediction_new).mean(),
                             "mean_abs_prediction_delta": np.mean(np.abs(x.prediction_old - x.prediction_new)),
                             "max_abs_prediction_delta": np.max(np.abs(x.prediction_old - x.prediction_new))}),
        include_groups=False,
    ).reset_index().to_csv(OUT / "PAIRED_DIFFERENCES.csv", index=False)
    print("wrote diagnostics, November metrics and paired differences")


if __name__ == "__main__":
    main()
