"""Reproduce EXP-015 W50 error and bounded historical-history sensitivities."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mumbai_pm25.data import load_data
from mumbai_pm25.legacy_seasonal import build_seasonal_features, load_2024_history

OUT = ROOT / "reports/ml_pipeline/exp_015"
KEY = ["regime", "prediction_origin", "location_id", "target_start"]


def metrics(frame: pd.DataFrame) -> dict:
    err = frame.prediction.to_numpy() - frame.y.to_numpy()
    return {
        "rows": len(frame), "rmse": float(np.sqrt(np.mean(err**2))),
        "mae": float(np.mean(np.abs(err))), "bias": float(np.mean(err)),
        "median_error": float(np.median(err)),
        "clean_rmse_y_lt_500": float(np.sqrt(np.mean(err[frame.y.to_numpy() < 500]**2)))
        if (frame.y < 500).any() else None,
        "extreme_rows": int((frame.y >= 500).sum()),
        "extreme_sse_pct": float(100 * np.sum(err[frame.y.to_numpy() >= 500]**2) / np.sum(err**2)),
    }


def seasonal_sensitivity_from_w50(
    baseline: np.ndarray, original_season: np.ndarray, alternative_season: np.ndarray
) -> np.ndarray:
    """Change only W50's seasonal term, preserving its recent-only fallback."""
    if not (baseline.shape == original_season.shape == alternative_season.shape):
        raise ValueError("Matched predictions and seasonal features require identical shapes")
    recent = np.where(np.isfinite(original_season), 2 * baseline - original_season, baseline)
    return np.where(np.isfinite(alternative_season),
                    0.5 * (recent + alternative_season), recent)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    w50 = pd.read_csv(ROOT / "data/processed/exp014_oof.csv.gz")
    w50 = w50.loc[w50.model.eq("w50")].copy().reset_index(drop=True)
    for field in ("prediction_origin", "target_start", "target_end", "pm_history_cutoff"):
        w50[field] = pd.to_datetime(w50[field], utc=True).dt.tz_convert("Asia/Kolkata")
    train, test, _, _ = load_data(ROOT / "data/raw/challenge")
    archive = load_2024_history(ROOT / "data/raw/challenge/AdditionalHistory.zip")
    assert archive.hour_start.max() < w50.prediction_origin.min(), "Historical prior after origin"
    targets = w50[["location_id", "target_start"]].copy()
    original = build_seasonal_features(archive, targets).hist24_same_hour_mean.to_numpy()
    exclude_mindspace = archive.loc[~archive.station_name.str.contains("Mindspace-Malad", case=False)].copy()
    scenarios = {
        "w50": original,
        "exclude_mindspace": build_seasonal_features(exclude_mindspace, targets).hist24_same_hour_mean.to_numpy(),
    }
    for shift in (-1, 1):
        shifted = archive.copy()
        shifted["hour_start"] += pd.Timedelta(hours=shift)
        scenarios[f"archive_shift_{shift:+d}h"] = build_seasonal_features(
            shifted, targets
        ).hist24_same_hour_mean.to_numpy()
    # W50 is 50:50 when seasonal exists, recent-only otherwise. Recover the
    # recent component algebraically from the audited W50 row prediction.
    baseline = w50.prediction.to_numpy()
    reconstructed = seasonal_sensitivity_from_w50(baseline, original, original)
    if not np.allclose(reconstructed, w50.prediction.to_numpy(), rtol=0, atol=1e-10):
        raise ValueError("W50 decomposition does not reproduce cached predictions")
    records = []
    station_records = []
    fold_records = []
    pred_frames = {}
    for name, season in scenarios.items():
        d = w50.copy()
        d["prediction"] = seasonal_sensitivity_from_w50(baseline, original, season)
        d["model"] = name
        d["season_available"] = np.isfinite(season)
        d["recent_available"] = True
        pred_frames[name] = d
        for regime, sub in d.groupby("regime"):
            for label, part in (("all", sub), ("november", sub.loc[sub.target_start.dt.month.eq(11)])):
                if len(part):
                    records.append({"model": name, "regime": regime, "partition": label, **metrics(part),
                                    "changed_predictions": int(np.sum(~np.isclose(
                                        part.prediction.to_numpy(), w50.loc[part.index, "prediction"].to_numpy()))),
                                    "max_abs_prediction_change": float(np.max(np.abs(
                                        part.prediction.to_numpy() - w50.loc[part.index, "prediction"].to_numpy()))),
                                    "seasonal_fallback_rows": int((~part.season_available).sum())})
            for station, part in sub.groupby("location_id"):
                station_records.append({"model": name, "regime": regime,
                                        "location_id": station, **metrics(part)})
            for origin, part in sub.groupby("prediction_origin"):
                fold_records.append({"model": name, "regime": regime,
                                     "prediction_origin": origin, **metrics(part)})
    result = pd.DataFrame(records)
    result.to_csv(OUT / "TARGETED_EXPERIMENT_RESULTS.csv", index=False)
    pd.DataFrame(station_records).to_csv(OUT / "TARGETED_STATION_RESULTS.csv", index=False)
    pd.DataFrame(fold_records).to_csv(OUT / "TARGETED_FOLD_RESULTS.csv", index=False)
    base = pred_frames["w50"]
    detail = {}
    for regime, sub in base.groupby("regime"):
        detail[regime] = {"overall": metrics(sub),
                          "error_percentiles": {str(p): float(np.percentile(sub.prediction - sub.y, p))
                                                for p in (1, 5, 25, 50, 75, 95, 99)},
                          "by_station": {str(k): metrics(g) for k, g in sub.groupby("location_id")},
                          "by_month": {str(k): metrics(g) for k, g in sub.groupby(sub.target_start.dt.month)},
                          "by_target_hour": {str(k): metrics(g) for k, g in sub.groupby(sub.target_start.dt.hour)},
                          "by_lead_day": {str(k): metrics(g) for k, g in sub.groupby(np.ceil(sub.actual_lead_hours / 24).astype(int))},
                          "by_y_bucket": {str(k): metrics(g) for k, g in sub.groupby(
                              pd.cut(sub.y, [-1, 25, 50, 100, 500, np.inf]), observed=True)},
                          "by_season_availability": {str(k): metrics(g) for k, g in sub.groupby("season_available")}}
    (OUT / "ERROR_DIAGNOSTICS.json").write_text(json.dumps(detail, indent=2), encoding="utf-8")
    events = base.loc[base.y.ge(500), KEY + ["y", "prediction"]].copy()
    events = events.merge(train[["location_id", "target_start", "flag_high_1000", "count", "series_id"]],
                          on=["location_id", "target_start"], validate="many_to_one")
    events.to_csv(OUT / "EXTREME_EVENT_ROWS.csv", index=False)
    # Historical rows can recur under different prediction origins and in prior experiments.
    lineage = {}
    prior_paths = {"exp012": ROOT / "data/processed/exp012_row_predictions.csv.gz",
                   "exp013": ROOT / "data/processed/exp013_row_predictions.csv.gz"}
    current = pd.MultiIndex.from_frame(base[["location_id", "target_start"]])
    for name, path in prior_paths.items():
        old = pd.read_csv(path, usecols=["location_id", "target_start"])
        old["target_start"] = pd.to_datetime(old.target_start, utc=True).dt.tz_convert("Asia/Kolkata")
        keys = pd.MultiIndex.from_frame(old.drop_duplicates())
        lineage[name] = {"prior_unique_station_hours": len(keys),
                         "current_scoring_rows_reused": int(current.isin(keys).sum()),
                         "current_unique_station_hours_reused": int(current.drop_duplicates().isin(keys).sum())}
    lineage["exp014"] = {"scoring_rows": len(base),
                           "unique_station_hours": len(current.drop_duplicates()),
                           "unique_origins": int(base.prediction_origin.nunique()),
                           "repeat_scoring_rows": int(len(base) - len(current.drop_duplicates()))}
    (OUT / "FOLD_LINEAGE.json").write_text(json.dumps(lineage, indent=2), encoding="utf-8")
    # Count current Test predictions touched by a provenance correction without producing a submission.
    target_test = test[["location_id", "target_start"]]
    old = build_seasonal_features(archive, target_test).hist24_same_hour_mean.to_numpy()
    new = build_seasonal_features(exclude_mindspace, target_test).hist24_same_hour_mean.to_numpy()
    changed = np.isfinite(old) & np.isfinite(new) & (~np.isclose(old, new))
    impact = {"test_rows": len(test), "test_rows_changed_exclude_mindspace": int(changed.sum()),
              "malad_test_rows": int(test.location_id.eq(11611).sum()),
              "max_abs_w50_test_change": float(np.max(np.abs(0.5 * (new[changed] - old[changed])))) if changed.any() else 0.0}
    (OUT / "TEST_SENSITIVITY.json").write_text(json.dumps(impact, indent=2), encoding="utf-8")
    print(result.to_string(index=False))
    print("lineage", lineage)
    print("test impact", impact)


if __name__ == "__main__":
    main()
