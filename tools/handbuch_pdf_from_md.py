#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Markdown → PDF für HANDBUCH.md / HANDBOOK_EN.md.

Visueller Stil angelehnt an „generate_handbuch_v2“ (Farben, Deckblatt, Kopf-/Fußzeile,
linke Akzentlinie). Inhalt kommt weiterhin aus Markdown — bei Erweiterungen des Handbuchs
genügt HANDBUCH*.md zu pflegen; dieser Builder mappt Überschriften & Blöcke konsistent
in denselben PDF-Stil.
"""

from __future__ import annotations

import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.platypus import HRFlowable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

# ── Palette & Maße (wie generate_handbuch_v2) ────────────────────────────────
PAGE_W, PAGE_H = A4
MARGIN = 2.0 * cm

C_DARK = colors.HexColor("#0F172A")
C_BLUE_MID = colors.HexColor("#2563EB")
C_TEAL = colors.HexColor("#0D9488")
C_GREY_LIGHT = colors.HexColor("#F1F5F9")
C_GREY_MID = colors.HexColor("#CBD5E1")
C_WHITE = colors.white
C_BLACK = colors.HexColor("#1E293B")
C_BORDER = colors.HexColor("#E2E8F0")
C_MUTED = colors.HexColor("#94A3B8")
ROOT = Path(__file__).resolve().parents[1]


def _read_app_version() -> str:
    p = ROOT / "ugreen_app" / "nas_manager.py"
    if not p.is_file():
        return "?"
    txt = p.read_text(encoding="utf-8", errors="replace")
    m = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', txt)
    return m.group(1).strip() if m else "?"


def register_fonts() -> tuple[str, str]:
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


def make_styles(base_font: str, bold_font: str) -> dict[str, ParagraphStyle]:
    styles = getSampleStyleSheet()
    return {
        "cover_h1": ParagraphStyle(
            "cover_h1",
            parent=styles["Normal"],
            fontName=bold_font,
            fontSize=34,
            textColor=C_WHITE,
            alignment=TA_CENTER,
            leading=42,
            spaceAfter=8,
        ),
        "cover_h2": ParagraphStyle(
            "cover_h2",
            parent=styles["Normal"],
            fontName=base_font,
            fontSize=15,
            textColor=colors.HexColor("#BFDBFE"),
            alignment=TA_CENTER,
            leading=20,
        ),
        "cover_ver": ParagraphStyle(
            "cover_ver",
            parent=styles["Normal"],
            fontName=base_font,
            fontSize=11,
            textColor=C_MUTED,
            alignment=TA_CENTER,
        ),
        "h1": ParagraphStyle(
            "h1",
            parent=styles["Heading1"],
            fontName=bold_font,
            fontSize=19,
            leading=24,
            textColor=C_DARK,
            spaceBefore=16,
            spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "h2",
            parent=styles["Heading2"],
            fontName=bold_font,
            fontSize=13,
            leading=17,
            textColor=C_BLUE_MID,
            spaceBefore=14,
            spaceAfter=5,
        ),
        "h3": ParagraphStyle(
            "h3",
            parent=styles["Heading3"],
            fontName=bold_font,
            fontSize=11,
            leading=14,
            textColor=C_TEAL,
            spaceBefore=10,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "body",
            parent=styles["BodyText"],
            fontName=base_font,
            fontSize=10,
            leading=15,
            textColor=C_BLACK,
            spaceAfter=5,
            alignment=TA_JUSTIFY,
        ),
        "bullet": ParagraphStyle(
            "bullet",
            parent=styles["BodyText"],
            fontName=base_font,
            fontSize=10,
            leading=15,
            textColor=C_BLACK,
            leftIndent=14,
            spaceAfter=4,
        ),
        "blockquote": ParagraphStyle(
            "blockquote",
            parent=styles["BodyText"],
            fontName=base_font,
            fontSize=9.5,
            leading=14,
            textColor=C_BLUE_MID,
            leftIndent=14,
            borderPadding=4,
            spaceAfter=6,
        ),
    }


def _sp(h: float = 0.35) -> Spacer:
    return Spacer(1, h * cm)


def cover_page(version: str, *, lang: str, st: dict[str, ParagraphStyle]) -> list:
    if lang == "de":
        titel2 = "Benutzerhandbuch"
        ver = f"Version {version}  ·  Deutsch"
        sub = "Erzeugt aus <b>HANDBUCH.md</b> — gleicher Stil wie das vollständige PDF-Layout (Farben, Rahmen)."
    else:
        titel2 = "User manual"
        ver = f"Version {version}  ·  English"
        sub = "Built from <b>HANDBOOK_EN.md</b> — same visual style as the full layout (colors, frames)."
    tw = PAGE_W - 2 * MARGIN
    bg = Table(
        [
            [Paragraph("Ugreen NAS Admin", st["cover_h1"])],
            [Paragraph(titel2, st["cover_h2"])],
            [_sp(0.35)],
            [Paragraph(ver, st["cover_ver"])],
            [Paragraph(sub, st["cover_ver"])],
        ],
        colWidths=[tw],
    )
    bg.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), C_DARK),
                ("TOPPADDING", (0, 0), (-1, -1), 22),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 22),
                ("LEFTPADDING", (0, 0), (-1, -1), 20),
                ("RIGHTPADDING", (0, 0), (-1, -1), 20),
            ]
        )
    )
    return [_sp(2.2), bg, PageBreak()]


class HandbuchPageFrame(pdfcanvas.Canvas):
    """Kopf-/Fußzeile + linke Akzentlinie ab Seite 2 (Seite 1 = Deckblatt)."""

    def __init__(
        self,
        *args,
        version: str,
        header_right: str,
        footer_center: str,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._saved: list[dict] = []
        self._version = version
        self._header_right = header_right
        self._footer_center = footer_center

    def showPage(self):
        self._saved.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._saved)
        for i, s in enumerate(self._saved):
            self.__dict__.update(s)
            self._draw_frame(i + 1, total)
            super().showPage()
        super().save()

    def _draw_frame(self, page_num: int, total: int):
        if page_num <= 1:
            return
        self.setFillColor(C_DARK)
        self.rect(0, PAGE_H - 1.05 * cm, PAGE_W, 1.05 * cm, fill=1, stroke=0)
        self.setFillColor(C_WHITE)
        self.setFont("Helvetica-Bold", 8.5)
        self.drawString(MARGIN, PAGE_H - 0.68 * cm, f"Ugreen NAS Admin v{self._version}")
        self.setFont("Helvetica", 8.5)
        self.drawRightString(PAGE_W - MARGIN, PAGE_H - 0.68 * cm, self._header_right)
        self.setFillColor(C_DARK)
        self.rect(0, 0, PAGE_W, 0.85 * cm, fill=1, stroke=0)
        self.setFillColor(C_WHITE)
        self.setFont("Helvetica", 8)
        self.drawCentredString(PAGE_W / 2, 0.28 * cm, self._footer_center)
        self.drawRightString(PAGE_W - MARGIN, 0.28 * cm, f"{page_num} / {total}")
        self.setFillColor(C_BLUE_MID)
        self.rect(0, 0.85 * cm, 0.25 * cm, PAGE_H - 1.9 * cm, fill=1, stroke=0)


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _md_inline_bold(s: str) -> str:
    """Ersetzt **fett** durch ReportLab <b>."""
    parts: list[str] = []
    cur = 0
    for m in re.finditer(r"\*\*(.+?)\*\*", s):
        parts.append(_escape(s[cur : m.start()]))
        parts.append(f"<b>{_escape(m.group(1))}</b>")
        cur = m.end()
    parts.append(_escape(s[cur:]))
    return "".join(parts)


def md_to_story(md_text: str, st: dict[str, ParagraphStyle]) -> list:
    story: list = []
    h1, h2, h3, body, bullet, bq = (
        st["h1"],
        st["h2"],
        st["h3"],
        st["body"],
        st["bullet"],
        st["blockquote"],
    )
    para_buf: list[str] = []

    def flush_paragraph():
        if not para_buf:
            return
        txt = " ".join(x.strip() for x in para_buf if x.strip())
        if txt:
            story.append(Paragraph(_md_inline_bold(txt), body))
        para_buf.clear()

    for raw in md_text.splitlines():
        line = raw.rstrip()
        if re.match(r"^---+\s*$", line):
            flush_paragraph()
            story.append(HRFlowable(width="100%", thickness=1, color=C_GREY_MID, spaceBefore=6, spaceAfter=10))
            continue
        if line.startswith("# "):
            flush_paragraph()
            story.append(Paragraph(_md_inline_bold(line[2:].strip()), h1))
            story.append(HRFlowable(width="100%", thickness=0.9, color=C_BORDER, spaceBefore=2, spaceAfter=10))
            continue
        if line.startswith("## "):
            flush_paragraph()
            story.append(Spacer(1, 3))
            story.append(Paragraph(_md_inline_bold(line[3:].strip()), h2))
            continue
        if line.startswith("### "):
            flush_paragraph()
            story.append(Paragraph(_md_inline_bold(line[4:].strip()), h3))
            continue
        if line.startswith("#### "):
            flush_paragraph()
            story.append(Paragraph(_md_inline_bold(line[5:].strip()), h3))
            continue
        if not line.strip():
            flush_paragraph()
            continue
        stripped = line.strip()
        if stripped.startswith("> "):
            flush_paragraph()
            story.append(Paragraph(_md_inline_bold(stripped[2:].strip()), bq))
            continue
        if stripped.startswith("- "):
            flush_paragraph()
            story.append(Paragraph("&#8226;  " + _md_inline_bold(stripped[2:].strip()), bullet))
            continue
        para_buf.append(line)
    flush_paragraph()
    return story


def canvas_factory(version: str, header_right: str, footer_center: str):
    def _maker(*args, **kwargs):
        return HandbuchPageFrame(
            *args,
            version=version,
            header_right=header_right,
            footer_center=footer_center,
            **kwargs,
        )

    return _maker


def build_pdf(
    *,
    src: Path,
    out: Path,
    lang: str,
    pdf_title: str,
) -> int:
    if not src.is_file():
        raise FileNotFoundError(f"missing source: {src}")
    version = _read_app_version()
    raw = src.read_text(encoding="utf-8", errors="replace")
    base_font, bold_font = register_fonts()
    st = make_styles(base_font, bold_font)

    story: list = []
    story.extend(cover_page(version, lang=lang, st=st))
    story.extend(md_to_story(raw, st))

    left_m = MARGIN + 0.25 * cm
    if lang == "de":
        hdr_r = "Benutzerhandbuch — aus Markdown"
        foot = "Ugreen NAS Admin Handbuch · Projekt-Dokumentation"
    else:
        hdr_r = "Manual — from Markdown"
        foot = "Ugreen NAS Admin handbook · project documentation"

    doc = SimpleDocTemplate(
        str(out),
        pagesize=A4,
        leftMargin=left_m,
        rightMargin=MARGIN,
        topMargin=1.3 * cm,
        bottomMargin=1.15 * cm,
        title=pdf_title,
        author="Ugreen NAS Admin",
    )
    doc.build(
        story,
        canvasmaker=canvas_factory(version, hdr_r, foot),
    )
    print(f"written: {out}")
    return 0
