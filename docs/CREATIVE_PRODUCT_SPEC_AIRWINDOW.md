# Creative Product Specification — AirWindow Mumbai

**Working name:** AirWindow Mumbai<br>
**Tagline:** Turn hourly air-quality forecasts into better-timed outdoor plans.<br>
**Category:** Best Additional / Most Creative Submission.

## 1. Product thesis

Existing air-quality services are strong at displaying readings, maps, forecasts and advisories. AirWindow focuses on a narrower last-mile question:

> Given the forecast at a selected CPCB monitoring station, which upcoming one-, two- or three-hour windows have the comparatively lower predicted PM2.5 concentration, and how confident should a user be in that comparison?

The app is a decision-support prototype, not an official alert service, medical product or hyperlocal exposure map.

## 2. Primary users

Prioritise two user groups for the MVP:

1. School / sports / outdoor-event coordinators who must choose among available activity windows.
2. Outdoor operations supervisors who need to compare forecast periods for outdoor tasks or breaks.

Secondary audiences: environmental NGOs, community organisers and researchers.

## 3. Core user journey

1. User chooses one of the four actual monitored stations.
2. User chooses an activity duration: 1, 2 or 3 contiguous hours.
3. User selects the planning horizon (within available forecast hours).
4. The app ranks candidate windows using the mean of the predicted hourly PM2.5 concentrations.
5. Each option shows forecast values, an uncertainty interval, issue time, last PM observation time and a validation note.
6. User opens a shareable planning brief suitable for a school or event coordinator.

Do not state that any window is “safe”, “healthy” or medically recommended. Say “lower predicted concentration relative to the other windows shown”.

## 4. MVP features

### A. Four-station map

- Plot only the four challenge stations from `Stations.csv`.
- Show station name, coordinates, latest known PM observation and data timestamp.
- Do not interpolate a continuous Mumbai pollution surface.
- Do not imply that a station reading represents every nearby street or building.

### B. Hourly forecast timeline

- Display forecast PM2.5 per station.
- Distinguish measured history from future model outputs.
- Show issue time, target interval and model version.
- Show prediction intervals only after they are calibrated from validation residuals.

### C. Time-window ranking

For a requested duration `d`, calculate the rolling mean of the next `d` predicted hourly PM2.5 values. Rank windows from lower to higher predicted mean. Also show the difference from the median of candidate windows. Do not call this a personal exposure or dose estimate.

### D. Forecast context

Optionally show weather variables such as wind, humidity, rain and boundary-layer height when the data source is approved and has a correct issue-time vintage. Use neutral language such as “forecast conditions associated with this model output”. Do not claim causal source attribution.

### E. Trust centre

Show:
- Latest PM observation timestamp per station.
- PM history cutoff used by the model.
- Weather issue time, provider and model if weather is included.
- Forecast horizon.
- Per-station rolling-origin validation RMSE at comparable horizons.
- Number of historical validation samples.
- Data-missingness and uncertainty notes.
- Model version and data fingerprint.

### F. Shareable planning brief

Provide a print/download/share view containing selected station, chosen duration, recommended relative window, alternatives, predicted concentrations, uncertainty, timestamps, model performance note and limitations.

### G. Historical replay

Provide a fixed, clearly labelled backtest example showing actual observed target vs historical forecast, where prediction and label are legitimately available. Never use hidden private labels before they are officially released.

## 5. Data contract between ML and app

The frontend must consume a generated, versioned forecast artifact. Do not train models inside the browser.

Suggested file: `apps/airwindow/public/data/forecast.json`.

Suggested top-level fields:

```json
{
  "schema_version": "1.0",
  "generated_at_ist": "...",
  "model_id": "...",
  "model_version": "...",
  "training_data_hash": "...",
  "pm_history_cutoff_ist": "...",
  "weather_issue_time_ist": null,
  "weather_source": null,
  "stations": [
    {
      "station_id": "BOR",
      "station_name": "Borivali East",
      "latitude": 19.23241,
      "longitude": 72.86895,
      "last_observation_ist": "...",
      "validation": {
        "horizon_hours": 48,
        "rmse": null,
        "n_targets": null
      },
      "forecasts": [
        {
          "target_start_ist": "...",
          "target_end_ist": "...",
          "pm25_pred": 0.0,
          "lower": null,
          "upper": null
        }
      ]
    }
  ]
}
```

This is a schema example, not actual forecast data. `lower`/`upper` must remain null until calibrated prediction intervals exist. Do not put hidden labels or secret credentials in the artifact.

## 6. Technical architecture

- Frontend: React + Vite + TypeScript.
- Charts: Chart.js / Recharts (choose one, avoid duplicate chart dependencies).
- Map: Leaflet or MapLibre using a basemap provider whose terms are compatible; four station markers only.
- Hosting: Firebase Hosting Spark, subject to plan and product quota review.
- Data interface: static versioned JSON generated from the ML package.
- No database, authentication, user tracking or live backend in MVP.
- Use accessible contrast, keyboard interaction and responsive layout.

## 7. Non-goals

- No continuous 500m/300m/road-level PM2.5 map.
- No route planner or “cleanest route” recommendation from four stations.
- No medical advice, disease prediction or personal dose calculation.
- No claims that wind/fire/satellite observations prove a particular pollution source.
- No replacement for CPCB, IITM or government alerts.
- No unvalidated forecast or uncertainty range presented as ground truth.
- No unnecessary LLM chatbot, user account system or backend.

## 8. MVP acceptance criteria

- App loads from public URL without login.
- All four station records render correctly.
- User can change station and activity duration.
- Window ranking is calculated from actual provided forecast values.
- Forecast history and forecast future are visually distinct.
- Every value has a timestamp and unit.
- Trust centre shows actual validation evidence or clearly says “not yet measured”.
- App has no dead buttons or fabricated values.
- No prediction surface is shown outside monitored stations.
- Mobile and desktop layouts work.
- A PDF/print brief is generated correctly.
- A static demo still works if an API is unavailable.
