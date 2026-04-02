# -*- coding: utf-8 -*-
"""ZIP aus öffentlich/ für Forum-Upload (ohne .git, build, dist, __pycache__)."""
from __future__ import annotations

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "öffentlich"
if not PUBLIC.is_dir():
    PUBLIC = next((d for d in ROOT.iterdir() if d.is_dir() and "ffentlich" in d.name), PUBLIC)
SKIP_DIR_NAMES = {".git", "__pycache__", "build", "dist"}
SKIP_SUFFIXES = {".pyc", ".pyo"}
OUT = ROOT / "UgreenNASAdmin_v22.2.0_oeffentlich_forum.zip"
OUT_WITH_EXE = ROOT / "UgreenNASAdmin_v22.2.0_oeffentlich_mit_EXE.zip"


def zip_tree(*, include_exe: bool) -> Path:
    if not PUBLIC.is_dir():
        raise SystemExit(f"Nicht gefunden: {PUBLIC}")
    out = OUT_WITH_EXE if include_exe else OUT
    if out.exists():
        out.unlink()
    n = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in PUBLIC.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(PUBLIC)
            parts = rel.parts
            if any(p in SKIP_DIR_NAMES for p in parts):
                continue
            if path.suffix.lower() in SKIP_SUFFIXES:
                continue
            if not include_exe and path.suffix.lower() == ".exe":
                continue
            arc = Path("UgreenNASAdmin_public") / rel
            zf.write(path, arc.as_posix())
            n += 1
    print(f"OK {n} Dateien -> {out} ({out.stat().st_size // 1024} KB)")
    return out


def main() -> None:
    zip_tree(include_exe=False)
    zip_tree(include_exe=True)


if __name__ == "__main__":
    main()
