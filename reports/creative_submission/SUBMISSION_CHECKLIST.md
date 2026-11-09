# AirWindow 2.0 - Submission checklist

**Creative deadline:** 13 November 2026, 18:29 GMT / 23:59 IST, subject to checking the current official page/form. [Challenge](https://zindi.world/competitions/google-mumbai-data-challenge), [creative form](https://forms.gle/uLpzqYfJm9AjTvjT9).

## Product and evidence review

- [x] Existing AirWindow identity and primary coordinator workflow retained in the updated specification.
- [x] Preimplementation comparison with IITM/SAFAR, Google, UK and AirQo services recorded.
- [x] Genuine current forecast and separate retrospective replay artifacts generated with model/input lineage.
- [x] All declared replay cases and missing outcomes retained; current calibration explicitly unavailable.
- [x] No calibrated probability/interval, hidden actuals, safe/healthy label, street/route inference or measured health benefit.
- [x] Frontend build, twelve domain tests, eight browser/adversarial tests, responsive/keyboard/print captures completed; see the [app README](../../apps/airwindow/README.md) and [INTEGRATION_QA.md](INTEGRATION_QA.md) for execution records.
- [x] Final PDF rebuilt against frozen captures, all five pages rendered/visually inspected, and source hashes verified; 162,376 bytes. See [PDF_QA.md](PDF_QA.md).

## Firebase Hosting Spark preparation

The app includes static hosting configuration. Root's environment check found no Firebase CLI, saved CLI credentials or configured project. Deployment is **pending**, not completed. No paid billing or new project is enabled.

After the account owner supplies access to an authorised Spark project, from `apps/airwindow/`:

```powershell
npm ci
npm run build
npx firebase-tools login
npx firebase-tools projects:list
npx firebase-tools use EXISTING_AUTHORISED_SPARK_PROJECT_ID
npx firebase-tools deploy --only hosting --project EXISTING_AUTHORISED_SPARK_PROJECT_ID
```

The project ID above is an operator placeholder, not an actual project. Before deploying, verify in the Firebase console that the project is on Spark with no billing upgrade. Use Hosting, not App Hosting or paid Functions. Check current [Spark plans](https://firebase.google.com/docs/projects/billing/firebase-pricing-plans), [Hosting quickstart](https://firebase.google.com/docs/hosting/quickstart) and [project-level quotas](https://firebase.google.com/docs/hosting/usage-quotas-pricing). The no-cost plan does not remove quota limits or prove competition eligibility.

- [ ] Deployment succeeds and exact release/commit/artifact hashes are saved.
- [ ] Public link works without login in a signed-out browser and on mobile.
- [ ] Invalid/missing JSON, impossible duration, stale snapshot and print output tested on the deployed build.
- [ ] Any video link plays signed out; no recording completion is assumed.

## Human form action

- [ ] Current form accepts responses; deadline, upload limit and required working-link format confirmed.
- [ ] Source branch and final public/deployment or other accepted working link verified.
- [ ] Final PDF/document is below 10 MB and opens correctly.
- [ ] Entrant email/username/names match Zindi; eligibility/travel statements are accurate. Keep identity documents private.
- [ ] Confirm 19 November creative presentation versus separate 20 November event details if relevant.
- [ ] Submit manually or explicitly authorise submission; preserve actual confirmation and timestamp.

No public URL, Firebase deployment, cloud-notebook execution, user-study result or submission processing is claimed without a corresponding execution record.

## Final handoff - 9 November 2026

- [x] Main-branch audit; forecast/replay hashes unchanged; local notebook cells reproduce all metrics.
- [x] Forecast-first replay/reveal/reset, ranked candidates and malformed replay/retry checked.
- [x] Production static build tested in real installed Chrome; local one-page print output checked.
- [x] Main source link and five-page package refreshed; see final PDF audit for exact bytes/hash.
- [ ] Owner signs in to the official creative form and confirms it accepts responses, current upload limit/fields and whether video is required. Public read returned 401; this is not evidence it is closed.
- [ ] Owner authenticates Firebase locally and identifies an existing authorised Spark project; verify its plan in console, without upgrading or creating resources. CLI/project credentials were absent, so no project plan or public deployment is claimed.
- [ ] After authorised Hosting deployment, verify all three pages/artifacts/print/mobile signed out, record release timestamp/commit/hashes and replace the public-link placeholder.
- [ ] Owner completes identity, residency/eligibility and travel answers and submits manually. No personal choices or form submission were automated.

Prepared form content (fields based on the earlier supplied form copy; current verification pending):

- Working public application: **not deployed**. Never paste an invented URL.
- Source/reproduction link: https://github.com/acchasujal/aqi/tree/main/apps/airwindow
- Document: `AIRWINDOW_2_SUBMISSION.pdf` (five A4 pages, well below 10 MB).
- Description: AirWindow Mumbai helps school sports coordinators compare an existing outdoor booking with complete feasible time windows at four monitored stations. It separates numerical ranking from evidence, abstains without calibrated support, replays all declared retrospective decisions including failures and missing outcomes, and prints a provenance-bearing event brief. It uses a genuine frozen P_fix snapshot; no health benefit or live refresh is claimed.
- Entrant email/username/name and eligibility/travel: human must supply accurate account details; do not commit them.

One human access step for hosting: authenticate the Firebase CLI to the existing authorised Spark project on the owner's machine. The prepared commands above then build and deploy Hosting only. Do not send passwords or tokens in chat. A signed-in form check/submission is a separate human platform action.

The official page reconfirmed the deadline as **13 November 2026, 23:59 IST**. No numeric judging weights or video requirement was confirmed from the inaccessible form.
