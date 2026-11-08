# AirWindow 2.0 - Preimplementation red-team review

**Review date:** 8 November 2026 IST. **Decision:** proceed with constrained event comparison, genuine historical replay and explicit uncalibrated abstention. A map/forecast or a lowest-hour button alone is not a defensible differentiator. Review findings were sent to the frontend and evidence implementers before code changes.

## Prior art checked

| Benchmark | Verified capability and source | Consequence for AirWindow |
|---|---|---|
| IITM Mumbai EWS / SAFAR | The official [IITM SAFAR project](https://www.tropmet.res.in/project_details.php?position=7&project_id=3) describes Mumbai site-specific products and public dissemination. Direct [Mumbai EWS](https://ews.tropmet.res.in/mumbai/) access timed out; no fresh UI claim is made. | Do not claim Mumbai lacks forecasts or replace official operational systems. |
| Google Air View+ | Google's [20 November 2024 announcement](https://blog.google/intl/en-in/company-news/using-googles-ai-and-local-ecosystem-to-generate-actionable-air-quality-insights-in-india-with-air-view/) describes hyperlocal India information through local sensors and Maps. | Four challenge stations cannot support equivalent spatial density or a first-hyperlocal-map claim. |
| Google Air Quality API | Official [forecast documentation](https://developers.google.com/maps/documentation/air-quality/forecast) provides up to 96 hours of hourly forecasts and pollutant information. | Forecast display is established. Never silently substitute API output for our model. |
| Best-time outdoor services / Hawa Score | [AirNow's official use guide](https://www.airnow.gov/aqi/aqi-basics/using-air-quality-index/) connects information with outdoor timing; [Plume Labs' first-party tutorial](https://tutorial.plumelabs.com/) explicitly suggests scheduling activities when pollution is lower (the tutorial is older, so current app availability is not inferred). A current official Hawa Score page was not verified; no features are attributed to it. | Generic best-time advice is insufficient. Show the existing booking and evidence. |
| Constraint-based outdoor planners | [WeatherView's first-party planning page](https://www.weatherview.cloud/outdoor-planning) describes duration/time-of-day choices, complete forecast-hour requirements, window comparisons and no safety promise. | Even duration constraints and missing-data abstention are established in weather planning. The more defensible contribution is the paired OOF decision audit and original-event evidence, not scheduling alone. |
| London alerts | [London City Hall](https://www.london.gov.uk/programmes-strategies/environment-and-climate-change/pollution-and-air-quality/models-and-alerts-air-quality) describes forecast-triggered public and school/stakeholder messages; [airTEXT](https://airtext.info/alerts) provides advance alerts. | School targeting/alerts alone are not novel. Add a specific comparison and shareable record, without health advice. |
| Breathe London | The official [network page](https://www.breathelondon.org/sensors/join-the-breathe-london-network) describes sensing and real-time information; the [monitoring report](https://www.breathelondon.org/s/BREATHE-LONDON-NETWORK-AIR-QUALITY-MONITORING-REPORT-2021-2022.pdf) documents reference comparisons. | Expose provenance/freshness/limits. Do not imply equivalent sensor density or calibration. |
| AirQo | Its official [AI Platform](https://airqo.africa/products/ai-platform) covers forecasting, site selection, categorisation and reporting. | General decision support is established. Demonstrate the narrower event decision and reproducible errors. |

This focused comparison is not an exhaustive novelty search. Product descriptions do not establish our model's comparative accuracy.

## Ten adversarial questions

1. **What is added?** The original booking and feasible constraints, complete alternatives, paired OOF replay and an evidence state that can abstain. The combined workflow is the product hypothesis.
2. **Is confidence real?** Implement same-origin predicted/observed differences and held-out-origin diagnostics. Current history does not establish independent probability calibration; state that prominently.
3. **Could it look generic?** Yes. Lead with one event question/form and the comparison; make charts and model details secondary.
4. **Can reliability be reproduced?** Preserve code/input hashes, issue/cutoff clocks, fold IDs, case eligibility, station/duration/lead matching and all-case metrics. A badge without that chain fails review.
5. **Are four stations enough?** For station selection and exact points, yes. For continuous heatmaps, street estimates, routes or school exposure claims, no.
6. **Can the judge finish in 60 seconds?** The intended path is station, booking, duration/range and compare. Actual timing is QA, not a user-study claim.
7. **Can it run offline?** Bundled genuine artifacts and deterministic arithmetic avoid a runtime weather/Maps/LLM dependency.
8. **What if data are stale/missing?** Display actual issue/last observation and snapshot status. Reject incomplete original slots and exclude incomplete alternatives with a reason. No extrapolation.
9. **What if the ranking fails?** Abstain or label the numerical option tentative. Keep failures in replay/aggregate results. Never invent thresholds to force a robust state.
10. **Smallest credible version?** Real-artifact comparison, explicit evidence state, trust centre, all-case retrospective replay and printable brief. No account, chatbot or dense map.

## Residual risks and release checks

- TASK008 OOF is retrospectively generated under an interval-end availability proxy, not archived operational first-publication evidence. Prior analyst exposure limits independent confirmation.
- Case counts can be large while independent-origin support is small; station/duration/lead support and dependence must remain visible.
- No current evidence authorises calibrated probabilities, prediction intervals, ROBUST recommendations, personal exposure or health-impact claims.
- Firebase requires a known authorised project and Spark verification. [Hosting quotas](https://firebase.google.com/docs/hosting/usage-quotas-pricing) are project-level; no-cost storage limits can block deployment. Configuration alone is not deployment, billing approval or prize eligibility approval.
- Verify actual responsive/keyboard/print/missing/stale paths and capture real screenshots before submitting. Public-link and form processing must be separately confirmed.
- No user interviews or user study have been performed. The use case remains an engineering/product hypothesis.
