"""Reproduce leakage-safe schedule-baseline comparisons from the frozen replay."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

from scipy.stats import binomtest, t

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPLAY = ROOT / "apps/airwindow/public/data/replay.json"
DEFAULT_OUTPUT = ROOT / "apps/airwindow/public/data/baseline_comparison.json"
BOOTSTRAPS = 2_000
SEED = 20261111
ORIGIN_TIE_TOLERANCE = 0.01


def _cleanest_start(history: list[dict[str, Any]], station: str, duration: int) -> str | None:
    values: dict[str, list[float]] = defaultdict(list)
    for case in history:
        if case["station_id"] != station or case["duration_hours"] != duration:
            continue
        for window in case["windows"]:
            observed = window["mean_observed"]
            if observed is not None and math.isfinite(observed):
                values[window["start_ist"][11:16]].append(float(observed))
    if not values:
        return None
    return min(values, key=lambda start: (sum(values[start]) / len(values[start]), start))


def _case_deltas(cases: list[dict[str, Any]], baseline: str) -> dict[str, Any]:
    pairs: list[tuple[str, float, float]] = []
    for case in cases:
        aw = case["selected"].get("mean_observed")
        if baseline == "latest":
            target = max(case["windows"], key=lambda window: window["start_ist"])
        elif baseline == "usual_cleanest":
            target = case.get("_usual_cleanest_window")
            if target is None:
                continue
        else:
            raise ValueError(f"Unknown baseline: {baseline}")
        other = target.get("mean_observed")
        if aw is None or other is None or not math.isfinite(aw) or not math.isfinite(other):
            continue
        pairs.append((case["fold_id"], float(aw), float(other)))
    if not pairs:
        return {"paired_cases": 0, "origins": 0, "airwindow_mean": None,
                "baseline_mean": None, "mean_delta": None, "median_delta": None,
                "cluster_bootstrap_95": [None, None], "direction": "unavailable",
                "origin_level": {"tie_tolerance": ORIGIN_TIE_TOLERANCE,
                                 "favor_airwindow": 0, "favor_baseline": 0, "ties": 0,
                                 "equal_origin_mean_delta": None, "student_t_95": [None, None],
                                 "exact_sign_test_two_sided_p": None}}

    clusters: dict[str, list[float]] = defaultdict(list)
    for origin, aw, base in pairs:
        clusters[origin].append(aw - base)
    origin_ids = sorted(clusters)
    origin_means = [statistics.fmean(clusters[origin]) for origin in origin_ids]
    favor_airwindow = sum(value < -ORIGIN_TIE_TOLERANCE for value in origin_means)
    favor_baseline = sum(value > ORIGIN_TIE_TOLERANCE for value in origin_means)
    ties = len(origin_means) - favor_airwindow - favor_baseline
    non_ties = favor_airwindow + favor_baseline
    equal_origin_mean = statistics.fmean(origin_means)
    if len(origin_means) >= 2:
        sem = statistics.stdev(origin_means) / math.sqrt(len(origin_means))
        critical = float(t.ppf(0.975, df=len(origin_means) - 1))
        t_interval = [equal_origin_mean - critical * sem, equal_origin_mean + critical * sem]
    else:
        t_interval = [None, None]
    sign_p = float(binomtest(favor_airwindow, non_ties, p=0.5, alternative="two-sided").pvalue) if non_ties else None
    point = sum(delta for _, aw, base in pairs for delta in [aw - base]) / len(pairs)
    rng = __import__("random").Random(SEED)
    boot = []
    for _ in range(BOOTSTRAPS):
        sampled = [rng.choice(origin_ids) for _ in origin_ids]
        values = [value for origin in sampled for value in clusters[origin]]
        boot.append(sum(values) / len(values))
    boot.sort()
    lo, hi = boot[int(0.025 * BOOTSTRAPS)], boot[int(0.975 * BOOTSTRAPS) - 1]
    direction = "interval_below_zero" if hi < 0 else "interval_above_zero" if lo > 0 else "interval_includes_zero"
    return {
        "paired_cases": len(pairs), "origins": len(origin_ids),
        "airwindow_mean": sum(aw for _, aw, _ in pairs) / len(pairs),
        "baseline_mean": sum(base for _, _, base in pairs) / len(pairs),
        "mean_delta": point,
        "median_delta": statistics.median(aw - base for _, aw, base in pairs),
        "cluster_bootstrap_95": [lo, hi], "direction": direction,
        "origin_level": {
            "tie_tolerance": ORIGIN_TIE_TOLERANCE,
            "favor_airwindow": favor_airwindow,
            "favor_baseline": favor_baseline,
            "ties": ties,
            "equal_origin_mean_delta": equal_origin_mean,
            "student_t_95": t_interval,
            "exact_sign_test_two_sided_p": sign_p,
        },
    }


def calculate(replay: dict[str, Any], source_sha256: str | None = None) -> dict[str, Any]:
    cases = replay["cases"]
    origins = sorted({case["fold_id"] for case in cases})
    by_origin: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for case in cases:
        by_origin[case["fold_id"]].append(case)

    # Expanding, strictly prior-origin baseline selection for full-replay results.
    prior: list[dict[str, Any]] = []
    full_cases: list[dict[str, Any]] = []
    full_supported = 0
    for origin in origins:
        current = by_origin[origin]
        for case in current:
            start = _cleanest_start(prior, case["station_id"], case["duration_hours"])
            case_copy = dict(case)
            case_copy["_usual_cleanest_window"] = next(
                (window for window in case["windows"] if window["start_ist"][11:16] == start), None
            ) if start else None
            if case_copy["_usual_cleanest_window"] is not None:
                full_supported += 1
            full_cases.append(case_copy)
        prior.extend(current)

    development = [case for case in cases if case["split"] == "development"]
    heldout = [case for case in cases if case["split"] == "confirmation"]
    heldout_slots = {
        f"{station}:{duration}": _cleanest_start(development, station, duration)
        for station in sorted({case["station_id"] for case in heldout})
        for duration in sorted({case["duration_hours"] for case in heldout if case["station_id"] == station})
    }
    heldout_cases: list[dict[str, Any]] = []
    heldout_supported = 0
    for case in heldout:
        start = _cleanest_start(development, case["station_id"], case["duration_hours"])
        case_copy = dict(case)
        case_copy["_usual_cleanest_window"] = next(
            (window for window in case["windows"] if window["start_ist"][11:16] == start), None
        ) if start else None
        if case_copy["_usual_cleanest_window"] is not None:
            heldout_supported += 1
        heldout_cases.append(case_copy)

    def panel(rows: list[dict[str, Any]], supported: int) -> dict[str, Any]:
        return {
            "cases": len(rows),
            "usual_cleanest_supported_cases": supported,
            "usual_cleanest": _case_deltas(rows, "usual_cleanest"),
            "latest_window": _case_deltas(rows, "latest"),
        }

    return {
        "schema_version": "1.0.0",
        "title": "Retrospective event-window baselines",
        "source_replay_sha256": source_sha256 or hashlib.sha256(
            json.dumps(replay, separators=(",", ":"), ensure_ascii=False).encode()
        ).hexdigest(),
        "method": {
            "outcome": "paired mean observed PM2.5 for the same station, duration and replay case; lower is better",
            "airwindow": "forecast-ranked window retained in the replay artifact, selected without using outcomes",
            "usual_cleanest": "window start with the lowest mean observed PM2.5 in eligible earlier origins; confirmation uses development origins only",
            "latest_window": "latest-starting complete forecast window in each case's pre-ranked feasible set",
            "full_replay": "expanding-origin evaluation; baseline start is learned only from earlier origins",
            "heldout": "confirmation split; usual-cleanest start learned from development outcomes only",
            "interval": f"percentile 95% cluster bootstrap of paired mean deltas, resampling whole forecast origins ({BOOTSTRAPS} replicates, seed {SEED}); negative favors AirWindow",
            "origin_level": f"Each origin's statistic is its mean paired case delta (AirWindow minus baseline); origins with means below -{ORIGIN_TIE_TOLERANCE} µg/m³ favor AirWindow, above +{ORIGIN_TIE_TOLERANCE} favor the baseline, otherwise tie. Equal-origin Student-t interval uses origin means (df = origins - 1); exact two-sided sign test excludes ties. Sensitivity analyses, not superiority tests.",
            "missingness": "only paired cases with both subsequent observed means are scored; missing outcomes are excluded from the paired estimate and retained in coverage counts",
        },
        "full_replay": panel(full_cases, full_supported),
        "heldout": panel(heldout_cases, heldout_supported),
        "heldout_usual_cleanest_start_by_station_duration": heldout_slots,
        "limitations": [
            "Retrospective evidence, not a guarantee of future performance.",
            "The held-out confirmation origins were previously inspected by analysts and are not independent calibration.",
            "A confidence interval spanning zero does not establish superiority; overlapping cases within origins are dependent.",
            "A fixed usual-cleanest time is a simple schedule baseline and may not represent a coordinator's genuine routine.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay", type=Path, default=DEFAULT_REPLAY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    raw = args.replay.read_bytes()
    replay = json.loads(raw)
    result = calculate(replay, hashlib.sha256(raw).hexdigest())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("full_replay", "heldout")}, indent=2))


if __name__ == "__main__":
    main()
