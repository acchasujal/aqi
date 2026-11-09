# EXP-015 station provenance findings

The 2024 archive has 216,472 rows across sources; the production seasonal loader keeps `cpcb_caaqm` rows, then drops `station_id` and `series_id` and matches target names by substring. This causes Mindspace-Malad to enter Malad West's seasonal pool. Archive `HistoryNotes.txt` explicitly says source identifiers cannot be equated with OpenAQ IDs; there is no supplied crosswalk. The archive ends in 2024 and Train begins later, so **no direct cross-source temporal overlap exists** to correlate historical sites with target sensors. Selecting a series from validation RMSE would be circular.

| Target | 2024 series, rows | Location evidence | Production pooling | Disposition |
|---|---|---|---|---|
| Borivali East 11606 | site_5113 8,097; site_5400 7,387 | Both exact target coordinates and name | Both | Physical site verified; sensor identity ambiguous |
| Malad West 11611 | site_5102 7,486; site_5402 5,982 | Both exact target coordinates and name | Both | Physical site verified; sensor identity ambiguous |
| Malad West 11611 | site_5807 Mindspace-Malad 8,120 | Distinct coordinates, about 1.1 km from target; MPCB versus IITM | Yes, unintended substring match | Rejected as same physical station |
| Byculla 3409510 | site_5960 8,456 | Exact target coordinates and name | Yes | Site verified; source-to-target sensor crosswalk unavailable |
| Shivaji Nagar 3409511 | site_5961 5,856 | Exact target coordinates and name | Yes | Site verified; source-to-target sensor crosswalk unavailable |

All listed sources are hourly-modal, non-null after loader filtering, and have no *within-series* duplicate station-hour. Pooling distinct series creates 6,738 overlapping Borivali hours and 7,833 overlapping Malad hours. At shared hours, Borivali's two site values correlate 0.701 (6,738 pairs) but differ in median level (site_5113 15.87, site_5400 34.99 µg/m³); the Malad site pair correlates 0.683 (5,145 pairs) with medians 24.405 and 33.23. Thus the same-site series are not interchangeable measurements. Mindspace median is 28.585, versus site_5102 24.405 and site_5402 33.23.

The EXP-008 audit provides the full coordinate, source, coverage, and missingness matrix. The bounded EXP-015 sensitivity removes *only* the geographically distinct Mindspace source, leaving both same-coordinate Malad series untouched. This tests a documented identity error without claiming the remaining sensor mapping is settled. `TEST_SENSITIVITY.json` records the resulting count and magnitude of current Test predictions that would change; no production mapping is changed.
