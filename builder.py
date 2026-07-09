import os
import subprocess
import sys
import time
import hashlib
import shutil

# --- KONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SPEC_NAME = "UgreenNASAdmin.spec"
EXE_NAME = "UgreenNASAdmin"
# ---------------------

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from tools.build_python import resolve_build_python  # noqa: E402


def _taskkill_exe_if_running(exe_stem: str) -> None:
    """Windows: beendet laufende Instanz der EXE, damit dist\\*.exe ueberschrieben werden kann."""
    if os.name != "nt":
        return
    exe = f"{exe_stem}.exe"
    try:
        kwargs = {"args": ["taskkill", "/IM", exe, "/F"], "capture_output": True, "timeout": 15}
        if hasattr(subprocess, "CREATE_NO_WINDOW"):
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
        r = subprocess.run(**kwargs)
        if r.returncode == 0:
            print(f'Hinweis: laufende "{exe}" wurde beendet (Lock auf dist\\{exe}).')
            time.sleep(0.4)
    except Exception:
        pass


def _remove_dist_exe_maybe_locked(path: str, exe_stem: str) -> bool:
    if not os.path.isfile(path):
        return True
    try:
        os.remove(path)
        print("Alte dist-EXE entfernt (erzwingt neuen Windows-Icon-Cache fuer diese Datei).")
        return True
    except OSError as e:
        print(f"Konnte alte EXE nicht loeschen: {e}")
        print("Versuch: gleichnamiges Programm unter Windows beenden …")
        _taskkill_exe_if_running(exe_stem)
        try:
            os.remove(path)
            print("Alte dist-EXE nach Beenden erfolgreich entfernt.")
            return True
        except OSError as e2:
            print(f"FEHLER: dist-EXE ist noch gesperrt (haeufig: App noch offen / Explorer-Vorschau): {e2}")
            print("— UgreenNASAdmin.exe schliessen, ggf. Task-Manager, Build erneut starten.")
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
        print("Icons per create_icon.py aktualisiert.")
    except Exception as e:
        print(f"Hinweis: create_icon.py konnte nicht laufen ({e}) — vorhandene nas_icon.* werden genutzt.")

    icon_path = os.path.join(BASE_DIR, "nas_icon.ico")
    spec_path = os.path.join(BASE_DIR, SPEC_NAME)

    if not os.path.isfile(spec_path):
        print(f"KRITISCH: {SPEC_NAME} fehlt in {BASE_DIR}")
        sys.exit(1)
    if not os.path.isfile(icon_path):
        print(f"KRITISCH: nas_icon.ico fehlt — bitte create_icon.py ausfuehren.")
        print(f"Erwartet: {icon_path}")
        sys.exit(1)

    mtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(icon_path)))
    size = os.path.getsize(icon_path)
    print(f"Icon: {icon_path}")
    print(f"       Groesse {size} Bytes, geaendert {mtime}")

    dist_dir = os.path.join(BASE_DIR, "dist", EXE_NAME)
    dist_exe = os.path.join(dist_dir, f"{EXE_NAME}.exe")
    legacy_exe = os.path.join(BASE_DIR, "dist", f"{EXE_NAME}.exe")
    if os.path.isfile(legacy_exe):
        _remove_dist_exe_maybe_locked(legacy_exe, EXE_NAME)
    if os.path.isdir(dist_dir):
        _taskkill_exe_if_running(EXE_NAME)
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
        f"--distpath={os.path.join(BASE_DIR, 'dist')}",
        f"--workpath={os.path.join(BASE_DIR, 'build')}",
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
        r = subprocess.run(cmd, cwd=BASE_DIR)
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
        "- Fuer lokale Starts hilft meist ein Defender-Exclude fuer den dist-Ordner (Admin):\n"
        f"  Add-MpPreference -ExclusionPath \"{os.path.join(BASE_DIR, 'dist')}\""
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
