# AirWindow Mumbai 2.1 - Submission checklist

**Creative deadline:** 13 November 2026, 18:29 GMT / 23:59 IST, subject to checking the current official page/form. [Challenge](https://zindi.world/competitions/google-mumbai-data-challenge), [creative form](https://forms.gle/uLpzqYfJm9AjTvjT9).

## Product and evidence review

- [x] Existing AirWindow identity and primary coordinator workflow retained in the updated specification.
- [x] Preimplementation comparison with IITM/SAFAR, Google, UK and AirQo services recorded.
- [x] Genuine current forecast and separate retrospective replay artifacts generated with model/input lineage.
- [x] All declared replay cases and missing outcomes retained; current calibration explicitly unavailable.
- [x] No calibrated probability/interval, hidden actuals, safe/healthy label, street/route inference or measured health benefit.
- [x] Frontend build, domain tests, nine browser/adversarial tests, responsive/keyboard/print captures completed; see the [app README](../../apps/airwindow/README.md) and [INTEGRATION_QA.md](INTEGRATION_QA.md) for execution records.
- [x] Submission PDF rebuilt against current captures; final size/hash and page review are recorded in [PDF_QA.md](PDF_QA.md).

## Firebase Hosting deployment

Static Hosting was deployed to the existing `airwindow-99085` project on 11 November 2026 at 21:09 IST. Public URL: **https://airwindow-99085.web.app**. A fresh signed-out Chrome context returned HTTP 200 and verified the forecast, 10.5 MB replay, baseline comparison and preserved fallback JSON content types and SHA-256 hashes against the public manifest. Hosting only was deployed; billing was not changed. The Firebase billing plan was not independently confirmed.

The existing `airwindow-99085` project was used for Hosting only. Deployment and public artifact verification are complete; no billing change was made and the billing tier was not independently verified. The current release is documented in the app README. For a future authorized static Hosting release, from `apps/airwindow/`:

```powershell
npm ci
npm run build
npx firebase-tools login
npx firebase-tools projects:list
npx firebase-tools use airwindow-99085
npx firebase-tools deploy --only hosting --project airwindow-99085
```

Use Hosting only and verify current Firebase quotas and project status before any future release. The billing tier is unverified.

- [x] Deployment succeeds and exact release/artifact hashes are saved (Firebase release `3b43a385b43dbc71`).
- [x] Public link and forecast/replay/baseline/fallback JSON work without login in a signed-out browser; mobile layout is covered by local production browser tests.
- [ ] Invalid/missing JSON, impossible duration, stale snapshot and print output tested on the deployed build.
- [ ] Any video link plays signed out; no recording completion is assumed.

## Human form action

- [ ] Current form accepts responses; deadline, upload limit and required working-link format confirmed.
- [ ] Source branch and final public/deployment or other accepted working link verified.
- [ ] Final PDF/document is below 10 MB and opens correctly.
- [ ] Entrant email/username/names match Zindi; eligibility/travel statements are accurate. Keep identity documents private.
- [ ] Confirm 19 November creative presentation versus separate 20 November event details if relevant.
- [ ] Submit manually or explicitly authorise submission; preserve actual confirmation and timestamp.

No cloud-notebook execution, user-study result or form processing is claimed without a corresponding execution record.

## Final handoff - 9 November 2026

- [x] Main-branch audit; forecast/replay hashes unchanged; local notebook cells reproduce all metrics.
- [x] Forecast-first replay/reveal/reset, ranked candidates and malformed replay/retry checked.
- [x] Production static build tested in real installed Chrome; local one-page print output checked.
- [x] Main source link and five-page package refreshed; see final PDF audit for exact bytes/hash.
- [ ] Owner signs in to the official creative form and confirms it accepts responses, current upload limit/fields and whether video is required. Public read returned 401; this is not evidence it is closed.
- [x] Owner authenticated Firebase CLI and identified the existing `airwindow-99085` project. Hosting deployment completed without a billing change; plan status still needs confirmation in Firebase console.
- [x] Hosting URL and all forecast/replay/baseline/fallback JSON validated in a fresh signed-out browser. Release `3b43a385b43dbc71`, URL https://airwindow-99085.web.app.
- [ ] Owner completes identity, residency/eligibility and travel answers and submits manually. No personal choices or form submission were automated.

Prepared form content (fields based on the earlier supplied form copy; current verification pending):

- Working public application: https://airwindow-99085.web.app (Hosting release `3b43a385b43dbc71`; HTTP 200 and manifest artifact hashes verified signed out).
- Source/reproduction link: https://github.com/acchasujal/aqi/tree/main/apps/airwindow
- Document: `AIRWINDOW_2_SUBMISSION.pdf` (five A4 pages, well below 10 MB).
- Description: AirWindow Mumbai helps school sports coordinators compare an existing outdoor booking with complete feasible time windows at four monitored stations. It separates numerical ranking from evidence, abstains without calibrated support, replays all declared retrospective decisions including failures and missing outcomes, and prints a provenance-bearing event brief. It uses a genuine frozen P_fix snapshot; no health benefit or live refresh is claimed.
- Entrant email/username/name and eligibility/travel: human must supply accurate account details; do not commit them.

Human follow-up: confirm the Firebase project billing plan is Spark in Console → Project settings → Usage and billing; no plan changes were made. The signed-in Zindi form, entrant identity/eligibility answers, and submission remain human actions.

The official page reconfirmed the deadline as **13 November 2026, 23:59 IST**. No numeric judging weights or video requirement was confirmed from the inaccessible form.
