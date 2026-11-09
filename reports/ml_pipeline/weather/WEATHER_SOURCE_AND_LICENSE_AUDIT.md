# Weather sources and eligibility — 8–9 November 2026

Both sources remain **RESEARCH ONLY / BLOCKED for competition use**. No
catalogue record or written organiser approval was established. The owner
confirmed that no defensible historical issue-time policy is currently available.
Dataset licensing does not resolve those separate gates.

| Source | Primary evidence | Finding / limitation |
|---|---|---|
| CAMS global forecasts | [ADS dataset](https://ads.atmosphere.copernicus.eu/datasets/cams-global-atmospheric-composition-forecasts?tab=overview), DOI [10.24381/04a0b097](https://doi.org/10.24381/04a0b097) | Dataset page displays CC-BY; attribute Copernicus/ECMWF and retain request/source identifiers. This is not organiser permission. |
| CAMS access | [ADS API setup](https://ads.atmosphere.copernicus.eu/how-to-api) | Account/token and manual dataset-terms acceptance required. Neither token nor terms acceptance is supplied by this repository. API downloader prepared; authenticated retrieval NOT RUN. Owner requested first establishing missing content and supplying an exact additional request. |
| CAMS publication/archive | [ECMWF documentation](https://confluence.ecmwf.int/spaces/CKB/pages/212454117/CAMS+Global+atmospheric+composition+forecast+data+documentation) | 00Z output guaranteed by10:00 UTC; earlier access is not guaranteed. Some archived fields are tape-resident. This general schedule is not the historical model issue-time mapping. |
| NOAA GFS | [NWS use policy](https://www.weather.gov/disclaimer), [NOAA-managed distribution record](https://registry.opendata.aws/noaa-gfs-bdp-pds/) | Public-domain/open use subject to source attribution and no implied NOAA endorsement; interpolated outputs are modified research products. |
| NOAA filter and parameters | [NOMADS filter](https://nomads.ncep.noaa.gov/gribfilter.php?ds=gfs_0p25&lat=), [NCEP inventory](https://www.nco.ncep.noaa.gov/pmb/products/gfs/), [NCEP mass parameter table](https://www.nco.ncep.noaa.gov/pmb/docs/grib2/grib2_doc/grib2_table4-2-0-3.shtml) | Six selected variables, three requested level categories. HPBL exact code0/3/196 means planetary boundary layer height in metres. Native ecCodes unknown name/unit preserved beside explicit table resolution. |
| Challenge catalogue | [ClimateVerse catalogue](https://india.climateverse.net/dataverse/google-air-quality-forecasting-challenge) | Browser retrieval failed; no membership inferred for either source. No organiser contacted or approval fabricated. |

Checked on8 November2026 UTC (work continued into9 November IST). The original
CAMS web request/retrieval time is unknown; owner describes an endpoint-only
request but the supplied bytes actually contain five complete hourly fields.
Record that discrepancy rather than attributing an unverified request to the file.
Local preservation proves possession only by its recorded time. Fresh NOAA
downloads have exact request URLs, SHA256 and completed retrieval timestamps;
these are conservative availability upper bounds, not first-publication times.

## Historical-vintage investigation

[NCEI GFS documentation](https://www.ncei.noaa.gov/products/weather-climate-models/global-forecast)
describes a trailing30-day high-resolution distribution and older lower-resolution
archives. [NCAR d084001](https://gdex.ucar.edu/datasets/d084001/)
describes retained individual0.25-degree runs with a coarser three-hour archive
cadence and an archive transition. These are discovery leads, not proof that every
TASK008 origin has48 hourly fields or an available-by timestamp. Web archive
metadata contains dates beyond the present task; no future forecast/observation
was fetched or used. No historical run was selected because doing so without
an agreed issue-time mapping would invent the missing information policy.

No realised weather, reanalysis, stitched forecast history or nominal run time
was substituted. Investigate archive retention and official publication evidence
only after the owner supplies/approves a defensible historical policy. Keep
TASK008 folds, label support and full-target scoring unchanged when that happens.

The public [ADS catalogue API](https://ads.atmosphere.copernicus.eu/api/catalogue/v1/collections/cams-global-atmospheric-composition-forecasts)
and its linked official request form were captured during final review. They
confirm CC-BY-4.0 and the current `data_format=grib` request field (older examples
use `format`). Both JSON snapshots are saved; all three prepared requests passed
field/allowed-value checks. The catalogue temporal extent is stale relative to
the supplied file and is not used as proof of run publication or availability.
