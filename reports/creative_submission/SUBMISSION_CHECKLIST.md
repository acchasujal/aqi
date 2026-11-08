# AirWindow 2.0 - Submission checklist

**Creative deadline:** 13 November 2026, 18:29 GMT / 23:59 IST, subject to checking the current official page/form. [Challenge](https://zindi.world/competitions/google-mumbai-data-challenge), [creative form](https://forms.gle/uLpzqYfJm9AjTvjT9).

## Product and evidence review

- [x] Existing AirWindow identity and primary coordinator workflow retained in the updated specification.
- [x] Preimplementation comparison with IITM/SAFAR, Google, UK and AirQo services recorded.
- [x] Genuine current forecast and separate retrospective replay artifacts generated with model/input lineage.
- [x] All declared replay cases and missing outcomes retained; current calibration explicitly unavailable.
- [x] No calibrated probability/interval, hidden actuals, safe/healthy label, street/route inference or measured health benefit.
- [x] Frontend build, nine domain tests, five browser/adversarial tests, responsive/keyboard/print captures completed; see the [app README](../../apps/airwindow/README.md) and [INTEGRATION_QA.md](INTEGRATION_QA.md) for execution records.
- [x] Final PDF rebuilt against frozen captures, all five pages rendered/visually inspected, and source hashes verified; 157,195 bytes. See [PDF_QA.md](PDF_QA.md).

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
