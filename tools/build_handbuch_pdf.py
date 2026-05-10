#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build HANDBUCH.pdf from HANDBUCH.md (Stil wie generate_handbuch_v2 — siehe handbuch_pdf_from_md)."""

from __future__ import annotations

import sys
from pathlib import Path

_TOOLS = Path(__file__).resolve().parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from handbuch_pdf_from_md import build_pdf

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "HANDBUCH.md"
OUT = ROOT / "HANDBUCH.pdf"


def main() -> int:
    return build_pdf(src=SRC, out=OUT, lang="de", pdf_title="Ugreen NAS Admin — Handbuch")


if __name__ == "__main__":
    raise SystemExit(main())
