# Changelog — Ugreen NAS Admin

## Unreleased

_(noch nicht veröffentlicht)_

## 23.4.0 — 2026-04-26

### Deutsch (ausführlich)

- **Mehrsprachige Oberfläche (i18n) ausgebaut:**
  - Umfangreiche **Übersetzungstabellen** in `i18n.py` und deutlich mehr **UI-Sprachen** (u. a. neben DE/EN z. B. kroatisch und weitere Locales, je nach Stand der `TRANSLATIONS_*`-Blöcke).
  - **`normalize_lang(...)`** — in der Verbindungskonfiguration und an anderen Stellen werden gespeicherte **Sprachcodes** normalisiert, statt sie strikt auf `de`/`en` zu begrenzen.
- **Einstellungen (Setup-Tab):** **UI-Sprache** wählbar (Dropdown) mit **Anwenden**-Button, damit der Wechsel der Oberflächensprache sichtbar und erreichbar ist.
- **Laufende i18n-Bereinigung:** vereinzelte fest codierte engl./deut. Texte auf **`self.t("…")` / `translate()`** umgestellt (u. a. Explorer-Panel „NAS“, Docker-Katalog **Image**-Spaltenkopf, Webcam-**FPS**-Label, Transfer **ETA-Platzhalter** und Meldung „Entpacke auf dem NAS…“).
- **Weitere Mixin-Verbesserungen:** u. a. **Theme-UI**, **Storage/ACL/Snap** und **Tab-Setup** für konsistenteres Verhalten.
- **Öffentliche Doku (README, GitHub):** deutlichere Erklärung, dass **Code → Download ZIP** stets **Quellcode** des **Standard-Branches** ist (kein Release-EXE-Bundle, keine Umlenkung des Buttons in Releases möglich); Screenshot-Beschriftung **v23+** statt veraltet wirkendem alten Versatz.

### English (summary)

- **Wider i18n coverage** (many locales and large translation table updates); **`normalize_lang()`** for stored UI language values (not limited to a strict de/en check).
- **Settings tab:** **UI language** combobox and **apply** for switching the interface language in-app.
- **More user-visible strings** moved to the translation system (Explorer NAS panel, Docker catalog **image** column, Webcam **FPS**, transfer ETA placeholder, “unpacking on NAS” text).
- **Polish** in **theme UI**, **storage/ACL/snap**, and **tab setup** mixins.
- **Public README** (generated for `öffentlich/`) clarifying GitHub **Code → Download ZIP** vs. **Releases/Assets**; updated screenshot line to **v23+**.

## 23.3.0 — 2026-04-23

### Deutsch (ausführlich)

- **Webcam Recorder (neu, produktionsreif):**
  - Neuer **Webcam-Panel-Workflow** in der App mit Geräte-Scan (`/dev/video*`), Live-Preview, Sofortaufnahme und täglicher Zeitplanung (Cron auf dem NAS).
  - **Kamera-Controls integriert:** Auto/Manual Exposure, Exposure-Wert, Gain und 50/60Hz Netzfrequenz über `v4l2-ctl`.
  - **Dauer-Auswahl verbessert:** Aufnahmezeit per Dropdown für **Sekunden, Minuten, Stunden, Tage**.
  - **Qualitätsprofile:** `compatible`, `hq`, `space` mit Encoder-Fallbacks (`libx264` / `libx265` / `mpeg4`) für unterschiedliche NAS-Umgebungen.
  - **Pre-Flight-Check:** Prüfung auf `ffmpeg`, `v4l2-ctl`, Device-Lesbarkeit, Zielordner-Schreibrechte und freien Speicher vor Aufnahme/Planung.
  - **1-Klick Selbsttest:** 3s Testaufnahme inkl. Datei-Validierung und klarer Statusausgabe (OK/Fail + Dateipfad).
  - **Dateirotation:** optionales Limit „keep N files“ löscht alte `webcam_*.mp4` automatisch.
  - **Motion Detection (optional):** Bewegungserkennung (Frame-Hash-Vergleich) mit Skip bei statischem Bild.
  - **Status & Transparenz:** Sichtbarer Aufnahme-Status inkl. letzter Ausgabedatei im Webcam-Fenster.
  - **Ordnerbrowser gehärtet:** Root zeigt nur sichere Datenpfade (`/volume*`), keine Systemordner.
- **Berechtigungen robuster behandelt:**
  - Preflight unterscheidet sauber zwischen **User-Write** und **Root-Write**.
  - Sofortaufnahme verlangt User-Schreibrecht; geplante Jobs/Selbsttest können bei Bedarf Root-Write nutzen.
- **Storage ergänzt (Disk Imaging/Restore):**
  - Scan von Block-Devices mit Kennzeichnung sensibler Ziele (System/RAID-Kontext) und Workflows für Image nach PC/NAS sowie Restore von PC/NAS.
- **Docker ergänzt (Catalog):**
  - Docker-Hub-Katalog mit Suche/Browse und Übergabe in den Docker-Assistenten (`docker run` / compose YAML mit Presets).
- **i18n/UX erweitert:**
  - Neue DE/EN-Texte für Webcam-Status, Preflight, Selbsttest, Qualitäts-/Motion-/Rotationsoptionen und Ordnerauswahl.

### English (summary)

- Added a full **Webcam Recorder suite**: device scan, live preview, immediate/scheduled recording, camera controls, quality profiles, preflight checks, self-test, rotation, optional motion detection, and clear status output with last file path.
- Hardened permission handling by separating **user write** vs **root write** checks (manual recording vs scheduled/root-capable flows).
- Added **disk imaging/restore** workflows with safer disk detection context.
- Added **Docker Hub catalog** helper to prefill deployment wizard (`docker run` / compose presets).
- Extended DE/EN i18n coverage for all new webcam and release-facing UI text.

## 23.2.0 — 2026-04-20

### Deutsch (ausführlich)

- **Mehrere SMB-Ziele (NAS ↔ NAS):**
  - Settings unterstützen jetzt **Profil-Liste** für das zweite NAS (`second_nas_smb_peers`) inkl. aktivem Index.
  - Profile können in den Settings per Dropdown gewählt, hinzugefügt und gelöscht werden.
  - Der aktive Peer wird im NAS↔NAS-Tab übernommen; beim Wechsel werden SMB-Verbindungen sauber getrennt und die Peer-Ansicht geleert.
  - Kompatibilität zu älteren Settings bleibt erhalten (`second_nas_smb` als aktives Profil).
- **Settings-Privacy für sensible Felder:**
  - Telegram- und E-Mail-Identitätsdaten (Token/Chat, SMTP User/Pass/From/To) werden beim Laden maskiert.
  - Neue **Show/Hide**-Schalter im Settings-Tab; maskierte Werte bleiben speicherbar ohne Klartext-Re-Edit.
  - Beim Wechsel in den Settings-Tab werden sensible Felder erneut aus Settings gezogen und maskiert angezeigt.
- **Script-Benachrichtigungen (neu):**
  - Neuer Block in den Settings: **Script wählen**, Kanal (**Telegram/E-Mail**), Trigger (**Erfolg/Fehler/beides**), Regeln verwalten.
  - Regeln werden in `app_settings.json` unter `script_notifications.rules` gespeichert.
  - Manuelle Host-Testläufe senden Benachrichtigungen regelbasiert.
  - Fehler beim Versand werden sichtbar geloggt (Telegram/SMTP-Fehlermeldung statt „still“).
- **Automatisch für Cron/Nachtläufe (ohne PC):**
  - Neuer NAS-Runner: `ugreen_script_notify_runner.py` + `ugreen_script_notify_config.json` auf `/volume1/scripts/`.
  - Cron-Einträge für Host/Docker-Skripte werden über den Runner gewrappt, damit Benachrichtigungen auch bei z. B. 03:00 Uhr funktionieren.
  - Neuer Settings-Button **„Auf NAS sync“** zum expliziten Upload von Runner + Config.
  - Robuster EXE-Fallback: wenn Runner-Datei lokal (PyInstaller-Temp) fehlt, wird eingebetteter Runner-Quelltext verwendet.
- **Sichtbarkeit „welche Scripts melden“:**
  - Script-Liste markiert aktive Regeln klar mit **`🔔`**-Präfix.
  - Zusätzliche Übersichtszeile zeigt für das ausgewählte Script den aktiven Notify-Status (Kanal + Trigger).
- **Media/Generator-Tools ergänzt:**
  - `tools/generate_code_rain_video.py` erweitert (Qualität/Duration/FPS/Workers/Codec, inkl. AV1-Optionen).
  - `tools/generate_window_sea_video.py` (30s Fenster-Meer-Animation).
  - `tools/generate_light_rain_audio.py` (WAV/MP3-Ausgabe, sanfter Regen).

### English (summary)

- Multi-peer SMB profiles for NAS↔NAS, with active profile switching and UI sync.
- Settings privacy masking + Show/Hide for Telegram/Email sensitive values.
- New script notification rules in Settings (script + channel + trigger).
- NAS-side runner for cron/night jobs (`/volume1/scripts/ugreen_script_notify_runner.py`) so alerts work even when the PC is off.
- New “sync to NAS” button and robust packaged-app fallback for runner source.
- Script list now visibly marks notification-enabled entries with `🔔`.
- Added/extended media generation helper tools (code-rain video, sea-window video, light rain audio).

## 22.6.0 — 2026-04-07

Kurz: SSH-**Profile**, Docker **Live-Log** + **Compose** (config/ps/up-d, Plugin/Legacy-Fallback), Script-**Vorlagen** rsync/restic/rclone, Tk-**Frame**-Padding-Fix, ZIP-Version aus `nas_manager.py`. Details: **`öffentlich/CHANGELOG.md`**.

## 22.5.0 — 2026-04-04

### Deutsch (ausführlich)

- **Öffentliches Release-Paket:** Forum-/Release-ZIP (**`UgreenNASAdmin_v22.5.0_oeffentlich_mit_EXE.zip`**) enthält neben Quellen und **`dist/UgreenNASAdmin.exe`** den Ordner **`images/`** inkl. **drei neuen Screenshots** zum Tab **System & Health** (`health_system_1.png`–`health_system_3.png`, einheitliche Dateinamen ohne Leerzeichen). Die bisherigen Übersichtsbilder **`1.png`–`6.png`** bleiben erhalten.
- **Dokumentation (`öffentlich/README.md` + Root-`README.md`):** Kurzanleitung **Einrichten der Benachrichtigungen** (Telegram-Wächter, NAS-Zentral-Wächter mit **E-Mail/Telegram**, Hinweise zu SMTP/SMTPS und DNS auf dem NAS) auf **Deutsch und Englisch**; neue **Funktionsliste** der App (DE/EN).
- **Internationalisierung:** Upload-/Download-**Dialoge** und zugehörige **Transfer-Log**-Texte über **`i18n`** (keine fest eingebauten deutschen `messagebox`-Titel mehr in diesen Pfaden); **Telegram:** manuelle NAS-Prüfung, Teststatus und **Testnachrichtentext** folgen der UI-Sprache.
- **Stabilität (Tk/Windows):** SSH-Befehle aus **Hintergrund-Threads** rufen die Statuszeile nicht mehr mit **`update_status=True`** auf (**Explorer** Verzeichnisgrößen/Aufklappen/Suche, **Transfer** Abbruch-Cleanup, **Docker** Stats/Inspect/Logs, **Telegram-Wächter** Prüfschleife) — reduziert Risiko von UI-Freezes analog zur bereits behobenen NAS-Wächter-Installation.
- **NAS-Zentral-Wächter / Tagesbericht (Kontext Release):** Fortführung der zuvor dokumentierten Features: **SMTPS (Port 465)**, **`--smtp-test`**, robusterer **E-Mail-Betreff**, optional **SSH-Login-Fehler** in der Auswertung, **Tagesbericht** (`nas_daily_report.py`) mit **`message_lang`**, gekürzter Berichtsinhalt und Emojis; **PyInstaller**-`datas` enthalten **`nas_central_watch.py`** und **`nas_daily_report.py`** (siehe `.spec`).
- **SSH / Zeitpläne:** Bei **`sudo -S`** liefert die App den Befehlsausgang ohne angehängte **stderr**-Zeilen (z. B. `[sudo] password for …`), damit **`/etc/cron.d/papa_jobs`** im Editor stabil bleibt; sudo-Zeilen werden beim Lesen von Cron-Text verworfen (`nas_ssh.run`, `_sanitize_stable_cron_text`).
- **Scripte-Tab:** **„💾 Speichern“** (root), **„💾 Als Benutzer“** und **Strg+S** speichern den Editor (u. a. **STABLE_TASKS**).
- **Docker-Assistent:** **Zwei Schritte** (Editor → Weiter → Scan/mkdir/Start), **grid**-Layout, **`tk.Button`**, Mindesthöhe Editor.
- **System & Health (Layout):** Aktionsleiste, scrollbares Panel für Telegram/Wächter/Tagesbericht, Mausrad-Scroll, Telegram **Cooldown** neben **Temp max**, NAS-Wächter-Checkboxen kompakt.

### English (summary)

- **Public zip:** includes **`images/`** with three **System & Health** screenshots (`health_system_1.png`–`3.png`); README updates (notification setup **DE/EN**, feature list **DE/EN**).
- **i18n:** transfer/telegram dialogs and log strings; no hardcoded German in those UI paths.
- **Threading:** `run_ssh_cmd(..., update_status=False)` from worker threads in explorer, transfer cleanup, docker log/stats/inspect, telegram guard checks — fewer Tk freezes on Windows.

### Build

- **`UgreenNASAdmin.spec`:** `nas_daily_report.py` in **`datas`** (bereits im Hauptprojekt; öffentliche `.spec` angeglichen).
- **`tools/zip_oeffentlich_forum.py`:** Ausgabearchive auf **v22.5.0** umbenannt.

## 22.4.0 — 2026-04-03

### Neu

- **Docker-Assistent („Neuer Docker“):** Nach **„Variablen scannen“** werden u. a. **`${PLATZHALTER}`** / `$VAR`, **Compose-Volume-Hostpfade**, **`type: bind` → `source:`**, **`-v`/`--volume`**, **Host-Ports** (`-p` / `ports:`) und **`-e KEY=` mit Pfad/leer** als Formularfelder angeboten; nach Ausfüllen werden Werte eingesetzt, optional **Host-Ordner auf dem NAS** angelegt, dann Compose oder `docker run` ausgeführt. Modul **`ugreen_app/docker_deploy_wizard.py`**, Tests **`tests/test_docker_deploy_wizard.py`**.

### Build

- PyInstaller Hidden Import **`ugreen_app.docker_deploy_wizard`**.

### Behoben

- **`nas_ssh.write_remote_file_sudo`:** SFTP versucht nacheinander **relativen Dateinamen** (SFTP-Chroot), **`$HOME/…`**, **`/tmp`**, dann `sudo mv`. Schlägt SFTP komplett fehl, **Fallback ohne SFTP:** `sudo python3 -c …` schreibt die Datei per **Base64** direkt nach Ziel + `chmod` — **„Auf NAS installieren“** auch bei restriktivem SFTP.
- **Zeitpläne (stabile Cron-Zeilen):** Endet der Skriptname mit **`.py`**, wird in **`/etc/cron.d/papa_jobs`** jetzt **`/usr/bin/python3 …`** statt **`/bin/bash …`** geschrieben; Pfad mit **`posixpath.basename`** + **`shlex.quote`** (`mixin_editor_cron.add_to_stable_cron`).

### Entfernt

- Browser-/Docker-Web-Stack (`web/`, `docker-compose.web.yml`, zugehörige Deploy-Doku und Skripte). Betrieb nur noch über die Desktop-App (`ugreen_nas_admin.py` / `öffentlich/`).

## 22.3.0 — 2026-04-03

### Neu / geändert

- **NAS-Zentral-Wächter:** Python-Skript `ugreen_app/resources/nas_central_watch.py` — läuft **auf dem NAS** (Cron), prüft Speicher, RAID, Temperatur, **Docker** (exited/restarting/unhealthy, Pflicht-Container), optional **systemd failed**; Benachrichtigung per **Telegram**, **E-Mail** oder **beides**; optional **docker start** für konfigurierte Namen (mit Cooldown). Im Tab **System & Health:** Bereich zum Konfigurieren, **Auf NAS installieren** (nach `/volume1/scripts/`), **Test (--once)**. Lokale UI-Werte in `nas_watch_local.json` (gitignored).
- **Docker:** **Stop** und **Restart** mit **zusätzlicher Bestätigung**; Container-Namen per `shlex.quote` an `docker` übergeben.

### Build

- PyInstaller: `datas` für `ugreen_app/resources/nas_central_watch.py`, Hidden Import `ugreen_app.mixin_nas_watch_deploy`.

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
