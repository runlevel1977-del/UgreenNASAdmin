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
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAS_MANAGER = ROOT / "ugreen_app" / "nas_manager.py"
DIST_EXE = ROOT / "dist" / "UgreenNASAdmin.exe"
INSTALLER_OUT = ROOT / "installer" / "output"
RELEASE_DIR = ROOT / "release"

ROOT_FILES = (
    "ugreen_nas_admin.py",
    "nas_ssh.py",
    "nas_utils.py",
    "builder.py",
    "create_icon.py",
    "UgreenNASAdmin.spec",
    "requirements.txt",
    "LICENSE",
    "README.md",
    "CHANGELOG.md",
    "nas_icon.ico",
    "nas_icon_app.png",
    "HANDBUCH.md",
    "HANDBUCH_STRUKTURIERT.md",
    "HANDBOOK_EN.md",
    "HANDBUCH.pdf",
    "HANDBOOK_EN.pdf",
    "handbook_page_index.json",
)


def _read_version() -> str:
    raw = NAS_MANAGER.read_text(encoding="utf-8", errors="replace")
    m = re.search(r'__version__\s*=\s*["\']([0-9]+(?:\.[0-9]+)*)["\']', raw)
    if not m:
        raise SystemExit(f"Konnte __version__ nicht in {NAS_MANAGER} finden.")
    return m.group(1)


_SKIP_NAMES = frozenset(
    {
        "__pycache__",
        ".mypy_cache",
        "app_settings.json",
        "nas_admin_connection.json",
        "telegram_notify.json",
        "nas_watch_local.json",
        "nas_daily_report_local.json",
        "transfer_log.txt",
        "last_github_update_check.txt",
    }
)


def _ignore_ugreen_app(_dirpath: str, names: list[str]) -> set[str]:
    out: set[str] = set()
    for n in names:
        if n in _SKIP_NAMES or n.endswith(".pyc"):
            out.add(n)
    return out


def main() -> int:
    ver = _read_version()
    if not DIST_EXE.is_file():
        print(f"FEHLER: {DIST_EXE} fehlt — zuerst ``python builder.py`` ausführen.", file=sys.stderr)
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

        # Quellbaum
        shutil.copytree(
            ROOT / "ugreen_app",
            src_root / "ugreen_app",
            ignore=_ignore_ugreen_app,
        )
        for name in ROOT_FILES:
            src = ROOT / name
            if src.is_file():
                shutil.copy2(src, src_root / name)

        # dist nur die EXE (keine lokalen JSON/Logs aus dem Arbeits-dist)
        dist_dst = src_root / "dist"
        dist_dst.mkdir(parents=True)
        shutil.copy2(DIST_EXE, dist_dst / DIST_EXE.name)

        # Installer: nur Setup zur aktuellen Version (keine alten Builds im ZIP)
        setup_ver = INSTALLER_OUT / f"UgreenNASAdmin_setup_{ver}.exe"
        if setup_ver.is_file():
            shutil.copy2(setup_ver, inst / setup_ver.name)
        else:
            (inst / "README_INSTALLER_BAUEN.txt").write_text(
                f"Keine passende Setup-EXE: erwartet installer/output/UgreenNASAdmin_setup_{ver}.exe\n\n"
                "1) Im Projektroot: python builder.py\n"
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
            "  Optional: pip install keyring  (für PW-Tresor in der App)\n"
            "  Dann im Ordner source/: python builder.py\n"
            "  Die fertige Portable-EXE liegt zusätzlich unter source/dist/ (Kopie vom Build).\n\n"
            "installer/\n"
            "  Windows-Setup (Inno Setup), falls beim Packen vorhanden.\n"
            "  Neu bauen: installer/BUILD_INSTALLER.ps1 nach builder.py; Version in\n"
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

        out_base = RELEASE_DIR / bundle_name
        out_zip = RELEASE_DIR / f"{bundle_name}.zip"
        if out_zip.is_file():
            out_zip.unlink()

        shutil.make_archive(str(out_base), "zip", root_dir=tmp, base_dir=bundle_name)

    print(f"OK: {out_zip}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
