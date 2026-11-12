from __future__ import annotations

import hashlib
import json
from pathlib import Path

from apps.airwindow.audit_release import same_metrics
from apps.airwindow.baseline_comparison import calculate

ROOT = Path(__file__).resolve().parents[1]


def _replay() -> dict:
    return json.loads((ROOT / "apps/airwindow/public/data/replay.json").read_text(encoding="utf-8"))


def test_baseline_results_reproduce_committed_artifact() -> None:
    replay = _replay()
    replay_path = ROOT / "apps/airwindow/public/data/replay.json"
    expected = json.loads((ROOT / "apps/airwindow/public/data/baseline_comparison.json").read_text(encoding="utf-8"))
    assert same_metrics(calculate(replay, hashlib.sha256(replay_path.read_bytes()).hexdigest()), expected)
    assert expected["full_replay"]["usual_cleanest"]["paired_cases"] == 1414
    assert expected["heldout"]["latest_window"]["cluster_bootstrap_95"] == [-2.659286659108088, 0.16387225115740733]
    usual = expected["heldout"]["usual_cleanest"]["origin_level"]
    latest = expected["heldout"]["latest_window"]["origin_level"]
    assert (usual["favor_airwindow"], usual["favor_baseline"], usual["ties"]) == (4, 4, 0)
    assert (latest["favor_airwindow"], latest["favor_baseline"], latest["ties"]) == (5, 3, 0)
    assert usual["tie_tolerance"] == 0.01
    assert usual["student_t_95"][0] < 0 < usual["student_t_95"][1]
    assert latest["student_t_95"][0] < 0 < latest["student_t_95"][1]
    assert usual["exact_sign_test_two_sided_p"] == 1.0


def test_heldout_cleanest_time_is_selected_from_development_only() -> None:
    replay = _replay()
    original = calculate(replay)["heldout_usual_cleanest_start_by_station_duration"]
    for case in replay["cases"]:
        if case["split"] == "confirmation":
            for window in case["windows"]:
                if window["mean_observed"] is not None:
                    window["mean_observed"] = 500_000.0 - window["mean_observed"]
    changed_outcomes = calculate(replay)
    assert changed_outcomes["heldout_usual_cleanest_start_by_station_duration"] == original
    assert changed_outcomes["heldout"]["usual_cleanest"]["baseline_mean"] != calculate(_replay())["heldout"]["usual_cleanest"]["baseline_mean"]
