# EXP-008 — Historical station provenance audit

**Status: BLOCKED before forecasting changes.** Audit performed 2026-11-07 against `AdditionalHistory.zip`, `Stations.csv`, `DataDictionary.txt`, `HistoryNotes.txt`, and `XKDR_All_Stations.csv`. Raw inputs were not modified.

## Method and evidence

The 2024 table has 216,472 rows, with `station_id`, `station_name`, `source`, `series_id`, `timestamp_ist`, and `value`; it has no row-level coordinates or provider/operator column beyond the broad `source` value. The XKDR lookup provides station coordinates and source IDs, but no link to competition OpenAQ sensor IDs. Competition coordinates in `Stations.csv` exactly match the identified IITM/BMC lookup entries. The archive notes warn that source IDs are not interchangeable and that no automatic cross-source merge was performed.

For each archive series below, observation counts and coverage are after filtering to `source == cpcb_caaqm`; date ranges are 2024-01-01 through the listed last timestamp. Values are non-null in all listed series. Modal spacing is one hour. The overlap/duplicate count describes timestamps with multiple records under the existing substring-based target mapping.

| Target / ID | Archive name / ID / series | Provider | Coordinates (archive lookup) | N | Coverage end | Frequency | Duplicate pooled station-hours | Missing values | Currently pooled? | Classification / confidence |
|---|---|---|---|---:|---|---|---:|---:|---|---|
| Borivali East / 11606 | Borivali East, Mumbai - IITM / `site_5113` / `xkdr:site_5113` | `cpcb_caaqm`; operator not separately recorded | 19.232410, 72.868950 (exact target coordinate match) | 8,097 | Dec 31 15:00 | 1h modal, 98.8% adjacent one-hour steps | 6,738 across pooled match | 0% | Yes, with other series | Physical site VERIFIED (high); series choice AMBIGUOUS |
| Borivali East / 11606 | Borivali East, Mumbai - IITM / `site_5400` / `xkdr:site_5400` | `cpcb_caaqm`; operator not separately recorded | 19.232410, 72.868950 (exact target coordinate match) | 7,387 | Dec 31 23:00 | 1h modal, 99.0% adjacent steps | 6,738 across pooled match | 0% | Yes, with other series | Physical site VERIFIED (high); series choice AMBIGUOUS |
| Malad West / 11611 | Malad West, Mumbai - IITM / `site_5102` / `xkdr:site_5102` | `cpcb_caaqm`; operator not separately recorded | 19.197090, 72.822040 (exact target coordinate match) | 7,486 | Dec 31 23:00 | 1h modal, 92.8% adjacent steps | 7,833 across pooled match | 0% | Yes, with two other series | Physical site VERIFIED (high); this series is a plausible mapping |
| Malad West / 11611 | Malad West, Mumbai - IITM / `site_5402` / `xkdr:site_5402` | `cpcb_caaqm`; operator not separately recorded | 19.197090, 72.822040 (exact target coordinate match) | 5,982 | Dec 31 23:00 | 1h modal, 99.5% adjacent steps | 7,833 across pooled match | 0% | Yes, with two other series | Physical site VERIFIED (high); duplicate-site series choice AMBIGUOUS |
| Malad West / 11611 | Mindspace-Malad West, Mumbai - MPCB / `site_5807` / `xkdr:site_5807` | `cpcb_caaqm`; operator label MPCB | 19.187866, 72.830407 (about 1.1 km from target) | 8,120 | Dec 31 23:00 | 1h modal, 99.4% adjacent steps | 7,833 across pooled match | 0% | Yes, due substring `Malad West` | REJECTED as same physical station (high confidence); separate nearby site |
| Byculla / 3409510 | Byculla, Mumbai - BMC / `site_5960` / `xkdr:site_5960` | `cpcb_caaqm`; operator label BMC | 18.976700, 72.838000 (exact target coordinate match) | 8,456 | Dec 31 23:00 | 1h modal, 99.4% adjacent steps | 0 | 0% | Yes | Physical site VERIFIED (high); series identity plausible, no sensor crosswalk |
| Shivaji Nagar / 3409511 | Shivaji Nagar, Mumbai - BMC / `site_5961` / `xkdr:site_5961` | `cpcb_caaqm`; operator label BMC | 19.060498, 72.923356 (exact target coordinate match) | 5,856 | Dec 31 19:00 | 1h modal, 98.9% adjacent steps | 0 | 0% | Yes | Physical site VERIFIED (high); series identity plausible, no sensor crosswalk |

`XKDR_All_Stations.csv` reports two site IDs for each of Borivali East and Malad West at identical coordinates and names. No source documentation explains whether these are sensor replacements, parallel collectors, duplicates, or distinct series versions. Their observed means also differ materially (Borivali 20.88 vs 43.05; Malad 29.96 vs 46.87), which makes pooling or choosing by completeness/score particularly unsafe. The current substring code yields target-level pooled counts of 15,484 Borivali and 21,588 Malad rows; multiple series collide on 6,738 and 7,833 station-hour timestamps respectively.

## Mapping disposition

| Target | Existing rule | Audit disposition | Recommended mapping now |
|---|---|---|---|
| Borivali East | substring `Borivali East`, pools site_5113 and site_5400 | Site VERIFIED; series AMBIGUOUS | None until provider supplies a sensor/series crosswalk or a documented canonical-series rule |
| Malad West | substring `Malad West`, pools site_5102, site_5402, and site_5807 | Current pooling confirmed defective; site_5807 REJECTED as target station. Two target-coordinate series remain ambiguous | Remove site_5807 from any target mapping; do not select between site_5102/site_5402 without provenance |
| Byculla | substring `Byculla`, one series site_5960 | Site VERIFIED; series plausible | Plausible explicit candidate, but target sensor crosswalk absent |
| Shivaji Nagar | substring `Shivaji Nagar`, one Mumbai BMC series site_5961 | Site VERIFIED; series plausible; city qualifier needed to avoid other cities | Plausible explicit candidate, but target sensor crosswalk absent |

The source-aware mapping required for a scientifically interpretable EXP-008 candidate is not defensible for Borivali and Malad from supplied evidence. Therefore no new feature generator or model behavior was implemented, and no validation comparison was run. Do not interpret this as evidence for or against the current candidate's RMSE.
