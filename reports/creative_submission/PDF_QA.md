# AirWindow 2.0 submission PDF verification

**Publication status:** complete after the final five-test browser/date-boundary pass and screenshot freeze. The PDF was rebuilt, all five pages rendered and visually reviewed, and both source capture hashes verified.

**Final document:** `AIRWINDOW_2_SUBMISSION.pdf`, **5 A4 pages**, **157,195 bytes** (below 10 MB).

SHA-256: `e457929edc97bcb730b4c62ffff3fc8436bd91cf72d6a190a22da7678799786e`.

Created from final genuine forecast/replay artifacts and actual browser captures after the frontend screenshot-freeze signal. The comparison capture shows the original/alternative cards, prominent abstention and forecast trajectory. The replay detail shows a numerical move that was worse in later observations; it is explicitly labelled historical simulation. Neither screenshot is synthetic or altered for the PDF.

## Reproduce

PDF-only dependencies were installed into ignored `data/processed/airwindow_pdf_deps`, not the ML or app dependency set: ReportLab 5.1.0, pypdf 7.0.0 and pypdfium2 5.15.1 (Windows ARM64 wheels), with their required Pillow/charset-normalizer packages.

```powershell
.venv\Scripts\python.exe -m pip install --target data/processed/airwindow_pdf_deps --only-binary=:all: reportlab pypdf pypdfium2
.venv\Scripts\python.exe reports/creative_submission/build_submission_pdf.py --desktop reports/creative_submission/screenshots/airwindow_desktop_decision.png --replay reports/creative_submission/screenshots/airwindow_desktop_replay_detail.png
.venv\Scripts\python.exe -m ruff check reports/creative_submission/build_submission_pdf.py
```

The PDF skill's artifact-operation marker was executed successfully once before authoring. The sandbox could not read the packages installed by the approved network command, so the authoring/render command used approved execution outside the sandbox. No paid service, ML package change or model execution was needed.

## Actual checks

- Builder completed successfully; pypdf reopened all five pages and extracted non-empty text from each (678 / 1,781 / 1,096 / 2,035 / 1,807 characters).
- PDFium rendered every page to `data/processed/airwindow_pdf_render/page-1.png` through `page-5.png`, 893 x 1,263 pixels each.
- All five final page PNGs were opened and visually inspected: consistent margins/typography, sharp primary values/tables, genuine screenshot content, vector architecture, no overlap/clipping or broken glyphs. This review covers the final render, after the last rebuild.
- Final PDF hash and both frozen screenshot hashes match `AIRWINDOW_2_SUBMISSION.audit.json`.
- Generator scoped Ruff check passed. Relevant document diff whitespace checks passed.

The audit JSON records exact screenshot hashes, size/hash and completed visual/source inspection. Rebuilding the PDF may alter creation metadata and thus its file hash; re-render and inspect after changes. Intermediate drafts and render/dependency directories remain ignored.

The document states that calibration and Firebase deployment are unavailable and that no form processing, cloud Colab execution, user interview or measured health benefit is claimed. Firebase/project access and human creative submission remain pending release actions.

## 9 November 2026 final package

Supersedes the preceding original-build size/hash: **5 A4 pages, 162,376 bytes**,
SHA-256 `aa0adabe83849a2bb647472d2ea935406a15768b5f34dca10494c42d72dfd168`.
The existing PDF was rebuilt because genuine UI captures and its obsolete source
branch link changed. All five final PDFium page PNGs were inspected after the final
rebuild: no overlap, clipping or broken glyphs; evidence denominators and limitations
are readable. Source capture hashes match the new audit. The document now links to
main and uses the 9 November review date. The underlying forecast and replay bytes
and claims remain frozen.

The actual Chrome-generated event brief remains **one A4 page**. Text inspection
confirms original/alternative, peak times, PM cutoff, issue/model/artifact, unmatched
validation warning and abstention; its print-rendered PNG was visually reviewed.
Native print-dialog review was unavailable because Computer Use could not verify
the current Chrome URL and stopped. This does not imply native print-preview QA.

Authoring used the existing isolated PDF libraries and the builder command above;
the PDF skill's operation marker ran successfully once before this task's authoring.
The final `apps/airwindow/audit_release.py` verifies PDF/source hashes together with
forecast/replay contracts and local notebook execution. No new PDF dependencies
were installed. Native sandbox reads of the old PDF dependency folder initially
failed with PermissionError; approved execution succeeded.

## 11 November final submission refresh

Rebuilt after final baseline and Hosting release verification: **5 A4 pages, 180,988 bytes**, SHA-256 e0ed7790244d1df0d949b16f04d7e388ee150dc8f9e54efe39e774770a7ba63. All five final rendered pages were visually inspected. The paired baseline table is readable, all four intervals cross zero, deployment URL and limits are explicit, and no clipping or overlap was found. The audit JSON pins final PDF and screenshot hashes.
