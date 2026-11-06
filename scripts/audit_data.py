"""Create a compact, fail-fast challenge input audit without dumping raw rows."""
from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from mumbai_pm25.data import load_data


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    data_dir = root / "data/raw/challenge"
    files = [data_dir / name for name in ("Train.csv", "Test.csv", "SampleSubmission.csv", "Stations.csv", "DataDictionary.txt", "AdditionalHistory.zip")]
    if any(not path.is_file() for path in files):
        missing = [str(path) for path in files if not path.is_file()]
        raise FileNotFoundError(f"Missing challenge inputs: {missing}")
    train, test, sample, stations = load_data(data_dir)
    if test.ID.tolist() != sample.ID.tolist() or test.ID.duplicated().any():
        raise ValueError("Test/SampleSubmission IDs must match exactly and be unique")
    cutoff_train = train.groupby("location_id").target_start.max()
    gaps = {}
    for sid, group in train.groupby("location_id"):
        series = group.target_start.sort_values()
        delta = series.diff().dropna().dt.total_seconds().div(3600)
        gaps[str(int(sid))] = {"observed_hours": len(series), "max_missing_run_hours": int(max(0, delta.max() - 1)) if len(delta) else 0,
                               "start": series.min().isoformat(), "end": series.max().isoformat()}
    quantiles = train.pm25.quantile([.5, .9, .99, .999]).to_dict()
    by_station = {}
    for sid, group in train.groupby("location_id"):
        by_station[str(int(sid))] = {
            "station_name": str(group.station_name.iloc[0]), "rows": len(group),
            "median": float(group.pm25.median()), "p90": float(group.pm25.quantile(.9)),
            "p99": float(group.pm25.quantile(.99)), "maximum": float(group.pm25.max()),
            "counts_over_threshold": {str(threshold): int((group.pm25 > threshold).sum())
                                      for threshold in (100, 300, 500, 1000)},
        }
    extremes = train.loc[train.pm25 > 1000, ["timestamp_ist", "station_name", "location_id", "pm25", "count"]]
    extreme_records = [{**row, "timestamp_ist": row["timestamp_ist"].isoformat()}
                       for row in extremes.assign(timestamp_ist=train.loc[extremes.index, "timestamp_ist"]).to_dict("records")]
    archive_members = []
    with zipfile.ZipFile(data_dir / "AdditionalHistory.zip") as archive:
        for name in archive.namelist():
            member_digest = hashlib.sha256()
            with archive.open(name) as member_stream:
                for block in iter(lambda: member_stream.read(1024 * 1024), b""):
                    member_digest.update(block)
            if name.endswith(".txt"):
                preview = archive.read(name).decode("utf-8", errors="replace")
                archive_members.append({"name": name, "bytes": archive.getinfo(name).file_size,
                                        "sha256_member_bytes": member_digest.hexdigest(),
                                        "text_preview": preview[:500]})
                continue
            with archive.open(name) as stream:
                try:
                    rows = 0
                    null_counts: dict[str, int] = {}
                    dtypes: dict[str, str] = {}
                    columns: list[str] = []
                    for chunk in pd.read_csv(stream, compression="gzip" if name.endswith(".gz") else None,
                                             chunksize=100_000, low_memory=False):
                        rows += len(chunk)
                        if not columns:
                            columns = list(chunk.columns)
                            dtypes = chunk.dtypes.astype(str).to_dict()
                            null_counts = {column: 0 for column in columns}
                        chunk_nulls = chunk.isna().sum()
                        for column in columns:
                            null_counts[column] += int(chunk_nulls[column])
                    archive_members.append({"name": name, "rows": rows, "columns": columns,
                                            "dtypes": dtypes, "null_counts": null_counts,
                                            "sha256_member_bytes": member_digest.hexdigest()})
                except (UnicodeDecodeError, pd.errors.ParserError) as exc:
                    raise ValueError(f"Could not inspect AdditionalHistory member {name}: {exc}") from exc
    report = {
        "created_at_utc": datetime.now(UTC).isoformat(),
        "files": {p.name: {"bytes": p.stat().st_size, "sha256": sha256(p)} for p in files},
        "train": {"rows": len(train), "columns": list(train.columns), "nulls": train.isna().sum().to_dict(),
                  "duplicates_station_hour": int(train.duplicated(["location_id", "target_start"]).sum()),
                  "target_min": float(train.pm25.min()), "target_max": float(train.pm25.max()),
                  "target_quantiles": {str(k): float(v) for k, v in quantiles.items()},
                  "counts_over_threshold": {str(x): int((train.pm25 > x).sum()) for x in (100, 300, 500, 1000)},
                  "mean_equals_pm25": bool(train["mean"].equals(train.pm25)) if "mean" in train else None,
                  "station_distributions": by_station, "extreme_rows_over_1000": extreme_records,
                  "station_coverage": gaps, "last_target_start_by_station": {str(int(k)): v.isoformat() for k, v in cutoff_train.items()}},
        "test": {"rows": len(test), "columns": list(test.columns), "nulls": test.isna().sum().to_dict(),
                 "period_start": test.target_start.min().isoformat(),
                 "period_end": test.target_end.max().isoformat(), "scoring_block_counts": test.scoring_block.value_counts().to_dict(),
                 "station_rows": test.location_id.value_counts().sort_index().to_dict()},
        "submission_ids_match_test_order": True,
        "station_metadata_rows": len(stations),
        "csv_schemas": {
            "SampleSubmission.csv": {"rows": len(sample), "columns": list(sample.columns),
                                     "dtypes": sample.dtypes.astype(str).to_dict(), "nulls": sample.isna().sum().to_dict()},
            "Stations.csv": {"rows": len(stations), "columns": list(stations.columns),
                             "dtypes": stations.dtypes.astype(str).to_dict(), "nulls": stations.isna().sum().to_dict()},
        },
        "data_dictionary": {"bytes": (data_dir / "DataDictionary.txt").stat().st_size,
                            "lines": len((data_dir / "DataDictionary.txt").read_text(encoding="utf-8", errors="replace").splitlines()),
                            "section_headings": [line.lstrip("# ").strip() for line in (data_dir / "DataDictionary.txt").read_text(encoding="utf-8", errors="replace").splitlines() if line.startswith("#")]},
        "additional_history_members": archive_members,
    }
    out = root / "reports/ml_pipeline/audit"
    out.mkdir(parents=True, exist_ok=True)
    (out / "data_audit.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    lines = ["# Challenge data audit", "", f"Generated UTC: {report['created_at_utc']}", "",
             f"Train: {len(train):,} rows; test: {len(test):,} rows; stations: {len(stations)}.",
             f"Target range: {train.pm25.min():.3f}–{train.pm25.max():.3f}; >1,000: {(train.pm25 > 1000).sum()} rows.",
             f"Test target intervals: {report['test']['period_start']} to {report['test']['period_end']}.",
             "", "## Station coverage", "", "| Location ID | Observed hours | Largest gap (hours) | Start | End |", "|---:|---:|---:|---|---|"]
    for sid, values in gaps.items():
        lines.append(f"| {sid} | {values['observed_hours']} | {values['max_missing_run_hours']} | {values['start']} | {values['end']} |")
    lines += ["", "## Station target distributions", "", "| Location ID | Rows | Median | P90 | P99 | Max | >1,000 |", "|---:|---:|---:|---:|---:|---:|---:|"]
    for sid, values in by_station.items():
        lines.append(f"| {sid} | {values['rows']} | {values['median']:.2f} | {values['p90']:.2f} | {values['p99']:.2f} | {values['maximum']:.2f} | {values['counts_over_threshold']['1000']} |")
    lines += ["", f"The audit lists {len(extreme_records)} individual rows above 1,000 µg/m³ in `data_audit.json`; all remain unmodified."]
    lines += ["", "## SHA-256", "", "| File | SHA-256 |", "|---|---|"]
    lines += [f"| {name} | `{meta['sha256']}` |" for name, meta in report["files"].items()]
    (out / "data_audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote audit to {out}")


if __name__ == "__main__":
    main()
