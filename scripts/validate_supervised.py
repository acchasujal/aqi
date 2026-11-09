"""Bounded EXP-014 rolling-origin comparison on current public/private leads."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mumbai_pm25.data import load_data
from mumbai_pm25.historical_archive import load_2024_history
from mumbai_pm25.supervised import FEATURE_COLUMNS, build_examples, fit_predict

MODELS = ("lightgbm", "catboost", "catboost_huber", "hist_gradient_boosting",
          "lightgbm_residual")
KEY = ["regime", "prediction_origin", "location_id", "target_start"]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def score(frame: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    data = frame.assign(error=frame.prediction-frame.y)
    data["squared"] = data.error**2
    grouped = data.groupby(keys, dropna=False)
    result = grouped.agg(rows=("y", "size"),
                         rmse=("squared", lambda x: float(np.sqrt(x.mean()))),
                         mae=("error", lambda x: float(x.abs().mean())),
                         median_ae=("error", lambda x: float(x.abs().median())),
                         bias=("error", "mean"),
                         extreme_rows=("y", lambda x: int((x >= 500).sum())),
                         prediction_min=("prediction", "min"),
                         prediction_median=("prediction", "median"),
                         prediction_max=("prediction", "max")).reset_index()
    clean = data.loc[data.y < 500].groupby(keys).squared.mean().pow(.5).rename("clean_rmse")
    return result.merge(clean.reset_index(), on=keys, how="left", validate="one_to_one")


def validation_days(days: pd.DatetimeIndex, smoke: bool) -> list[pd.Timestamp]:
    """Fixed, sparse development origins plus November-like checks."""
    candidates = list(days[24::10])
    november = [day for day in days if day.year == 2025 and day.month == 11]
    candidates.extend(november[:2])
    october = [day for day in days if day.year == 2026 and day.month == 10]
    candidates.extend(october[-1:])
    # Known prior-audit extreme periods are fixed stress folds, not fresh
    # confirmation or hyperparameter-selection dates.
    stress_dates = {"2025-08-09", "2026-05-09"}
    candidates.extend(day for day in days if day.strftime("%Y-%m-%d") in stress_dates)
    selected = sorted(set(candidates))
    if smoke:
        return selected[:2]
    return selected


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    raw = ROOT / "data/raw/challenge"
    out = ROOT / ("data/processed/exp014_smoke" if args.smoke else "reports/ml_pipeline/exp_014")
    out.mkdir(parents=True, exist_ok=True)
    train, _, _, stations = load_data(raw)
    archive = load_2024_history(raw / "AdditionalHistory.zip")
    if archive.hour_start.max() >= train.target_start.min():
        raise ValueError("2024 archive does not predate all supervised examples")
    first_day = train.target_start.min().ceil("D") + pd.Timedelta(days=16)
    last_day = train.target_start.max().normalize() - pd.Timedelta(days=2)
    days = pd.date_range(first_day, last_day, freq="7D")
    station_ids = tuple(sorted(int(v) for v in stations.location_id))
    examples = build_examples(train, archive, days, station_ids)
    if not set(FEATURE_COLUMNS) <= set(examples.columns):
        raise ValueError("Supervised feature schema incomplete")
    if examples.duplicated(KEY).any():
        raise ValueError("Duplicate supervised example key")
    chosen = validation_days(days, args.smoke)
    output = []
    coverage = []
    for day in chosen:
        for regime in ("public", "private"):
            val = examples.loc[examples.target_start.between(
                day, day + pd.Timedelta(hours=48), inclusive="left") &
                examples.regime.eq(regime)].copy()
            if val.empty:
                continue
            cutoff = val.pm_history_cutoff.iloc[0]
            eligible = examples.loc[examples.target_end <= cutoff].copy()
            # A purged training example's label must end before the validation
            # PM cutoff, including examples from the opposite lead regime.
            if (eligible.target_end > cutoff).any() or (val.target_start < val.prediction_origin).any():
                raise ValueError("Chronological training or validation clock violation")
            if len(eligible) < 500:
                continue
            coverage.append({"target_day": day, "regime": regime,
                             "training_rows": len(eligible), "scoring_rows": len(val),
                             "stations": val.location_id.nunique(),
                             "actual_lead_min": val.actual_lead_hours.min(),
                             "actual_lead_max": val.actual_lead_hours.max()})
            columns = KEY + ["pm_history_cutoff", "target_end", "lead_hours",
                             "actual_lead_hours", "y"]
            base = val[columns].copy()
            base["model"] = "w50"
            base["prediction"] = val.w50.to_numpy()
            output.append(base)
            for name in MODELS:
                pred = fit_predict(name, eligible, val)
                part = val[columns].copy()
                part["model"] = name
                part["prediction"] = pred
                output.append(part)
            print(f"{day.date()} {regime}: fit={len(eligible)} score={len(val)}", flush=True)
    if not output:
        raise ValueError("No validation folds met training and scoring eligibility")
    oof = pd.concat(output, ignore_index=True)
    per_model = oof.groupby(KEY).model.nunique()
    if not per_model.eq(len(MODELS)+1).all():
        raise ValueError("Candidates were not scored on identical rows")
    oof.to_csv(ROOT / "data/processed/exp014_oof.csv.gz", index=False, compression="gzip")
    horizon_results = score(oof, ["regime", "model"])
    horizon_results.to_csv(out / "HORIZON_RESULTS.csv", index=False)
    for regime, filename in (("public", "PUBLIC_HORIZON_RESULTS.csv"),
                             ("private", "PRIVATE_HORIZON_RESULTS.csv")):
        horizon_results.loc[horizon_results.regime.eq(regime)].to_csv(out / filename, index=False)
    score(oof, ["regime", "model", "prediction_origin"]).to_csv(out / "FOLD_RESULTS.csv", index=False)
    score(oof, ["regime", "model", "location_id"]).to_csv(out / "STATION_RESULTS.csv", index=False)
    score(oof, ["regime", "model", "lead_hours"]).to_csv(out / "LEAD_RESULTS.csv", index=False)
    score(oof.loc[oof.target_start.dt.month.eq(11)], ["regime", "model"]).to_csv(
        out / "NOVEMBER_RESULTS.csv", index=False)
    pd.DataFrame(coverage).to_csv(out / "FOLD_COVERAGE.csv", index=False)
    examples.groupby(["regime", "location_id", examples.prediction_origin.dt.strftime("%Y-%m")],
                     observed=True).size().rename("rows").reset_index().to_csv(
                         out / "EXAMPLE_COUNTS.csv", index=False)
    metadata = {"train_sha256": sha(raw / "Train.csv"),
                "archive_sha256": sha(raw / "AdditionalHistory.zip"),
                "seed": 42, "feature_schema": list(FEATURE_COLUMNS),
                "training_example_rows": len(examples),
                "selected_target_days": [day.isoformat() for day in chosen],
                "validation_fold_count": len(coverage),
                "validation_rows_per_model": len(oof)//(len(MODELS)+1),
                "reused_evidence": True}
    (out / "RUN_METADATA.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(f"completed folds={len(coverage)} rows/model={metadata['validation_rows_per_model']}")


if __name__ == "__main__":
    main()
