# Changelog — Ugreen NAS Admin

## Unreleased

### Entfernt

- Browser-/Docker-Web-Stack (`web/`, `docker-compose.web.yml`, zugehörige Deploy-Doku und Skripte). Betrieb nur noch über die Desktop-App (`ugreen_nas_admin.py` / `öffentlich/`).

## 22.2.0 — 2026-04-01

### Kurzüberblick

Ausführlich im öffentlichen Baum: **`öffentlich/CHANGELOG.md`** (DE + EN) und **`öffentlich/README.md`**.

- **Sicherheit:** Standard **eingeschränkter Modus**; Header-Button **„Volle Rechte“ / „Full access“** schaltet riskante Aktionen nach Bestätigung frei; **`mixin_safety_lock`**, **`_danger_gate()`**, **`RoundedButton.set_enabled`**.
- **UI:** **Live-Monitor** (CPU gesamt + RAM) unten in der **Sidebar**; kompakter **Header** (eine Zeile Verbindungsfelder, SSH-Key-Pfad fester Breite, Hinweis mit dynamischem **wraplength**); rechte Buttons unten am Kopfbereich ausgerichtet; Startgeometrie **1500×1020**, **minsize** Breite **1260**.
- **i18n:** neue Texte für Sicherheitsdialoge, Sidebar-Monitor, SSH-Key-Labels.
- **Build:** PyInstaller **Hidden Import** `ugreen_app.mixin_safety_lock`.
- **Doku:** README mit Screenshots **`images/1.png`–`6.png`**, Release-Paket unter **`öffentlich/release/UgreenNASAdmin_v22.2.0/`** (EXE + CHANGELOG + README.txt).

## 22.1.0 — 2026-04-01

### Verbessert (Kurzüberblick)

Ausführlich im öffentlichen **`öffentlich/CHANGELOG.md`** und in **`öffentlich/README.md`** (u. a. *Verbindung zur NAS* mit **SSH-Port** und **SSH-Key**).

- **SSH (`nas_ssh`):** `compress=True`; optional lokalisierte Status-/Fehlertexte (`i18n`); `run_ssh_cmd` übergibt Übersetzungen.
- **UI:** Explorer Aufklappen + Suche im Thread; Docker Stats/Inspect/Logs asynchron; Docker-Überschriften über `i18n`.
- **Sicherheit:** Kopfzeilen-Hinweis Klartext-JSON; **🔐 PW Tresor** + `keyring_helper`; optional `keyring`; Hidden Import in `.spec`.
- **`nas_utils`:** `looks_like_ssh_error_output`, erweiterte Sanitize für EN-SSH-Fehler.
- **Doku / GitHub:** README-Screenshots oben, Tresor-Anleitung, Verbindungstabelle; CHANGELOG 22.1.0 ausführlich.
- **Tests:** `tests/test_nas_utils.py` erweitert (nur im privaten Baum).

## 22.0.0 (Public) — 2026-03-30

### Neu

- Ordner **`öffentlich/`**: enthält alle zum **Starten** und **Bauen** der App nötigen Dateien (Release-Quelle für öffentliche Versionen). Siehe `öffentlich/README.md` — **Ordner nicht löschen**; bei Änderungen im Hauptprojekt Inhalt bei Bedarf spiegeln.
- **Öffentliche Version** mit zweisprachiger Oberfläche **Deutsch / Englisch**.
- **Sprach-Umschalter** `DE / EN` unten links in der Statusleiste; Umschalten lädt die UI neu (gleiche Session, Verbindungsdaten bleiben erhalten).
- **Persistenz:** `ui_lang` wird in `nas_admin_connection.json` neben IP/User/Passwort gespeichert (beim „Verbindung speichern“ mit abgelegt).
- **Übersetzungen** zentral in `ugreen_app/i18n.py` (UI-Texte, Cron-Klartext-Mappings, häufige Dialoge).
- **Versionsnummer** und Fenstertitel nutzen die gleiche Quelle (`__version__`).
- **NAS Explorer (Tab):** Zwei-Spalten-Ansicht (NAS-Baum / **Dieser PC**) zum **Hoch- und Herunterladen** sowie **Kopieren** zwischen NAS und lokalem Rechner — über Werkzeugleiste, Kontextmenü und Direktaktionen (z. B. Upload einzelner Dateien oder ganzer Ordner, „Auf NAS kopieren“ / „Auf PC kopieren“), inkl. Fortschrittsanzeige bei Übertragungen.

### Geändert (gegenüber 21.2.0)

- Hauptfenster, Sidebar, alle Tab-Bereiche (Scripts, Explorer, Docker, Health/Telegram, Speicher, ACL, Snapshots, Planer), Statuszeile und viele Meldungen sind **sprachabhängig**.
- Cron-/Planer-Klartext und Combobox-Bezeichnungen folgen der gewählten Sprache.
- Abgerundete Buttons (Pillow) unverändert nutzbar; PyInstaller: `ugreen_app.i18n` als Hidden Import ergänzt.

### Hinweis

- Einzelne tiefe Dialoge (z. B. einige Snapper/Btrfs-Eingaben) können noch deutsche Standardtexte zeigen; die zentralen Pfade sind übersetzt.

---

## 21.2.0 und älter

- Vorherige Versionen ohne integrierte DE/EN-Umschaltung; siehe Git/Backup bzw. interne Release-Notizen.
