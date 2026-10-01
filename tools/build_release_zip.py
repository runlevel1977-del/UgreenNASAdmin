#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Erzeugt ein Release-ZIP mit zwei Unterordnern:

  <Name>/source/    — Quellen + Build-Skripte + fertige EXE unter dist/
  <Name>/installer/ — Inno-Setup-Installer (*.exe aus installer/output/)

Voraussetzungen:
  - dist/UgreenNASAdmin.exe muss existieren (z. B. nach ``python builder.py``).
  - installer/output/*.exe optional; fehlt eine Setup-EXE, liegt eine README im Ordner.

Ausgabe: release/UgreenNASAdmin_v<Version>_release.zip (Version aus ugreen_app/nas_manager.py).
"""

from __future__ import annotations

import re
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.release_source_guard import release_source_state, reject_runtime_files, export_committed_sources
NAS_MANAGER = ROOT / "ugreen_app" / "nas_manager.py"
DIST_DIR = ROOT / "dist" / "UgreenNASAdmin"
DIST_EXE = DIST_DIR / "UgreenNASAdmin.exe"
INSTALLER_OUT = ROOT / "installer" / "output"
RELEASE_DIR = ROOT / "release"

def _read_version() -> str:
    raw = NAS_MANAGER.read_text(encoding="utf-8", errors="replace")
    m = re.search(r'__version__\s*=\s*["\']([0-9]+(?:\.[0-9]+)*)["\']', raw)
    if not m:
        raise SystemExit(f"Konnte __version__ nicht in {NAS_MANAGER} finden.")
    return m.group(1)


def main() -> int:
    ver = _read_version()
    if not DIST_EXE.is_file():
        print(f"FEHLER: {DIST_EXE} fehlt — zuerst ``python packaging/builder.py`` ausführen.", file=sys.stderr)
        return 2

    try:
        source_state = release_source_state(ROOT, ver)
        reject_runtime_files(DIST_DIR)
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(f"FEHLER: {exc}", file=sys.stderr)
        return 2
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    bundle_name = f"UgreenNASAdmin_v{ver}_release"

    with tempfile.TemporaryDirectory(prefix="ugrel_") as td:
        tmp = Path(td)
        base = tmp / bundle_name
        src_root = base / "source"
        inst = base / "installer"
        src_root.mkdir(parents=True)
        inst.mkdir(parents=True)

        # Only the exact committed source tree, never ignored local settings.
        export_committed_sources(ROOT, src_root, source_state)

        # dist: kompletter One-Dir-Ordner (EXE + DLLs)
        dist_dst = src_root / "dist" / "UgreenNASAdmin"
        if dist_dst.exists():
            shutil.rmtree(dist_dst)
        shutil.copytree(DIST_DIR, dist_dst)

        # Installer: nur Setup zur aktuellen Version (keine alten Builds im ZIP)
        setup_ver = INSTALLER_OUT / f"UgreenNASAdmin_setup_{ver}.exe"
        if setup_ver.is_file():
            shutil.copy2(setup_ver, inst / setup_ver.name)
        else:
            (inst / "README_INSTALLER_BAUEN.txt").write_text(
                f"Keine passende Setup-EXE: erwartet installer/output/UgreenNASAdmin_setup_{ver}.exe\n\n"
                "1) Im Projektroot: python packaging/builder.py\n"
                "2) installer/UgreenNASAdmin_installer.iss: MyAppVersion prüfen\n"
                "3) installer/BUILD_INSTALLER.ps1 (oder Inno Setup GUI) ausführen\n"
                "4) Dieses Skript erneut: python tools/build_release_zip.py\n",
                encoding="utf-8",
            )

        (base / "LIESMICH_RELEASE.txt").write_text(
            f"Ugreen NAS Admin — Release-Paket v{ver}\n\n"
            "source/\n"
            "  Quellcode und Dateien zum Selbstbauen der App (Python + PyInstaller).\n"
            "  Kurz: pip install -r requirements.txt && pip install \"paramiko>=3.0\"\n"
            "  (keyring steht in requirements.txt — Passwort im Windows-Tresor)\n"
            "  Empfohlen: Python 3.12 (packaging/builder.py bevorzugt py -3.12; optional\n"
            "  UGREEN_BUILD_PYTHON=… setzen). Hilfsmodul: tools/build_python.py\n"
            "  Dann im Ordner source/: python packaging/builder.py\n"
            "  Die fertige Portable-EXE liegt zusätzlich unter source/dist/ (Kopie vom Build).\n\n"
            "installer/\n"
            "  Windows-Setup (Inno Setup), falls beim Packen vorhanden.\n"
            "  Neu bauen: installer/BUILD_INSTALLER.ps1 nach packaging/builder.py; Version in\n"
            "  installer/UgreenNASAdmin_installer.iss (#define MyAppVersion) anpassen.\n\n"
            "Installer: gespeicherte Verbindungen (.json) mitnehmen\n"
            "  Von alter EXE/Installation die Konfig-JSONs übernehmen, z. B.:\n"
            "  nas_admin_connection.json, app_settings.json, telegram_notify.json,\n"
            "  qnap_smb_prefs.json, nas_watch_local.json, nas_daily_report_local.json.\n"
            "  Ziel: Ordner der neuen UgreenNASAdmin.exe (z. B. unter Programme) NUR,\n"
            "  wenn die App dort schreiben darf. Üblich bei Installation unter\n"
            "  „Programme“: Konfiguration liegt unter\n"
            "  %LOCALAPPDATA%\\UgreenNASAdmin\\\n"
            "  — JSONs dorthin kopieren (App vorher beenden), dann neu starten.\n\n",
            encoding="utf-8",
        )

        out_zip = RELEASE_DIR / f"{bundle_name}.zip"
        # Build elsewhere; preserve a prior release ZIP if packing fails.
        staged_zip = shutil.make_archive(str(tmp / "completed-release"), "zip", root_dir=base.parent, base_dir=bundle_name)
        fd, staged_destination = tempfile.mkstemp(prefix=".ugreen-release-", suffix=".zip", dir=RELEASE_DIR)
        os.close(fd)
        try:
            shutil.copyfile(staged_zip, staged_destination)
            os.replace(staged_destination, out_zip)
        finally:
            if os.path.exists(staged_destination):
                os.unlink(staged_destination)

    print(f"OK: {out_zip}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
