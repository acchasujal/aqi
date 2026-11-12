"""Verify committed creative artifacts and execute the replay notebook locally.

Run from any directory. Does not train, refresh forecasts or load raw targets.
"""
from __future__ import annotations

import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from apps.airwindow.baseline_comparison import calculate as calculate_baseline
from apps.airwindow.contract_validation import validate_artifact
from apps.airwindow.replay_validation import validate_replay


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def same_metrics(actual: object, expected: object) -> bool:
    """Preserve exact structure while tolerating 1e-12 floating-point drift."""
    if isinstance(expected, dict):
        return isinstance(actual, dict) and actual.keys() == expected.keys() and all(
            same_metrics(actual[key], expected[key]) for key in expected
        )
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(
            same_metrics(value, reference) for value, reference in zip(actual, expected, strict=True)
        )
    if isinstance(expected, float):
        return isinstance(actual, float) and math.isclose(actual, expected, rel_tol=0, abs_tol=1e-12)
    return actual == expected


def main() -> None:
    data = ROOT / "apps/airwindow/public/data"
    manifest = json.loads((data / "manifest.json").read_text(encoding="utf-8"))
    for name, validator in (("forecast", validate_artifact), ("replay", validate_replay)):
        path = data / f"{name}.json"
        if sha256(path) != manifest[f"{name}_sha256"]:
            raise ValueError(f"{name} bytes differ from manifest")
        validator(json.loads(path.read_text(encoding="utf-8")))
    if "fallback_forecast_file" in manifest:
        fallback = data / manifest["fallback_forecast_file"]
        if sha256(fallback) != manifest["fallback_forecast_sha256"]:
            raise ValueError("fallback forecast bytes differ from manifest")
        fallback_artifact = json.loads(fallback.read_text(encoding="utf-8"))
        if fallback_artifact["model_issue_time_ist"] != "2026-11-08T15:58:00+05:30":
            raise ValueError("fallback forecast is not the original TASK008 snapshot")
    forecast = json.loads((data / "forecast.json").read_text(encoding="utf-8"))
    for key, actual in (("forecast_issue_time_ist", forecast["model_issue_time_ist"]),
                        ("forecast_pm_history_cutoff_ist", forecast["pm_history_cutoff_ist"]),
                        ("forecast_generated_at_ist", forecast["generated_at_ist"])):
        if key in manifest and manifest[key] != actual:
            raise ValueError(f"forecast clock differs from manifest: {key}")
    baseline_path = data / "baseline_comparison.json"
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    if sha256(baseline_path) != manifest["baseline_comparison_sha256"]:
        raise ValueError("baseline comparison bytes differ from manifest")
    if baseline["source_replay_sha256"] != manifest["replay_sha256"]:
        raise ValueError("baseline comparison does not fingerprint the replay artifact")
    if baseline["full_replay"]["cases"] != manifest["replay_summary"]["cases"]:
        raise ValueError("baseline comparison coverage differs from replay manifest")
    replay_raw = (data / "replay.json").read_bytes()
    replay_obj = json.loads(replay_raw)
    reproduced = calculate_baseline(replay_obj, hashlib.sha256(replay_raw).hexdigest())
    if not same_metrics(reproduced, baseline):
        raise ValueError("baseline comparison metrics differ from deterministic replay calculation")
    folder = ROOT / "reports/creative_submission"
    audit = json.loads((folder / "AIRWINDOW_2_SUBMISSION.audit.json").read_text(encoding="utf-8"))
    pdf = folder / "AIRWINDOW_2_SUBMISSION.pdf"
    if sha256(pdf) != audit["sha256"] or pdf.stat().st_size != audit["bytes"] or pdf.stat().st_size >= 10_000_000:
        raise ValueError("Submission PDF hash/size audit failed")
    for name, expected in audit["source_screenshot_sha256"].items():
        # Audits made on Windows may contain backslashes even on Colab/Linux.
        if sha256(ROOT / name.replace("\\", "/")) != expected:
            raise ValueError(f"PDF source capture changed: {name}")
    notebook = json.loads((ROOT / "apps/airwindow/notebooks/Decision_Replay.ipynb").read_text(encoding="utf-8"))
    source_cells = ["".join(c["source"]) for c in notebook["cells"] if c["cell_type"] == "code"]
    # Run all cells in one isolated interpreter with an explicit checkout cwd.
    # No caller working-directory assumption and no persistent notebook output.
    subprocess.run([sys.executable, "-c", "\n\n".join(source_cells)],
                   cwd=ROOT, check=True, capture_output=True, text=True)
    print(json.dumps({"forecast_sha256": manifest["forecast_sha256"],
                      "replay_sha256": manifest["replay_sha256"],
                      "baseline_comparison_sha256": manifest["baseline_comparison_sha256"],
                      "pdf_sha256": audit["sha256"], "pdf_bytes": audit["bytes"],
                      "notebook_code_cells_executed": len(source_cells),
                      "replay_summary": manifest["replay_summary"],
                      "cloud_execution": "not performed", "result": "PASS"}, indent=2))


if __name__ == "__main__":
    main()
