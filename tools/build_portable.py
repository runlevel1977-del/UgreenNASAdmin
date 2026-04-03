# -*- coding: utf-8 -*-
"""Baut die EXE im Projektroot und legt eine portable Kopie unter MEINE_APPS_PORTABLE ab."""
from __future__ import annotations

import importlib.util
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Ziel: gemeinsamer Ordner für alle portablen Apps (Umgebungsvariable überschreibt Basisordner)
_PORTABLE_BASE = Path(
    os.environ.get("MEINE_APPS_PORTABLE", r"D:\APP PROJEKTE\MEINE_APPS_PORTABLE")
)
PORTABLE = _PORTABLE_BASE / "UgreenNASAdmin"
DIST_EXE = ROOT / "dist" / "UgreenNASAdmin.exe"
CHANGELOG = ROOT / "CHANGELOG.md"


def _version() -> str:
    spec = importlib.util.spec_from_file_location(
        "nas_manager_v", ROOT / "ugreen_app" / "nas_manager.py"
    )
    if spec and spec.loader:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return getattr(mod, "__version__", "?")
    return "?"


def main() -> None:
    sys.path.insert(0, str(ROOT))
    import builder  # noqa: E402

    print("=== Portable: EXE bauen (Projektroot) ===")
    builder.build()

    if not DIST_EXE.is_file():
        raise SystemExit(f"Fehlt nach Build: {DIST_EXE}")

    ver = _version()
    if PORTABLE.is_dir():
        shutil.rmtree(PORTABLE)
    PORTABLE.mkdir(parents=True)

    shutil.copy2(DIST_EXE, PORTABLE / "UgreenNASAdmin.exe")
    if CHANGELOG.is_file():
        shutil.copy2(CHANGELOG, PORTABLE / "CHANGELOG.md")

    readme = PORTABLE / "README_PORTABLE.txt"
    readme.write_text(
        f"""Ugreen NAS Admin — portable Ordner (privater Build)
Version laut nas_manager.py: {ver}

Start: UgreenNASAdmin.exe doppelklicken.
Konfiguration: nas_admin_connection.json wird neben der EXE angelegt (nicht mitliefern/teilen).

Details zu Releases: CHANGELOG.md (Kurzfassung) bzw. oeffentlich/CHANGELOG.md fuer die ausfuehrliche oeffentliche Notiz.

Zielordner: {_PORTABLE_BASE}\\UgreenNASAdmin\\
(Optional: Umgebungsvariable MEINE_APPS_PORTABLE setzen, um den Basisordner zu aendern.)

Build erzeugt mit: python tools/build_portable.py
""",
        encoding="utf-8",
    )

    print(f"OK portable -> {PORTABLE} (Version {ver})")


if __name__ == "__main__":
    main()
