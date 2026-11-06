# Real-World Air-Quality Product Benchmarks

**Purpose:** Avoid rebuilding an existing AQI map and identify a defensible product gap for the creative submission.

## Executive finding

Mumbai already has a public Air Quality Early Warning and Decision Support System from IITM/Ministry of Earth Sciences, and Google already offers Air View+ in India. International services also combine monitoring, forecasts, advisories and alerts. Therefore, the project must not claim to be Mumbai's first AQI dashboard, first air-quality forecast or first hyperlocal air map.

A more defensible contribution is a transparent **forecast-to-action planning workflow** built on the challenge's four-station data, with explicit uncertainty, data freshness and spatial limits.

## Benchmark matrix

| System / country | Existing capability | What it teaches us | What not to claim/copy |
|---|---|---|---|
| IITM Mumbai Air Quality Early Warning System, India | Current observations from multiple stations, next-day station forecasts, hourly forecast verification and weather context | Benchmark the actual local public service; show forecast trust and decision usefulness | Do not claim no Mumbai forecasting system exists; do not present our model as official IITM/CPCB output |
| India IMD/IITM AQ-EWS / SAFAR | In-situ observations, satellite AOD/fire information, weather forecasts, chemistry-transport models, 3-day forecasts and bulletins/alerts | Forecasting is a complete chain: observations -> meteorology -> air-quality models -> warnings -> dissemination | Do not pretend a tabular four-monitor model replaces an operational chemical transport system |
| Google Air View+, India | Google AI and local sensor partners provide hyperlocal air-quality information in Google Maps and public-agency insights; deployment/validation ecosystem | Google integration and local sensor QA matter; a map alone is not novel | Do not claim first hyperlocal Indian air map or first Google air-quality service |
| Google Air Quality API | Current conditions, up to 30 days hourly history, up to 96-hour forecasts and heatmap tiles; stated 500m resolution in 100+ countries | Useful product benchmark for forecast presentation and user recommendations | Do not use its output as an unapproved hidden substitute for our model or claim our four-station data is 500m resolution |
| Breathe London, UK | 136 local sensors; quality assurance, calibration and reference-sensor context before public display | Data quality, provenance and calibration should be visible user features | Do not pretend the four CPCB target stations form a dense local sensing network |
| Mayor of London Air Quality Alerts, UK | Forecast-triggered alerts distributed via social channels, transport infrastructure, schools, boroughs, NHS and clinicians | Last-mile delivery and stakeholder-specific messages are a real product value | Do not make medical advice or issue official alerts without authority and validation |
| Singapore NEA haze service | Separates 1-hour PM2.5 from 24-hour PSI; gives time-specific advisory and next-day forecast | Clearly label averaging periods; concise advice can be more useful than many metrics | Do not copy Singapore's band thresholds into India or call hourly PM2.5 an official Indian AQI |
| Seoul Metropolitan Government | District-oriented fine-particle forecasts and alerts | Geographic clarity and simple interpretation | Do not create district-level predictions from four station targets without validation |
| Taiwan Ministry of Environment air-quality IoT network | Local-government sensor network, public platform, analytics to identify possible hotspots and issue event alerts | A monitoring network creates value when paired with local governance and alert workflows | Do not infer source attribution or hotspot certainty from sparse target stations |
| AirQo AI Platform, Africa | Forecasting, monitoring-site selection, site categorisation, reporting, spatial analysis and decision support | Move from data prediction to practical decision support and monitoring strategy | Do not claim to have AirQo's dense network or validated spatial inference with four sites |
| AirNow Fire and Smoke Map, US | Permanent/temporary monitors, low-cost sensors, smoke plumes, fire detections, outlooks and winds; explains satellite limitations | Label observed vs satellite/context layers and explain cloud/night limitations | Do not treat a satellite plume or fire point as a surface PM2.5 measurement |
| Wuhan Urban Air Health Navigation System research | PM2.5 forecast plus spatial interpolation and low-exposure route planning in a dense urban data setup | Route/exposure planning is a researched direction; route-based utility can be compelling when data support it | Do not copy route-level exposure maps with only four monitoring stations; local interpolation would be unvalidated |

## Lessons mapped to AirWindow

1. **IITM/SAFAR:** respect the existing official forecast service and clearly label our outputs as an independent challenge model.
2. **Google Air View+:** Google integration should add real user value, not merely decorate the interface.
3. **Breathe London:** expose data freshness, missingness, measurement provenance and validation.
4. **London alerts:** make the output easy for a school or event organiser to share.
5. **Singapore:** distinguish hourly PM2.5 from daily AQI/PSI and avoid overloading users with indicators.
6. **Taiwan/AirQo:** connect information with planning and decision-support workflows.
7. **AirNow:** distinguish weather/satellite context from ground observations.
8. **Wuhan research:** do not attempt route-level exposure inference without sufficient spatial observations and validation.

## Research notes: India system depth

The IMD Air Quality Early Warning System SOP describes a pipeline using in-situ air-quality and meteorological observations, satellite AOD and fire counts, forecast meteorology, air-quality models including WRF-Chem, SILAM, NCUM dust and ENFUSER, and dissemination through visualisations, bulletins, website, email and WhatsApp. It describes 3-day forecasts for several pollutants. SAFAR was developed with IITM, IMD and NCMRWF and is described as providing location-specific near-real-time and up-to-3-day information in cities including Mumbai.

The SOP's ENFUSER section describes GIS inputs such as road networks, buildings, land use, satellite imagery, elevation and population. The documented 27m/1h setup shown in that SOP is for Delhi; do not imply that exact resolution applies to Mumbai.

## Primary sources

- IITM Mumbai EWS: https://ews.tropmet.res.in/mumbai/
- IMD/Ministry of Earth Sciences AQ-EWS SOP (PDF): https://mausam.imd.gov.in/imd_latest/contents/pdf/emrc_sop.pdf
- Google Air View+ announcement (20 Nov 2024): https://blog.google/intl/en-in/company-news/using-googles-ai-and-local-ecosystem-to-generate-actionable-air-quality-insights-in-india-with-air-view/
- Google Air Quality API overview: https://developers.google.com/maps/documentation/air-quality/overview
- Google Air Quality API forecast: https://developers.google.com/maps/documentation/air-quality/forecast
- Breathe London sensors: https://www.breathelondon.org/our-sensor-network
- Mayor of London alerts: https://www.london.gov.uk/programmes-strategies/environment-and-climate-change/air-quality/models-and-alerts-air-quality
- Singapore NEA haze service: https://www.haze.gov.sg/
- Singapore NEA PM2.5 FAQ: https://www.nea.gov.sg/our-services/pollution-control/air-pollution/faqs
- Seoul air quality: https://english.seoul.go.kr/policy/environment-energy-ord/air-quality/
- Taiwan Ministry of Environment IoT network: https://www.moenv.gov.tw/en/env-affairs/atmospheric-environment/atmospheric-monitoring-and-forecast-of-air-quality/intelligent-network-deployment-planning/3796.html
- AirQo AI Platform: https://airqo.africa/products/ai-platform
- US AirNow Fire and Smoke Map: https://fire.airnow.gov/
- Wuhan route-planning research (2024): https://www.sciencedirect.com/science/article/pii/S0160412024003799

All feature descriptions should be rechecked against sources before public-facing claims. This benchmark is not a formal competitive market study.
