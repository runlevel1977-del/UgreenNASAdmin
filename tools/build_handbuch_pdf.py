#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build HANDBUCH.pdf from HANDBUCH.md using reportlab."""

from __future__ import annotations

from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "HANDBUCH.md"
OUT = ROOT / "HANDBUCH.pdf"


def _register_fonts() -> tuple[str, str]:
    # Priorisiert moderne UI-Schrift für angenehme Lesbarkeit.
    pairs = [
        ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/segoeuib.ttf"),
        ("C:/Windows/Fonts/calibri.ttf", "C:/Windows/Fonts/calibrib.ttf"),
        ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
    ]
    for regular, bold in pairs:
        p_regular = Path(regular)
        p_bold = Path(bold)
        if p_regular.is_file() and p_bold.is_file():
            regular_name = f"ManualRegular_{p_regular.stem}"
            bold_name = f"ManualBold_{p_bold.stem}"
            pdfmetrics.registerFont(TTFont(regular_name, str(p_regular)))
            pdfmetrics.registerFont(TTFont(bold_name, str(p_bold)))
            return regular_name, bold_name
    return "Helvetica", "Helvetica-Bold"


def _build_story(md_text: str):
    base_font, bold_font = _register_fonts()
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle(
        "H1",
        parent=styles["Heading1"],
        fontName=bold_font,
        fontSize=22,
        leading=26,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=10,
    )
    h2 = ParagraphStyle(
        "H2",
        parent=styles["Heading2"],
        fontName=bold_font,
        fontSize=14.5,
        leading=19,
        textColor=colors.HexColor("#1d4ed8"),
        spaceBefore=10,
        spaceAfter=5,
    )
    body = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontName=base_font,
        fontSize=10.6,
        leading=14.5,
        textColor=colors.HexColor("#111827"),
        spaceAfter=4.5,
    )
    bullet = ParagraphStyle(
        "Bullet",
        parent=body,
        leftIndent=12,
        bulletIndent=3,
        spaceAfter=3.5,
    )

    story = []
    para_buf: list[str] = []

    def _escape(text: str) -> str:
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def flush_paragraph():
        if not para_buf:
            return
        txt = " ".join(x.strip() for x in para_buf if x.strip())
        if txt:
            safe = _escape(txt)
            story.append(Paragraph(safe, body))
        para_buf.clear()

    for raw in md_text.splitlines():
        line = raw.rstrip()
        if line.startswith("# "):
            flush_paragraph()
            story.append(Paragraph(_escape(line[2:].strip()), h1))
            story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#cbd5e1"), spaceBefore=2, spaceAfter=8))
            continue
        if line.startswith("## "):
            flush_paragraph()
            story.append(Spacer(1, 4))
            story.append(Paragraph(_escape(line[3:].strip()), h2))
            continue
        if not line.strip():
            flush_paragraph()
            continue
        if line.strip().startswith("- "):
            flush_paragraph()
            story.append(Paragraph(_escape("• " + line.strip()[2:]), bullet))
        else:
            para_buf.append(line)
    flush_paragraph()
    return story


def _draw_page_number(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(colors.HexColor("#6b7280"))
    canvas.drawRightString(A4[0] - 16 * mm, 10 * mm, f"Seite {doc.page}")
    canvas.restoreState()


def main() -> int:
    if not SRC.is_file():
        raise FileNotFoundError(f"missing source: {SRC}")
    text = SRC.read_text(encoding="utf-8", errors="replace")
    story = _build_story(text)
    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=A4,
        leftMargin=17 * mm,
        rightMargin=17 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title="Ugreen NAS Admin Handbuch",
    )
    doc.build(story, onFirstPage=_draw_page_number, onLaterPages=_draw_page_number)
    print(f"written: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
