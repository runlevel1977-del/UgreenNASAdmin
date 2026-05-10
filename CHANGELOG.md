# Changelog — Ugreen NAS Admin

## Unreleased

_(noch nicht veröffentlicht)_

- **Tab „NAS-Verwaltung“:** Vollständige Übersetzung der **NAS-Admin-Oberfläche** für **alle eingebauten UI-Sprachen** (`hr`, `fr`, `es`, `it`, `pl`, `ru`, `tr`, `ko`, `zh` über `NAS_ADMIN_SUPPLEMENT` + Locale-Module; **nicht** nur DE/EN-Fallback). **Service-Bestätigungsdialog** nutzt lokalisierte Aktion („Start/Stopp/…“); Übersetzungs-Fallback: für fehlende Schlüssel zuerst **EN**, dann **DE**.
- **Windows (installation unter `Program Files`):** Wenn das EXE-Verzeichnis **nicht beschreibbar** ist, liegt die lokale Konfiguration unter **`%LocalAppData%\UgreenNASAdmin`** (bei schreibbarem Pfad weiterhin **neben der EXE**, z. B. `dist\`). Bekannte JSON/State-Dateien werden **einmalig** vom Installationsordner übernommen, falls dort vorhanden. **`nas_watch_local.json`** / **`nas_daily_report_local.json`** nutzen denselben Speicherort.
- **Windows-Installer → erste App-Sprache:** Inno schreibt nach dem Setup **`HKCU\Software\UgreenNASAdmin\InstallerUiLang`** und zusätzlich **`%LocalAppData%\UgreenNASAdmin\installer_selected_ui_lang.txt`**. Bei der ersten Konfigurationsladung gilt dieser Hinweis **vor** gespeicherter **`ui_lang`** in **`nas_admin_connection.json`** — notwendig, wenn eine **übernommene/migrierte** JSON bereits `"ui_lang":"de"` erzwungen hätte. **Nach** dem Einmal-Anwenden: Wert wird in die JSON geschrieben, **Registry** und **Marker-Datei** entfernt.
- **Repository:** **`.gitignore`** ergänzt um **`/installer/output/`** (nur die gebaute Setup-EXE bleibt lokal).

## 23.8.0 — 2026-05-09

### Deutsch

- **Handbuch (DE/EN):** Tab **NAS-Verwaltung** ist jetzt ein eigenes Kapitel **`## 14.`** mit großer PDF-Überschrift (wie andere Tabs); folgende Kapitel wurden um eins nach hinten verschoben. **`HANDBUCH_STRUKTURIERT.md`** verweist auf **`## 14`** statt der alten Unternummer **31.6**.
- **Cron lesen (NAS-Verwaltung):** Zusätzlich **`ls /etc/cron.d`** und **direktes Lesen** der root-**Crontab-Spool-Dateien** (`/var/spool/cron/…`), weil `crontab -l` per SSH oft leer bleibt. **TimedShutdown**-Zeilen (z. B. **`/sbin/TimedShutdown`** in der Root-Crontab, typisch für UGOS-Zeitabschaltung) werden ausdrücklich erkannt, nicht nur allgemeines `shutdown`/`poweroff`.
- **Dashboard → Netzwerk (Kachel erweitert):** Während der **Live-Überwachung** werden pro physischer NIC u. a. **`ip -j addr`** und die **IPv4-Standardroute** (`ip -j route`) ausgewertet und in der Kachel unter **„Aktuelle Konfiguration“** angezeigt (Zustand, MAC, IPv4/Präfix, DHCP vs. statisch, Standard-Gateway wenn diese Schnittstelle die Default-Route trägt). **Dropdown „Schnittstelle“** wählt die Detailansicht; Auswahl wird in **`app_settings.json` → `dashboard.net_detail_iface`** gespeichert. **Filterzeile** (kommagetrennt, z. B. `eth0,eth1`) begrenzt die **Sparkline-Durchsatzkurven**; leer = alle NICs wie bisher — gespeichert unter **`dashboard.net_monitor_filter`**. Zum **Ändern:** Felder **IPv4**, **Präfix**, **Gateway**, Modus **Statisch** oder **DHCP neu**; **„Vom NAS laden“** übernimmt die zuletzt gemessenen Werte; **„Anwenden (sudo)“** setzt Laufzeit-Settings per `ip` bzw. `dhclient`/`dhcpcd` und erfordert **„Volle Rechte“** im Header sowie Bestätigung (Risiko: falsche Adresse bricht SSH ab). **Hinweis:** OS-seitige Speicher in UGOS kann die Werte nach Neustart wieder überschreiben — dauerhafte System-IP bleibt primär Sache der NAS-Oberfläche. Beim Speichern unter **Settings** bleiben **`dashboard`** und **`docker_update`** in **`app_settings.json`** erhalten (Merge).
- **Dashboard → Lüfter:** Über den Bereich liegt eine Zeile mit **„Lüfter prüfen & zuordnen …“** (SSH/sudo): Scan von **`/proc/it86/fan`** und **`hwmon`-`fan*_input`**, dann im Dialog **PWM-Kanal** (UGOS Kanal 1 vs. 2: `set`/`cpu` vs. `set2`/`cpu2`/`fan2`) und **RPM-Anzeige** pro Kachel wählbar; Speicherung lokal unter **`app_settings.json` → `dashboard`:** **`fan_slot0_use_pwm_secondary`**, **`fan_slot1_use_pwm_secondary`**, **`fan_slot0_rpm_key`**, **`fan_slot1_rpm_key`**. Persistiertes **Boot-PWM** (`ugreen_fan_boot.env`) enthält zusätzlich **`SLOT0_USE2`** / **`SLOT1_USE2`** passend zur Zuordnung. **Nur ein physischer Lüfter:** die zweite Kachel zeigt keine duplizierte Drehzahl mehr („nicht lesbar“, bis eine zweite RPM-Quelle existiert oder im Dialog eine Zeile gewählt wurde).
- **Dokumentation:** **`README.md`**, **`HANDBUCH.md`**, **`HANDBOOK_EN.md`**, **`HANDBUCH_STRUKTURIERT.md`** — Lüfter- und Netz-Kapitel (§ 6); PDF über **`tools/handbuch_pdf_from_md.py`**, Build: `python tools/build_handbuch_pdf.py`, `python tools/build_handbook_en_pdf.py`.

### English (short)

- **NAS management — cron reads:** **cron.d** listing, root **spool** paths, explicit **TimedShutdown** line detection.
- **Dashboard network tile:** **`ip -j addr` / route** summary, NIC **sparkline filter**, guarded runtime IP apply; **`dashboard`** merge on Settings save.
- **Dashboard fans:** **Probe & map** per tile (PWM + tach), **`SLOT0_USE2`/`SLOT1_USE2`** in boot env; no duplicate RPM when only one fan is present.

## 23.7.0 — 2026-05-09

- **Tab „NAS-Verwaltung“ ausgebaut (ein Scroll-Layout, gemeinsames Protokoll):** zusätzlich zu USB/SMART/RAID-Wartung/LED/Summer u. a. **Energie** (`/etc/power.conf`, WoL), **täglicher Shutdown** über `/etc/cron.d/nas_admin_timed_shutdown`, **UGOS-USB-Auswurf** mit `USBDiskStop` und lsof/fuser-Vorcheck (Dialogs nur im UI-Thread), **SMART Self-Test Log**, **mdcheck Fortschritt**, **SSH-Härtung** als `sshd_config.d`-Drop-in mit **bestätigtem Rollback** (`at` nur gezielt per Job-ID, Schreiben per base64), **UGOS-`*_serv`-Konsole**, **NGINX** Reload/Recovery, **earlyOOM**-Editor, **Samba** Freigaben/Papierkorb/Schnellanlage, vollständige **DE/EN-Übersetzungen** für die neuen Texte.

## 23.6.0 — 2026-05-08

Vergleichsbasis: **neueste öffentliche GitHub-Release `v23.5.2`**.

### Deutsch (ausführlich)

- **Settings / SSH-Workflow deutlich erweitert:**
  - Neue Buttons im Verbindungsbereich:
    - **`🔑 SSH-Key-Paar erstellen …`**
    - **`📌 Öffentlichen Key auf NAS installieren …`**
  - Direkter In-App-Flow für Key-basierte Authentifizierung:
    - Schlüsselpaar lokal erzeugen (`ugreen_nas_admin` + `.pub`)
    - optionaler Passphrase-Flow (kompatibel mit RSA/Ed25519-Strategie)
    - Public-Key-Installation auf Zielsystem über einmalige Passwort-SSH-Session
    - Zielauswahl **UGREEN** oder **zweites NAS/QNAP** inkl. SSH-Port-Abfrage für QNAP/Second-NAS.
  - Zweck: reproduzierbare, zentral gesteuerte SSH-Key-Einrichtung ohne externe PowerShell-Schritte.

- **Health/System-Bereich erweitert:**
  - Neuer Health-Hauptbutton **`🗓️ Scheduler-Inventar`** zur schnellen Übersicht geplanter Jobs.
  - UGOS-Service-Panel und zugehörige Texte/Erklärungen weiter ausgebaut.

- **Dashboard deutlich erweitert (Live-Metriken + Visualisierung):**
  - Dashboard-UI und Live-Loop ausgebaut (stabilere Aktualisierung und automatische Live-Synchronisation beim Tab-Wechsel).
  - Sparkline-/Trenddarstellung für Kennzahlen (inkl. Disk/Netz-Visualisierung) als kompakter Verlauf statt reiner Textwerte.
  - Verbesserte Erkennung NAS-relevanter Mounts (inkl. USB-/externer Mount-Hinweise) für die Dashboard-Storage-Sicht.

- **Lüftersteuerung massiv ausgebaut (Dashboard):**
  - Zwei Lüfter-Kacheln (System + CPU) mit RPM-Anzeige und Zustandszeile.
  - Modus-Buttons je Kanal: **Silent**, **Standard**, **Max** sowie **Manuell (%)** mit Apply.
  - Precheck vor Schreibzugriffen (hwmonitor/it86-Pfadprüfung) und robustere SSH-Fehlerbehandlung in der UI.
  - Explizite Rückgabe an UGOS über **„UGOS-Steuerung zurückgeben“** (Auto-Betrieb wiederherstellen, Cron-/Boot-Block aufräumen).
  - Persistenz-Flow für manuelle Lüfter-Profile über NAS-seitige Boot-Umgebung (`/volume1/scripts/ugreen_fan_boot_apply.sh`, `.env`) und Reboot-Integration.

- **Internationalisierung (i18n) erweitert und bereinigt:**
  - Neue SSH-/Settings-Texte in DE/EN plus Ergänzungen für zusätzliche Sprachen (u. a. hr/fr/es/it/pl/ru/tr/ko/zh) in den Supplement-Locales.
  - Ergänzung neuer Health-Labels (`health.scheduler_inventory`) in den Zusatzsprachen.
  - Ziel: konsistente UX ohne englische Resttexte in neu hinzugefügten Funktionen.

- **Dokumentation stark ausgebaut (gegenüber `v23.5.2`):**
  - Deutsches Handbuch **`HANDBUCH.md`** und englisches Handbuch **`HANDBOOK_EN.md`** mit vollständigen Settings-/SSH-Abschnitten:
    - Knopf-für-Knopf-Erklärung
    - Schritt-für-Schritt-Verfahren (UGREEN + QNAP/Second NAS)
    - technische Wirkung (`authorized_keys`, Public/Private-Key-Trennung)
    - Sicherheits- und Fehlerhinweise.
  - Strukturierte Zusatzfassung **`HANDBUCH_STRUKTURIERT.md`** ergänzt.
  - PDF-Generatoren für Handbücher vorhanden:
    - `tools/build_handbuch_pdf.py`
    - `tools/build_handbook_en_pdf.py`
  - Ergebnisartefakte:
    - `HANDBUCH.pdf`
    - `HANDBOOK_EN.pdf`

- **Projektregeln/Release-Disziplin geschärft:**
  - In `.cursorrules` explizit verankert:
    - Bei jeder neuen Funktion/Button müssen **Handbuch (DE/EN)**, **README** und **CHANGELOG** im selben Arbeitsgang aktualisiert werden.
  - Ziel: keine Feature-Drift zwischen UI, Doku und Release-Notizen.

- **Allgemeine Weiterentwicklung seit `v23.5.2` (bereits im Repo-Changelog dokumentiert):**
  - Ausbau Netzwerkgeräte-/Dashboard-/Docker-/Webcam-/Backup-Flows.
  - Größere i18n-Abdeckung.
  - Verbesserungen an Theme/UI, Explorer, Storage/ACL/Snap, Settings-Tab und Dokumentations-Tooling.
  - Siehe auch die bereits vorhandenen Einträge **23.3.0**, **23.4.0**, **23.5.x** für die chronologische Detailhistorie.

### English (summary)

- Compared to the latest public GitHub release **`v23.5.2`**, the current unreleased state adds a full **Settings SSH key workflow** (create key pair, install public key to UGREEN or second NAS/QNAP, one-time password install flow, key-based reuse afterwards).
- Health adds **Scheduler inventory** and improved UGOS service visibility text.
- Dashboard was expanded with richer live metrics and sparkline-style trend visualization (including storage/network rows).
- Fan control in Dashboard was extended to dual-channel control (System/CPU) with preset modes (Silent/Standard/Max), manual percent apply, UGOS handover, and boot-profile persistence flow.
- i18n was extended for new Settings/SSH/Health labels across DE/EN and supplemental locales.
- Documentation now includes complete DE/EN manuals with step-by-step SSH procedures, plus PDF build scripts and generated handbook PDFs.
- Project rules now explicitly require synchronized updates of **manuals + README + CHANGELOG** whenever features/buttons are added or changed.

## 23.5.2 — 2026-05-03

### Deutsch (ausführlich)

- **Öffentliche GitHub-Doku / README:** Screenshot-Galerie komplett erneuert — Bilder nach **App-Bereichen** benannt und unter **`images/`** ohne Leerzeichen im Dateinamen (u. a. `dashboard.png`, `scripts.png`, `task_scheduler.png`, `explorer.png`, `nas_to_nas.png`, `devices.png`, `storage.png`, `docker.png`, `users.png`, `snapshots.png`, `backup.png` / `backup_2.png` / `backup_3.png`, `system_health*.png`, `settings*.png`, `info.png`), damit **GitHub und ZIP** die Links zuverlässig auflösen.
- **`tools/build_oeffentlich_readme.py`** (privates Projekt): Pfade und Bildunterschriften an die neue Galerie angepasst; **„What’s new“** um **v23.5.2** ergänzt — nach `python tools/build_oeffentlich_readme.py` ist dieses **`README.md`** aktualisiert.
- **`__version__`** → **23.5.2** in **`ugreen_app/nas_manager.py`**.

### English (summary)

- **Public README / GitHub:** full **screenshot refresh** — area-based filenames under **`images/`** (URL-safe); captions aligned with major tabs.
- **Version bump** to **23.5.2**.

## 23.5.1 — 2026-05-01

Patch-Release (**ohne neue App-Features**) — Versionsnummer, Doku und **öffentlicher** Release-Tree an die Backup-Dokumentation angeglichen.

### Deutsch (ausführlich)

- **`README.md` (privat):** Abschnitt **„10) Backup & Wiederherstellen“ / „Backup & restore“** stark erweitert — **drei Modi** (Docker+Skripte / Userdaten / alle Daten), **Ziele** NAS-intern · **PC-Ordner** · **USB am NAS** · **Zweit-NAS (SMB)**; **geplante Jobs** (`scheduled_backups.json`, **`ugreen_scheduled_backup_runner.py`**, Cron), Hinweis **kein reines „Ziel nur PC“** bei Cron; Kurz-Verweis für „Backup-first“-Nutzer direkt unter der Sicherheitwarnung (DE + EN Tab-Liste).
- **`tools/build_oeffentlich_readme.py`:** Öffentliches README-Intro + **What’s new** an Backup-Kapitel und **v23.5.1** angepasst.
- **`ugreen_app/nas_manager.py`:** **`__version__`** → **23.5.1**.

### English (summary)

- **README:** Expanded **§10 Backup & restore** (three modes, NAS/PC/USB/second‑NAS destinations, NAS-side cron notes); backup-focused callouts; synced public README generator blurbs.
- **Version bump** to **23.5.1** (`nas_manager.py`).

## 23.5.0 — 2026-05-01

### Deutsch (ausführlich)

- **Tab „Netzwerkgeräte“:** neue Übersicht **LAN- und USB-Geräte, die das NAS über SSH sieht** (Nachbarschaft/ARP-artige Daten; `lsusb` / `lsblk` für USB; ohne aktive SSH-Session Hinweis statt Scan). Für Nutzer dokumentiert die **README** den Ablauf **Geräte suchen** und Abgrenzung zum PC-Netzwerkscan.
- **Internationalisierung (alle UI-Sprachen):** Modul **`ugreen_app/i18n_supplement_devices_telegram.py`** mit vollständigen Einträgen für **`tab.devices`**, **`nav.devices`**, alle **`devices.*`**-Zeichenketten sowie **vollständigem `health.telegram_hint`** (Token/Settings, NAS-Zentral-Wächter/Cron, **SSH-Login-Meldungen vs. Platten-Schwellen**, **SSH-Keepalive**, UGOS/vertrauenswürdige Client-IP) für **hr, fr, es, it, pl, ru, tr, ko, zh** — eingebunden per zusätzlichem Merge in **`i18n.py`**. PyInstaller: **`hiddenimports`** **`ugreen_app.i18n_supplement_devices_telegram`** in **`UgreenNASAdmin.spec`**.
- **`translate()`:** bei Aufrufen **ohne** `str.format`-Platzhalter **LRU-Cache** (weniger Arbeit bei häufigen `self.t(...)`-Zugriffen).
- **Dokumentation:** **`README.md`** stark erweitert — vollständige **Tab-Reihenfolge** (inkl. **Dashboard**, Netzwerkgeräte), neue Kapitel **Dashboard / Netzwerkgeräte / Backup-Einstieg**, Abschnitt **SSH-Login vs. Telegram-Wächter** (DE + EN); **`CHANGELOG.md`** dieser Eintrag.

### English (summary)

- **Network devices** tab: NAS-side LAN/USB discovery over SSH (documented in README).
- **i18n:** `i18n_supplement_devices_telegram.py` + merged into **`i18n.py`** for nine locales; full **devices** strings and extended **health.telegram_hint**; PyInstaller hidden import in **`UgreenNASAdmin.spec`**.
- **`translate()`:** LRU cache for plain lookups (no format kwargs).
- **Docs:** README tab overview, Dashboard / Network devices, Backup overview, Telegram/SSH clarification (EN + DE).

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
