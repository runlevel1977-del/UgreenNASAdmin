#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Erzeugt ein Release-ZIP mit zwei Unterordnern:

  <Name>/source/    — Quellen + Build-Skripte + fertige EXE unter dist/
  <Name>/installer/ — Inno-Setup-Installer (*.exe aus installer/output/)

Voraussetzungen: --build-dir mit geprüftem BUILD_MANIFEST, Portable-EXE und
Installer aus dem öffentlichen, sauber getaggten Quellstand. Siehe
docs/PUBLIC_RELEASE_BINDING_DE.md. Lokale dist/-Dateien genügen nicht.

Ausgabe: release/UgreenNASAdmin_v<Version>_release.zip (Version aus ugreen_app/nas_manager.py).
"""

from __future__ import annotations

import re
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.release_source_guard import public_release_state, reject_runtime_files, export_committed_sources
from tools.reproducible_release import verify_record
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


def _pack_bundle(
    *,
    ver: str,
    source_state: dict,
    dist_dir: Path,
    installer_out: Path,
    manifest_src: Path,
) -> int:
    if manifest_src is None or not manifest_src.is_file():
        raise ValueError('A verified BUILD_MANIFEST is required for release packaging')
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
        if manifest_src is not None and manifest_src.is_file():
            shutil.copy2(manifest_src, base / "BUILD_MANIFEST.json")
            inventory = manifest_src.with_name('NATIVE_INVENTORY.json')
            if inventory.is_file():
                shutil.copy2(inventory, base / inventory.name)

        # dist: kompletter One-Dir-Ordner (EXE + DLLs)
        dist_dst = src_root / "dist" / "UgreenNASAdmin"
        if dist_dst.exists():
            shutil.rmtree(dist_dst)
        shutil.copytree(dist_dir, dist_dst)

        # Installer: nur Setup zur aktuellen Version (keine alten Builds im ZIP)
        setup_ver = installer_out / f"UgreenNASAdmin_setup_{ver}.exe"
        if setup_ver.is_file():
            shutil.copy2(setup_ver, inst / setup_ver.name)
            for extra in (Path(str(setup_ver) + ".sig"), Path(str(setup_ver) + ".release.json")):
                if extra.is_file():
                    shutil.copy2(extra, inst / extra.name)
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


def main_from_build_dir(build_dir: Path) -> int:
    ver = _read_version()
    dist_dir = build_dir / "portable"
    installer_out = build_dir / "installer"
    try:
        source_state = public_release_state(ROOT, ver)
        record = verify_record(build_dir)
        if not (dist_dir / 'UgreenNASAdmin.exe').is_file() or not (installer_out / f'UgreenNASAdmin_setup_{ver}.exe').is_file():
            raise ValueError('Recorded release build must contain portable EXE and matching installer')
        if record["source"]["source_commit"] != source_state["source_commit"]:
            raise ValueError("Build manifest belongs to a different source commit")
        reject_runtime_files(dist_dir)
    except (KeyError, ValueError, OSError, subprocess.SubprocessError) as exc:
        print(f"FEHLER: {exc}", file=sys.stderr)
        return 2

    # Hash-check against a throwaway export, then pack the real bundle.
    with tempfile.TemporaryDirectory(prefix="ugrel_hash_") as td:
        probe = Path(td) / "source"
        probe.mkdir()
        exported = export_committed_sources(ROOT, probe, source_state)
        if exported["source_sha256"] != record["source"]["source_sha256"]:
            print("FEHLER: Build source hashes differ from exported release sources", file=sys.stderr)
            return 2
    return _pack_bundle(
        ver=ver,
        source_state=source_state,
        dist_dir=dist_dir,
        installer_out=installer_out,
        manifest_src=build_dir / "BUILD_MANIFEST.json",
    )


def main_from_local_dist() -> int:
    """Keep an actionable error for old automation instead of bypassing verification."""
    print('FEHLER: --local-dist hat keinen Build-Nachweis. Aus dem öffentlichen Commit mit '
          'tools/reproducible_release.py build bauen; dann --build-dir verwenden. '
          'Ein sauberer Quellbaum belegt nicht die Herkunft einer alten lokalen EXE.', file=sys.stderr)
    return 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Package a verified release build")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--build-dir", type=Path, help="Verified reproducible build directory")
    mode.add_argument(
        "--local-dist",
        action="store_true",
        help="Removed unsafe release shortcut; prints migration guidance",
    )
    args = parser.parse_args()
    if args.local_dist:
        raise SystemExit(main_from_local_dist())
    raise SystemExit(main_from_build_dir(args.build_dir))
