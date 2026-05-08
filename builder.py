import os
import subprocess
import sys
import time
import hashlib

# --- KONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SPEC_NAME = "UgreenNASAdmin.spec"
EXE_NAME = "UgreenNASAdmin"
# ---------------------


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

    dist_exe = os.path.join(BASE_DIR, "dist", f"{EXE_NAME}.exe")
    if not _remove_dist_exe_maybe_locked(dist_exe, EXE_NAME):
        sys.exit(1)

    params = [
        spec_path,
        "--clean",
        "--noconfirm",
        f"--distpath={os.path.join(BASE_DIR, 'dist')}",
        f"--workpath={os.path.join(BASE_DIR, 'build')}",
    ]

    print(f"Spec:  {spec_path}")
    print("Starte PyInstaller...")
    cmd = [sys.executable, "-m", "PyInstaller", *params]
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
        input("FERTIG. Druecke Enter zum Schliessen...")
    sys.exit(0)
