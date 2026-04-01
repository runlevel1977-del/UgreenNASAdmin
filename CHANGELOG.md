# Changelog — Ugreen NAS Admin

---

## Deutsch

### 22.1.0 (Public) — 2026-04-01

#### Neu / Verbessert

- **SSH:** Verbindung mit Kompression (`compress`), Fehlermeldungen DE/EN über `i18n`; Statuszeile nutzt übersetzte SSH-Texte.
- **UI-Flüssigkeit:** NAS-Explorer Ordner aufklappen und Suche laufen im Hintergrund (kein Einfrieren); Docker Stats / Inspect / Logs ebenfalls asynchron.
- **Sicherheit & Komfort:** Hinweis zu Klartext in `nas_admin_connection.json`; Button **🔐 PW Tresor** speichert das SSH-Passwort optional im OS-Tresor (`pip install keyring`). Leeres Passwort in der JSON wird beim Start aus dem Tresor geladen (gleiche IP/User).
- **Doku:** Schritt-für-Schritt-Anleitung (Tresor, `pip`, EXE neu bauen) in **`README.md`** unter *SSH-Passwort im Windows-Tresor*.
- **Tests:** Hilfsfunktion `looks_like_ssh_error_output` in `nas_utils` abgedeckt.

### 22.0.0 (Public) — 2026-03-30

#### Neu

- Ordner **`öffentlich/`**: enthält alle zum **Starten** und **Bauen** der App nötigen Dateien (Release-Quelle für öffentliche Versionen). Siehe `öffentlich/README.md` — **Ordner nicht löschen**; bei Änderungen im Hauptprojekt Inhalt bei Bedarf spiegeln.
- **Öffentliche Version** mit zweisprachiger Oberfläche **Deutsch / Englisch**.
- **Sprach-Umschalter** `DE / EN` unten links in der Statusleiste; Umschalten lädt die UI neu (gleiche Session, Verbindungsdaten bleiben erhalten).
- **Persistenz:** `ui_lang` wird in `nas_admin_connection.json` neben IP/User/Passwort gespeichert (beim „Verbindung speichern“ mit abgelegt).
- **Übersetzungen** zentral in `ugreen_app/i18n.py` (UI-Texte, Cron-Klartext-Mappings, häufige Dialoge).
- **Versionsnummer** und Fenstertitel nutzen die gleiche Quelle (`__version__`).
- **NAS Explorer (Tab):** Zwei-Spalten-Ansicht (NAS-Baum / **Dieser PC**) zum **Hoch- und Herunterladen** sowie **Kopieren** zwischen NAS und lokalem Rechner — über Werkzeugleiste, Kontextmenü und Direktaktionen (z. B. Upload einzelner Dateien oder ganzer Ordner, „Auf NAS kopieren“ / „Auf PC kopieren“), inkl. Fortschrittsanzeige bei Übertragungen.

#### Geändert (gegenüber 21.2.0)

- Hauptfenster, Sidebar, alle Tab-Bereiche (Scripts, Explorer, Docker, Health/Telegram, Speicher, ACL, Snapshots, Planer), Statuszeile und viele Meldungen sind **sprachabhängig**.
- Cron-/Planer-Klartext und Combobox-Bezeichnungen folgen der gewählten Sprache.
- Abgerundete Buttons (Pillow) unverändert nutzbar; PyInstaller: `ugreen_app.i18n` als Hidden Import ergänzt.

#### Hinweis

- Einzelne tiefe Dialoge (z. B. einige Snapper/Btrfs-Eingaben) können noch deutsche Standardtexte zeigen; die zentralen Pfade sind übersetzt.

#### 21.2.0 und älter

- Vorherige Versionen ohne integrierte DE/EN-Umschaltung; siehe Git/Backup bzw. interne Release-Notizen.

---

## English

### 22.1.0 (Public) — 2026-04-01

#### Added / improved

- **SSH:** connection uses compression; error strings localized via `i18n`; status bar uses translated SSH messages.
- **Responsiveness:** NAS Explorer expand + search off the main thread; Docker stats / inspect / logs fetched in background threads.
- **Security / comfort:** note about plain-text `nas_admin_connection.json`; **🔐 PW vault** stores the SSH password in the OS credential store (`pip install keyring`). Empty JSON password loads from the vault on startup (same IP/user).
- **Docs:** step-by-step (vault, `pip`, rebuild EXE) in **`README.md`** under *SSH password in the OS vault*.
- **Tests:** `looks_like_ssh_error_output` in `nas_utils` covered.

### 22.0.0 (Public) — 2026-03-30

#### Added

- Folder **`öffentlich/`**: contains everything needed to **run** and **build** the app (release source for public builds). See `öffentlich/README.md` — **do not delete** this folder; mirror changes from the main project when needed.
- **Public build** with a bilingual UI **German / English**.
- **Language toggle** `DE / EN` bottom-left in the status bar; switching reloads the UI (same session, connection fields preserved).
- **Persistence:** `ui_lang` is stored in `nas_admin_connection.json` alongside IP/user/password (saved with “Save connection”).
- **Translations** centralized in `ugreen_app/i18n.py` (UI strings, cron human-readable mappings, common dialogs).
- **Version** and window title use the same source (`__version__`).
- **NAS Explorer (tab):** Two-pane layout (NAS tree / **This PC**) for **uploading and downloading** and **copying** between the NAS and the local machine — via toolbar, context menu, and direct actions (e.g. upload files or whole folders, “Copy to NAS” / “Copy to PC”), including progress UI for transfers.

#### Changed (vs 21.2.0)

- Main window, sidebar, all tab areas (Scripts, Explorer, Docker, Health/Telegram, Storage, ACL, Snapshots, scheduler), status bar, and many messages are **language-aware**.
- Cron/scheduler human-readable text and combobox labels follow the selected language.
- Rounded buttons (Pillow) unchanged; PyInstaller: `ugreen_app.i18n` added as hidden import.

#### Note

- Some deep dialogs (e.g. certain Snapper/Btrfs prompts) may still show German defaults; main paths are translated.

#### 21.2.0 and earlier

- Earlier versions without built-in DE/EN toggle; see Git/backup or internal release notes.
