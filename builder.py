import os
import shutil
import sys
import time

import PyInstaller.__main__

# --- KONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SPEC_NAME = "UgreenNASAdmin.spec"
EXE_NAME = "UgreenNASAdmin"
# ---------------------


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
        return
    if not os.path.isfile(icon_path):
        print(f"KRITISCH: nas_icon.ico fehlt — bitte create_icon.py ausfuehren.")
        print(f"Erwartet: {icon_path}")
        return

    mtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(icon_path)))
    size = os.path.getsize(icon_path)
    print(f"Icon: {icon_path}")
    print(f"       Groesse {size} Bytes, geaendert {mtime}")

    dist_exe = os.path.join(BASE_DIR, "dist", f"{EXE_NAME}.exe")
    if os.path.isfile(dist_exe):
        try:
            os.remove(dist_exe)
            print("Alte dist-EXE entfernt (erzwingt neuen Windows-Icon-Cache fuer diese Datei).")
        except OSError as e:
            print(f"Konnte alte EXE nicht loeschen (evtl. noch gestartet): {e}")

    params = [
        spec_path,
        "--clean",
        "--noconfirm",
        f"--distpath={os.path.join(BASE_DIR, 'dist')}",
        f"--workpath={os.path.join(BASE_DIR, 'build')}",
    ]

    print(f"Spec:  {spec_path}")
    print("Starte PyInstaller...")
    try:
        PyInstaller.__main__.run(params)
        print("\n" + "*" * 20)
        print("BAU ABGESCHLOSSEN — EXE in dist/")
        print("*" * 20)
        if os.path.isfile(dist_exe):
            em = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(dist_exe)))
            print(f"Neue EXE: {dist_exe} ({em})")
        print(
            "\nTipp: Zeigt Windows noch das alte Symbol, Kurz umbenennen (z.B. UgreenNASAdmin2.exe)\n"
            "oder Explorer neu starten — Icon-Cache von Windows, nicht vom Builder."
        )
    except Exception as e:
        print(f"\nFEHLER: {e}")


if __name__ == "__main__":
    build()
    print("\n" + "=" * 60)
    if sys.stdin.isatty():
        input("FERTIG. Druecke Enter zum Schliessen...")
