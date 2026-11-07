"""Summarize EXP-010 row predictions without rerunning folds."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
rows = ROOT / "data/processed/exp010_row_predictions.csv.gz"
out = ROOT / "reports/ml_pipeline/exp_010/DIAGNOSTICS.csv"


def main() -> None:
    data = pd.read_csv(rows)
    data["squared"] = (data.prediction - data.y) ** 2
    result = data.groupby(["partition", "gap_hours", "weight"]).apply(
        lambda x: pd.Series({
            "rows": len(x),
            "extreme_rows_ge500": int((x.y >= 500).sum()),
            "extreme_sse_pct": float(100 * x.loc[x.y >= 500, "squared"].sum() / x.squared.sum()),
            "actual_gap_median_h": float(x.pm_gap_hours.median()),
            "actual_gap_min_h": float(x.pm_gap_hours.min()),
            "actual_gap_max_h": float(x.pm_gap_hours.max()),
            "fallback_pct": float(100 * x.fallback.mean()),
            "median_ae": float((x.prediction - x.y).abs().median()),
        }), include_groups=False,
    ).reset_index()
    result.to_csv(out, index=False)
    print(f"wrote {len(result)} rows to {out}")


if __name__ == "__main__":
    main()
