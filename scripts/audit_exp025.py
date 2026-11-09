"""Pin supplied source code, reproduce C, and score it on frozen TASK008 rows."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from mumbai_pm25.calibration import CLOCKS, validate_oof
from mumbai_pm25.data import load_data
from mumbai_pm25.forecast import derive_pm_history_cutoff, validate_submission
from mumbai_pm25.historical_archive import load_2024_history
from mumbai_pm25.source_candidates import branch_c, branch_seasonal
from scripts.run_exp024 import save_metrics, sha256

BRANCH_COMMIT = "a191dbaf89f3324e8d8fe77542bf8cc70a848b4e"
LOW_REF = "a4afdc56c757ce4138113b423a001275e38c0dff"
LOW_BLOB = "72061108e958a1ad23b90d523f215df7d47357ee"
LOW_TRAIN_BLOB = "a42fee690528a49def992650f89c7dfaf1a3b14b"
LOW_TEST_BLOB = "cecd70446c5de6b89b31c086f01f042d934a4b59"


def git_blob(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()


def matches_crlf_blob(path: Path, expected_blob: str) -> bool:
    """Compare to a published Windows CSV without rewriting either source."""
    canonical = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    return git_blob(canonical) == expected_blob


def git_bytes(path: str) -> bytes:
    return subprocess.run(["git", "show", f"{BRANCH_COMMIT}:{path}"], cwd=ROOT,
                          capture_output=True, check=True).stdout


def snapshot_source(directory: Path) -> dict[str, str]:
    paths = subprocess.run(["git", "ls-tree", "-r", "--name-only", BRANCH_COMMIT,
                            "src/mumbai_pm25"], cwd=ROOT, capture_output=True,
                           text=True, check=True).stdout.splitlines()
    hashes = {}
    for path in paths:
        if not path.endswith(".py"):
            continue
        target = directory / path
        if not target.resolve().is_relative_to(directory.resolve()):
            raise ValueError("Source snapshot path escapes intended directory")
        target.parent.mkdir(parents=True, exist_ok=True)
        content = git_bytes(path)
        target.write_bytes(content)
        hashes[path] = hashlib.sha256(content).hexdigest()
    return hashes


def reproduce_source(snapshot: Path, raw: Path, output: Path, *, model: str) -> None:
    # Run the reviewed original code in a separate interpreter. Do not import
    # its identically named package over the active repository's package.
    program = """
import sys
from pathlib import Path
import pandas as pd
from mumbai_pm25.data import load_data
from mumbai_pm25.historical_archive import load_2024_history
from mumbai_pm25.forecast import predict_test_with_hist24_blend, predict_test_ensemble
train,test,_,_=load_data(Path(sys.argv[1]))
archive=load_2024_history(Path(sys.argv[1])/'AdditionalHistory.zip')
fn=predict_test_with_hist24_blend if sys.argv[3]=='C' else predict_test_ensemble
kw={} if sys.argv[3]=='C' else {'ensemble_type':'robust'}
pred=fn(train,test,archive,issue_time=pd.Timestamp('2026-11-08T12:00:00+05:30'),
        pm_history_cutoff=train.timestamp_ist.max(),**kw)
pred.to_csv(sys.argv[2],index=False)
"""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(snapshot / "src")
    subprocess.run([sys.executable, "-c", program, str(raw), str(output), model],
                   cwd=snapshot, env=env, check=True, capture_output=True, text=True)


def comparison(generated: pd.DataFrame, supplied: Path, test: pd.DataFrame) -> dict:
    original = pd.read_csv(supplied)
    validate_submission(original, test)
    validate_submission(generated, test)
    delta = generated.Target.to_numpy()-original.Target.to_numpy()
    return {"supplied_sha256": sha256(supplied), "rows": len(original),
            "max_absolute_difference": float(np.max(np.abs(delta))),
            "exact_values": bool(np.array_equal(generated.Target, original.Target)),
            "within_1e_10": bool(np.allclose(delta, 0, rtol=0, atol=1e-10))}


def run(supplied: Path, output: Path) -> None:
    if output.exists():
        raise FileExistsError("Choose a new experiment output directory")
    output.mkdir(parents=True)
    cache = ROOT / "data/processed/exp025" / output.name
    if cache.exists():
        raise FileExistsError("Choose a run name with an unused source cache")
    source_hashes = snapshot_source(cache)
    raw = ROOT / "data/raw/challenge"
    old = ROOT / "reports/ml_pipeline/task008/run01"
    original_manifest = json.loads((old / "manifest.json").read_text(encoding="utf-8"))
    raw_hashes = {n: sha256(raw/n) for n in original_manifest["input_hashes"]}
    if raw_hashes != original_manifest["input_hashes"]:
        raise ValueError("Frozen TASK008 raw snapshot mismatch")
    input_parity = {}
    for name in raw_hashes:
        a, b = (raw/name).read_bytes(), git_bytes("data/raw/challenge/"+name)
        input_parity[name] = {"exact_bytes": a == b,
                              "equal_after_crlf_normalization": a.replace(b"\r\n", b"\n") == b.replace(b"\r\n", b"\n")}
    train, test, _, _ = load_data(raw)
    archive = load_2024_history(raw / "AdditionalHistory.zip")
    source_c = cache / "source_C.csv"
    reproduce_source(cache, raw, source_c, model="C")
    c = pd.read_csv(source_c)
    c_comparison = comparison(c, supplied / "submission_C_statistical_seasonal.csv", test)
    independent = branch_c(train, test, branch_seasonal(archive, test), derive_pm_history_cutoff(train))
    if not np.allclose(c.Target, independent, rtol=0, atol=1e-10):
        raise ValueError("Independent candidate C does not reproduce original source")
    b_comparison = {"status": "NOT RUN", "reason": "CatBoost is absent; Windows ARM64 runtime has no native PyPI wheel. No substitute model used."}
    if importlib.util.find_spec("catboost") is not None:
        source_b = cache / "source_B.csv"
        reproduce_source(cache, raw, source_b, model="B")
        b_comparison = {"status": "executed", **comparison(pd.read_csv(source_b), supplied / "submission_B_robust_ensemble.csv", test)}
    audit = json.loads((old / "result_audit.json").read_text(encoding="utf-8"))
    oof = old / "matched_oof.csv.gz"
    if sha256(oof) != audit["output_files_sha256"]["matched_oof.csv.gz"]:
        raise ValueError("Original OOF hash mismatch")
    rows = pd.read_csv(oof)
    for name in CLOCKS:
        rows[name] = pd.to_datetime(rows[name], utc=True).dt.tz_convert("Asia/Kolkata")
    validate_oof(rows)
    truth = rows.merge(train[["location_id", "target_start", "pm25"]],
                       on=["location_id", "target_start"], how="left", validate="one_to_one")
    if not np.array_equal(rows.y, truth.pm25):
        raise ValueError("OOF truth differs from official labels")
    rows["branch_C"] = np.nan
    seasonal = branch_seasonal(archive, rows)
    for _, part in rows.groupby("fold_id", sort=True):
        rows.loc[part.index, "branch_C"] = branch_c(
            train, part, seasonal[part.index.to_numpy()], part.pm_history_cutoff.iloc[0])
    models = ["P_fix", "median72", "blend_recent_50", "branch_C"]
    for split, part in rows.groupby("split"):
        save_metrics(part, models, output / split)
    keep = [*CLOCKS, "split", "location_id", "forecast_lead_hours", "y", *models]
    rows[keep].to_csv(output / "matched_oof.csv.gz", index=False,
                      compression={"method": "gzip", "mtime": 0})
    manifest = {"branch_commit": BRANCH_COMMIT, "low_ref": LOW_REF,
        "command": subprocess.list2cmdline(sys.argv), "python": sys.version,
        "platform": platform.platform(), "branch_source_hashes": source_hashes,
        "local_source_hashes": {p: sha256(ROOT/p) for p in ["scripts/audit_exp025.py",
            "src/mumbai_pm25/source_candidates.py", "experiments/EXP-20261108-025.yaml"]},
        "branch_input_parity": input_parity, "raw_hashes": raw_hashes,
        "raw_unchanged": all(sha256(raw/n) == h for n,h in raw_hashes.items()),
        "source_oof_sha256": sha256(oof), "rows": len(rows), "origins": rows.fold_id.nunique(),
        "C_reproduction": c_comparison,
        "independent_C_max_difference": float(np.max(np.abs(c.Target-independent))),
        "B_reproduction": b_comparison,
        "low_published_blob_matches": git_blob((supplied / "low.csv").read_bytes()) == LOW_BLOB,
        "low_train_blob_matches": git_blob((raw / "Train.csv").read_bytes()) == LOW_TRAIN_BLOB,
        "low_test_blob_matches": git_blob((raw / "Test.csv").read_bytes()) == LOW_TEST_BLOB,
        "low_train_matches_after_crlf_conversion": matches_crlf_blob(raw / "Train.csv", LOW_TRAIN_BLOB),
        "low_test_matches_after_crlf_conversion": matches_crlf_blob(raw / "Test.csv", LOW_TEST_BLOB),
        "low_model_training_code": "ABSENT from inspected repository tree; build_data consumes forecasts",
        "production": "UNCHANGED; analyst-exposed confirmation and unknown registered-team status"}
    manifest["output_hashes"] = {p.relative_to(output).as_posix(): sha256(p)
                                  for p in sorted(output.rglob("*")) if p.is_file()}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({k: manifest[k] for k in ["rows", "origins", "C_reproduction", "B_reproduction",
        "low_published_blob_matches", "low_train_blob_matches", "low_test_blob_matches", "raw_unchanged"]}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--supplied-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.supplied_dir, args.output)
