"""TASK 013: Generate and audit the Task 012 Corrected Kernel Climatology Blend test submission.

Model Strategy:
  - 50% recent 72-hour station median (median72) strictly before eligible cutoff
  - 50% clean 2024 Gaussian kernel climatology (sigma_doy=10.0, sigma_hour=1.0)

Generates:
  - artifacts/submissions/submission_task012_corrected_blend_test.csv
  - artifacts/submissions/submission_task012_corrected_blend_test.manifest.txt
  - reports/task013_prediction_distribution.csv
  - reports/task013_largest_predictions.csv
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from mumbai_pm25.climatology.kernel import KernelClimatology
from mumbai_pm25.data import load_data
from mumbai_pm25.forecast import recent_median72, validate_submission
from mumbai_pm25.historical_archive import ARCHIVE_SERIES, load_2024_history

DATA_DIR = ROOT / "data" / "raw" / "challenge"
SUBMISSIONS_DIR = ROOT / "artifacts" / "submissions"
REPORTS_DIR = ROOT / "reports"
TARGET_STATIONS = [11606, 11611, 3409510, 3409511]


def sha256_file(path: Path) -> str:
    """Calculate SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def get_git_info() -> tuple[str, str]:
    """Retrieve current commit hash and working tree status."""
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
    except (subprocess.SubprocessError, OSError):
        commit = "unknown"
    try:
        status = subprocess.run(
            ["git", "status", "--porcelain"], cwd=ROOT, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
        working_tree = "clean" if not status else "modified"
    except (subprocess.SubprocessError, OSError):
        working_tree = "unknown"
    return commit, working_tree


def build_clean_2024_history(hist_2024: pd.DataFrame, station_id: int) -> pd.DataFrame:
    """Extract clean 2024 archive history using timestamp_median collocation."""
    allowed = ARCHIVE_SERIES[station_id]
    sub = hist_2024.loc[hist_2024["series_id"].isin(allowed)].copy()
    if sub.empty:
        raise ValueError(f"No archive observations for station {station_id}")
    agg = sub.groupby("hour_start")["pm25"].median().reset_index()
    agg = agg.rename(columns={"hour_start": "timestamp"})
    return agg.sort_values("timestamp").reset_index(drop=True)


def lead_bucket_label(lead_hours: int) -> str:
    """Assign human-readable lead bucket."""
    if lead_hours <= 0:
        return "00h (Past/Public)"
    elif lead_hours <= 24:
        return "01-24h"
    elif lead_hours <= 48:
        return "25-48h (Nov 11 Private Early)"
    elif lead_hours <= 72:
        return "49-72h (Nov 11-12 Private Mid)"
    elif lead_hours <= 96:
        return "73-96h (Nov 12 Private Late)"
    else:
        return ">96h"


def main() -> None:
    print("=" * 80)
    print("TASK 013: GENERATE CORRECTED BLEND TEST SUBMISSION")
    print("=" * 80)

    # 1. Load data
    train_path = DATA_DIR / "Train.csv"
    test_path = DATA_DIR / "Test.csv"
    archive_path = DATA_DIR / "AdditionalHistory.zip"
    sample_path = DATA_DIR / "SampleSubmission.csv"
    stations_path = DATA_DIR / "Stations.csv"
    data_dict_path = DATA_DIR / "DataDictionary.txt"

    train_df, test_df, sample_df, stations_df = load_data(DATA_DIR)
    hist_2024 = load_2024_history(archive_path)

    print(f"Loaded Train: {len(train_df):,} rows")
    print(f"Loaded Test: {len(test_df):,} rows")
    print(f"Loaded SampleSubmission: {len(sample_df):,} rows")
    print(f"Loaded 2024 Archive: {len(hist_2024):,} rows")

    # 2. Derive station cutoffs from Train snapshot (latest interval end)
    station_cutoffs: dict[int, pd.Timestamp] = {}
    for sid in TARGET_STATIONS:
        s_starts = train_df.loc[train_df["location_id"] == sid, "target_start"]
        latest_start = s_starts.max()
        station_cutoffs[sid] = latest_start + pd.Timedelta(hours=1)

    global_cutoff = max(station_cutoffs.values())
    model_run_time = pd.Timestamp.now(tz="Asia/Kolkata")

    print("\nStation Cutoffs (Interval End of Latest Train Observation):")
    for sid, sc in station_cutoffs.items():
        print(f"  Station {sid}: {sc.isoformat()}")
    print(f"Global Cutoff: {global_cutoff.isoformat()}")
    print(f"Model Run Time: {model_run_time.isoformat()}")

    # 3. Clean 2024 Kernel Climatology
    print("\nComputing Clean 2024 Kernel Climatology per station...")
    clim_estimator = KernelClimatology(
        sigma_doy=10.0,
        sigma_hour=1.0,
        clim_gap_days=14,
        min_weight=5.0,
    )

    clean_clim_preds: dict[str, float] = {}
    for sid in TARGET_STATIONS:
        clean_df = build_clean_2024_history(hist_2024, sid)
        s_test = test_df.loc[test_df["location_id"] == sid]
        t_targets = list(pd.to_datetime(s_test["target_start"]))
        elig = clim_estimator._extract_eligible_history(clean_df, station_cutoffs[sid])
        c_res = clim_estimator.estimate_batch(elig, t_targets)
        for (_, row), cres in zip(s_test.iterrows(), c_res):
            clean_clim_preds[row["ID"]] = float(cres["clim_prediction"])

    # 4. Station Recent 72-Hour Median with Temporal Eligibility
    print("Computing Recent 72-Hour Station Medians...")
    station_histories = {
        sid: train_df.loc[train_df["location_id"] == sid].set_index("target_start")["pm25"].sort_index()
        for sid in TARGET_STATIONS
    }

    median72_preds: dict[str, float] = {}
    lead_hours_map: dict[str, int] = {}
    eligible_cutoffs_map: dict[str, str] = {}

    for _, row in test_df.iterrows():
        tid = row["ID"]
        sid = int(row["location_id"])
        t_target = row["target_start"]
        s_history = station_histories[sid]

        # Enforce temporal eligibility: never use observations after target begins
        s_cutoff = station_cutoffs[sid]
        row_cutoff = min(s_cutoff, t_target)
        eligible_cutoffs_map[tid] = row_cutoff.isoformat()

        m72_val = recent_median72(s_history, row_cutoff)
        if m72_val is None or not np.isfinite(m72_val):
            # Fallback to station-level overall median if window empty
            m72_val = float(s_history.loc[s_history.index + pd.Timedelta(hours=1) <= row_cutoff].median())
        median72_preds[tid] = float(m72_val)

        # Calculate actual forecast lead time from observation cutoff
        lead_h = max(0, int((t_target - s_cutoff).total_seconds() / 3600.0))
        lead_hours_map[tid] = lead_h

    # 5. Form the Corrected Blend (50:50)
    print("\nBlending: 50% median72 + 50% clean kernel climatology...")
    final_records: list[dict[str, Any]] = []
    submission_rows: list[dict[str, Any]] = []

    for _, row in test_df.iterrows():
        tid = row["ID"]
        sid = int(row["location_id"])
        t_start = row["target_start"]
        t_end = row["target_end"]
        block = row.get("scoring_block", "unknown")

        c_val = clean_clim_preds[tid]
        m_val = median72_preds[tid]
        lead_h = lead_hours_map[tid]

        # Exact 50:50 blend formula
        pred = 0.50 * m_val + 0.50 * c_val

        submission_rows.append({
            "ID": tid,
            "Target": pred,
        })
        final_records.append({
            "ID": tid,
            "location_id": sid,
            "scoring_block": block,
            "target_start": t_start,
            "target_end": t_end,
            "date": t_start.strftime("%Y-%m-%d"),
            "lead_hours": lead_h,
            "lead_bucket": lead_bucket_label(lead_h),
            "median72": round(m_val, 4),
            "clean_climatology": round(c_val, 4),
            "prediction": round(pred, 4),
        })

    sub_df = pd.DataFrame(submission_rows)
    audit_df = pd.DataFrame(final_records)

    # 6. Submission Validation Checks
    print("\n" + "=" * 80)
    print("RUNNING SUBMISSION VALIDATION GATES")
    print("=" * 80)

    # Check 1: Row count
    assert len(sub_df) == 2592, f"Expected 2,592 rows, got {len(sub_df)}"
    print(f"[PASS] Exact row count: {len(sub_df)}")

    # Check 2: ID match and order
    assert sub_df["ID"].tolist() == test_df["ID"].tolist(), "IDs do not match Test.csv in original order"
    print("[PASS] IDs match Test.csv exactly in original order")

    # Check 3: Unique IDs
    assert sub_df["ID"].nunique() == 2592, "Duplicate IDs detected"
    print(f"[PASS] Unique IDs: {sub_df['ID'].nunique()}")

    # Check 4: Column names
    assert list(sub_df.columns) == ["ID", "Target"], f"Columns must be ['ID', 'Target'], got {list(sub_df.columns)}"
    print(f"[PASS] Column names: {list(sub_df.columns)}")

    # Check 5: Finite and non-negative
    target_vals = sub_df["Target"].to_numpy(dtype=float)
    assert np.isfinite(target_vals).all(), "Non-finite predictions detected"
    assert (target_vals >= 0).all(), "Negative predictions detected"
    print(f"[PASS] All predictions finite and non-negative: min={target_vals.min():.4f}, max={target_vals.max():.4f}")

    # Check 6: validate_submission utility
    validate_submission(sub_df, test_df)
    print("[PASS] Passed mumbai_pm25.forecast.validate_submission()")

    # 7. Write Submission File
    output_csv = SUBMISSIONS_DIR / "submission_task012_corrected_blend_test.csv"
    SUBMISSIONS_DIR.mkdir(parents=True, exist_ok=True)
    sub_df.to_csv(output_csv, index=False)
    csv_sha256 = sha256_file(output_csv)
    print(f"\n[OUTPUT] Written submission CSV: {output_csv}")
    print(f"[SHA256] {csv_sha256}")

    # 8. Write Manifest File
    manifest_file = output_csv.with_suffix(".manifest.txt")
    git_commit, git_tree = get_git_info()

    def get_pkg(name: str) -> str:
        try:
            return importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            return "not-installed"

    manifest_lines = [
        "submission_file: submission_task012_corrected_blend_test.csv",
        f"sha256: {csv_sha256}",
        "task: TASK 013 (Test Submission for Manual Review)",
        "model: corrected_kernel_climatology_blend_50_50",
        "ensemble_weights: 0.50 * recent_median72 + 0.50 * clean_2024_kernel_climatology",
        f"model_run_time: {model_run_time.isoformat()}",
        f"pm_history_cutoff_global: {global_cutoff.isoformat()}",
        f"git_commit: {git_commit}",
        f"git_working_tree: {git_tree}",
        f"python: {sys.version.split()[0]}",
        f"platform: {platform.platform()}",
        f"pandas: {pd.__version__}",
        f"numpy: {np.__version__}",
        f"lightgbm: {get_pkg('lightgbm')}",
        f"catboost: {get_pkg('catboost')}",
        f"xgboost: {get_pkg('xgboost')}",
        f"scikit_learn: {get_pkg('scikit-learn')}",
        "climatology_source: clean 2024 CPCB CAAQS archive (History_Mumbai_2024.csv.gz)",
        "climatology_params: sigma_doy=10.0, sigma_hour=1.0, clim_gap_days=14, min_weight=5.0",
        "recent_median_window_hours: 72",
        "train_data_spikes_excluded: True (unflagged Train logger errors excluded from climatology)",
        "total_rows: 2592",
        "summary_statistics:",
        f"  min: {target_vals.min():.4f}",
        f"  mean: {target_vals.mean():.4f}",
        f"  median: {np.median(target_vals):.4f}",
        f"  max: {target_vals.max():.4f}",
        f"  std: {target_vals.std():.4f}",
        "station_pm_history_cutoffs:",
    ]
    for sid, sc in station_cutoffs.items():
        manifest_lines.append(f"  {sid}: {sc.isoformat()}")

    station_names = stations_df.set_index("location_id")["station_name"]
    manifest_lines.append("station_names:")
    for sid in TARGET_STATIONS:
        manifest_lines.append(f"  {sid}: {station_names.loc[sid]}")

    manifest_lines.append("input_sha256:")
    for p in [train_path, test_path, sample_path, stations_path, data_dict_path, archive_path]:
        manifest_lines.append(f"  {p.name}: {sha256_file(p)}")

    manifest_file.write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
    print(f"[MANIFEST] Written manifest: {manifest_file}")

    # 9. Detailed Prediction Distribution Analysis
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # Station Distribution
    st_stats = []
    for sid, grp in audit_df.groupby("location_id"):
        p = grp["prediction"].to_numpy()
        st_stats.append({
            "category": "station",
            "group": str(sid),
            "station_name": station_names.loc[sid],
            "count": len(p),
            "mean": round(float(np.mean(p)), 4),
            "std": round(float(np.std(p)), 4),
            "min": round(float(np.min(p)), 4),
            "p25": round(float(np.percentile(p, 25)), 4),
            "median": round(float(np.median(p)), 4),
            "p75": round(float(np.percentile(p, 75)), 4),
            "max": round(float(np.max(p)), 4),
        })

    # Lead Bucket Distribution
    for l_bucket, grp in audit_df.groupby("lead_bucket"):
        p = grp["prediction"].to_numpy()
        st_stats.append({
            "category": "lead_bucket",
            "group": l_bucket,
            "station_name": "all_stations",
            "count": len(p),
            "mean": round(float(np.mean(p)), 4),
            "std": round(float(np.std(p)), 4),
            "min": round(float(np.min(p)), 4),
            "p25": round(float(np.percentile(p, 25)), 4),
            "median": round(float(np.median(p)), 4),
            "p75": round(float(np.percentile(p, 75)), 4),
            "max": round(float(np.max(p)), 4),
        })

    # Date Distribution
    for dt, grp in audit_df.groupby("date"):
        p = grp["prediction"].to_numpy()
        st_stats.append({
            "category": "forecast_date",
            "group": dt,
            "station_name": "all_stations",
            "count": len(p),
            "mean": round(float(np.mean(p)), 4),
            "std": round(float(np.std(p)), 4),
            "min": round(float(np.min(p)), 4),
            "p25": round(float(np.percentile(p, 25)), 4),
            "median": round(float(np.median(p)), 4),
            "p75": round(float(np.percentile(p, 75)), 4),
            "max": round(float(np.max(p)), 4),
        })

    dist_df = pd.DataFrame(st_stats)
    dist_csv = REPORTS_DIR / "task013_prediction_distribution.csv"
    dist_df.to_csv(dist_csv, index=False)
    print(f"\n[REPORT] Written prediction distribution table: {dist_csv}")

    # 10. Extract 20 Largest Predictions
    top20_df = audit_df.sort_values("prediction", ascending=False).head(20).copy()
    top20_df["station_name"] = top20_df["location_id"].map(station_names)
    top20_export = top20_df[[
        "ID", "location_id", "station_name", "scoring_block",
        "target_start", "target_end", "lead_hours",
        "median72", "clean_climatology", "prediction",
    ]]
    top20_csv = REPORTS_DIR / "task013_largest_predictions.csv"
    top20_export.to_csv(top20_csv, index=False)
    print(f"[REPORT] Written 20 largest predictions table: {top20_csv}")

    # Print summary to console
    print("\n" + "=" * 80)
    print("SUBMISSION PREDICTION SUMMARY STATISTICS (N=2,592)")
    print("=" * 80)
    print(f"Overall Mean:   {target_vals.mean():.4f} ug/m3")
    print(f"Overall Median: {np.median(target_vals):.4f} ug/m3")
    print(f"Overall Std:    {target_vals.std():.4f} ug/m3")
    print(f"Overall Min:    {target_vals.min():.4f} ug/m3")
    print(f"Overall Max:    {target_vals.max():.4f} ug/m3")

    print("\nStation Breakdown:")
    for row in st_stats[:4]:
        print(f"  {row['station_name']} ({row['group']}): "
              f"Mean={row['mean']:.2f}, Median={row['median']:.2f}, Min={row['min']:.2f}, Max={row['max']:.2f}")

    print("\nTop 5 Largest Predictions:")
    print(top20_export.head(5).to_string(index=False))


if __name__ == "__main__":
    main()
