"""In-memory public/private CatBoost Huber forecast diagnostic; no CSV submission."""
from __future__ import annotations

import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mumbai_pm25.data import load_data
from mumbai_pm25.forecast import derive_pm_history_cutoff, predict_test_with_hist24_blend
from mumbai_pm25.historical_archive import load_2024_history
from mumbai_pm25.supervised import (
    FEATURE_COLUMNS,
    add_seasonal_and_baseline,
    build_examples,
    candidate_model,
    make_origin,
    origin_features,
)


def main() -> None:
    raw = ROOT / "data/raw/challenge"
    train, test, sample, stations = load_data(raw)
    archive = load_2024_history(raw / "AdditionalHistory.zip")
    cutoff = derive_pm_history_cutoff(train)
    station_ids = tuple(sorted(int(v) for v in stations.location_id))
    first_day = train.target_start.min().ceil("D") + pd.Timedelta(days=16)
    last_day = train.target_start.max().normalize() - pd.Timedelta(days=2)
    days = pd.date_range(first_day, last_day, freq="7D")
    examples = build_examples(train, archive, days, station_ids)
    training = examples.loc[examples.target_end <= cutoff]
    model = candidate_model("catboost_huber")
    model.fit(training[list(FEATURE_COLUMNS)], training.y.to_numpy(dtype=float))
    restored = pickle.loads(pickle.dumps(model))
    parts = []
    for day_text, regime in (("2026-11-03", "public"), ("2026-11-11", "private")):
        day = pd.Timestamp(day_text, tz="Asia/Kolkata")
        target = test.loc[test.target_start.between(
            day, day+pd.Timedelta(hours=48), inclusive="left")]
        origin = make_origin(day, regime)
        if origin.pm_cutoff != cutoff or len(target) != 192:
            raise ValueError("Live snapshot or target grid differs from EXP-014 design")
        features = add_seasonal_and_baseline(
            origin_features(train, target, origin, station_ids), archive)
        if len(features) != len(target):
            raise ValueError("Missing public/private station predictions")
        direct = model.predict(features[list(FEATURE_COLUMNS)])
        roundtrip = restored.predict(features[list(FEATURE_COLUMNS)])
        np.testing.assert_array_equal(direct, roundtrip)
        prediction = np.maximum(np.asarray(direct, dtype=float), 0.0)
        if not np.isfinite(prediction).all():
            raise ValueError("Non-finite challenger prediction")
        features["candidate"] = prediction
        features["regime"] = regime
        parts.append(features.merge(target[["location_id", "target_start", "ID"]],
                                    on=["location_id", "target_start"],
                                    validate="one_to_one"))
    comparison = pd.concat(parts, ignore_index=True)
    baseline = predict_test_with_hist24_blend(
        train, test, archive, issue_time=pd.Timestamp("2026-11-07T12:00:00+05:30"),
        pm_history_cutoff=cutoff)
    if baseline.ID.tolist() != sample.ID.tolist():
        raise ValueError("W50 submission order differs from sample")
    comparison = comparison.merge(baseline, on="ID", validate="one_to_one")
    if not np.array_equal(comparison.w50.to_numpy(), comparison.Target.to_numpy()):
        raise ValueError("Supervised W50 feature differs from production inference")
    summary = {}
    for (regime, station), group in comparison.groupby(["regime", "location_id"]):
        difference = (group.candidate - group.Target).abs()
        summary[f"{regime}:{station}"] = {
            "rows": len(group), "changed": int((difference > 0).sum()),
            "mean_absolute_difference": float(difference.mean()),
            "max_absolute_difference": float(difference.max()),
            "prediction_min": float(group.candidate.min()),
            "prediction_median": float(group.candidate.median()),
            "prediction_max": float(group.candidate.max()),
        }
    output = ROOT / "reports/ml_pipeline/exp_014/INFERENCE_DIAGNOSTIC.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"in-memory rows={len(comparison)} changed="
          f"{int((comparison.candidate != comparison.Target).sum())} "
          f"range={comparison.candidate.min():.3f}-{comparison.candidate.max():.3f} "
          "W50 parity exact; model serialization exact; no CSV saved")


if __name__ == "__main__":
    main()
