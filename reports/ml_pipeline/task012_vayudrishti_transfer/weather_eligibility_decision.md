# Weather eligibility decision — TASK012

**Decision: BLOCKED. No weather model was fitted or promoted.**

The repository's `WEATHER_EXPERIMENT_REPORT.md`, `WEATHER_SOURCE_AND_LICENSE_AUDIT.md`, and `WEATHER_ALIGNMENT_REPORT.md` were reviewed. Existing current-period CAMS/GFS diagnostics have complete (or explicitly partial for CAMS pressure) coverage, but they are not historical as-issued forecast vintages for the TASK011 folds. The owner previously confirmed that no documented historical model issue-time mapping is available and explicitly prohibited inventing one. Catalogue eligibility is unresolved for CAMS and NOAA/GFS under the competition's source policy. Existing campaign downloads do not establish that the matching forecasts would have been published by each historical pseudo-issue time.

Consequently, CAMS MOS saturation, ventilation (`PBLH * wind_speed`), wind anomalies, CAMS synoptic/diurnal decomposition, and weather analogs remain untested and unavailable for promotion. Realised observations, reanalysis, nominal run initialisation times, and current November forecast products were not substituted. `P_fix` and the P_fix/B50 controls were evaluated without weather changes.

Reopen only when all of the following are documented: the dataset/source is eligible under the challenge rules and its licence/terms; exact forecast run publication or conservative availability time for each fold; complete archived forecast fields over target hours; and a matched comparison on the unchanged raw-label chronological folds.
