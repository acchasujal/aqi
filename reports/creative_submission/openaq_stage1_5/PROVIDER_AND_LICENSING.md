# Provider, provenance and licensing review

Date: 2026-11-13. Scope: OpenAQ v3 Mumbai PM2.5 locations in the Stage 1 catalog.
This is a research and source review, not a legal opinion or permission to publish observations.

## Source dependency

| Locations | OpenAQ provider | Listed owner | OpenAQ license metadata | Interpretation |
|---|---|---|---|---|
| Borivali East 11606; Malad West 11611 | CPCB | Indian Institute of Tropical Meteorology | `null` | Same location and sensor IDs as AirWindow Train; OpenAQ is a redistribution path, not an independent monitor. |
| Byculla 3409510; Shivaji Nagar 3409511 | CPCB | Brihanmumbai Municipal Corporation | `null` | Same CPCB measurement chain as AirWindow Train. |
| Deonar 3409329; Siddharth Nagar-Worli 6959; Worli 3409323 | CPCB | IITM or Maharashtra Pollution Control Board | `null` | Additional physical station leads; distinct station IDs, but still CPCB-distributed observations. |
| Mumbai 8039, PM2.5 sensor 23320 | AirNow | Unknown Governmental Organization | `US Public Domain` in OpenAQ location metadata | Potentially distinct provider. Exact physical operator, instrument and upstream grant remain unverified. |

Older `caaqm` series at the same Deonar/Worli coordinates stopped before the replay period. They must not be silently combined with current CPCB sensor IDs. The OpenAQ `Government Monitor` instrument label is generic; it does not identify the exact analyser make or method at any location.

## Priority-site identity and observed cadence

| Location ID / PM2.5 sensor ID | Coordinates (lat, lon) | Provider / owner | Sampled raw cadence | Physical identity confidence |
|---|---|---|---:|---|
| Deonar `3409329 / 12236385` | 19.04946, 72.92300 | CPCB / IITM | 15 min | Distinct named OpenAQ site; exact equipment and on-site coordinates unverified. |
| Siddharth Nagar-Worli `6959 / 12236435` | 19.000083, 72.813993 | CPCB / IITM | 15 min | Distinct site from Worli-MPCB; do not pool by name. |
| Worli-MPCB `3409323 / 12235914` | 18.9936162, 72.8128113 | CPCB / MPCB | 15 min | Distinct location and sensor ID from Siddharth Nagar-Worli. |
| AirNow Mumbai `8039 / 23320` | 19.07283, 72.88261 | AirNow / unknown government organisation | 60 min | Exact physical site, operator and instrument unverified; do not assume it is a consulate monitor. |

The 15-minute and 60-minute cadences are measured from the bounded October–November 2026 Stage 1 raw API responses. OpenAQ's `/hours` endpoint exposes a one-hour period with explicit start and end; the CPCB-derived raw quarter-hours are aggregated by OpenAQ, while AirNow's sampled raw records are already hourly. Neither the generic instrument label nor cadence establishes station-specific PM2.5 measurement technology or historical first-publication latency.

[CPCB's CAAQM documentation](https://cpcb.nic.in/upload/NAAQS_2019.pdf) describes beta attenuation as the normal PM2.5 monitoring principle. This supports method plausibility for CPCB-network stations, **not** proof that each named OpenAQ sensor used the same instrument throughout the replay period. [AirNow's data description](https://www.airnow.gov/about-the-data/) says its near-real-time readings receive preliminary checks and are not equivalent to fully certified AQS data; it does not establish the Mumbai sensor's exact equipment or release latency.

## Storage, redistribution and attribution

- [OpenAQ's terms](https://docs.openaq.org/about/terms) require registered API access for programmatic downloads, attribution to OpenAQ when using its service, and compliance with applicable underlying-provider terms. OpenAQ explicitly does not guarantee that third-party source data is free of claims. Its API access permits this bounded research audit; the terms do not by themselves establish an unrestricted right to republish CPCB records.
- OpenAQ's CPCB location records have **no license object**. No CPCB page found in this audit expressly grants redistribution of these exact OpenAQ CPCB time series. Internal historical analysis with source attribution is the present bounded use. **Do not publish raw CPCB-derived observations or embed them in AirWindow until upstream terms and required attribution are confirmed.**
- The [Government Open Data License — India](https://data.gov.in/Godl) provides broad reuse rights for qualifying government datasets, but we have not established that these particular CPCB/OpenAQ sensor streams were published under that license. Do not apply it by inference.
- OpenAQ labels the AirNow Mumbai location `US Public Domain`, but its attribution object names an unknown government organisation. Verify the actual upstream operator and any station-specific conditions before redistribution. Continue to credit OpenAQ for API access.
- OpenAQ location and sensor IDs, provider, owner, coordinates, units, license metadata and downloaded response JSON are retained separately in ignored local caches. Summary reports identify provenance without publishing bulk observations.

## Conditions before Stage 2

Obtain a provider-level reuse/attribution determination for CPCB, IITM, BMC and MPCB sources; verify AirNow Mumbai's operator and license chain; document exact per-sensor averaging and instrument details. Keep each source and sensor separate. No Stage 1.5 finding authorises production station support or a claim of independent validation.
