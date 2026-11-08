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
