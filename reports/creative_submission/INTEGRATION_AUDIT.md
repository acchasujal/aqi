# AirWindow Foundation Audit

**Audit date:** 2026-11-06<br>
**Repository at start:** branch `main`, commit `c5e6a3f`; user-added README section and the creative strategy pack were uncommitted and have been preserved on `feature/airwindow-creative`.

## ML-to-app integration point

| Question | Observed repository state |
|---|---|
| Reusable forecast-generation script? | No. `src/mumbai_pm25/` contains only a README. `scripts/legacy_validation/` has audit/baseline/model experiments, but no supported inference/export CLI. `scripts/fetch_single_run_weather.py` is an unvalidated weather-feature fetch prototype, not a PM forecast generator. |
| Row-level predictions saved? | The local ignored `base_gap48/72/96/120.pkl` files contain row-level legacy OOF predictions (`C`, model, station, target timestamp, label, prediction). The committed experiment output has aggregate metrics only. No final-grid prediction artifact or row-level predictions are versioned. |
| Forecast metadata recorded? | Partially for experiments: config identifies models, gap and fold period; baseline rows contain a naïve local cutoff and target timestamp. No canonical artifact records generation time, model version/commit, training-data hash, target interval start/end, weather issue metadata or explicit availability state. |
| Station validation metrics available? | Not in the committed baseline experiment report. Its metrics cover aggregate models/gaps only. Local OOF rows could be regrouped by station; no production-model station metrics exist. |
| Model issue time and data cutoffs exposable? | Not from an existing exporter. Legacy rows have `C` but no distinct `model_issue_time_ist`; the weather prototype has issue/run metadata for weather features only. The proposed contract has separate fields for model issue, PM cutoff and weather issue, but no current exporter can populate them. |
| Prediction intervals calibrated? | No. Baseline OOF records are point predictions; no calibration method, coverage study or empirical interval result is saved. The proposed artifact must leave intervals null and mark uncertainty `not_calibrated` until evidence exists. |

## Creative documentation integration

The strategy pack's seven creative docs and master prompt were absent from the canonical repo locations. They have been moved into `docs/` and `prompts/`; the supplied app README is under `apps/airwindow/README.md`; the pack README is preserved in `reports/creative_submission/`. The README now presents ML and AirWindow as separate workstreams. `AGENTS.md` states that app changes must not destabilise ML code.

## Product scope

Initial user: school/sports coordinator or outdoor-event organiser choosing among available activity slots. The decision is to compare one-, two- or three-hour contiguous windows at one selected monitored station by mean predicted hourly PM2.5. The interface must say “lower predicted concentration among the windows shown,” show data freshness and real validation evidence, and state that results are station-based rather than street-level. No route planner, dose estimate, diagnosis, chatbot, account, or interpolation is in scope.

The application scaffold is deliberately limited to a README and contract files. The contract is a draft; full React/Vite implementation waits for owner approval.

## Current external rules and deployment assessment

The competition page currently lists the creative award at $500, expert review for impact/novelty/functionality, a Google-tools bonus, and a submission deadline of 13 November 2026 at 18:29 GMT. Its competition-specific display lists 140 total submissions and a 30/70 split, while the same page's generic Full Challenge Rules text still describes 300 submissions and a 20/80 split. Use the specific competition section and organiser discussion pending a clarification. The page states CC-BY-SA 4.0 for challenge data; the creative-specific organiser discussion permits relevant ClimateVerse catalogue datasets, subject to each provider's terms. No external data is used by this foundation.

Firebase Hosting is a plausible no-billing static host on Spark: Firebase says Spark needs no payment information and grants Hosting no-cost quotas. Current Hosting docs list up to 10 GB stored content and 10 GB/month data transfer; reaching the Spark quota disables Hosting until the next cycle, rather than charging automatically. Static hosting serves content over SSL at a `SITE_ID.web.app` or `SITE_ID.firebaseapp.com` URL. As of 15 October 2026, a Firebase default Hosting site is no longer created automatically with every project, so an explicit site must be created. No Firebase project, site, deployment, hosting URL or public/incognito access test exists in this repository.

Firebase's terms page (last modified 24 September 2026) lists Firebase Hosting under Google APIs Terms of Service. Those terms still apply on Spark. The static Hosting product/setup pages reviewed do not state a visible “hosted by Firebase” attribution requirement. That is an inference from the reviewed pages; source datasets still require their own attribution. Avoid Google/Firebase marks unless their brand rules are checked. A Spark deployment appears compatible with the competition's no-paid-services/no-credit-card requirement while within quota; the challenge organiser has not specifically confirmed Firebase Hosting or whether it counts for the Google-tools bonus.

Firebase Hosting's official product/setup pages reviewed do not state a visible product-attribution requirement; that is an inference from the reviewed docs, not legal advice. The app should credit source datasets and model provenance and may identify Firebase as its deployment host. Do not display Google/Firebase marks without checking brand rules. Hosting on Spark appears compatible with the competition's “no paid services/no credit card” constraint if the project stays on Spark and within quota; Zindi has not specifically confirmed Firebase Hosting. Google Maps Platform is excluded from this plan because it requires billing enablement. No Firebase billing or paid API was enabled.

## Source register checked 2026-11-06

- Zindi competition page: https://zindi.world/competitions/google-mumbai-data-challenge
- Organiser creative/rules discussion: https://zindi.world/competitions/google-mumbai-data-challenge/discussions/35720
- Firebase Spark/Blaze plans: https://firebase.google.com/docs/projects/billing/firebase-pricing-plans
- Firebase Hosting quotas: https://firebase.google.com/docs/hosting/usage-quotas-pricing
- Firebase Hosting quickstart / public subdomains: https://firebase.google.com/docs/hosting/quickstart
- Firebase default Hosting site behavior effective 15 Oct 2026: https://firebase.google.com/docs/hosting/default-site
- Firebase pricing summary: https://firebase.google.com/pricing
- Firebase service terms (modified 24 Sep 2026): https://firebase.google.com/terms

## Remaining blockers

- Owner approval of `docs/FORECAST_ARTIFACT_CONTRACT.md` before full app scaffold.
- A real, reproducible ML inference/export command and artifact metadata.
- Station-level validation metrics from identical chronological OOF rows.
- Empirical uncertainty calibration before any interval display.
- Product-specific confirmation of Firebase acceptance is desirable before claiming Google-tool bonus; no deployment has been made.
- Organiser answers on award stacking and eligibility are still absent.
- The creative finalist presentation is listed as 19 November in one organiser post while another describes the closing event as 20 November; confirm whether these are separate events.
