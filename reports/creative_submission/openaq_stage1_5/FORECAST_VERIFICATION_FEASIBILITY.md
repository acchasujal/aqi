# Forecast verification feasibility

Date: 2026-11-13. AirWindow replay cases span May 2025 through 1 November 2026, with 77 unique simulated issue origins, four PM2.5 stations and 6,160 distinct station-hour targets.

| Forecast record | Issue / generation | Version evidence | Valid times | Assessment |
|---|---|---|---|---|
| `replay.json` retrospective P_fix OOF | Simulated issue times from 24 April 2025 to 22 October 2026; artifact generated 8 November 2026 | `provenance.prediction_lineage` explicitly says retrospective OOF, not archived real-time vintages | Replay outcomes May 2025–1 November 2026 | Useful for chronological research checks, **not** an operational forecast-vintage archive. |
| Historical `forecast.json` from Git commit `b8aed54fd35af5f62a5181f3047b91accc09b75f` | Issue 8 November 2026 15:58 IST; generated 16:28 IST; Git records commit time 16:39 IST | Byte-identical to current `forecast_fallback_task008.json`, SHA-256 `821c6b01078200baa61a754ff19b6af9a5ccee063f5cca51b5fa24f13f58f541` | 8–20 November 2026 | A versioned candidate vintage has recorded timestamps before November 11–12 targets. It does **not** overlap the replay period; Git metadata alone is not an external publication timestamp. |
| Current `forecast.json` from Git commit `15cd3869013a4713f0074051316ffb5e14397172` | Issue 10 November 2026 15:47 IST; generated 11 November 20:58 IST; committed 21:16 IST | Versioned file in Git | 10–20 November 2026 | For strict contemporaneous evidence, only target hours after its verified commit time qualify; metadata issue time alone cannot prove earlier publication. |

## Matching and leakage gates

- **Issue / valid time:** Replay `issue_time_ist` is a pseudo-origin; every replay target follows it by construction and `replay_validation.py` checks this. It does not prove that a forecast was actually issued then. The November 8 Git artifact has a recorded pre-target commit time for November 11–12, but this falls outside the replay dataset and does not prove external publication.
- **Station / pollutant:** The two versioned forecast artifacts cover AirWindow's four station IDs and hourly PM2.5 predictions. OpenAQ provides matching PM2.5 sensor IDs for those stations. Deonar, Worli and AirNow Mumbai have no AirWindow station-specific forecast in these artifacts.
- **Observation availability:** OpenAQ hourly periods contain actual interval starts/ends. Use only observations after their target interval completes. The API does not expose verified first-publication times; historical reporting latency cannot be reconstructed. No observed outcome may enter forecast features at an earlier issue time.
- **Lead compatibility:** Replay pseudo-origin forecasts use roughly eight-day PM-information ages. Actual November artifact lead and PM cutoff must be measured separately. A matching target timestamp alone does not establish comparable lead.
- **Independent origins:** Replay's 77 origins are fixed-origin backtests generated together on 8 November, not 77 independent contemporaneously archived runs. The versioned November 8 forecast is one real archival candidate, insufficient by itself for reliable forecast-performance claims.
- **Independent observations:** The four OpenAQ station series list CPCB as provider and closely match the local CPCB-derived Train values. They are a second access path to the same underlying observations, **not independent sensor validation**. AirNow Mumbai is a different location and cannot validate a specific AirWindow station forecast without a defensible spatial transfer model.

**Decision:** Do not label replay comparisons as prospective forecast verification. Stage 2 may develop an external-observation interface or prospectively archive future forecast vintages with issue time, immutable hash, PM cutoff, station, pollutant and valid interval. The November 8 artifact can be examined separately against later observations, explicitly as one vintage and the same CPCB observation source.
