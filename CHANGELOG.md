# Changelog — Ugreen NAS Admin

---

## Deutsch

### 22.2.0 (Public) — 2026-04-01

Größeres UI-/Sicherheits-Update: **eingeschränkter Standardmodus**, schlankerer **Header**, **Live-Monitor** in der Sidebar, feste **SSH-Key-Feldbreite**, größere **Startfensterbreite**.

#### Sicherheit: „Volle Rechte“ / Restricted Mode

- **Standard:** Viele **riskante Aktionen** sind **deaktiviert** (ausgegraute Buttons, gesperrte Planer-Steuerelemente, eingeschränkte Kontextmenüs), bis du sie bewusst freischaltest.
- **Roter Header-Button** „**⚠ Volle Rechte**“ / „**⚠ Full access**“: Nach Bestätigung des Dialogs **„Vorsicht: Absolute Rechte“** werden u. a. Löschen, Uploads, Docker-Aktionen (Start/Stop/Löschen/…), Cron-/Planer-Jobs, ACL-Schreibzugriffe, Snapshot anlegen/löschen, NAS-Neustart/Herunterfahren, Telegram-Aktionen im Health-Tab, Health-Snapshot speichern und ähnliche Funktionen **bedienbar**.
- **Erneuter Klick** (orange „**🔒 Einschränken**“ / „**🔒 Restrict**“) kann den eingeschränkten Modus **wieder aktivieren** (mit Bestätigung).
- **Technik:** Modul `ugreen_app/mixin_safety_lock.py`; abgerundete Buttons unterstützen **`set_enabled()`** in `rounded_ui.py`; zusätzlich **`_danger_gate()`** an zentralen Einstiegspunkten (z. B. `write_root_file`, Upload-Queue, Docker, Explorer-Löschen, …), falls eine Aktion die UI umgeht.
- **Session:** Freischaltung gilt für die **laufende Sitzung** (kein separates JSON-Flag); nach **Theme-/Sprachwechsel** bleibt der Zustand erhalten, die UI wird neu aufgebaut.

#### Kopfzeile (Header)

- **Eine Zeile** für **NAS-IP, SSH-Port, User, Passwort, SSH-Key (Checkbox + Pfad), Passphrase** — kompaktere Abstände, **linksbündige** IP/User für bessere Lesbarkeit.
- **SSH-Key-Pfad:** **Feste Zeichenbreite** (wächst nicht unbegrenzt bei maximiertem Fenster); freier Platz wandert in eine **Leerspalte** rechts der Passphrase statt einen Riesen-Eintrag zu erzeugen.
- **Hinweistext** (Klartext-JSON / Tresor): **`wraplength`** passt sich der **Headerbreite** an (`Configure`-Event).
- **Rechte Aktionen** (Volle Rechte, Theme, Verbindung speichern, PW-Tresor, Coffee): per **Grid** am **unteren Rand des gesamten Kopfbereichs** (inkl. Hinweiszeile) ausgerichtet — optisch eine Linie mit den Eingabefeldern.
- **Startbreite** Standard **1500 px**, **`minsize`** Breite **1260 px** (siehe `nas_manager.py`).

#### Live-Monitor

- Aus dem Header in die **linke Sidebar** unten verlegt (**über** der Statusleiste mit DE/EN), Abschnitt **„Live-Monitor“**.
- **Kleinerer Start-Button** (kurze Beschriftung **„▶ Live“** / **„⏹ Stop“**).
- **CPU:** nur noch **Gesamt-CPU** (Zeile `cpu` in `/proc/stat`), **keine** Einzelkerne mehr.
- **RAM:** unverändert über `free` (ein Balken + Prozent).

#### Internationalisierung (`i18n.py`)

- Neue Schlüssel u. a. für Sicherheitsdialoge, Sidebar-Monitor, kompakte SSH-Key-Labels (**„SSH-Key“**, **„Passphrase“**).

#### Build / PyInstaller

- **`UgreenNASAdmin.spec`:** Hidden Import **`ugreen_app.mixin_safety_lock`**.

#### Dokumentation & Screenshots

- **`README.md`:** Aktualisiert (Header, Sicherheitsmodus, Live-Monitor, Screenshots **1.png–6.png** unter `images/`).
- **`images/`:** bis zu sechs App-Screenshots für GitHub-README (keine echten Passwörter/IPs in den Bildern).

---

### 22.1.0 (Public) — 2026-04-01

Ausführliche Übersicht der Änderungen gegenüber 22.0.0 (Verbindungsfelder **NAS-IP / SSH-Port / User / Passwort / SSH-Key** gab es schon früher; sie sind in **`README.md`** unter *Verbindung zur NAS (Kopfzeile)* beschrieben).

#### SSH (`nas_ssh.py`, `run_ssh_cmd`)

- **Kompression:** Paramiko-Verbindung nutzt **`compress=True`** (kann bei vielen/kleinen SSH-Antworten die Last etwas reduzieren).
- **Wiederverwendung:** unverändert eine SSH-Sitzung pro Kontext mit Lock (kein Verbindungschaos bei schnellen Klicks).
- **Lokalisierte Texte:** `SSHManager.run()` akzeptiert jetzt optionale Parameter **`status_connected`**, **`status_failed`**, **`error_message_fmt`**; die App übergibt Übersetzungen aus **`i18n`** (`status.ssh_connected`, `status.ssh_failed`, `ssh.error`). Fehler wie „SSH connection error: …“ / „Fehler bei SSH-Verbindung: …“ folgen der gewählten Sprache (DE/EN).
- **Rückwärtskompatibel:** Ohne diese Parameter bleiben die bisherigen deutschen Standardstrings.

#### Oberfläche & Reaktionszeit

- **NAS-Explorer:** Beim **Aufklappen** eines Ordners läuft `ls` per SSH in einem **Hintergrundthread**; die Treeview wird per **`after(0)`** auf dem UI-Thread aktualisiert (kurz „Lade…“ als Platzhalter). Die UI friert nicht mehr während des Verzeichnislistings ein.
- **NAS-Explorer — Suche:** `ls` + Auswertung der Treffer ebenfalls im **Hintergrund**; Meldungsdialoge nur noch vom Hauptthread.
- **Docker-Tab:** **Stats**, **Inspect** und **Container-Logs** holen die SSH-Ausgabe im Hintergrund und schreiben ins Log-Fenster, wenn die Daten da sind (kein langes Blockieren beim Klick).
- **Docker-Log-Überschrift:** einheitlich über **`i18n`** (`docker.logs_banner` / `docker.log_loading_stats` wo zutreffend).

#### Sicherheit & Passwort

- **Hinweistext** unter der Verbindungszeile: erklärt, dass **„Verbindung speichern“** das Passwort in **`nas_admin_connection.json` im Klartext** ablegt und weist auf den **optionalen OS-Tresor** hin.
- **Button „🔐 PW Tresor“ / „🔐 PW vault“:** speichert das aktuelle SSH-Passwort über das optionale Paket **`keyring`** in der **Windows-Anmeldeinformationsverwaltung** (Dienstname `UgreenNASAdmin`, Schlüssel `user@host`).
- **Laden:** Ist in der JSON das Passwort **leer**, aber IP und User gesetzt, wird beim Start aus dem Tresor gelesen (gleiche Kombination).
- **Neues Modul** `ugreen_app/keyring_helper.py` (Try/Import `keyring`; ohne Paket nur Hinweisdialog).
- **PyInstaller:** `ugreen_app.keyring_helper` als **Hidden Import** in **`UgreenNASAdmin.spec`**, damit die gebaute EXE das Modul findet (trotzdem: `pip install keyring` vor dem Build, wenn der Tresor in der EXE funktionieren soll).

#### Hilfsfunktionen (`nas_utils.py`)

- **`looks_like_ssh_error_output(text)`:** erkennt typische SSH-Verbindungsfehler-Strings (DE und EN), damit Explorer/Du-Hintergrundjobs fehlerhafte Ausgaben nicht als Dateilisten interpretieren.
- **`explorer_sanitize_ls_line`:** filtert zusätzlich englische SSH-Fehlerzeilen (konsistent zu den neuen Übersetzungen).

#### Qualität / Tests (nur Quellbaum mit `tests/`)

- Zusätzliche Unit-Tests für **`looks_like_ssh_error_output`** und Sanitize-Verhalten (im **privaten** Hauptprojekt unter `tests/`; die öffentliche ZIP-Quelle enthält die Tests optional nicht).

#### Dokumentation & GitHub-README

- **`README.md`:** Abschnitt **Screenshots / App-Bilder** oben (zentrierte Vorschau für GitHub); ausführlicher Abschnitt **SSH-Passwort im Windows-Tresor**; **Verbindung zur NAS (Kopfzeile)** mit SSH-Port und SSH-Key; Hinweise zu öffentlichen Screenshots.
- **`requirements.txt`:** Kommentar zu optionalem **`pip install keyring`**.
- Dieses **CHANGELOG:** ausführliche Release-Notiz für 22.1.0.

### 22.0.0 (Public) — 2026-03-30

#### Neu

- Ordner **`öffentlich/`**: enthält alle zum **Starten** und **Bauen** der App nötigen Dateien (Release-Quelle für öffentliche Versionen). Siehe `README.md` — **Ordner nicht löschen**; bei Änderungen im Hauptprojekt Inhalt bei Bedarf spiegeln.
- **Öffentliche Version** mit zweisprachiger Oberfläche **Deutsch / Englisch**.
- **Sprach-Umschalter** `DE / EN` unten links in die Statusleiste; Umschalten lädt die UI neu (gleiche Session, Verbindungsdaten bleiben erhalten).
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

### 22.2.0 (Public) — 2026-04-01

Major UI/safety update: **restricted default mode**, slimmer **header**, **live monitor** in the sidebar, fixed-width **SSH key path**, larger **default window width**.

#### Safety: “Full access” / restricted mode

- **By default**, many **risky actions** are **disabled** (grayed buttons, planner controls locked, context menus trimmed) until you explicitly unlock.
- **Red header button** “**⚠ Full access**”: after confirming **“Caution: full privileges”**, destructive operations (delete, uploads, Docker start/stop/rm/…, cron/planner jobs, ACL writes, snapshot create/delete, NAS reboot/shutdown, Telegram actions on the Health tab, saving health snapshots, etc.) become **available**.
- **Second click** (amber “**🔒 Restrict**”) can **re-enable** restriction (with confirmation).
- **Implementation:** `ugreen_app/mixin_safety_lock.py`; rounded buttons support **`set_enabled()`** in `rounded_ui.py`; **`_danger_gate()`** on key entry points as a backstop.
- **Session-only** unlock (no separate JSON flag); **theme/language rebuild** keeps state and reapplies UI.

#### Header

- **Single row** for **NAS IP, SSH port, user, password, SSH key (checkbox + path), passphrase** — tighter spacing, **left-aligned** IP/user.
- **SSH key path:** **Fixed character width** (does not grow without bound when maximized); extra space goes to a **spacer column** after passphrase.
- **Security hint** under the row: **`wraplength`** tracks **header width**.
- **Right-side actions** aligned to the **bottom of the full header block** (including the hint row) via **grid**.
- **Default width** **1500 px**, **minimum width** **1260 px** (`nas_manager.py`).

#### Live monitor

- Moved from the header to the **bottom of the left sidebar** (above the status bar / language toggle), section **“Live monitor”**.
- **Smaller button** (“**▶ Live**” / “**⏹ Stop**”).
- **CPU:** **aggregate only** (`cpu` line in `/proc/stat`), **no** per-core bars.
- **RAM:** unchanged (`free` — one bar + percent).

#### i18n

- New keys for safety dialogs, sidebar monitor, compact SSH labels.

#### Build / PyInstaller

- **`UgreenNASAdmin.spec`:** hidden import **`ugreen_app.mixin_safety_lock`**.

#### Docs & screenshots

- **`README.md`** updated (header, safety mode, live monitor, screenshots **1.png–6.png** in `images/`).

---

### 22.1.0 (Public) — 2026-04-01

Detailed changes vs 22.0.0. (**NAS IP / SSH port / user / password / SSH key** fields already existed in earlier releases; see **`README.md`** → *Connection to the NAS (header bar)*.)

#### SSH (`nas_ssh.py`, `run_ssh_cmd`)

- **Compression:** Paramiko uses **`compress=True`** (may reduce traffic for chatty sessions).
- **Session reuse:** unchanged — one SSH session per context with a lock.
- **Localized strings:** `SSHManager.run()` now accepts optional **`status_connected`**, **`status_failed`**, **`error_message_fmt`**; the app passes strings from **`i18n`** (`status.ssh_connected`, `status.ssh_failed`, `ssh.error`). Error messages follow DE/EN.
- **Backward compatible:** omitting those parameters keeps the previous German defaults.

#### UI & responsiveness

- **NAS Explorer — expand:** remote `ls` runs in a **worker thread**; the tree updates via **`after(0)`** (short “loading…” placeholder). The window stays responsive.
- **NAS Explorer — search:** remote listing + hit filtering in a **background thread**; message boxes only from the main thread.
- **Docker tab:** **Stats**, **Inspect**, and **container logs** fetch SSH output in the **background** and append when ready.
- **Docker strings:** headings use **`i18n`** (`docker.logs_banner`, `docker.log_loading_stats` where applicable).

#### Security & password

- **Hint** under the connection row explains plain-text **`nas_admin_connection.json`** and points to the **optional OS vault**.
- **“🔐 PW vault”** stores the current SSH password via **`keyring`** in **Windows Credential Manager** (service `UgreenNASAdmin`, account `user@host`).
- **Load:** if the JSON password is **empty** but IP and user are set, the password is read from the vault on startup (same pair).
- **New module** `ugreen_app/keyring_helper.py` (optional `keyring`; without package, info dialog only).
- **PyInstaller:** `ugreen_app.keyring_helper` as **hidden import** in **`UgreenNASAdmin.spec`** (still run `pip install keyring` before build if you want vault support in the EXE).

#### Helpers (`nas_utils.py`)

- **`looks_like_ssh_error_output(text)`** detects typical SSH error strings (DE/EN).
- **`explorer_sanitize_ls_line`** also filters English SSH error lines.

#### Docs

- **`README.md`:** screenshots block, vault section, connection table with SSH port and key.
- **`requirements.txt`:** note on optional **`keyring`**.

### 22.0.0 (Public) — 2026-03-30

#### New

- **`öffentlich/`** folder as the canonical public release source.
- **DE/EN UI** with **language toggle** in the status bar; **`ui_lang`** persisted in **`nas_admin_connection.json`**.
- **Translations** in **`ugreen_app/i18n.py`**.
- **NAS Explorer** two-pane (NAS / **This PC**), upload/download/copy, progress UI.

#### Changed

- Tabs, sidebar, planner, status bar largely localized; PyInstaller hidden import **`ugreen_app.i18n`**.

#### Note

- Some deep dialogs (e.g. Snapper/Btrfs prompts) may still show German defaults.

#### 21.2.0 and older

- See internal notes / backups.
