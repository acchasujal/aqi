# Auxiliary-station spatial eligibility — TASK012

**Decision: REJECT for final inference; no spatial model was fitted.**

`AdditionalHistory.zip` was inspected without changing its bytes. `Other_Mumbai_Stations_2025_2026.csv.gz` contains 9,125 records for 14 location/sensor IDs and ends at `2026-10-16 00:00 IST`. It carries `timestamp_ist`, `available_at`, station name and series metadata, but no coordinates. The notes say `available_at` is file modification time, not first publication. The target Test station-hours start 11 November; these data are historical/stale and provide no contemporaneous private-inference readings.

The archive's XKDR lookup uses string `station_id` values and coordinates; the 2025–2026 auxiliary table uses integer OpenAQ/CPCB location and sensor IDs. The archive does not establish a source-owner crosswalk connecting those identities or proving interval alignment across datasets. Names alone are not accepted as a station mapping, and `available_at` cannot be used as a release-time clock. The target stations do have coordinates in `Stations.csv`, but the auxiliary table itself does not provide verified spatial coordinates. These gaps make upwind concentration, bearing alignment, distance-weighted PM, gradients, missingness-age features, and any wind-directed graph unsupported for the final forecast.

No additional station series were joined to target features. Reopen only with a verified ID/provenance crosswalk, reliable coordinates and interval semantics, a timestamp/release-availability audit per origin, and eligible contemporaneous private inference data. The current evidence fails those gates, so Experiment F is also blocked by the weather gate.
