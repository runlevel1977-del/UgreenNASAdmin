import os
import subprocess
import sys
import time
import hashlib
import shutil

# packaging/ → Projektroot
PACK_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(PACK_DIR)
SPEC_NAME = "UgreenNASAdmin.spec"
EXE_NAME = "UgreenNASAdmin"
ASSETS = os.path.join(ROOT, "assets")

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
if PACK_DIR not in sys.path:
    sys.path.insert(0, PACK_DIR)

from tools.build_python import resolve_build_python  # noqa: E402


def _remove_dist_exe_maybe_locked(path: str, exe_stem: str) -> bool:
    if not os.path.isfile(path):
        return True
    try:
        os.remove(path)
        print("Alte dist-EXE entfernt (erzwingt neuen Windows-Icon-Cache fuer diese Datei).")
        return True
    except OSError as e:
        print(f"Konnte alte EXE nicht loeschen: {e}")
        print("Bitte die laufende App selbst schließen und den Build erneut starten.")
        return False


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build():
    print("=" * 60)
    print("CLEAN-BUILD (PyInstaller + Spec + Icons)")
    print("=" * 60)

    try:
        import create_icon

        create_icon.main()
        print("Icons per packaging/create_icon.py aktualisiert.")
    except Exception as e:
        print(f"Hinweis: create_icon.py konnte nicht laufen ({e}) — vorhandene assets/nas_icon.* werden genutzt.")

    icon_path = os.path.join(ASSETS, "nas_icon.ico")
    spec_path = os.path.join(PACK_DIR, SPEC_NAME)

    if not os.path.isfile(spec_path):
        print(f"KRITISCH: {SPEC_NAME} fehlt in {PACK_DIR}")
        sys.exit(1)
    if not os.path.isfile(icon_path):
        print(f"KRITISCH: nas_icon.ico fehlt — bitte packaging/create_icon.py ausfuehren.")
        print(f"Erwartet: {icon_path}")
        sys.exit(1)

    mtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(icon_path)))
    size = os.path.getsize(icon_path)
    print(f"Icon: {icon_path}")
    print(f"       Groesse {size} Bytes, geaendert {mtime}")

    dist_dir = os.path.join(ROOT, "dist", EXE_NAME)
    dist_exe = os.path.join(dist_dir, f"{EXE_NAME}.exe")
    legacy_exe = os.path.join(ROOT, "dist", f"{EXE_NAME}.exe")
    if os.path.isfile(legacy_exe):
        if not _remove_dist_exe_maybe_locked(legacy_exe, EXE_NAME):
            sys.exit(1)
    if os.path.isdir(dist_dir):
        try:
            shutil.rmtree(dist_dir, ignore_errors=False)
            print(f"Altes dist/{EXE_NAME}/ entfernt.")
        except OSError as e:
            print(f"Konnte dist/{EXE_NAME}/ nicht loeschen: {e}")
            sys.exit(1)

    params = [
        spec_path,
        "--clean",
        "--noconfirm",
        f"--distpath={os.path.join(ROOT, 'dist')}",
        f"--workpath={os.path.join(ROOT, 'build')}",
    ]

    print(f"Spec:  {spec_path}")
    try:
        py_exe = resolve_build_python()
    except RuntimeError as exc:
        print(f"FEHLER: {exc}")
        sys.exit(1)
    print(f"Build-Python: {py_exe}")
    print("Starte PyInstaller...")
    cmd = [py_exe, "-m", "PyInstaller", *params]
    try:
        r = subprocess.run(cmd, cwd=ROOT)
    except Exception as e:
        print(f"\nFEHLER: PyInstaller konnte nicht gestartet werden: {e}")
        sys.exit(1)
    if r.returncode != 0:
        print(f"\nFEHLER: PyInstaller beendete sich mit Code {r.returncode}.")
        sys.exit(r.returncode)

    print("\n" + "*" * 20)
    print("BAU ABGESCHLOSSEN — EXE in dist/")
    print("*" * 20)
    if os.path.isfile(dist_exe):
        em = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(dist_exe)))
        print(f"Neue EXE: {dist_exe} ({em})")
        print(f"SHA256: {_sha256(dist_exe)}")
    else:
        print("WARNUNG: dist-EXE wurde nicht gefunden (Build unvollstaendig).")
        sys.exit(1)
    print(
        "\nTipp: Zeigt Windows noch das alte Symbol, Kurz umbenennen (z.B. UgreenNASAdmin2.exe)\n"
        "oder Explorer neu starten — Icon-Cache von Windows, nicht vom Builder."
    )
    print(
        "\nWindows-Hinweis:\n"
        "- Defender-Fehlalarme werden durch den Build reduziert (UPX ist deaktiviert).\n"
        "- SmartScreen-Warnungen lassen sich ohne Code-Signatur nicht vollstaendig vermeiden.\n"
        "- Sicherheitsmeldungen vor einer Ausführung prüfen; keine pauschalen Scanner-Ausnahmen setzen.\n"
    )


if __name__ == "__main__":
    build()
    print("\n" + "=" * 60)
    if sys.stdin.isatty():
        try:
            input("FERTIG. Druecke Enter zum Schliessen...")
        except EOFError:
            pass
    sys.exit(0)
