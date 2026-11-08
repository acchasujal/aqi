"""Verify committed creative artifacts and execute the replay notebook locally.

Run from any directory. Does not train, refresh forecasts or load raw targets.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from apps.airwindow.contract_validation import validate_artifact
from apps.airwindow.replay_validation import validate_replay


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    data = ROOT / "apps/airwindow/public/data"
    manifest = json.loads((data / "manifest.json").read_text(encoding="utf-8"))
    for name, validator in (("forecast", validate_artifact), ("replay", validate_replay)):
        path = data / f"{name}.json"
        if sha256(path) != manifest[f"{name}_sha256"]:
            raise ValueError(f"{name} bytes differ from manifest")
        validator(json.loads(path.read_text(encoding="utf-8")))
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
                      "pdf_sha256": audit["sha256"], "pdf_bytes": audit["bytes"],
                      "notebook_code_cells_executed": len(source_cells),
                      "replay_summary": manifest["replay_summary"],
                      "cloud_execution": "not performed", "result": "PASS"}, indent=2))


if __name__ == "__main__":
    main()
