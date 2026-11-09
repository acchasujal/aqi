# EXP-014 final recommendation

**RETAIN W50.** The bounded supervised experiment did not establish a meaningful full-target RMSE improvement that transfers to the competition's private November horizon. CatBoost Huber shows a useful public short-lead ordinary-range signal, but its private and November regressions make it unsuitable as the final submission. The other squared-error gradient-boosted and residual candidates are less reliable on the original extreme labels. No EXP-014 challenger submission was generated or uploaded; production model selection is unchanged.

The current, independently reproduced W50 CSV remains available at `C:\Users\dyara\aqi-exp013\artifacts\submissions\exp013\w50_fcee20ebf7bd_d1a47ee18372_20261107_1848.csv`, 2,592 rows, SHA-256 `55e2fc8c7cad94db22f1358a8715216b0c7fbbb7a50c728c4413890f6a8716bc`. It is based on the November 5 Train release and must be refreshed after the organiser's final official Train update. No leaderboard improvement is claimed.

Highest-value follow-up: obtain the final official Train refresh, rerun cutoff and lead audits, and test any locked short-horizon robust model only against new legitimately released labels while preserving W50 for private scoring. EXP-008 archive station-series provenance and hourly timestamp semantics, and historical first-publication timing, remain unresolved.
