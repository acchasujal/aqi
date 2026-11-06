# Evaluation, Submission and Competition Rules

**Snapshot:** 2026-11-06. Verify live pages and save organiser replies before final submission.

## Known evaluation mechanics

- Target: hourly PM2.5 (µg/m³).
- Metric: RMSE; lower is better.
- Test submission grid: 2,592 rows, every ID required, original order preserved.
- The supplied DataDictionary says the private evaluation is 11–12 November 2026 and that the full submission grid also contains unscored rows.
- The uploaded dictionary indicates 192 valid private rows and a dynamic public window. It also says the 3–4 November active public reference contained 92 valid targets out of 192 potential station-hours.
- Organiser discussion `35663` says the latest valid submission is evaluated on the private period 11–12 November. Generic Zindi info currently still describes the usual selection-of-two flow. Obtain confirmation or obey the interface and most specific organiser announcement.

## Conflicting statements — do not silently reconcile

| Topic | Generic Info page | Competition-specific discussion / file | Safe action |
|---|---|---|---|
| Total submissions | 300 | Organiser discussion says 140 | Respect 140 until written clarification |
| Daily submissions | 10 | 10 | Respect 10/day |
| Selected submissions | Choose 2 | Organiser evaluation discussion says latest valid submission | Keep best two candidates and ensure intended latest submission is valid; follow UI and organiser clarification |
| Public/private | Generic page says approx. 20% public / 80% private | Organiser-specific rule discussion says approx. 30% / 70%; DataDictionary describes a 192-row private subset | Treat actual named 11–12 Nov private reference as authoritative pending confirmation |
| 5 Nov public dates | Info page text has said 1–2 Nov | Uploaded dictionary says revised to 3–4 Nov | Record actual organiser active window; do not infer from static scoring_block |
| External data | Generic rules have restrictive wording | Competition-specific discussion permits relevant ClimateVerse catalogue data | Use only named catalogue after licence and prediction-time checks; ask about non-catalogue sources |

## Current conservative compliance posture

1. Maximum 10 submissions per day.
2. Keep total submissions at or below 140 until clarified.
3. Use core competition data and relevant datasets explicitly listed in the named ClimateVerse challenge catalogue only, unless organisers approve other sources in writing.
4. Independently check each dataset licence and API terms. Competition permission does not override third-party licence terms.
5. No paid services, hidden labels, post-deadline observations, unauthorised private data, AutoML or code-sharing outside registered teams where rules prohibit it.
6. Maintain reproducible code, seeds, dataset/source manifests and a final clean run.
7. Keep the latest intended submission valid. If selection of two is required in the platform UI, deliberately select the best two validated candidates.

## Source links

- Competition Info: https://zindi.world/competitions/google-mumbai-data-challenge
- Competition Data: https://zindi.world/competitions/google-mumbai-data-challenge/data
- Organiser rules discussion (specific limits and ClimateVerse permission): https://zindi.world/competitions/google-mumbai-data-challenge/discussions/35761
- Organiser rules discussion: https://zindi.world/competitions/google-mumbai-data-challenge/discussions/35720
- Organiser evaluation/private period discussion: https://zindi.world/competitions/google-mumbai-data-challenge/discussions/35663

## Required organiser clarification record

Create `reports/organiser_clarifications.md` and paste verbatim answers with dates. Questions:
- Are exactly the 192 rows for 11–12 Nov used for final private scoring?
- Does latest-valid override selected-two? If not, what selection action is required?
- Is the enforceable total limit 140 or 300?
- Which public window is active after the 5 Nov update?
- Is Open-Meteo API access under its free API terms acceptable for this prize competition, in addition to being in ClimateVerse?
- Are only ClimateVerse-listed datasets permitted, or are other public datasets allowed?

Do not mark unresolved rule items as resolved without written evidence.
