# External Data and ClimateVerse Policy

## Permitted-source baseline

The competition-specific organiser rules discussion states that participants may use relevant publicly accessible datasets listed through the ClimateVerse Google Air Quality Forecasting Challenge catalogue, subject to the applicable licence and no leakage. Use this explicit catalogue permission as the starting boundary; do not assume unrelated external datasets are allowed.

Catalogue: https://india.climateverse.net/dataverse/google-air-quality-forecasting-challenge

## Data candidate priorities

1. **Open-Meteo hourly forecast vintages:** highest-priority experiment because fresh weather may complement stale PM history. Prefer individual Single Runs/Previous Runs when reconstructing historical issue-time forecasts.
2. **IMD/METAR:** lower-priority regional weather context. Airport observations are not exact monitor-site weather; publication times and station distance must be checked.
3. **Dynamic satellite/fire products:** consider only if temporal resolution, release lag and spatial coverage are suitable for hourly forecasts.
4. **Static land use/buildings/roads/population/port/transport:** low first-pass priority; four station identifiers may already absorb much of this static site effect.
5. **Other-station historical PM2.5:** only after source ID, averaging interval, station mapping and release time are verified; never assume similar names mean same sensors.

## Open-Meteo API distinctions

- **Forecast API:** latest operational forecast, not necessarily an archived historical vintage.
- **Historical Forecast API:** creates a continuous time series by stitching early forecast hours from successive runs. Useful for some retrospective weather series, but not equivalent to the full multi-day forecast issued at a particular origin.
- **Single Runs API:** retrieves a full individual forecast run using its run initialisation time. Better suited to issue-time backtesting when the run's actual publication delay is respected.
- **Previous Runs API:** provides fixed lead-time offsets and can be useful for evaluating skill at particular horizons; assess availability and coverage before choosing it.
- **ERA5/ERA5-Land reanalysis:** analysis/reanalysis product, not a historical forecast vintage. Do not train a live forecast model on it without explicitly modelling the mismatch and proving the feature could have been available.

Official docs:
- https://open-meteo.com/en/docs/single-runs-api
- https://open-meteo.com/en/docs/historical-forecast-api
- https://open-meteo.com/en/docs/previous-runs-api
- https://open-meteo.com/en/terms
- https://open-meteo.com/en/pricing

Open-Meteo's Single Runs documentation states global runs commonly become accessible around 4–6 hours after initialisation, not immediately at the run timestamp. Store the run initialisation time and the conservative availability time separately. Verify actual product/model updates and archive coverage.

## Licence and API terms gate

A dataset being listed in ClimateVerse does not automatically mean every API access tier is permissible for every use. Check:
- dataset licence;
- API terms of service;
- free-tier use restrictions;
- attribution obligations;
- redistribution restrictions;
- whether prize competition / potential commercial or rights-assignment terms conflict with the API usage tier.

The Zindi rules require permitted publicly accessible data and prediction-time availability. Open-Meteo currently states that its free API is limited to non-commercial use, while API data is CC-BY 4.0; its pricing page also states that historical, climate, ensemble and satellite-radiation APIs require the Professional plan or higher. Therefore, do not assume the Single Runs or historical archive endpoint is free or available under the basic tier. Verify the exact endpoint, model archive, plan requirement and API terms before downloading. A dataset licence does not automatically grant free API access. A prize competition with possible code-rights assignment is not automatically commercial or non-commercial; obtain written provider and organiser clarification before relying on this source.

## External data manifest

Every download needs a manifest row containing:
`source_id, dataset_title, URL/DOI, publisher, licence, terms_checked_date, access_method, retrieval_time_utc, issue_time_utc, valid_time_start, valid_time_end, coordinates, model/provider, variables, file_hash, attribution, allowed_for_model, approval_reference`.

Never commit API secrets. Prefer storing fetch scripts and manifests; commit data snapshots only if licence, size and reproducibility requirements permit.
