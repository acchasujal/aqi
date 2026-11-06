# Sources and Evidence Register

This file records primary/official sources and what each supports. Check dates and page contents again before final submission.

| ID | Source | Use | Notes |
|---|---|---|---|
| S-01 | https://zindi.world/competitions/google-mumbai-data-challenge | Official competition overview/rules | Generic page currently describes 300 submissions and standard two-submission / 20-80 language; compare organiser-specific announcements |
| S-02 | https://zindi.world/competitions/google-mumbai-data-challenge/data | Official files and data descriptions | Source of six challenge data assets plus starter notebook |
| S-03 | https://zindi.world/competitions/google-mumbai-data-challenge/discussions/35761 | Organiser-specific rules | States 10/day, 140 overall, 30/70 and ClimateVerse catalogue use; conflicts with generic page |
| S-04 | https://zindi.world/competitions/google-mumbai-data-challenge/discussions/35720 | Organiser-specific rules | Repeats competition-specific conditions |
| S-05 | https://zindi.world/competitions/google-mumbai-data-challenge/discussions/35663 | Organiser evaluation statement | Says latest valid submission evaluated on private period 11–12 Nov; also describes creative award timing |
| S-06 | `data/raw/challenge/DataDictionary.txt` | Timestamp semantics and dated scoring windows | Uploaded dictionary states Train timestamp ends hour, Test target_start/target_end, dynamic public window and 11–12 Nov private period |
| S-07 | https://india.climateverse.net/dataverse/google-air-quality-forecasting-challenge | Named external catalogue | Dataset-specific records, licence, time coverage and limits must be inspected individually |
| S-08 | https://open-meteo.com/en/docs/single-runs-api | Individual weather forecast runs | Run init time differs from availability time; global runs commonly become available 4–6h after init; ECMWF IFS HRES archive from Mar 2024 |
| S-09 | https://open-meteo.com/en/docs/historical-forecast-api | Stitched historical forecasts | First hours of successive runs stitched into continuous hourly series; not equivalent to full run horizon |
| S-10 | https://open-meteo.com/en/docs/previous-runs-api | Fixed forecast lead-time history | Candidate alternative for forecast-vintage experiments |
| S-11 | https://github.com/mnm-rnd/competitions/tree/master/zindi/airqo-ugandan-air-quality-forecast-challenge | 2020 AirQo winner code/approach | Public solution repository; inspect code before relying on implementation details |
| S-12 | https://zindi.world/competitions/layerai-air-quality-prediction-challenge/discussions/13525 | 2022 Layer.ai Air Quality winner discussion | Historical transfer lessons; check exact page availability and content |
| S-13 | https://open-meteo.com/en/terms | Open-Meteo API terms | Free API restricted to non-commercial use; separate from data licence |
| S-14 | https://open-meteo.com/en/pricing | Open-Meteo API pricing tiers | Page states historical, climate, ensemble and satellite-radiation APIs require Professional plan or higher; verify exact endpoint/tier |

## Evidence labels

- **Official fact:** current official challenge page, organiser announcement or supplied data dictionary.
- **File-derived fact:** computed from exact version/hash of supplied files.
- **Reproduced experiment:** code and result reproduced in this repo with saved config and predictions.
- **External research:** historical competition write-up or scientific source.
- **Hypothesis:** requires experiment; not a conclusion.

Do not promote a claim to “reproduced” unless the scripts and artifacts are committed or otherwise retrievable and the command is documented in `PROGRESS.md`.
