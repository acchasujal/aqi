"""Create and render the AirWindow judging PDF from genuine artifacts/screenshots.

PDF dependencies are isolated under data/processed/airwindow_pdf_deps; they are
not application or ML dependencies. Run only after real UI screenshots exist.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "data/processed/airwindow_pdf_deps"))

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    Flowable,
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

NAVY = colors.HexColor("#16362F")
TEAL = colors.HexColor("#226D5A")
CREAM = colors.HexColor("#F6F3EA")
INK = colors.HexColor("#1B2925")
MUTED = colors.HexColor("#52665D")
LINE = colors.HexColor("#D4DDD5")
AMBER = colors.HexColor("#A45D1E")
WIDTH, HEIGHT = A4
CONTENT_WIDTH = WIDTH - 84


class ArchitectureFlow(Flowable):
    """Vector architecture, distinct from the unmodified real UI screenshots."""

    def __init__(self) -> None:
        super().__init__()
        self.width = CONTENT_WIDTH
        self.height = 142

    def draw(self) -> None:
        canvas = self.canv
        items = [
            ("IMMUTABLE OFFICIAL INPUTS + REVIEWED ML PIPELINE", "Forecast CSV and provenance | Fixed-origin OOF predictions"),
            ("DETERMINISTIC CREATIVE BUILD + VALIDATORS", "Live forecast JSON separated from retrospective replay JSON"),
            ("STATIC REACT APPLICATION", "Original vs alternative | Evidence / abstention | Replay | Print"),
        ]
        for index, (title, detail) in enumerate(items):
            y = self.height - 40 - index*50
            canvas.setFillColor(colors.white)
            canvas.setStrokeColor(LINE)
            canvas.roundRect(0, y, self.width, 39, 7, stroke=1, fill=1)
            canvas.setFillColor(TEAL)
            canvas.setFont("Helvetica-Bold", 8)
            canvas.drawCentredString(self.width/2, y+24, title)
            canvas.setFillColor(MUTED)
            canvas.setFont("Helvetica", 8)
            canvas.drawCentredString(self.width/2, y+10, detail)
            if index < 2:
                canvas.setStrokeColor(TEAL)
                canvas.line(self.width/2, y-1, self.width/2, y-9)
                canvas.line(self.width/2-3, y-6, self.width/2, y-9)
                canvas.line(self.width/2+3, y-6, self.width/2, y-9)


def styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    result = {
        "title": ParagraphStyle("Hero", fontName="Helvetica-Bold", fontSize=31,
                                 leading=35, textColor=NAVY, spaceAfter=12),
        "subtitle": ParagraphStyle("Subtitle", fontName="Helvetica", fontSize=15,
                                    leading=20, textColor=MUTED, spaceAfter=16),
        "heading": ParagraphStyle("Heading", fontName="Helvetica-Bold", fontSize=19,
                                   leading=24, textColor=NAVY, spaceAfter=12),
        "subhead": ParagraphStyle("Subhead", fontName="Helvetica-Bold", fontSize=11,
                                   leading=15, textColor=TEAL, spaceBefore=9, spaceAfter=5),
        "body": ParagraphStyle("Body", parent=base["BodyText"], fontName="Helvetica",
                                fontSize=10, leading=14, textColor=INK, spaceAfter=9),
        "small": ParagraphStyle("Small", fontName="Helvetica", fontSize=8,
                                 leading=11, textColor=MUTED, spaceAfter=6),
        "label": ParagraphStyle("Label", fontName="Helvetica-Bold", fontSize=8,
                                 leading=12, textColor=TEAL, spaceAfter=10),
        "callout": ParagraphStyle("Callout", fontName="Helvetica-Bold", fontSize=11,
                                   leading=16, textColor=AMBER, spaceAfter=8),
        "cell": ParagraphStyle("Cell", fontName="Helvetica", fontSize=9,
                                leading=12, textColor=INK),
        "cellbold": ParagraphStyle("CellBold", fontName="Helvetica-Bold", fontSize=9,
                                    leading=12, textColor=NAVY),
    }
    return result


def footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFillColor(CREAM)
    canvas.rect(0, 0, WIDTH, HEIGHT, fill=1, stroke=0)
    # Background is painted through onPage before frame content.
    canvas.setStrokeColor(LINE)
    canvas.line(42, HEIGHT - 35, WIDTH - 42, HEIGHT - 35)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.setFillColor(TEAL)
    canvas.drawString(42, HEIGHT - 25, "AIRWINDOW MUMBAI / PRODUCT + EVIDENCE")
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(42, 24, "Independent challenge prototype | 8 November 2026 | IST")
    canvas.drawRightString(WIDTH - 42, 24, str(doc.page))
    canvas.restoreState()


def screenshot(path: Path, maximum_height: float) -> Image:
    if not path.is_file():
        raise FileNotFoundError(f"Real screenshot required: {path}")
    width, height = ImageReader(str(path)).getSize()
    ratio = min(CONTENT_WIDTH / width, maximum_height / height)
    return Image(str(path), width=width*ratio, height=height*ratio, hAlign="CENTER")


def table(rows: list[list[str]], style: dict[str, ParagraphStyle], widths: list[float]) -> Table:
    cells = [[Paragraph(str(value), style["cellbold"] if index == 0 else style["cell"])
              for index, value in enumerate(row)] for row in rows]
    item = Table(cells, colWidths=widths, hAlign="LEFT")
    item.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("LINEBELOW", (0, 0), (-1, -1), .4, LINE),
    ]))
    return item


def make_pdf(output: Path, desktop: Path, replay_image: Path) -> None:
    style = styles()
    data = ROOT / "apps/airwindow/public/data"
    forecast = json.loads((data / "forecast.json").read_text(encoding="utf-8"))
    replay = json.loads((data / "replay.json").read_text(encoding="utf-8"))
    manifest = json.loads((data / "manifest.json").read_text(encoding="utf-8"))
    summary = replay["summary"]
    diagnostics = json.loads((ROOT / "apps/airwindow/evidence/replay_diagnostics.json").read_text(encoding="utf-8"))
    confirm = diagnostics["confirmation_metrics"]
    if replay["calibration"]["status"] != "not_calibrated":
        raise ValueError("Review PDF language before using a different calibration artifact")
    p = lambda text, name="body": Paragraph(text, style[name])
    story = [p("A PRACTICAL DECISION, WITH ITS LIMITS ATTACHED", "label"),
             p("Should you move<br/>your outdoor event?", "title"),
             p("AirWindow Mumbai", "subtitle"),
             p("A confidence-aware activity scheduler for school sports coordinators and outdoor-event organisers."),
             screenshot(desktop, 315), Spacer(1, 10),
             p("Real application screenshot. Forecast values come from the participant model artifact; no synthetic production data." , "small"),
             p("Compare your original booking with complete alternatives. See the predicted difference, then see whether historical evidence is strong enough to act on it."),
             p("Current evidence is uncalibrated. A lower forecast is not a guarantee, and the product is allowed to abstain.", "callout"),
             PageBreak()]
    story += [p("01 / THE PLANNING WORKFLOW", "label"),
              p("A booking is the starting point.", "heading"),
              p("A coordinator has a two-hour event already scheduled. It can move between an earliest start and latest finish. AirWindow keeps that original visible while it compares the available options."),
              table([
                  ["Configure", "Choose one actual monitor, original start, duration 1/2/3h and feasible range."],
                  ["Compare", "Every candidate requires complete consecutive hourly forecasts. Show mean, maximum, peak hour and difference from the original."],
                  ["Assess evidence", "Show a prominent decision state, comparable support and validation limits. Do not turn numerical rank into certainty."],
                  ["Replay", "Inspect what a genuine historical forecast knew, its selected slot and subsequent actual observations."],
                  ["Share", "Print a one-page event brief with comparison, model version, timestamps and limitations."],
              ], style, [112, CONTENT_WIDTH-112]), Spacer(1, 14),
              p("Four states, with permission to abstain", "subhead"),
              p("<b>ROBUST IMPROVEMENT</b> is reserved for independently validated decision reliability. <b>TENTATIVE IMPROVEMENT</b> identifies an unproven numerical alternative. <b>NO CLEAR WINNER</b> permits ties or indistinguishable options. <b>INSUFFICIENT EVIDENCE</b> makes missing comparable support explicit."),
              p("Why this is distinctive", "subhead"),
              p("IITM/SAFAR, Google Air View+, Google Air Quality API, London alerts and AirQo already provide forecasts, local information or decision support. AirWindow's narrower contribution is the original-event constraint, paired historical decision replay and honest abstention. This is a product hypothesis, not a first-in-Mumbai claim."),
              p("The four supported stations are Borivali East, Malad West, Byculla and Shivaji Nagar. A monitor may not represent nearby streets. No route, heatmap, medical, safe-window or personal-exposure claim is made.", "small"),
              PageBreak()]
    story += [p("02 / HISTORICAL DECISION REPLAY", "label"),
              p("Show the forecast.<br/>Then show what happened.", "heading"),
              screenshot(replay_image, 240), Spacer(1, 9),
              p("Real application replay. This displayed numerical choice was worse afterwards. Subsequent observations are retrospective outcomes, kept separate from the live artifact; the table below includes all declared cases.", "small"),
              table([
                  ["All declared cases", f"{summary['cases']:,} cases across {summary['origins']} forecast origins"],
                  ["Observed coverage", f"{summary['paired_outcome_cases']:,} paired original/selected outcomes; {summary['missing_outcome_cases']:,} missing outcomes retained"],
                  ["Numerical alternatives", f"{summary['selected_alternative_cases']:,} lower-forecast alternatives with paired observations"],
                  ["Lower afterwards", f"{summary['lower_observed_fraction']*100:.2f}% of those numerical alternatives had lower later observed PM2.5"],
                  ["Realised difference", f"Median selected minus original: {summary['median_realised_difference']:.2f} µg/m³ for numerical alternatives"],
                  ["Hindsight gap", f"Median {summary['hindsight_gap_median']:.2f} µg/m³ when every feasible observed comparison is complete ({summary['complete_hindsight_cases']:,} cases); {summary['missing_hindsight_cases']:,} paired cases unavailable"],
              ], style, [124, CONTENT_WIDTH-124]), Spacer(1, 8),
              p("These are descriptive retrospective outcomes, not a probability for today's event, a measured health benefit or a calibrated recommendation. Calibrated recommendations: zero.", "callout"),
              PageBreak()]
    story += [p("03 / REPRODUCIBLE EVIDENCE", "label"),
              p("The evidence chain is inspectable.", "heading"),
              p("The declared scenario uses a 09:00 original booking, 08:00-18:00 feasible range, durations 1/2/3 hours, both target days, all four stations and every matched OOF origin. Numerical selection occurs before inspecting outcomes. Missing observations remain in coverage."),
              p("Forecasts are genuine retrospective rolling-origin backtests with a frozen PM cutoff. They were generated on 8 November, using simulated historical origins and an interval-end availability proxy. They are not archived operational first-publication vintages."),
              p("Underlying P_fix full-target raw-scale RMSE: 757.9880 on 11,001 development rows, 15.7963 on 1,400 later rows. Eight extreme labels drive 99.846% of development squared error; later rows have no such extremes. These populations are not interchangeable.", "small"),
              table([
                  ["Chronological split", "69 development origins; 8 later confirmation origins. Cases overlap within origins and are not independent samples."],
                  ["Later-origin diagnostic", f"{confirm['cases']} declared cases, {confirm['paired_outcome_cases']} paired outcomes, {confirm['selected_alternative_cases']} numerical alternatives; {confirm['lower_observed_fraction']*100:.2f}% lower afterwards."],
                  ["Dependence", "Exploratory resampling uses contiguous blocks of four forecast origins, not independent hourly errors."],
                  ["Calibration limit", "Later historical origins had prior analyst exposure. No independent calibration, live probability or uncertainty interval is claimed."],
                  ["Lead limit", "OOF issue equals PM cutoff at 193-240h lead. The current live issue is later than the PM cutoff; matching PM age does not establish matching issue-lead calibration."],
              ], style, [124, CONTENT_WIDTH-124]), Spacer(1, 12),
              p("Current forecast provenance", "subhead"),
              p(f"Model: P_fix / TASK008 provisional. Issue: {forecast['model_issue_time_ist']}. PM-history cutoff and latest station observation: {forecast['pm_history_cutoff_ist']}. No weather was used. Final official refresh remains pending."),
              p(f"Training SHA-256: {manifest['training_data_sha256']}<br/>Prediction SHA-256: {manifest['prediction_sha256']}", "small"),
              PageBreak()]
    story += [p("04 / ARCHITECTURE, TOOLS AND HANDOFF", "label"),
              p("A stable demo, without a live API.", "heading"),
              ArchitectureFlow(), Spacer(1, 13),
              p("Google tools: Firebase Hosting Spark configuration and a Colab-compatible reproducibility notebook. The notebook is not a live application dependency."),
              p("Deployment status", "subhead"),
              p("The application runs locally and static deployment configuration is prepared. Firebase deployment is pending authenticated CLI/project access. No billing was enabled, and no public hosting URL or cloud-notebook execution is claimed."),
              p("Working source and reproducibility", "subhead"),
              p('<link href="https://github.com/acchasujal/aqi/tree/feature/task008-final-gap-execution" color="#226D5A">Source: github.com/acchasujal/aqi - existing feature branch</link><br/>Run/build instructions, tests and notebook: apps/airwindow/<br/>Method, red-team review, real screenshots and submission checklist: reports/creative_submission/'),
              p("Selected primary references", "subhead"),
              p('<link href="https://www.tropmet.res.in/project_details.php?position=7&amp;project_id=3">IITM SAFAR project</link> · <link href="https://developers.google.com/maps/documentation/air-quality/forecast">Google Air Quality API</link> · <link href="https://airqo.africa/products/ai-platform">AirQo AI Platform</link><br/><link href="https://www.london.gov.uk/programmes-strategies/environment-and-climate-change/pollution-and-air-quality/models-and-alerts-air-quality">London City Hall alerts</link> · <link href="https://www.breathelondon.org/sensors/join-the-breathe-london-network">Breathe London</link> · <link href="https://firebase.google.com/docs/hosting/usage-quotas-pricing">Firebase Hosting quotas</link>', "small"),
              p("Data and use limits", "subhead"),
              p("Uses official challenge data and genuine model artifacts; no extra environmental dataset is required. Four stations do not support street/building predictions. No user interviews, measured health benefit, award guarantee, deployment or form-processing result is invented. Consult official CPCB/government guidance for health decisions."),
              p("Creative deadline: 13 November 2026, 18:29 GMT / 23:59 IST. Recheck the official form and submit through the human entrant; this package is not submission confirmation.", "small")]
    output.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(output), pagesize=A4, rightMargin=42, leftMargin=42,
                            topMargin=53, bottomMargin=47, title="AirWindow Mumbai 2.0",
                            author="AirWindow Mumbai", subject="Auditable outdoor event scheduling")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    if output.stat().st_size >= 10_000_000:
        raise ValueError("Submission PDF exceeds 10 MB")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--desktop", type=Path, required=True)
    parser.add_argument("--replay", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "reports/creative_submission/AIRWINDOW_2_SUBMISSION.pdf")
    args = parser.parse_args()
    make_pdf(args.output, args.desktop, args.replay)
    import pypdfium2
    from pypdf import PdfReader

    render_dir = ROOT / "data/processed/airwindow_pdf_render"
    render_dir.mkdir(parents=True, exist_ok=True)
    document = pypdfium2.PdfDocument(str(args.output))
    for index, page in enumerate(document):
        page.render(scale=1.5).to_pil().save(render_dir / f"page-{index+1}.png")
    reader = PdfReader(args.output)
    pages = [page.extract_text() for page in reader.pages]
    audit = {"file": args.output.name, "bytes": args.output.stat().st_size,
             "pages": len(reader.pages), "sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
             "render_directory": render_dir.relative_to(ROOT).as_posix(),
             "text_characters_per_page": [len(text) for text in pages],
             "source_screenshots": [str(args.desktop), str(args.replay)],
             "source_screenshot_sha256": {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                                           for path in (args.desktop, args.replay)},
             "visual_inspection": "PENDING until page PNGs are reviewed"}
    args.output.with_suffix(".audit.json").write_text(json.dumps(audit, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
