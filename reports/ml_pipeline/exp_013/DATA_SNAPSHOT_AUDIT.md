# EXP-013 data snapshot audit



Local official challenge files were read without modification. Schema, station IDs, timezone, hourly test intervals and sample order passed `load_data` validation.

Train: 47,849 rows; test/sample: 2,592/2,592; four stations. No duplicate test IDs: 0. Sample ID order exact: True.

Train aligned target starts: 2025-02-19T02:00:00+05:30 to 2026-11-02T22:00:00+05:30; test: 2026-10-22T00:00:00+05:30 to 2026-11-20T23:00:00+05:30.

Latest PM interval ends by station: {'11606': '2026-11-02T23:00:00+05:30', '11611': '2026-11-02T23:00:00+05:30', '3409510': '2026-11-02T23:00:00+05:30', '3409511': '2026-11-02T23:00:00+05:30'}. Current global cutoff: `2026-11-02T23:00:00+05:30`.

Full schemas, null counts and input SHA-256 hashes are in `SNAPSHOT.json`. The local Train hash matches the 5 November snapshot recorded in EXP-012; no newer official file was supplied locally as of this audit. The official page schedules later updates, but authenticated download availability was not verified by this script.
