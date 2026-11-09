#!/usr/bin/env python3
"""Audit/export GRIB or retrieve a single complete source run; research only."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mumbai_pm25.weather_download import cams_request, fetch_cams, fetch_gfs_block
from mumbai_pm25.weather_grib import decode_grib, validate_run


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    audit = commands.add_parser("audit")
    audit.add_argument("input", type=Path)
    audit.add_argument("--output", type=Path, required=True)
    audit.add_argument("--include-grid", action="store_true")
    block = commands.add_parser("decode-block")
    block.add_argument("--source", choices=["cams", "gfs"], required=True)
    block.add_argument("--input", type=Path, nargs="+", required=True)
    block.add_argument("--output", type=Path, required=True)
    block.add_argument("--date", type=int, required=True)
    block.add_argument("--cycle", type=int, required=True)
    block.add_argument("--first", type=int, required=True)
    block.add_argument("--last", type=int, required=True)
    for source in ("cams", "gfs"):
        command = commands.add_parser(source)
        command.add_argument("--date", required=True, help="YYYY-MM-DD")
        command.add_argument("--cycle", type=int, required=True)
        command.add_argument("--first", type=int, required=True)
        command.add_argument("--last", type=int, required=True)
        command.add_argument("--output", type=Path, required=True)
        command.add_argument("--request-only", action="store_true")
    args = parser.parse_args()
    if args.command == "decode-block":
        messages = []
        files = []
        for path in args.input:
            decoded = decode_grib(path.resolve(), include_grid=True)
            receipt_path = path.with_suffix(path.suffix + ".receipt.json")
            receipt = json.loads(receipt_path.read_text()) if receipt_path.is_file() else {}
            for row in decoded["messages"]:
                row["source_sha256"] = decoded["sha256"]
                row["raw_path"] = path.as_posix()
                row["retrieved_at_utc"] = receipt.get("retrieved_at_utc")
            messages.extend(decoded["messages"])
            files.append({k: v for k, v in decoded.items() if k != "messages"})
        selected = validate_run(
            messages, args.source, args.date, args.cycle, list(range(args.first, args.last + 1))
        )
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(
                {"schema_version": "1.0", "files": files, "messages": selected},
                stream,
                sort_keys=True,
                allow_nan=False,
            )
            stream.write("\n")
        print(f"Validated {len(selected)} selected field/hours")
    elif args.command == "audit":
        payload = decode_grib(args.input.resolve(), include_grid=args.include_grid)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")
        print(f"Audited {payload['message_count']} messages; SHA256 {payload['sha256']}")
    elif args.command == "cams":
        request = cams_request(args.date, args.cycle, args.first, args.last)
        if args.request_only:
            print(json.dumps(request, indent=2))
        else:
            fetch_cams(args.output.resolve(), request)
    elif args.request_only:
        from mumbai_pm25.weather_download import gfs_url

        for lead in range(args.first, args.last + 1):
            print(gfs_url(args.date.replace("-", ""), args.cycle, lead))
    else:
        receipts = fetch_gfs_block(
            args.output.resolve(), args.date.replace("-", ""), args.cycle, args.first, args.last
        )
        print(f"Validated {len(receipts)} hourly files")


if __name__ == "__main__":
    main()
