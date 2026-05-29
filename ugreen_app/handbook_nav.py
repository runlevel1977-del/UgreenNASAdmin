# -*- coding: utf-8 -*-
"""Handbuch-Navigation: Tab → Kapitel, PDF-Seite, Markdown-Abschnitt."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

# Kapitelnummern in HANDBUCH.md / HANDBOOK_EN.md (## N. …)
TAB_HANDBOOK_CHAPTER: dict[str, str] = {
    "settings": "5",
    "dashboard": "6",
    "scripts": "7",
    "explorer": "9",
    "nas2nas": "10",
    "devices": "11",
    "docker": "12",
    "health": "13",
    "login_track": "14",
    "nas_admin": "15",
    "storage": "16",
    "acl": "17",
    "snapshots": "18",
    "backup": "19",
}

_INDEX_CACHE: dict | None = None


def ui_lang_to_handbook_lang(code: str) -> str:
    return "de" if str(code or "de").lower().startswith("de") else "en"


def handbook_md_filename(lang: str) -> str:
    return "HANDBUCH.md" if lang == "de" else "HANDBOOK_EN.md"


def handbook_pdf_filename(lang: str) -> str:
    return "HANDBUCH.pdf" if lang == "de" else "HANDBOOK_EN.pdf"


def load_page_index(index_path: str | Path) -> dict:
    global _INDEX_CACHE
    p = Path(index_path)
    if not p.is_file():
        return {}
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if isinstance(raw, dict) and ("de" in raw or "en" in raw):
        return raw
    return {}


def chapter_page(page_index: dict, lang: str, chapter: str) -> int | None:
    lang_map = page_index.get(lang) if isinstance(page_index, dict) else None
    if not isinstance(lang_map, dict):
        return None
    val = lang_map.get(str(chapter))
    try:
        pg = int(val)
        return pg if pg > 0 else None
    except (TypeError, ValueError):
        return None


def extract_chapter_markdown(md_text: str, chapter: str) -> tuple[str, str]:
    """Liefert (Titel, Abschnitt-Text) für Kapitel N bis zum nächsten ##."""
    ch = str(chapter).strip()
    lines = md_text.splitlines()
    start = None
    title = ""
    for i, line in enumerate(lines):
        m = re.match(rf"^##\s+{re.escape(ch)}\.\s*(.+)$", line.strip())
        if m:
            start = i
            title = m.group(1).strip()
            break
    if start is None:
        return "", ""
    out: list[str] = []
    for line in lines[start + 1 :]:
        if re.match(r"^##\s+\d+\.", line.strip()):
            break
        out.append(line)
    body = "\n".join(out).strip()
    return title, body


def open_pdf_at_page(pdf_path: str | Path, page: int) -> bool:
    """PDF bei Seite öffnen (Windows: Sumatra/Edge/Adobe). Gibt True zurück wenn Seitenjump versucht."""
    path = os.path.abspath(str(pdf_path))
    if not os.path.isfile(path):
        return False
    pg = max(1, int(page))

    if sys.platform == "win32":
        sumatra_candidates = [
            os.path.expandvars(r"%LOCALAPPDATA%\SumatraPDF\SumatraPDF.exe"),
            r"C:\Program Files\SumatraPDF\SumatraPDF.exe",
            r"C:\Program Files (x86)\SumatraPDF\SumatraPDF.exe",
        ]
        for exe in sumatra_candidates:
            if os.path.isfile(exe):
                subprocess.Popen([exe, "-page", str(pg), path], close_fds=True)
                return True

        edge_candidates = [
            os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        ]
        uri = Path(path).as_uri() + f"#page={pg}"
        for edge in edge_candidates:
            if os.path.isfile(edge):
                subprocess.Popen([edge, uri], close_fds=True)
                return True

        adobe_candidates = [
            r"C:\Program Files\Adobe\Acrobat DC\Acrobat\Acrobat.exe",
            r"C:\Program Files (x86)\Adobe\Acrobat Reader DC\Reader\AcroRd32.exe",
            r"C:\Program Files\Adobe\Acrobat Reader DC\Reader\AcroRd32.exe",
        ]
        for adobe in adobe_candidates:
            if os.path.isfile(adobe):
                subprocess.Popen([adobe, "/A", f"page={pg}", path], close_fds=True)
                return True

        try:
            os.startfile(path)  # noqa: S606
            return False
        except OSError:
            return False

    if sys.platform == "darwin":
        try:
            subprocess.Popen(["open", path], close_fds=True)
            return False
        except OSError:
            return False

    try:
        subprocess.Popen(["xdg-open", path], close_fds=True)
        return False
    except OSError:
        return False
