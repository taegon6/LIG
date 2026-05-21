from __future__ import annotations

import argparse
import re
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "docs" / "report.md"
DEFAULT_OUTPUT = PROJECT_ROOT / "output" / "pdf" / "aegis-swarm-dah2026-report.pdf"


def _register_fonts() -> tuple[str, str, str]:
    windows_font_dir = Path("C:/Windows/Fonts")
    regular = windows_font_dir / "malgun.ttf"
    bold = windows_font_dir / "malgunbd.ttf"
    mono = windows_font_dir / "consola.ttf"

    if regular.exists():
        pdfmetrics.registerFont(TTFont("MalgunGothic", str(regular)))
        regular_name = "MalgunGothic"
    else:
        regular_name = "Helvetica"

    if bold.exists():
        pdfmetrics.registerFont(TTFont("MalgunGothic-Bold", str(bold)))
        bold_name = "MalgunGothic-Bold"
    else:
        bold_name = "Helvetica-Bold"

    if mono.exists():
        pdfmetrics.registerFont(TTFont("Consolas", str(mono)))
        mono_name = "Consolas"
    else:
        mono_name = "Courier"

    return regular_name, bold_name, mono_name


def _styles() -> dict[str, ParagraphStyle]:
    font, bold_font, mono_font = _register_fonts()
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "AegisTitle",
            parent=base["Title"],
            fontName=bold_font,
            fontSize=22,
            leading=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#111827"),
            spaceAfter=10,
        ),
        "subtitle": ParagraphStyle(
            "AegisSubtitle",
            parent=base["BodyText"],
            fontName=font,
            fontSize=10,
            leading=15,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#4b5563"),
            spaceAfter=18,
        ),
        "h1": ParagraphStyle(
            "AegisH1",
            parent=base["Heading1"],
            fontName=bold_font,
            fontSize=17,
            leading=23,
            textColor=colors.HexColor("#0f172a"),
            spaceBefore=10,
            spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "AegisH2",
            parent=base["Heading2"],
            fontName=bold_font,
            fontSize=13,
            leading=18,
            textColor=colors.HexColor("#1f2937"),
            spaceBefore=12,
            spaceAfter=6,
        ),
        "h3": ParagraphStyle(
            "AegisH3",
            parent=base["Heading3"],
            fontName=bold_font,
            fontSize=11,
            leading=16,
            textColor=colors.HexColor("#374151"),
            spaceBefore=8,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "AegisBody",
            parent=base["BodyText"],
            fontName=font,
            fontSize=9.5,
            leading=15,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#111827"),
            spaceAfter=6,
        ),
        "bullet": ParagraphStyle(
            "AegisBullet",
            parent=base["BodyText"],
            fontName=font,
            fontSize=9.2,
            leading=14,
            leftIndent=0,
            firstLineIndent=0,
            textColor=colors.HexColor("#111827"),
        ),
        "code": ParagraphStyle(
            "AegisCode",
            parent=base["Code"],
            fontName=mono_font,
            fontSize=7.6,
            leading=10,
            backColor=colors.HexColor("#f3f4f6"),
            borderColor=colors.HexColor("#e5e7eb"),
            borderWidth=0.5,
            borderPadding=5,
            textColor=colors.HexColor("#111827"),
            spaceBefore=4,
            spaceAfter=8,
        ),
        "footer": ParagraphStyle(
            "AegisFooter",
            parent=base["BodyText"],
            fontName=font,
            fontSize=7.5,
            leading=9,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#6b7280"),
        ),
    }


def _inline_markdown(text: str) -> str:
    text = escape(text)
    text = re.sub(r"`([^`]+)`", r'<font name="Consolas">\1</font>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    return text.replace("  ", "&nbsp;&nbsp;")


def _flush_list(items: list[str], story: list, styles: dict[str, ParagraphStyle]) -> None:
    if not items:
        return

    flowables = [
        ListItem(Paragraph(_inline_markdown(item), styles["bullet"]), leftIndent=10)
        for item in items
    ]
    story.append(
        ListFlowable(
            flowables,
            bulletType="bullet",
            start="circle",
            leftIndent=14,
            bulletFontName=styles["body"].fontName,
            bulletFontSize=6,
            bulletColor=colors.HexColor("#2563eb"),
        )
    )
    story.append(Spacer(1, 2 * mm))
    items.clear()


def markdown_to_story(markdown: str, styles: dict[str, ParagraphStyle]) -> list:
    story: list = []
    list_items: list[str] = []
    code_lines: list[str] = []
    in_code = False

    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()

        if line.startswith("```"):
            if in_code:
                story.append(Preformatted("\n".join(code_lines), styles["code"]))
                code_lines.clear()
                in_code = False
            else:
                _flush_list(list_items, story, styles)
                in_code = True
            continue

        if in_code:
            code_lines.append(line)
            continue

        if not line.strip():
            _flush_list(list_items, story, styles)
            story.append(Spacer(1, 2 * mm))
            continue

        if line.startswith("# "):
            _flush_list(list_items, story, styles)
            title = line[2:].strip()
            story.append(Paragraph(_inline_markdown(title), styles["title"]))
            story.append(
                Paragraph(
                    "DAH 2026 예선 제출 보고서 초안 | Safe Local Red-Blue Self-Play MVP",
                    styles["subtitle"],
                )
            )
            story.append(
                HRFlowable(
                    width="100%",
                    thickness=0.8,
                    color=colors.HexColor("#d1d5db"),
                    spaceBefore=2,
                    spaceAfter=8,
                )
            )
            continue

        if line.startswith("## "):
            _flush_list(list_items, story, styles)
            story.append(Paragraph(_inline_markdown(line[3:].strip()), styles["h1"]))
            continue

        if line.startswith("### "):
            _flush_list(list_items, story, styles)
            story.append(Paragraph(_inline_markdown(line[4:].strip()), styles["h2"]))
            continue

        if line.startswith("#### "):
            _flush_list(list_items, story, styles)
            story.append(Paragraph(_inline_markdown(line[5:].strip()), styles["h3"]))
            continue

        bullet_match = re.match(r"^[-*]\s+(.*)$", line)
        numbered_match = re.match(r"^\d+\.\s+(.*)$", line)
        if bullet_match:
            list_items.append(bullet_match.group(1).strip())
            continue
        if numbered_match:
            list_items.append(numbered_match.group(1).strip())
            continue

        _flush_list(list_items, story, styles)
        story.append(Paragraph(_inline_markdown(line), styles["body"]))

    if in_code and code_lines:
        story.append(Preformatted("\n".join(code_lines), styles["code"]))
    _flush_list(list_items, story, styles)
    return story


def _page(canvas, doc) -> None:
    canvas.saveState()
    width, height = A4
    canvas.setStrokeColor(colors.HexColor("#e5e7eb"))
    canvas.setLineWidth(0.5)
    canvas.line(18 * mm, height - 17 * mm, width - 18 * mm, height - 17 * mm)
    canvas.line(18 * mm, 15 * mm, width - 18 * mm, 15 * mm)
    canvas.setFont("MalgunGothic" if "MalgunGothic" in pdfmetrics.getRegisteredFontNames() else "Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#6b7280"))
    canvas.drawString(18 * mm, height - 12 * mm, "Aegis-Swarm | DAH 2026 Preliminary Report")
    canvas.drawRightString(width - 18 * mm, 9 * mm, f"{doc.page}")
    canvas.restoreState()


def build_pdf(input_path: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    markdown = input_path.read_text(encoding="utf-8")
    styles = _styles()
    story = markdown_to_story(markdown, styles)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=22 * mm,
        bottomMargin=20 * mm,
        title="Aegis-Swarm DAH 2026 Preliminary Report",
        author="Aegis-Swarm Team",
    )
    doc.build(story, onFirstPage=_page, onLaterPages=_page)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the DAH submission report PDF.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    build_pdf(args.input, args.output)
    print(args.output)


if __name__ == "__main__":
    main()
