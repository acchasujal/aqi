#!/usr/bin/env python3
"""Research-only single-run weather entry point.

The unvalidated Open-Meteo prototype has been retired: it inferred historical
issue times, duplicated station coordinates, matched hour starts and could mix
runs across stations. This entry point delegates to the shared audited CAMS/GFS
pipeline. Use `--help` for audit, decode-block, cams and gfs commands.
Historical issue schedules must be supplied as evidence, never inferred here.
Open-Meteo ingestion remains disabled pending endpoint/terms/availability review.
"""

from weather_pipeline import main

if __name__ == "__main__":
    main()
