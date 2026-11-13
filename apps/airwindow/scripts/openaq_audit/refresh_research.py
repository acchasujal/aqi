"""Manual, fail-closed OpenAQ research refresh; no browser key or backend."""

from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone

from .milestone2 import OUT, build
from .qualify_history import run as fetch_history
from .summarize_qualification import summarize


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if not os.environ.get("OPENAQ_API_KEY"):
        parser.error(
            "OPENAQ_API_KEY is required for a live refresh; existing static evidence is unchanged"
        )
    source = OUT / "source_runs" / args.run_id
    if source.exists() or (OUT / "runs" / args.run_id).exists():
        parser.error("Run ID already exists; immutable snapshots are not overwritten")
    # Stage 1 discovery catalog is the versioned sensor inventory for this run.
    # New sensors require a separate explicit catalog review, not silent station addition.
    fetched = fetch_history(output=source, workers=args.workers)
    if fetched["failures"] or fetched["truncated_sensors"]:
        raise RuntimeError("OpenAQ refresh incomplete; last published research summary retained")
    summarize(source)
    result = build(source, run_id=args.run_id)
    print(
        f"Validated local refresh {result['run_id']} with {result['validation']['normalized_hours']} hourly rows"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
