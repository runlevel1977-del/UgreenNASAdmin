#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Translate HANDBUCH.md to HANDBOOK_EN.md using deep-translator."""

from __future__ import annotations

from pathlib import Path
from time import sleep

from deep_translator import GoogleTranslator


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "HANDBUCH.md"
OUT = ROOT / "HANDBOOK_EN.md"


def translate_line(tr: GoogleTranslator, line: str) -> str:
    raw = line.rstrip("\n")
    if not raw.strip():
        return ""
    # Keep markdown separators and code-like lines untouched.
    if raw.strip() in {"---", "```"}:
        return raw
    if raw.lstrip().startswith("`") and raw.rstrip().endswith("`"):
        return raw

    # Preserve markdown prefixes while translating text content.
    prefixes = ["### ", "## ", "# ", "- ", "1. ", "2. ", "3. ", "4. ", "5. ", "6. ", "7. ", "8. ", "9. "]
    for p in prefixes:
        if raw.startswith(p):
            txt = raw[len(p) :].strip()
            if not txt:
                return raw
            for _ in range(3):
                try:
                    return p + tr.translate(txt)
                except Exception:
                    sleep(0.35)
            return p + txt

    for _ in range(3):
        try:
            return tr.translate(raw)
        except Exception:
            sleep(0.35)
    return raw


def main() -> int:
    if not SRC.is_file():
        raise FileNotFoundError(f"missing source: {SRC}")
    tr = GoogleTranslator(source="de", target="en")
    lines = SRC.read_text(encoding="utf-8", errors="replace").splitlines()
    out_lines: list[str] = []
    for i, ln in enumerate(lines, 1):
        out_lines.append(translate_line(tr, ln))
        if i % 120 == 0:
            sleep(0.2)
    OUT.write_text("\n".join(out_lines).rstrip() + "\n", encoding="utf-8")
    print(f"written: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
