# Ugreen NAS Admin - Komplettes Handbuch (strukturierte Edition)

> **Tab „Login Track“ (komplett):** **`HANDBUCH.md` → `## 14. Tab Login Track komplett`**. **Tab „NAS-Verwaltung“ (komplett):** **`HANDBUCH.md` → `## 15. Tab NAS-Verwaltung komplett`** (blaue PDF-Überschriften wie andere Tabs). Kurzfassungen hier **12.6** / **12.7**. Die App öffnet bei **Info → Handbuch** die **`HANDBUCH.pdf`** (neben der .exe) aus **`HANDBUCH.md`**. PDF aktualisieren: `python tools/build_handbuch_pdf.py`.

## 1. Ziel dieses Handbuchs

Dieses Handbuch erklaert die aktuelle App-Version als durchgaengigen Betriebsleitfaden. Jeder Bereich ist so aufgebaut, dass alles, was zusammengehoert, direkt im selben Kapitel steht: Felder, Buttons, typische Nutzung, Fehlerfaelle und sichere Reihenfolgen.

Die App arbeitet nicht als Demo, sondern veraendert reale NAS-Zustaende. Deshalb wird jede Funktion mit Wirkung beschrieben.

---

## 2. Schnellstart in 10 Minuten

1. `Settings` oeffnen und SSH-Verbindung vollstaendig eintragen.
2. `Speichern` und Verbindung pruefen.
3. Telegram oder SMTP konfigurieren.
4. `Dashboard` auf Live-Daten pruefen.
5. `Health` einmal komplett refreshen.
6. `Scripts` oeffnen und Bestand sichern (`Backup`).
7. Docker-Liste laden.
8. Backup-Ziel festlegen.
9. kleinen Test-Backup-Lauf ausfuehren.
10. `Watcher` und `Daily Report` aktivieren.

_(Hinweis ab App-Version **23.8.1+:** Nach funktionierender SSH-Verbindung einmal **„Alles aktualisieren“** (Sidebar unten) ausführen — der Gesamt-Refresh läuft **gebündelt** über das NAS (weniger einzelne SSH-Runden) und aktualisiert u.a. die **UGOS/OS-Zeile** im Header sowie die **Service-Dropdown-Liste** im Tab NAS-Verwaltung.)_

---

## 3. Header komplett

### 3.1 Elemente und Bedeutung

- `Volle Rechte` / `Einschraenken`: schaltet kritische Aktionen frei oder sperrt sie.
- Theme-Button: Light/Dark umschalten.
- Sprachwahl: UI-Sprache aendern.
- `Screenshot`: speichert App-Fensterbild in den in `Settings` gesetzten Screenshot-Pfad.
- `Info`: oeffnet Dokumente und Projektlinks.
- `Coffee`: Support-/Spendenlink.
- SSH-Statusbadge: zeigt Verbindungszustand.
- Modellanzeige: zeigt erkanntes NAS-Modell nach erfolgreicher SSH-Auslese.
- **UGOS/OS-Zeile** (unter der Modellanzeige): zeigt nach erfolgreicher Auslese u. a. **`OS_VERSION`** und **`PRETTY_NAME`** aus **`/etc/os-release`**, optional den Hinweis **Beta**, wenn **`OS_IS_BETA=true`**. Befüllung: nach **„Alles aktualisieren“** in der Sidebar (ein gebündelter SSH-Lauf) und/oder beim **ersten Start der Dashboard-Live-Daten**, falls die Zeile noch leer war. Ohne SSH bleibt ein Hinweistext stehen.

### 3.2 Sicheres Arbeiten im Header

Vor kritischen Aktionen immer erst auf SSH-Status achten. Nie dauerhaft in Vollrechten arbeiten.

---

## 4. Tab Settings komplett

Dieser Tab ist die Basis fuer fast alle anderen Bereiche.

### 4.1 Obere Buttons

- `Laden`: gespeicherte Konfiguration in UI laden.
- `Auf aktuelle UI anwenden`: Werte direkt in laufende Session uebernehmen.
- `Speichern`: dauerhaft in Konfigdatei schreiben.

### 4.2 Verbindung

Felder:

- NAS IP / Host
- SSH Port
- User
- Passwort oder Key-Daten

Buttons:

- `Verbindung speichern`
- `PW Tresor`
- `SSH-Key-Paar erstellen`
- `Oeffentlichen Key auf NAS installieren`
- Profilbuttons (`Neu`, `Loeschen`)

### 4.2.1 Was jeder SSH-bezogene Knopf genau macht

- `SSH-Key-Paar erstellen`
  - Erstellt auf deinem PC ein neues Schluesselpaar:
    - privat: `ugreen_nas_admin`
    - oeffentlich: `ugreen_nas_admin.pub`
  - Fragt optional nach Passphrase.
  - Kopiert den oeffentlichen Schluessel in die Zwischenablage.
  - Kann den privaten Key-Pfad direkt ins Verbindungsformular eintragen und `SSH-Key` aktivieren.

- `Oeffentlichen Key auf NAS installieren`
  - Verwendet eine **einmalige** SSH-Anmeldung mit Passwort (ohne Key), um den Public Key auf dem Zielsystem einzutragen.
  - Schreibt den Public Key in `~/.ssh/authorized_keys`.
  - Zielauswahl:
    - `UGREEN` ueber obere Verbindungsfelder (IP/Port/User/Passwort)
    - `Zweites NAS / QNAP` ueber unteres SMB-Profil plus abgefragten SSH-Port

- `Verbindung speichern`
  - Speichert alle Verbindungsfelder dauerhaft (inkl. Key-Pfad, Key-Option, Ports/User).

- `PW Tresor`
  - Speichert das Passwort im System-Keyring statt nur im Eingabefeld.

### 4.2.2 Komplette SSH-Key-Anleitung (Schritt fuer Schritt)

1. In `Settings -> Verbindung` NAS-IP, SSH-Port, User und Passwort korrekt eintragen.
2. `SSH-Key-Paar erstellen` klicken und Zielordner waehlen.
3. Optional Passphrase setzen:
   - mit Passphrase: RSA 4096 (kompatibel),
   - ohne Passphrase: Ed25519 (bevorzugt).
4. Rueckfrage bestaetigen, damit privater Key-Pfad uebernommen und `SSH-Key` aktiviert wird.
5. `Verbindung speichern` klicken.
6. `Oeffentlichen Key auf NAS installieren` klicken.
7. Ziel waehlen:
   - `UGREEN`: installiert auf dem NAS aus dem oberen Verbindungsblock,
   - `Zweites NAS / QNAP`: nutzt unteres Profil; SSH-Port wird extra abgefragt.
8. Nach Erfolg: kuenftige Logins und App-Aktionen laufen ueber den privaten Key vom PC.

### 4.2.3 Warum man das braucht

- Kein staendiges Passwort-Eingeben bei SSH-Aktionen.
- Ein Schluesselpaar kann fuer mehrere Systeme genutzt werden (UGREEN, QNAP, weitere Linux-Hosts).
- Stabilere und schnellere Automationen (z. B. Skripttests, Transfers, NAS↔NAS).
- Der private Key bleibt lokal auf dem PC; auf NAS wird nur der oeffentliche Anteil hinterlegt.

### 4.2.4 Wichtige Sicherheitsregeln

- Privaten Key niemals weitergeben oder auf NAS hochladen.
- Public Key darf verteilt werden, privater Key nie.
- Bei QNAP den echten SSH-Port verwenden (nicht immer Standard 22).
- Bei Fehlern zuerst pruefen: SSH aktiv, richtige Zugangsdaten, Home-Verzeichnis des Users vorhanden/beschreibbar.

### 4.3 Zweites NAS Profil (SMB)

Felder:

- Profilname
- Host
- Benutzer
- Passwort

Buttons:

- `Profil hinzufuegen`
- `Profil loeschen`

Dieses Profil wird spaeter in `NAS↔NAS` und `Backup` verwendet.

### 4.4 Telegram

Felder:

- Bot Token
- Chat ID

Button:

- `Secrets anzeigen/ausblenden`

### 4.5 SMTP / E-Mail

Felder:

- SMTP Host
- Port
- User
- Passwort
- From
- To

Optionen:

- STARTTLS
- SMTPS/SSL

### 4.6 Pfade

Felder:

- Scripts-Pfad
- Compose-Pfad
- Explorer-Root
- Screenshot-Pfad

Button:

- `Ordner waehlen`

### 4.7 Script-Notify-Regeln

Felder:

- Skript
- Kanal (`telegram`, `email`, `both`)
- Trigger (`success`, `fail`, `both`)

Buttons:

- `Refresh`
- `Regel hinzufuegen`
- `Regel loeschen`
- `Jetzt synchronisieren`

### 4.8 Telegram-Bot Schritt-fuer-Schritt

1. In Telegram `@BotFather` suchen.
2. `/newbot` senden.
3. Namen und `...bot`-Username vergeben.
4. Token kopieren.
5. Bot einmal anschreiben.
6. `https://api.telegram.org/bot<TOKEN>/getUpdates` aufrufen.
7. `chat.id` als Chat-ID uebernehmen.
8. Token + Chat-ID in Settings eintragen und speichern.

Fehlerbilder:

- `Unauthorized`: Token falsch.
- `chat not found`: falsche Chat-ID oder Bot nicht gestartet.

---

## 5. Tab Dashboard komplett

### 5.1 Live-Bloecke

- CPU
- RAM
- Volume/Belegung
- **Speicher (UGOS API):** Pools, Disks, Sysinfo, Lüfter/Netz/Volumes per Web-API (Settings → UGOS API); Details **`HANDBUCH.md`** → **42.7**
- Netzwerk (siehe **5.3**)
- Docker Uebersicht
- Skriptjob-Uebersicht

### 5.2 Lüfter-Bereich (dynamisch: 1–8 Kacheln)

**Handbuch im Dashboard-Tab:** **📖 Handbuch** (Kopfzeile) oder Tab-Button öffnet **Kapitel 6** in **`HANDBUCH.pdf`** — dort **24.2**, **42.6**, **62** (Erkennung, Steuerung, Kurven, UGOS-Rückgabe).

**Ablauf:** Zuerst **„Lüfter prüfen & zuordnen …“** (SSH/sudo-Scan von **`/proc/it86/fan`** und **`hwmon`** **`fan*_input`**). Pro **gefundenem** RPM-Sensor eine Zeile: **PWM-Kanal** (Kanal 1 `set/cpu` vs. Kanal 2 `set2/cpu2/fan2`) und **RPM-Zeile**. **Speichern** → **`app_settings.json`** → **`dashboard.fan_devices`**; Kacheln werden neu aufgebaut (Anzahl = gefundene Lüfter, nicht fest zwei).

**Je Kachel:** Leise / Standard / Max / Manuell % + Übernehmen / **Lüfterkurve …** / (erste Kachel) **UGOS-Steuerung zurückgeben**. Kurven unter **`dashboard.fan_curves.<fan_id>`**; NAS: **`ugreen_fan_curve_apply.sh`**, Cron minütlich. Boot-PWM: **`ugreen_fan_boot.env`** mit **`FAN_COUNT`**. Ausführlich **`HANDBUCH.md`** → **## 6** (**24.2**, **42.6**, **62**).

### 5.3 Netzwerk-Kachel (Durchsatz + Konfiguration)

- **Sparklines:** Durchsatz je NIC (physische Interfaces); optional **Filter** (kommagetrennt) nur fuer die Kurven; leer = alle. Gespeichert: `app_settings.json` → `dashboard.net_monitor_filter`.
- **Aktuelle Konfiguration:** live vom NAS (`ip -j addr`, Standardroute); **Dropdown Schnittstelle** waehlt die Detailansicht; gespeichert: `dashboard.net_detail_iface`.
- **Aendern:** IPv4, Praefix, Gateway, Modus **Statisch** oder **DHCP neu**; **Vom NAS laden** fuellt die Felder; **Anwenden (sudo)** nur mit **Volle Rechte** und Bestaetigung (Risiko: SSH-Abbruch). Laufzeit-`ip`/`dhclient` — UGOS kann nach Neustart ueberschreiben. Vollstaendig: **`HANDBUCH.md`** → **## 6**, Abschnitt **42.3 Netzwerk**.

---

## 6. Tab Scripte komplett

### 6.1 Linke Seite (Liste + Aktionen)

Buttons:

- `Backup`
- `Aktualisieren`
- `Testen (Host)`
- `Testen (Docker)`
- `Neue Datei`
- `Loeschen`
- `Zeitplaene`
- `PowerShell/SSH`

### 6.2 Rechte Seite (Editor)

Felder:

- Dateiname
- Skriptinhalt

Templates:

- `rsync`
- `restic`
- `rclone`

Speichern:

- `Speichern (root)`
- `Speichern (user)`

### 6.3 Sicherer Skriptablauf

1. Neues Skript mit klarer Datei-Endung anlegen.
2. Erst lokal logisch pruefen.
3. Speichern.
4. Host-Test.
5. Optional Docker-Test.
6. Danach Scheduler setzen.

---

## 7. Scheduler (aus Scripte heraus) komplett

Felder:

- Minute
- Stunde
- Tag
- Monat
- Wochentag

Option:

- erste Woche

Buttons:

- `Als Host-Job`
- `Als Docker-Job`

Nach dem Speichern den Cron-Postcheck beachten und Job einmal manuell testen.

---

## 8. Tab NAS Explorer komplett

### 8.1 Toolbar

- `NAS scannen`
- `Upload`
- `Perms 755`
- `NAS loeschen`
- `PC loeschen`
- `PC -> NAS`
- `NAS -> PC`
- `Suchen`

### 8.2 NAS-Baum Kontextmenue

- In Editor laden
- Rechte setzen
- Pfad kopieren
- Upload Datei/Ordner
- Loeschen

### 8.3 PC-Baum Kontextmenue

- Im Explorer oeffnen
- Pfad kopieren
- Lokal loeschen

Sicherheitsregel: Vor Loeschungen immer pruefen, ob Fokus wirklich auf NAS oder PC steht.

---

## 9. Tab NAS↔NAS komplett

### 9.1 Funktionen

- `Ugreen scannen`
- SMB/Freigaben scannen
- Profilauswahl fuer Ziel-NAS

### 9.2 Transferlogik

1. Quellseite scannen.
2. Zielseite scannen.
3. Pfad links/rechts explizit markieren.
4. Transfer per Kontextmenue starten.

Typische Fehler:

- Profil in Settings unvollstaendig.
- Freigaberechte fehlen.
- Zielhost nicht erreichbar.

---

## 10. Tab Netzwerkgeraete komplett

Button:

- `Geraete suchen`

Zeigt erkannte Netz-/USB-Geraete inklusive Basisdetails.

Wenn SSH fehlt oder Discovery scheitert, erscheint ein Hinweis statt Daten.

---

## 11. Tab Docker komplett

### 11.1 Obere Leiste

- `Docker Katalog`
- `Neuer Docker`
- `Docker Update`
- `Ausschlussliste`
- `Liste`
- `Alle Container stoppen`
- `Start`
- `Stop`
- `Restart`

Option:

- `Bei Fehler mit naechstem Container fortfahren`

### 11.2 Untere Diagnose-/Aktionsleiste

- `Stats`
- `Inspect`
- `Loeschen`
- `Fix 777`

### 11.3 Log- und Compose-Bereich

Logbuttons:

- `Live-Log starten`
- `Live-Log stoppen`

Compose:

- Dateifeld
- `config`
- `ps`
- `up -d`

### 11.4 Voller Docker-Workflow

1. `Liste` laden.
2. Zielcontainer markieren.
3. `Inspect` + `Logs` als Baseline lesen.
4. Aktion ausfuehren (`Start`, `Stop`, `Docker Update`).
5. Ergebnis mit Logs und Funktionscheck validieren.

---

## 12. Tab System & Health komplett

### 12.1 Hauptbuttons

- `Refresh Health`
- `RAID pruefen`
- `SMART pruefen`
- `Storage`
- `Report speichern`
- `Neustart`
- `Herunterfahren`

### 12.2 UGOS Service Dashboard

Zeigt Kernservice-Zustaende als schnelle Betriebskontrolle. Beim **Health-Refresh** zusaetzlich **UGOS API (live)** (Modell, Luefter, NIC-Geschwindigkeit, Volumes) sofern API konfiguriert; Warnung bei **`domain_tool.service` failed**. Vollstaendig **`HANDBUCH.md`** → **31.2**, **49.3**.

### 12.3 Telegram-Sofortmonitor

Felder/Schwellen:

- aktiv
- Intervall
- Disk Warn/Crit
- Temperaturgrenze
- Cooldown
- Fan-Minimum

Buttons:

- `Telegram-Test`
- `Manuelle Pruefung`

### 12.4 NAS Watcher

Kanaele:

- Telegram
- E-Mail
- Both

Check-Checkboxen:

- Disk
- RAID
- Netzwerk bereit
- Temperatur
- Docker
- SMART-Dienst
- SMB/NFS-Dienste
- Wartungstimer
- systemd failed
- Fan
- SSH Loginfehler

Weitere Felder:

- Required Container
- Ignore Pattern
- Auto-Restart-Liste
- Login-Fenster

Buttons:

- `Lokal speichern`
- `Auf NAS installieren`
- `Test auf NAS`

### 12.5 Daily Report

- `Daily aktiv`
- `Lokal speichern`
- `Auf NAS installieren`
- `Test senden`
- Der auf dem NAS laufende Bericht enthält seit v23.8.1 einen Block **OS / UGOS** (Auszug aus **`/etc/os-release`**: u. a. `PRETTY_NAME`, `VERSION_ID`, `OS_VERSION`, `OS_IS_BETA`).

### 12.6 Tab Login Track (Zugriffe nach Client-IP)

**Sidebar:** Zwischen **System & Health** und **NAS-Verwaltung** (Icon **🔐**).

**Zweck:** Anmeldungen und Verbindungen zum NAS **nach Client-IP** — SSH, SMB, UGOS-App (iPhone/PC), UGOS-Web, aktive TCP-Verbindungen (`ss`). **Echtzeit** (Standard): nur **neue** Zeilen seit Tab-Start/Baseline; **Aktualisieren** mit abgeschalteter Echtzeit lädt **Historie** (ca. 30 Tage Journal + Log-Tails).

**Bedienung:** Sortierung (**Datum/Uhrzeit** zuerst Tag, dann Uhrzeit; ohne Zeitstempel am Ende), Filter **App-Session-Pings ausblenden**, **Export …**, **IP sperren …** (Rechtsklick auf Zeile) → **`/ugreen/.config/block_ip_list`**. Liste nur lesen, Trennlinien zwischen Einträgen.

**Vollständig:** **`HANDBUCH.md` → `## 14. Tab Login Track komplett`**.

### 12.7 Tab NAS-Verwaltung (aktive Aktionen, SSH/sudo)

**Sidebar:** Zwischen **Login Track** und **Speicher & Freigaben**. Zwei Spalten: links alle Funktionsblöcke (scrollbar), rechts SSH-Protokoll; dazwischen **Splitter** ziehen (**50 : 50** beim Tab-Start).

**Rolle:** Gezielte **Aktionen** am NAS (Wartung, Dienste, Konfig), nicht nur Diagnose. Schreibende Schaltflächen brauchen **„Volle Rechte“** im Header und **sudo** für den SSH-User (wie Neustart/Herunterfahren im Health-Tab).

**Wichtige Blöcke (Stichworte):** Energie & WoL (`/etc/power.conf`), **HDD-Ruhezustand**, **UGOS Power-Scheduler** (Wochenplan OffSched/OnSched), **geplanter täglicher Shutdown** (Cron), USB (UGOS-Auswurf), SMART, RAID/TRIM/Scrub, SSH-Drop-in mit Rollback, UGOS-`*_serv`-Dienste (Combobox + **Status anzeigen**, **`.slog`-Tail**, `miniscreen_serv`/`player_serv`), **Netzwerk (UGOS, Lesen)**, **Support-Snapshot**, NGINX, earlyOOM, Samba, LED & Summer.

**„Cron lesen“ beim geplanten Shutdown:** Die App verwaltet die Datei **`/etc/cron.d/nas_admin_timed_shutdown`** nur dann, wenn du hier **„Cron schreiben“** genutzt hast. **UGOS** kann das tägliche Herunterfahren (z. B. 23:00) in **anderen** Cron-Dateien, der **root-crontab** oder **`/etc/crontab`** eintragen — **„Cron lesen“** sucht deshalb dort mit und zeigt alle passenden Zeilen im Protokoll. Wird eine **tägliche** Shutdown-Zeile gefunden, übernimmt die App **Stunde/Minute** in die Felder.

Details, Tabellen und sichere Abläufe: **`HANDBUCH.md` → `## 15. Tab NAS-Verwaltung komplett`** (vollständig).

---

## 13. Tab Speicher & Freigaben komplett

Buttons:

- `Volumes (df)`
- `Shares`
- **`Pools (UGOS API)`** — Pools/Volumes/Disks per Web-API (wie UGOS-GUI)
- `Alles aktualisieren`

Top-Verbrauch:

- Pfadfeld
- `Top20`

Disk-Image-Bereich:

- Device-Auswahl
- `Disk scannen`
- `Image nach PC`
- `Image nach NAS`
- `Restore von PC`
- `Restore von NAS`

Immer Device und Zielpfad doppelt pruefen.

---

## 14. Tab ACL komplett

Felder:

- Zielpfad
- Custom chmod
- owner:group

Buttons:

- `Anzeigen`
- `UGACL-Info`
- `chmod 755`
- `chmod 777 rekursiv`
- `chmod anwenden`
- `chown anwenden`
- `Benutzerliste`
- `Gruppenliste`

Empfehlung: erst `Anzeigen`, dann punktuell aendern, dann erneut pruefen.

---

## 15. Tab Snapshots komplett

Buttons:

- `Backend erkennen`
- `BTRFS list/create/delete`
- `ZFS list/create/delete`
- `Snapper list/create/delete`

Feld:

- Basispfad

Vor Loeschen immer Snapshot-ID und Wiederherstellungsplan pruefen.

---

## 16. Tab Backup komplett

### 16.1 Backup-Teil

Felder:

- Scope
- Volume
- User
- Zielmodus (`nas`, `pc`, `usb`)
- Zielprofil zweites NAS
- PC-Zielpfad
- USB-Ziel
- Option `NAS-Datei nach PC-Transfer entfernen`

Buttons:

- `Docker + Scripts Backup`
- `User Data Backup`
- `All Data Backup`
- `Listen aktualisieren`

### 16.2 Restore-Teil

Felder:

- Quellmodus (`nas`, `pc`)
- Archivpfad
- Zielpfad NAS

Buttons:

- `Datei waehlen`
- `Wiederherstellen starten`

### 16.3 Scheduled Backup

Felder:

- Label
- Jobtyp
- Cron-Felder
- Zusatzoptionen

Buttons:

- `Von NAS laden`
- `Auf NAS speichern`
- `Ausgewaehlten Job entfernen`
- `Job erstellen/aktualisieren`

### 16.4 Sicherer Restore-Workflow

1. Archivquelle verifizieren.
2. Zielpfad pruefen.
3. Optional Vorzustand sichern.
4. Restore starten.
5. Ergebnis pruefen (Dateien, Rechte, Dienste).

---

## 17. Info Dialog komplett

Buttons:

- `README`
- `Handbuch`
- `CHANGELOG`
- `YouTube`

Weitere Elemente:

- Support-Link
- Kontakt-E-Mail
- About-Text

---

## 18. Komplette Betriebsablaeufe

### 18.1 Erstinbetriebnahme

Settings -> Dashboard -> Health -> Scripts -> Docker -> Backup -> Watcher/Daily.

### 18.2 Geplante Wartung

1. Health Snapshot.
2. selektive Aenderung (z. B. Docker Update).
3. Verifikation.
4. Backup/Snapshot nach erfolgreichem Zustand.

### 18.3 Stoerungsfall

1. Dashboard Lagebild.
2. Health Kernchecks.
3. betroffenen Tab vertiefen.
4. eine Korrektur pro Schritt.
5. Ergebnis validieren.

---

## 19. Troubleshooting nach Bereich

- **SSH down**: Host/Port/Auth pruefen, dann Health neu laden.
- **Telegram down**: Token/Chat-ID und outbound Netzwerk pruefen.
- **Docker leer**: Dienststatus und Rechte pruefen.
- **NAS↔NAS ohne Profile**: Settings Profil speichern und neu laden.
- **Restore fehlschlaegt**: Archivpfad, Zielpfad, Rechte und Speicherplatz pruefen.
- **Fan wirkt blockiert**: `UGOS-Steuerung zurueckgeben` ausfuehren.

---

## 20. Wartungsplan

Taeglich:

- Dashboard Schnellblick
- Alerts pruefen

Woechentlich:

- Health Vollrefresh
- Docker/Storage Auffaelligkeiten behandeln

Monatlich:

- Restore-Test im kleinen Scope
- Cronjobs pruefen
- Notification-Test senden

---

## 21. Schluss

Dieses Handbuch ist absichtlich als zusammenhaengende, tab-zentrierte Betriebsanleitung geschrieben. Jeder Bereich enthaelt direkt die zugehoerigen Felder, Buttons und Workflows, damit du nicht zwischen weit entfernten Kapiteln springen musst.
