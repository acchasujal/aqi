"""EXP-012 fold-quality audit from the accepted EXP-011 matched OOF cache."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mumbai_pm25.data import load_data  # noqa: E402


def main() -> None:
    cache = ROOT / "data/processed/exp011_row_predictions.csv.gz"
    if not cache.exists():
        raise FileNotFoundError("Regenerate EXP-011 OOF with scripts/validate_calendar_alignment.py")
    oof = pd.read_csv(cache)
    oof = oof[oof.model.eq("legacy_w50")].copy()
    train, *_ = load_data(ROOT / "data/raw/challenge")
    train["target_start"] = pd.to_datetime(train.target_start)
    oof["fold_id"] = pd.to_datetime(oof.fold_id)
    oof["target_start"] = pd.to_datetime(oof.target_start)
    rows = []
    for (gap, fold), g in oof.groupby(["gap_hours", "fold_id"]):
        y = g.y.to_numpy(dtype=float)
        squared = (g.prediction.to_numpy(dtype=float) - y) ** 2
        available = train.loc[train.target_start + pd.Timedelta(hours=1) <= fold]
        rows.append({"gap_hours": gap, "fold_id": fold.isoformat(),
                     "target_first": g.target_start.min().isoformat(),
                     "target_last": g.target_start.max().isoformat(),
                     "target_rows": len(g), "station_count": g.location_id.nunique(),
                     "target_min": np.min(y), "target_median": np.median(y),
                     "target_mean": np.mean(y), "target_max": np.max(y),
                     **{f"n_gt_{threshold}": int((y > threshold).sum())
                        for threshold in (100, 250, 500, 1000, 10000)},
                     "sse_gt500_pct": 100 * squared[y > 500].sum() / squared.sum(),
                     "actual_gap_min_h": g.pm_gap_hours.min(),
                     "actual_gap_median_h": g.pm_gap_hours.median(),
                     "actual_gap_max_h": g.pm_gap_hours.max(),
                     "available_pm_rows": len(available),
                     "november_target_rows": int(g.target_start.dt.month.eq(11).sum()),
                     "private_style_lead": 192 <= gap <= 240})
    out = ROOT / "reports/ml_pipeline/exp_012"
    out.mkdir(parents=True, exist_ok=True)
    result = pd.DataFrame(rows)
    result.to_csv(out / "FOLD_QUALITY.csv", index=False)
    nov = result[result.november_target_rows.gt(0)]
    (out / "VALIDATION_DIAGNOSTICS.md").write_text(
        "# EXP-012 validation diagnostics\n\n"
        f"Audited {len(result)} `(gap, fold)` combinations from EXP-011 accepted legacy W50 OOF. "
        "All raw target labels were retained. Fold-level detail is in `FOLD_QUALITY.csv`.\n\n"
        f"November-containing combinations: {len(nov)}; labelled November rows counted across gaps: "
        f"{int(nov.november_target_rows.sum())}. These reuse the same historical dates across gaps "
        "and are not independent. November 2026 in Train ends November 2, leaving no comparable "
        "November 11–12 2026 labels. The strongest analogous period is November 2025, but one year "
        "cannot establish stable seasonal generalization.\n\n"
        f"Maximum fold target: {result.target_max.max():.3f} µg/m³. "
        f"Folds with targets >500: {int(result.n_gt_500.gt(0).sum())}. "
        f"Maximum extreme squared-error contribution in one fold: {result.sse_gt500_pct.max():.2f}%. "
        "The official comparison remains full-target RMSE; ordinary-range RMSE is diagnostic only.\n",
        encoding="utf-8")
    print(f"audited {len(result)} fold-gap combinations; November-containing {len(nov)}")


if __name__ == "__main__":
    main()
