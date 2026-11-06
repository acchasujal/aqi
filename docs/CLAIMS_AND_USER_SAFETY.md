# Claims, Spatial Limits and User Safety

## 1. Source and output labels

Every user-visible air-quality value must be labelled as one of:
- **Observed:** measured by the named source/station at a stated time.
- **Forecast:** model prediction for a stated future interval, with issue time and model version.
- **Context:** weather, fire, satellite or land-use information that is not itself a PM2.5 measurement.
- **Illustrative demo:** synthetic/static data used only for interface demonstration; never mix with actual forecast data.

Always show the units and averaging interval.

## 2. Spatial honesty

The project has four target monitoring stations. That is not sufficient to claim street-level or neighbourhood-wide exposure estimates across Mumbai.

- Map only the four actual stations for PM2.5 forecasts.
- Do not create a heatmap by interpolating four station values unless a separate dense independent dataset and validation justify it.
- Do not recommend a “cleanest route”.
- If showing a park, road, school or other POI layer, label it as a geographic/context layer, not as an air-quality measurement.
- Clearly state that readings at a station may not represent conditions at a user's exact address.

## 3. Health and action language

Do not:
- call a time window “safe”, “healthy”, “risk-free” or “medically recommended”;
- calculate a personal inhaled dose from ambient PM2.5 alone;
- diagnose or predict disease;
- advise individuals to change medication or treatment;
- imply that using the app prevents illness or reduces measured exposure.

Permitted wording:
- “lower predicted PM2.5 among the time windows compared”;
- “forecast uncertainty is high”;
- “this is an ambient monitoring-station estimate, not a personal exposure measurement”;
- “consult official CPCB / government guidance for health recommendations”.

If translating PM2.5 concentrations into an AQI, use the applicable official Indian AQI calculation, averaging period and breakpoint methodology. Do not use Singapore, US or Google-specific categories as if they were India's official standard. If hourly predictions cannot validly be converted to an official AQI, show hourly PM2.5 concentration only.

## 4. Causality and explanatory text

Wind, humidity, rainfall, boundary-layer height, fire detections and satellite measurements can provide context. They do not prove that a specific source caused a PM2.5 change at a monitor.

Use “associated with”, “coincides with” or “model context”. Do not say “traffic caused this spike” or “this fire caused the station reading” without a suitable source-attribution analysis.

## 5. Uncertainty

Only display prediction intervals after calibration on appropriate rolling-origin validation folds. If calibration evidence is missing, show a qualitative validation status and say that uncertainty intervals are not yet validated. Do not invent confidence percentages.

## 6. Privacy

The MVP should not collect health conditions, precise user location or personal schedules. Let users select one of four stations manually. No account or personal data is required.
