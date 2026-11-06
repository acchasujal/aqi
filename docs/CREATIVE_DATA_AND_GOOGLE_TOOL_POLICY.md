# Creative Data and Google Tool Policy

## 1. Data-source rule

The organiser says the creative entry may use the challenge dataset and additional relevant ClimateVerse catalogue datasets. Check both the competition permission and the underlying provider licence/terms. Do not assume that inclusion in the catalogue automatically grants every API tier or every form of commercial use.

For every external source, save a source manifest containing:
- title and dataset DOI/URL;
- publisher;
- licence;
- API/service terms URL and date checked;
- retrieval time;
- spatial/temporal coverage;
- variables;
- valid time and issue time if forecast;
- attribution text;
- restrictions and organiser approval if applicable.

## 2. Candidate dataset priorities

1. **Open-Meteo weather forecast vintages:** potential explanatory inputs for the PM2.5 forecast and context cards. Use individual forecast runs and respect run publication delay. The free API terms say use is non-commercial; paid plan requirements can differ by endpoint. Get organiser/provider clarification before relying on it for a cash-prize entry.
2. **IMD/METAR context:** useful if permitted and if timestamp/availability are known. Airport weather is not identical to the four monitor sites.
3. **Dynamic satellite/fire datasets:** only use as context and show temporal/spatial limitations; do not label them as direct PM2.5 observations.
4. **Static BMC parks / roads / buildings / land-use layers:** could add relevant context, but do not use them to generate unsupported pollution estimates.
5. **Other station PM2.5:** use only when IDs, sensor location, averaging intervals, timezone, release time and terms are verified.

## 3. Google tools

### Recommended: Firebase Hosting Spark

Use Firebase Hosting to deploy the static React application if quotas/terms fit. Spark is a no-cost plan that does not require payment information for no-cost products. Keep the deployed app static; do not add Cloud Functions or services that force Blaze billing without approval.

### Optional: Google Colab

Use Colab for reproducible analysis or a notebook that demonstrates the model pipeline. Do not make the live application depend on an interactive notebook.

### Use caution: Google Maps Platform

Maps JavaScript API requires billing to be enabled. Free SKU allowances do not eliminate the need to configure billing. Do not use unless the account owner approves billing and the organiser confirms compatibility with the challenge's restrictions.

### Avoid unless written approval: Google Earth Engine

The non-commercial terms for individuals receiving free access state they may not receive compensation for applications or data created using Earth Engine. Because this is a cash-prize competition, do not rely on the non-commercial tier without written clarification from Google.

### Avoid in MVP: Gemini API

The unpaid Gemini API terms allow submitted content to be used to improve Google products; other age/application terms apply. Explanations in AirWindow can be generated deterministically from model metadata and weather variables. An LLM is not necessary for the core product.

### Benchmark only: Google Air Quality API

Google's Air Quality API offers current, hourly history, forecasts up to 96 hours and map layers, with coverage stated across 100+ countries and a 500m resolution. It is a useful existing-product benchmark, but do not use its predictions as an undisclosed substitute for the participant model or as a model feature without explicit permission.

## 4. Sources

- ClimateVerse catalogue: https://india.climateverse.net/dataverse/google-air-quality-forecasting-challenge
- Open-Meteo terms: https://open-meteo.com/en/terms
- Open-Meteo Single Runs: https://open-meteo.com/en/docs/single-runs-api
- Open-Meteo pricing: https://open-meteo.com/en/pricing
- Firebase pricing plans: https://firebase.google.com/docs/projects/billing/firebase-pricing-plans
- Google Maps Platform pricing: https://developers.google.com/maps/billing-and-pricing/overview
- Maps JS billing: https://developers.google.com/maps/documentation/javascript/usage-and-billing
- Earth Engine non-commercial: https://earthengine.google.com/noncommercial/
- Gemini API terms: https://ai.google.dev/gemini-api/terms
- Google Air Quality API: https://developers.google.com/maps/documentation/air-quality/overview

## Gate

The creative application may launch using only core challenge data and static generated artefacts. Add external data only after a documented source/licence/availability review. Never delay the MVP while chasing an uncertain API.
