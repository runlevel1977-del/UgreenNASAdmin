# Ugreen NAS Admin — v23.8.1 (Forum-Changelog, DE)

Kurzfassung zum Kopieren ins Forum. Technisches Detail steht in `CHANGELOG.md` und im GitHub-Release.

---

## Neu: Windows-Installer & Release-ZIP

Ab **v23.8.1** gibt es neben der **portablen EXE** einen **richtigen Windows-Installer** (Inno Setup):

- **Installer:** `UgreenNASAdmin_setup_23.8.1.exe` — installiert die App z. B. unter „Programme“, optional Desktop-Verknüpfung, mehrsprachiger Setup-Assistent.
- **Release-Paket (ZIP):** `UgreenNASAdmin_v23.8.1_release.zip` enthält zwei Ordner:
  - **`source/`** — alles, was zum **Selbstbauen** aus den Quellen nötig ist (Python, `requirements.txt`, `builder.py`, …) **plus** die fertige portable **`dist/UgreenNASAdmin.exe`** (ohne private Entwickler-JSONs).
  - **`installer/`** — die gleiche **Setup-EXE** wie oben.

**Download:** [GitHub Releases — v23.8.1](https://github.com/runlevel1977-del/UgreenNASAdmin/releases/tag/v23.8.1)  
Dort die ZIP und/oder nur den Installer als Asset.

---

## Installer: alte Verbindungen / Einstellungen (.json) mitnehmen

Wenn du von einer **älteren EXE** (portabel, Ordner neben der Datei) oder einer früheren Installation umsteigst:

- Relevant können u. a. sein: `nas_admin_connection.json`, `app_settings.json`, `telegram_notify.json`, `qnap_smb_prefs.json`, `nas_watch_local.json`, `nas_daily_report_local.json`.
- **Oft:** Unter Installation in **„Programme“** legt Windows keine beschreibbaren Configs neben die EXE — die App nutzt dann **`%LOCALAPPDATA%\UgreenNASAdmin\`**.  
  **→ Die alten `.json` dort hineinkopieren** (App vorher **beenden**), danach neu starten.
- Wenn die Konfiguration bei dir **schon immer direkt neben der EXE** lag und der Zielordner beschreibbar ist, kannst du die Dateien **in denselben Ordner wie die neue `UgreenNASAdmin.exe`** legen.

---

## Was ist neu / geändert (App)

- **„Alles aktualisieren“** (Sidebar): NAS-Abfragen werden wo möglich in **einen sudo-SSH-Batch** gepackt (schneller, weniger Roundtrips); wenn die Shell die Marker nicht unterstützt, **automatischer Fallback** auf die bisherige Befehlskette. Zusätzlich u. a. **`/etc/os-release`** und eine **`systemctl`-Liste der `*_serv.service`** für die Service-Auswahl in der NAS-Verwaltung.
- **Header:** Zeile **UGOS / OS** inkl. **Beta**-Hinweis; wird nach Refresh bzw. beim Start der Dashboard-Live-Schleife befüllt, falls noch leer.
- **NAS-Verwaltung:** Button **Support-Snapshot** (nur Lesen: u. a. uname, os-release, Journal-/Log-Auszüge) — praktisch für Support oder Forenposts.
- **Tagesbericht-Skript** (`nas_daily_report.py`): Block **OS / UGOS** aus `os-release`.
- **Handbücher** (DE/EN + Kurzfassung) und PDFs an die neuen Themen angepasst.

---

## Hinweise

- **SmartScreen / Defender:** Unsigned EXE — ggf. „Trotzdem ausführen“ bzw. Ausnahme; am Build liegt kein „Virus“, sondern typisches Heuristik-Verhalten.
- **Quellen bauen:** Im ZIP unter `source/` siehe `README.md` / `LIESMICH_RELEASE.txt`; kurz: Python-Umgebung, `pip install -r requirements.txt`, `paramiko`, optional `keyring`, dann `python builder.py`.

---

*Stand: Release v23.8.1 — siehe GitHub oben für exakte Dateinamen und Prüfsummen im Release-Text.*
