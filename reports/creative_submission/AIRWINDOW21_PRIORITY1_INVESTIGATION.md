# AirWindow 2.1 Priority 1 investigation

**Date:** 12 November 2026. This records evidence and open gates; it does not claim new participants, a forecast refresh, new production stations, a Colab cloud run or new validation origins.

## Origin-level evaluation

`apps/airwindow/baseline_comparison.py` now reports each origin's mean paired case delta (AirWindow minus baseline). An origin favours AirWindow below -0.01 ug/m^3, favours the baseline above +0.01, and otherwise ties. Pooled paired denominators and the existing origin-cluster percentile bootstrap remain unchanged. As small-sample sensitivities, the artifact also reports a two-sided exact sign test over non-tied origin means and a two-sided Student-t interval for the equal-weight mean of origin means (df = origins - 1). These are distinct estimands and are exploratory, not proof of superiority.

| Population / baseline | Paired cases / origins | Favour AirWindow / baseline / tie | Equal-origin mean delta (ug/m^3) | 95% Student-t interval | Exact sign p |
|---|---:|---:|---:|---:|---:|
| Full / usual-cleanest | 1,414 / 76 | 42 / 34 / 0 | -4.20 | [-9.68, 1.29] | 0.422 |
| Full / latest-window | 1,411 / 77 | 43 / 32 / 2 | -0.40 | [-2.52, 1.73] | 0.248 |
| Held-out / usual-cleanest | 169 / 8 | 4 / 4 / 0 | -1.28 | [-3.79, 1.23] | 1.000 |
| Held-out / latest-window | 170 / 8 | 5 / 3 / 0 | -1.42 | [-3.55, 0.72] | 0.727 |

All four Student-t intervals include zero, as do the existing cluster-bootstrap intervals. The held-out eight origins were previously inspected by analysts. Nothing supports a statistical-superiority claim.

## More origins

The frozen TASK008 run contains 83 scheduled P_fix forecast blocks in `all_block_rows.csv.gz`; 77 passed the predeclared common-OOF training-support gate and carry at least one labelled row. The four April 2025 blocks were excluded because fewer than 500 eligible labelled training examples were available for the common supervised comparison; the 17 January 2026 and 24 October 2026 blocks have zero labelled rows. Although P_fix values exist in the cached all-block file for those six dates, using forecasts that were excluded from the locked matched evaluation would change its selection/coverage design. The 83-block cache also reflects the historical issue=PM-cutoff proxy, not archived first-publication vintages. Keep the 77-origin replay unchanged for this release; a separately specified P_fix-only sensitivity could be evaluated later with its own missingness and support rules.

## Additional station sources

CPCB's published CAAQMS station catalogue names Bandra, Mumbai; an older CPCB technical activity list also names additional Mumbai monitors including the airport, Powai, Kurla, Worli, Sion and Colaba. OpenAQ's Borivali East page identifies Maharashtra Pollution Control Board ownership, CPCB as provider, PM2.5 measurements, reporting since June 2019, and recent reporting. Its explorer currently requires sign-in to download. OpenAQ documents license-specific commercial-use, attribution, modification and redistribution fields; the actual license for a candidate Mumbai sensor has not been checked. These sources establish leads for research, not validated additions. Current station identity crosswalks, raw hourly coverage, averaging method/units, timestamp and first-publication rules, station operational continuity, data licence/terms, organiser permission, and P_fix forecast support remain unverified. Keep the four challenge stations only.

Sources checked 12 November 2026: [CPCB CAAQMS station list](https://cpcb.nic.in/upload/national-air-quality-index/Station_List_Of_CAAQMS.pdf), [CPCB technical activity report](https://cpcb.nic.in/uploads/it_technical_activity.pdf), [OpenAQ Borivali East listing](https://explore.openaq.org/locations/6965), and [OpenAQ license documentation](https://docs.openaq.org/resources/licenses).

## Event duration

The exported live snapshot has a 248-hour horizon per station, but its replay scenario, decision engine, tests and validation evidence support only contiguous 1-, 2- and 3-hour events. A longer raw forecast horizon does not validate longer activities. No organiser evidence for longer events or matched validation exists in the repository, so keep current choices unchanged and never bridge missing hours.

## Refresh and user evidence

The current refresh script pins the exact TASK011 output hash and validates order, provenance and artifact structure; it is not a refresh generator. No new source release is approved for automated publication. The existing GitHub Actions workflow builds and deploys static Hosting on a main push; it does not refresh model artifacts. No schedule was added. See [AIRWINDOW_REFRESH_RUNBOOK.md](AIRWINDOW_REFRESH_RUNBOOK.md) for the manual staging, validation and rollback gate. A three-to-five-person, privacy-conscious formative test is ready in [USABILITY_TEST_PROTOCOL.md](USABILITY_TEST_PROTOCOL.md); no user study has been conducted.
