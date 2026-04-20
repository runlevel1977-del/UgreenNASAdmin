# -*- coding: utf-8 -*-
"""Einmal-Sync: Hauptprojekt -> öffentlich/ (Quellen für Release-ZIP)."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = next((d for d in ROOT.iterdir() if d.is_dir() and "ffentlich" in d.name), None)
if PUBLIC is None:
    sys.exit("öffentlich/ nicht gefunden")

SKIP = {"__pycache__", ".pytest_cache"}


def _copytree(src: Path, dst: Path) -> None:
    if dst.is_dir():
        shutil.rmtree(dst)
    shutil.copytree(
        src,
        dst,
        ignore=shutil.ignore_patterns(*SKIP, "*.pyc"),
        dirs_exist_ok=False,
    )


def main() -> None:
    pairs = [
        (ROOT / "ugreen_app", PUBLIC / "ugreen_app"),
        (ROOT / "nas_ssh.py", PUBLIC / "nas_ssh.py"),
        (ROOT / "nas_utils.py", PUBLIC / "nas_utils.py"),
        (ROOT / "ugreen_nas_admin.py", PUBLIC / "ugreen_nas_admin.py"),
        (ROOT / "UgreenNASAdmin.spec", PUBLIC / "UgreenNASAdmin.spec"),
        (ROOT / "builder.py", PUBLIC / "builder.py"),
        (ROOT / "RUN_BUILDER.bat", PUBLIC / "RUN_BUILDER.bat"),
        (ROOT / "create_icon.py", PUBLIC / "create_icon.py"),
    ]
    for src, dst in pairs:
        if not src.is_file() and not src.is_dir():
            print("skip missing:", src)
            continue
        print(src.name, "->", dst.relative_to(PUBLIC))
        if src.is_dir():
            _copytree(src, dst)
        else:
            shutil.copy2(src, dst)
    print("OK sync ->", PUBLIC)


if __name__ == "__main__":
    main()
