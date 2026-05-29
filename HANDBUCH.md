# Ugreen NAS Admin – Komplettes Handbuch zur App und Benutzung

> **Tab „Login Track“:** Eigenes Kapitel **`## 14. Tab Login Track komplett`**. **Tab „NAS-Verwaltung“:** **`## 15. Tab NAS-Verwaltung komplett`** (blaue Hauptüberschriften in der PDF wie bei den anderen Tabs). Kurzfassungen teils in `HANDBUCH_STRUKTURIERT.md`. **ℹ Info → Handbuch** öffnet **`HANDBUCH.pdf`** — neu bauen mit `python tools/build_handbuch_pdf.py`, sonst fehlen neue Kapitel.

Diese Ausgabe ist tab-zentriert aufgebaut: Pro Bereich stehen Beschreibung, Buttons, Bedienung, Workflows und Fehlerfälle direkt zusammen – ohne verstreute Nachträge am Ende.

## 1. Zweck dieses Handbuchs

### Aus dem Bereich: 1. Zweck dieses Handbuchs

Dieses Handbuch ist als vollständige Bedienanleitung für die **aktuelle App-Version** geschrieben. Es erklärt die Bedienung **tab für tab**, inklusive Eingabefelder, Schaltflächen, typische Abläufe, Fehlerbilder und sinnvolle Vorgehensweisen im Alltag.  
Es ist **keine Kurzbeschreibung** und kein Marketingtext, sondern eine Arbeitsanleitung für den echten Betrieb.

Wichtig: Die App arbeitet in vielen Bereichen direkt auf deinem NAS. Änderungen sind nicht „simuliert“, sondern wirken direkt auf Dateien, Dienste, Container und Zeitpläne. Deshalb wird in diesem Handbuch immer beschrieben, **was ein Button konkret auslöst** und **wann du ihn besser nicht benutzen solltest**.

---

---

## 2. App-Logik und Sicherheitsprinzip

### Aus dem Bereich: 2. App-Logik und Sicherheitsprinzip

Die App ist modular aufgebaut: Dashboard, Skripte, Explorer, NAS↔NAS, Geräte, Docker, Health, **NAS-Verwaltung**, Storage, ACL, Snapshots, Backup, Settings.  
Fast alle Funktionen greifen über SSH auf das NAS zu. Ohne gültige Verbindung sind viele Aktionen nicht sinnvoll.

Ein zentraler Punkt ist der Schutzmodus:

- Im eingeschränkten Modus sind riskante Aktionen blockiert.
- Mit `Volle Rechte` werden kritische Schaltflächen freigegeben.
- Mit `Einschränken` setzt du den Schutz wieder aktiv.

Für produktive Umgebungen gilt als Standard:

1. Im Normalmodus analysieren.
2. Nur für konkrete Eingriffe Vollrechte aktivieren.
3. Nach dem Eingriff wieder einschränken.

---

---

## 3. Header komplett (alles an einem Ort)

### Aus dem Bereich: 3. Kopfbereich (Header) – aktuelle Version

Wichtig zur Einordnung: In der aktuellen UI liegen die umfangreichen Verbindungsfelder im `Settings`-Tab. Der Header enthält **nicht** mehr den alten großen Verbindungsblock.

### 3.1 Header-Elemente und Wirkung

- `⚠ Volle Rechte` / `🔒 Einschränken`  
  Schaltet den Risikomodus um. Kritische Buttons in mehreren Tabs hängen davon ab.

- Theme-Button (`☀ Light` / `🌙 Dark`)  
  Wechselt das Farbschema der Oberfläche.

- `ℹ Info`  
  Öffnet den Info-Dialog mit Dokumentenbuttons (`README`, `Handbuch`, `CHANGELOG`) und Kontaktbereich.

- `📸 Screenshot`  
  Erstellt einen Screenshot der App. Zielordner kommt aus `Settings -> Pfade -> Screenshot-Pfad`.

- `☕ Coffee`  
  Öffnet den Support-Link.

- SSH-Status-Badge  
  Zeigt, ob die SSH-Verbindung aktiv ist.

- Modellanzeige  
  Zeigt das erkannte NAS-Modell, sobald per SSH auslesbar.

- **UGOS/OS-Zeile** (direkt unter der Modellanzeige)  
  Zeigt nach erfolgreicher Auslese u. a. **`OS_VERSION`** und **`PRETTY_NAME`** aus **`/etc/os-release`** auf dem NAS; bei **`OS_IS_BETA=true`** erscheint ein **Beta**-Hinweis. **Befüllung:** (1) nach **„Alles aktualisieren“** in der Sidebar — dabei wird `os-release` in demselben gebündelten SSH-Lauf mitgelesen; (2) alternativ beim **ersten Start der Dashboard-Live-Daten** (Tab **Dashboard** aktiv, Live-Schleife startet), falls die Zeile noch leer ist. Ohne Verbindung bleibt ein erklärender Platzhaltertext.

### 3.2 Was du im Header nicht tun solltest

- Keine kritischen Aktionen starten, wenn SSH-Badge nicht verbunden ist.
- Nicht dauerhaft in Vollrechten arbeiten.

---

### Aus dem Bereich: 22. Vollständige Referenz: Header-Buttons (aktuelle UI)

### 22.1 `Volle Rechte` / `Einschränken`

**Zweck:** Sicherheitsfreigabe für kritische Aktionen.  
**Voraussetzung:** bewusste Bestätigung.  
**Wirkung:** Schaltet viele `danger`-markierte Buttons frei oder wieder zu.  
**Typischer Fehler:** Dauerhaft freigelassen und später versehentliche Lösch-/Systemaktion.

### 22.2 Theme-Button

**Zweck:** Wechsel Light/Dark Theme.  
**Wirkung:** rein visuell, keine NAS-Änderung.  
**Typischer Fehler:** keiner, nur Darstellungspräferenz.

### 22.3 `Info`

**Zweck:** Doku- und Kontaktdialog öffnen.  
**Wirkung:** Keine NAS-Aktion, nur UI-Dialog.

### 22.4 `Screenshot`

**Zweck:** aktuellen App-Bildschirm speichern.  
**Voraussetzung:** Screenshot-Zielpfad in Settings sinnvoll gesetzt.  
**Wirkung:** PNG-Datei im Zielordner.  
**Typischer Fehler:** leerer/ungültiger Zielpfad.

### 22.5 `Coffee`

**Zweck:** Support-Link öffnen.  
**Wirkung:** Browseraufruf.

---

### Aus dem Bereich: 64. Detailkatalog Header: jeder sichtbare Knopf im Kontext

### 64.1 Coffee

Leichtgewichtiger Aktionsknopf im Header.  
Je nach App-Logik meist als Schnellausloeser oder Utility-Funktion eingebunden.

### 64.2 Screenshot

Erzeugt sofort eine Aufnahme der App-Oberflaeche.  
Speicherort folgt dem in Settings gesetzten `screenshot_dir`.

### 64.3 Info

Oeffnet den Info-Dialog mit:

- Dokumentlinks (README/Handbuch/Changelog),
- Projekt-/Support-Links,
- Versions-/Hinweistext.

### 64.4 Theme / Sprache

Aendern Darstellung und Texthintergrund.  
Nach Sprachewechsel Dashboard-Sonderregel beachten (deutsch nur bei `de`, sonst englisch).

### 64.5 Modellanzeige

Wird beim verbundenen SSH-Status aktualisiert und zeigt das erkannte NAS-Modell an.

### 64.6 UGOS/OS-Zeile (unter dem Modell)

Ergänzt die Einordnung des Systems: **UGOS-Build** (`OS_VERSION`) und **Basis-OS** (`PRETTY_NAME` / `VERSION_ID` in einem String), optional **Beta**-Kennzeichnung. Die Daten stammen von **`/etc/os-release`** auf dem NAS. **Aktualisierung:** mit **„Alles aktualisieren“** (Sidebar) oder beim **ersten** Verbinden der **Dashboard-Live-Schleife**, wenn noch kein Wert gesetzt wurde.

---

---

## 4. Sidebar und Navigation komplett

### Aus dem Bereich: 4. Sidebar und Navigation

Links befindet sich die feste Navigation mit allen Haupttabs.

### 4.1 Navigationspunkte

- Dashboard
- Scripts
- Explorer
- NAS ↔ NAS
- Geräte
- Docker
- System Health
- Login Track
- NAS-Verwaltung
- Speicher
- Benutzer
- Snapshots
- Backup
- Settings

### 4.2 Tool-Buttons unten in der Sidebar

- `Alles aktualisieren`  
  Startet einen **Gesamt-Refresh** mehrerer Bereiche (Skriptliste, NAS-Scan, Docker-Liste, Health-Übersicht, Speicher-Tab usw.) über **SSH**. Technisch läuft das seit Version **23.8.1** in der Regel als **ein gebündelter sudo-Befehl** mit festen Markern in der Antwort (weniger Roundtrips, schneller als viele Einzelaufrufe). Schlägt das Bundling fehl, nutzt die App automatisch die **frühere Folge einzelner Befehle** (Fallback). Im selben Zyklus werden u. a. **`/etc/os-release`** (für die **UGOS/OS-Zeile** im Header) und die Liste der auf dem NAS aktiven **`*_serv.service`-Units** (für die **Service-Combobox** im Tab **NAS-Verwaltung**) eingelesen.

- `Health Snapshot`  
  Speichert den aktuellen Health-Zustand als Bericht.

---

### Aus dem Bereich: 41. Vollständige Navigationserklärung

Die Sidebar ist nicht nur „Tabwechsel“, sondern ein Arbeitsfluss:

1. `Settings` für Grundlagen.
2. `Dashboard` für schnellen Ist-Blick.
3. `Health` für Diagnose.
4. `Docker` / `Scripts` / `Backup` für operative Änderungen.
5. `Storage` / `ACL` / `Snapshots` für tiefe Datei- und Rechtearbeit.
6. `NAS↔NAS` für Transfers.

Unten:

- `Alles aktualisieren`: synchronisiert mehrere Bereiche (**gebündelter SSH-Lauf** seit v23.8.1, mit Fallback; aktualisiert u. a. **Header UGOS/OS** und **NAS-Verwaltung → Service-Liste**).
- `Health Snapshot`: dokumentiert Zustand.

Beide sind vor/nach Änderungen sehr wertvoll.

---

---

## 5. Tab Settings komplett (Felder, Knöpfe, Einrichtung, Telegram, SMTP)

### Aus dem Bereich: 23. Vollständige Referenz: Settings-Tab (Felder und Buttons)

### 23.1 Hauptbuttons oben

- **Laden:** setzt Formular auf gespeicherten Stand zurück.
- **Auf aktuelle UI anwenden:** übernimmt Formulardaten direkt in laufende App.
- **Speichern:** persistiert alle Settings.

### 23.2 Sprachbereich

- **Dropdown Sprache:** Auswahl der UI-Sprache.
- **Sprache anwenden:** setzt ausgewählte Sprache aktiv.

### 23.3 Verbindungsfelder

- `NAS IP`, `Port`, `User`, `Passwort`
- `SSH-Key nutzen`
- `SSH-Key-Pfad`
- `Passphrase`
- **UGOS API:** Port, HTTPS, SSL prüfen (Dashboard-Button „UGOS API“)
- **SSH-Befehl:** **Standard (s)** und **Lang (s)** — siehe **§79**

### 23.3.1 SSH-Befehl-Timeouts (Kurzüberblick)

Unter **Settings → Verbindung**, Zeile **SSH-Befehl:**

| Feld | Standard | Bedeutung |
|------|----------|-----------|
| **Standard (s)** | 120 | Kurze Befehle (`ls`, `df`, Listen aktualisieren) — bei Überschreitung Abbruch mit Meldung |
| **Lang (s)** | 0 | rsync, `du` Top-20, Backup — **0 = unbegrenzt** (empfohlen für große Migrationen) |

Nach Änderung **Speichern** klicken. Ausführliche Anleitung: **§79**.

### 23.4 Verbindungsbuttons (inkl. neuer SSH-Funktionen)

- **Verbindung speichern:** speichert alle Felder im Verbindungsbereich dauerhaft in der Konfiguration.
- **PW Tresor:** speichert das aktuelle SSH-Passwort im System-Keyring (sicherer als Klartext im Formular).
- **SSH-Key-Paar erstellen:** erstellt auf deinem PC ein neues Schluesselpaar (`ugreen_nas_admin` + `ugreen_nas_admin.pub`), kopiert den Public Key in die Zwischenablage und kann den privaten Key-Pfad direkt ins Formular uebernehmen.
- **Oeffentlichen Key auf NAS installieren:** verbindet sich einmalig per Passwort-SSH mit dem gewaehlten Ziel und traegt den Public Key in `~/.ssh/authorized_keys` ein.
- **Profil +/x:** Profil anlegen/loeschen.

### 23.4.1 Warum der SSH-Key-Workflow wichtig ist

- Mit Key-Login brauchst du im Alltag kein SSH-Passwort mehr bei jeder Aktion.
- Derselbe private Key auf deinem PC kann fuer UGREEN, QNAP und weitere Linux-Systeme genutzt werden.
- Automationen (z. B. Skript-Tests, Transfers, NAS↔NAS-Tools) werden stabiler und schneller.
- Das Passwort wird nur noch fuer die initiale Key-Installation benoetigt.

### 23.4.2 Exakte Schrittfolge (UGREEN + zweites NAS/QNAP)

1. In `Settings -> Verbindung` zuerst Host/IP, Port, User und Passwort korrekt eintragen.
2. `SSH-Key-Paar erstellen` klicken und Zielordner waehlen.
3. Optional Passphrase vergeben:
   - mit Passphrase: RSA 4096 (maximale Kompatibilitaet),
   - ohne Passphrase: bevorzugt Ed25519 (modern/schnell).
4. Bei Rueckfrage den privaten Key-Pfad ins Formular uebernehmen und `SSH-Key` aktivieren.
5. `Verbindung speichern` klicken, damit Key-Pfad und Optionen persistiert sind.
6. `Oeffentlichen Key auf NAS installieren` klicken und Ziel waehlen:
   - **UGREEN:** nutzt die oberen Verbindungsfelder (IP/Port/User/Passwort),
   - **Zweites NAS/QNAP:** nutzt das zweite NAS-Profil unten; SSH-Port wird abgefragt.
7. Nach erfolgreicher Installation nutzt die App fuer spaetere SSH-Logins den privaten Key.

### 23.4.3 Was technisch passiert

- Die App installiert **nur den Public Key** auf dem Zielsystem.
- Der private Key bleibt auf deinem PC und wird nie auf die NAS kopiert.
- Bei der Installation wird absichtlich eine einmalige Passwort-SSH-Session ohne Key verwendet.
- Auf dem Ziel wird genau eine Key-Zeile in `~/.ssh/authorized_keys` hinzugefuegt (oder als bereits vorhanden erkannt).

### 23.4.4 Was man vermeiden sollte

- Nicht den privaten Key weitergeben oder auf NAS/Cloud-Laufwerke kopieren.
- Nach Key-Umstellung kein altes/falsches Passwort im Formular belassen.
- Bei QNAP unbedingt den tatsaechlichen SSH-Port angeben (nicht immer 22).
- Bei Problemen zuerst pruefen: SSH-Dienst aktiv, User korrekt, Home-Verzeichnis beschreibbar.

### 23.4.5 UGOS: SSH-Key dauerhaft (nach Reboot)

Auf **UGOS** kann ein per App installierter Public Key nach **Neustart** oder Aenderungen in der **UGOS-Weboberfläche** wieder abgelehnt werden (Berechtigungen unter `~/.ssh`).

**Symptom:** Key-Login funktionierte, danach wieder nur Passwort.

**Loesung (Community, MIT):** In [UGOS_scripts — ssh_public_key](https://github.com/ln-12/UGOS_scripts/tree/main/ssh_public_key) ist ein **systemd-Dienst** (`ssh-permission-monitor`) beschrieben, der die SSH-Ordnerrechte stabil haelt. Die App zeigt nach erfolgreicher Key-Installation auf dem UGREEN-Ziel einen Hinweis mit diesem Link.

**Hinweis:** Skripte dort sind Community-Inhalte — vor Anwendung Backup der Systemkonfiguration; Nutzung auf eigenes Risiko.

### 23.5 SMB-Zweitprofil

Felder:

- Profilname
- Host
- User
- Passwort
- Passwort speichern (Checkbox)

Buttons:

- Profil hinzufügen
- Profil löschen

### 23.6 Telegram

- Felder Token + Chat-ID
- Button für Secret-Privacy (sichtbar/verdeckt)

### 23.7 E-Mail

- Felder Host, Port, User, Passwort, From, To
- Checkboxen STARTTLS und SSL
- Secret-Privacy-Button

### 23.8 Pfade

- Scripts-Pfad
- Compose-Pfad
- Explorer-Root
- Screenshot-Zielpfad
- `Ordner wählen` für Screenshot-Pfad

### 23.9 Script-Notify

Felder:

- Skript
- Kanal
- Triggerzeitpunkt

Buttons:

- Refresh
- Add
- Delete
- Sync

### 23.10 SSH-Key erstellen und installieren (komplette Anleitung)

Dieser Abschnitt erklaert die beiden neuen SSH-Buttons unter `Settings -> Verbindung` so, dass du den Ablauf ohne externe Tools komplett in der App durchfuehren kannst.

**Knopf: `SSH-Key-Paar erstellen`**
- Erstellt auf deinem PC ein neues SSH-Key-Paar (`ugreen_nas_admin` und `ugreen_nas_admin.pub`).
- Fragt optional nach Passphrase:
  - mit Passphrase: RSA 4096 (sehr kompatibel),
  - ohne Passphrase: Ed25519 (modern, schnell).
- Kopiert den Public Key in die Zwischenablage.
- Kann den privaten Key-Pfad sofort in die Verbindungsfelder uebernehmen und `SSH-Key nutzen` aktivieren.

**Knopf: `Oeffentlichen Key auf NAS installieren`**
- Macht eine einmalige SSH-Anmeldung mit Passwort (bewusst ohne Key-Login fuer diesen Schritt).
- Traegt den Public Key auf dem Ziel in `~/.ssh/authorized_keys` ein.
- Bietet Zielauswahl:
  - `UGREEN` ueber die oberen Felder (IP/Port/User/Passwort),
  - `Zweites NAS / QNAP` ueber das SMB-Profil unten (mit separater SSH-Port-Abfrage).

**Warum das wichtig ist**
- Danach meldet sich die App per Key an, nicht mehr mit Passwort bei jedem Lauf.
- Dasselbe Key-Paar kann fuer mehrere Systeme genutzt werden (UGREEN, QNAP, weitere Linux-Hosts).
- Automationen wie Script-Tests, Transfers und NAS↔NAS laufen stabiler.

**Empfohlenes Verfahren (exakt)**
1. Unter `Settings -> Verbindung` Host/IP, Port, User und Passwort korrekt eintragen.
2. `SSH-Key-Paar erstellen` klicken und Zielordner waehlen.
3. Optional Passphrase setzen und Key-Erstellung bestaetigen.
4. Bei Rueckfrage den privaten Key-Pfad in die UI uebernehmen.
5. `Verbindung speichern` klicken.
6. `Oeffentlichen Key auf NAS installieren` klicken und Zielsystem waehlen.
7. Erfolgsdialog pruefen; danach werden spaetere SSH-Aktionen ueber den privaten Key ausgefuehrt.

**UGOS (Dauerhaftigkeit):** Siehe Abschnitt **23.4.5** — bei abgelehntem Key nach Reboot ggf. `ssh-permission-monitor` aus [UGOS_scripts](https://github.com/ln-12/UGOS_scripts) einrichten.

**Wichtige Regeln**
- Niemals den privaten Key weitergeben oder auf NAS hochladen.
- Nur der Public Key gehoert auf die Zielsysteme.
- Bei QNAP unbedingt den echten SSH-Port angeben (nicht blind 22 annehmen).

---

### Aus dem Bereich: 39. Telegram komplett einrichten (von Null)

Dieser Abschnitt erklärt die Telegram-Einrichtung vollständig, damit Watcher, Tests und Daily Report sauber funktionieren.

### 39.1 Voraussetzungen

Du brauchst:

- ein Telegram-Konto auf dem Handy oder Desktop,
- Internetzugang vom NAS (für ausgehende Verbindungen zur Telegram API),
- Zugriff auf den Settings-Tab in der App.

### 39.2 Bot mit BotFather erstellen

1. Öffne Telegram und suche nach `@BotFather`.
2. Starte den Chat und sende `/start`.
3. Sende `/newbot`.
4. Vergib einen Anzeigenamen für deinen Bot (frei wählbar).
5. Vergib einen eindeutigen Username, der auf `bot` endet (z. B. `mein_nas_alarm_bot`).
6. BotFather antwortet mit einem Token im Format `123456789:AA...`.

Dieser Token ist dein API-Schlüssel. Ohne Token kein Versand.

### 39.3 Chat-ID bestimmen (einfacher Weg)

Variante A (Einzelchat):

1. Öffne den Chat mit deinem neuen Bot.
2. Sende ihm einmal eine Nachricht (z. B. `test`), damit der Chat existiert.
3. Öffne im Browser:
   `https://api.telegram.org/bot<TOKEN>/getUpdates`
4. Suche in der JSON-Antwort nach `"chat":{"id":...}`.
5. Diese Zahl ist die Chat-ID.

Variante B (Gruppe):

1. Erstelle oder nutze eine Gruppe.
2. Füge den Bot zur Gruppe hinzu.
3. Sende in die Gruppe eine Nachricht.
4. Erneut `getUpdates` aufrufen.
5. Gruppen-ID ist meist negativ (z. B. `-100...`).

### 39.4 Token und Chat-ID in die App eintragen

Settings -> Telegram:

- `Bot Token`: Token von BotFather
- `Chat ID`: aus `getUpdates`

Danach `Speichern`.

### 39.5 Telegram in Health testen

Health-Tab -> Telegram-Bereich:

- `Telegram-Test` drücken.
- Im Zielchat prüfen, ob Testnachricht ankommt.

Wenn keine Nachricht kommt:

1. Token prüfen (Tippfehler? altes Token?).
2. Chat-ID prüfen (richtiger Chat? Gruppe statt Einzelchat?).
3. NAS-Internetzugang prüfen (DNS/Firewall).
4. In Logs auf HTTP-Fehlertext achten.

### 39.6 Typische Telegram-Fehler

- **`chat not found`**  
  Bot hat noch keine Nachricht vom Chat erhalten oder falsche Chat-ID.

- **`Unauthorized`**  
  Token falsch oder widerrufen.

- **Nachricht kommt nur manchmal**  
  Cooldown/Schwellenwerte im Watcher prüfen.

- **Gruppenchat funktioniert nicht**  
  Bot nicht in Gruppe oder fehlende Chat-ID der Gruppe.

---

### Aus dem Bereich: 40. E-Mail/SMTP komplett einrichten (von Null)

### 40.1 Minimalwerte

Settings -> E-Mail:

- SMTP Host
- Port
- User
- Passwort
- From
- To
- STARTTLS oder SSL passend zum Provider

### 40.2 Typische Provider-Logik

- Port 587: meist STARTTLS
- Port 465: meist SSL/SMTPS

Nicht beide blind aktivieren. Immer zum Provider passend einstellen.

### 40.3 Testen

- Watcher-Test auf NAS ausführen (falls Kanal `email` oder `both`).
- Daily-Report-Test senden.

Wenn Versand fehlschlägt:

1. DNS-Auflösung am NAS prüfen.
2. SMTP-Credentials prüfen.
3. Port/TLS/SSL-Kombination prüfen.
4. Absenderadresse bei Provider erlaubt?

---

### Aus dem Bereich: 65. Detailkatalog Settings: jedes Feld erklaert

### 65.1 Verbindungsblock

- Host/IP: Zieladresse der NAS
- Port: SSH-Port
- User: SSH-Benutzer
- Passwort/Key: Authentisierung
- Sudo: noetig fuer privilegierte Aktionen

### 65.2 Notification block

- Telegram Token
- Telegram Chat ID
- SMTP Host/Port/User/Pass
- Sender/Empfaenger
- TLS/SSL Auswahl

### 65.3 Pfad-/Tooling-Block

- Screenshot-Verzeichnis
- lokale Arbeitsverzeichnisse
- optionale Toolpfade

### 65.4 Zweites NAS Profil

- Host
- User
- Passwort
- Share/Path-Angaben

Nutzen: Backupziel und NAS↔NAS.

---

---

## 6. Tab Dashboard komplett (Anzeige, Lüfter, Bedienung)

### Aus dem Bereich: 24. Vollständige Referenz: Dashboard-Tab

### 24.1 Elemente

- Dashboard-Titel
- Live-Hinweis (beim Start der Live-Schleife wird — falls die **UGOS/OS-Zeile** im Header noch leer ist — **`/etc/os-release`** einmalig mitgelesen)
- Webcam-Button
- Metrik-Kacheln (inkl. Netzwerk mit **aktueller Schnittstellen-Konfiguration**, Filter, Bearbeiten — siehe **42.3**)
- **Lüfter:** Hinweiszeile **„Lüfter prüfen & zuordnen …“** (öffnet den Erkennungs-/Zuordnungsdialog) sowie zwei Steuer-Kacheln
- Docker-Live
- geplante Skriptjobs

### 24.2 Fan-Steuerung und Zuordnung

**Buttons je Kachel (System links, CPU rechts):**

- **Silent / Standard / Max / Manuell (%)**
- **Übernehmen** (inkl. optionalem Boot-Profil wie bisher, siehe ausführlich **42.6**)
- **UGOS-Steuerung zurückgeben** (nur auf der linken Kachel; betrifft die gemeinsame UGOS-Rückgabe)

**„Lüfter prüfen & zuordnen …“**

- Vorbedingung: **SSH** (wie beim restlichen Dashboard), Schreibbefehle wie bisher über **sudo** mit dem eingetragenen Passwort / den üblichen Rechten.
- Die App liest per Scan u. a. **`/proc/it86/fan`** und **`/sys/class/hwmon/.../fan*_input`** und zeigt ein **Klartextprotokoll**.
- Pro Kachel wählst du:
  - **PWM-Kanal:** **Kanal 1** (UGOS-typisch `set` / `cpu`) oder **Kanal 2** (`set2` / `cpu2` / `fan2`) — welcher physische Zweig auf *deinem* NAS wirklich PWM-fähig ist, hängt vom Modell/Treiber ab.
  - **RPM-Anzeige:** **„Automatisch …“** (Heuristik System- vs. CPU-Kachel wie bisher) oder eine **konkrete Sensoren-Zeile** aus dem Scan (falls mehrere Zeilen vorhanden).
- **Speichern** schreibt lokal **`app_settings.json`** unter **`dashboard`:** **`fan_slot0_use_pwm_secondary`**, **`fan_slot1_use_pwm_secondary`** (Kanal 2 ja/nein je Kachel), **`fan_slot0_rpm_key`**, **`fan_slot1_rpm_key`** (RPM-Zeilenwahl, klein geschrieben; leer = automatisch).
- Das vorhandene **Boot-Skript** auf dem NAS nutzt dieselbe Zuordnung über **`SLOT0_USE2`** / **`SLOT1_USE2`** in **`ugreen_fan_boot.env`**.

**Nur ein eingebauter Lüfter (z. B. nur „System“):**  
Zeigt das NAS nur **eine** RPM-Quelle, bleibt die **rechte** Kachel für die Drehzahl **ohne zweite Quelle leer („nicht lesbar“)** — keine Spiegelung der gleichen Zahl auf beiden Seiten.

**Wichtiger Ablauf (Steuerung):** Modus wählen → **Übernehmen** → Verhalten beobachten → ggf. **UGOS-Steuerung zurückgeben**.

---

### Aus dem Bereich: 42. Dashboard komplett: Alle sichtbaren Funktionen im Betrieb

### 42.1 CPU/RAM-Karten

Zweck: schnelle Lastdiagnose.

Interpretation:

- Kurzspitzen sind normal.
- dauerhaft hohe Last + hoher RAM-Druck = tiefer prüfen in Docker/Health.

### 42.2 Volume-Karten

Zeigen Belegung und helfen früh bei „Platte voll“-Szenarien.

Wenn Belegung steigt:

1. Storage-Tab öffnen.
2. Top-Verbrauch ermitteln.
3. Backup-/Log-/Containerpfade prüfen.

### 42.3 Netzwerk

**Durchsatz (Sparklines)**  
Unterhalb der Konfiguration: pro physischer Netzwerkschnittstelle die **geschätzten Empfangs-/Sende-Raten** (aus `/proc/net/dev`, zweite und folgende Messung). Nützlich bei Backupfenstern, NAS↔NAS-Transfers und Docker-Downloads.

**Aktuelle Konfiguration (vom NAS)**  
Solange das Dashboard aktiv ist und SSH steht, wertet die App auf dem NAS **`ip -j addr`** und **`ip -j route`** aus und zeigt für die gewählte Schnittstelle u. a.:

- Betriebszustand (operstate), MAC-Adresse (sofern von `ip` geliefert),
- **IPv4** mit **Präfixlänge**,
- ob die Adresse als **DHCP/dynamisch** (`dynamic` in der JSON-Antwort) oder typischerweise **statisch** erscheint,
- ob diese Schnittstelle die **Standard-IPv4-Route** trägt und welches **Gateway** dann gilt.

Die Anzeige ist die **Ist-Konfiguration zum Messzeitpunkt** — nicht zwingend identisch mit dauerhaft in UGOS hinterlegten Profilen (die Oberfläche kann eigene Datenbank/Dateien nutzen).

**Schnittstelle wählen**  
Im Dropdown **„Schnittstelle“** stellst du ein, welche NIC im Textfeld **„Aktuelle Konfiguration“** beschrieben wird. Die Auswahl wird **lokal** in **`app_settings.json`** unter **`dashboard.net_detail_iface`** gespeichert (neben anderen App-Einstellungen).

**Sparklines auf ausgewählte NICs begrenzen**  
Das Feld unter dem Hinweistext **„Sparklines: leer = alle; sonst z. B. eth0,eth1“** filtert nur die **grünen Durchsatz-Sparklines** — nicht die technische Erkennung auf dem NAS. **Leer** = es erscheinen **alle** physischen Interfaces wie bisher. **Kommagetrennte Namen** (optional Semikolon) = nur diese Interfaces in den Sparklines, sofern sie existieren. Mit **„Filter speichern“** wird **`dashboard.net_monitor_filter`** in **`app_settings.json`** geschrieben.

**Werte ändern (Fortgeschrittene)**  
Darunter: **IPv4**, **Präfix** (z. B. `24`), **Gateway**, **Modus**:

- **Statisch (ip):** schreibt **Laufzeit**-Einstellungen per `ip -4 addr` / `ip -4 route` auf dem NAS (über **sudo**). Nach Neustart kann UGOS oder ein Dienst die Adresse wieder überschreiben.
- **DHCP neu:** startet auf dem NAS typischerweise `dhclient` bzw. `dhcpcd` für die gewählte Schnittstelle (falls vorhanden).

**„Vom NAS laden“** füllt IPv4, Präfix und Gateway sowie die Modus-Auswahl aus der **zuletzt empfangenen Live-Messung** für die aktuell gewählte Schnittstelle (nur Anzeige in den Feldern — nichts wird ohne **„Anwenden“** geändert).

**„Anwenden (sudo)“** erfordert im Header **„Volle Rechte“** (Danger-/Freigabe wie bei anderen riskanten Aktionen). Es erscheinen **Bestätigungsdialoge**. **Achtung:** falsche IP oder falsches Gateway können die **SSH-Verbindung zum NAS trennen** — nur in Wartungsfenstern nutzen, ggf. Konsole/IPKVM bereithalten.

**Settings und `app_settings.json`**  
Wenn du in **Settings** auf **Speichern** gehst, werden die Abschnitte **`dashboard`** und **`docker_update`** beim Schreiben der Datei **mitgeführt**, damit u. a. die Dashboard-Netzwerk-Präferenzen (**`net_detail_iface`**, **`net_monitor_filter`**) und die **Lüfter-Zuordnung** (**`fan_slot0_use_pwm_secondary`**, **`fan_slot1_use_pwm_secondary`**, **`fan_slot0_rpm_key`**, **`fan_slot1_rpm_key`**) nicht verloren gehen.

### 42.4 Docker-Kachel

Zeigt laufende Container als Frühindikator.  
Bei Abweichung in Docker-Tab wechseln und Liste/Logs prüfen.

### 42.5 Script-Jobs-Kachel

Zeigt geplante Jobs und laufende Aktivitäten.  
Hilft bei Korrelation „Lastanstieg <-> Cronjobzeitpunkt“.

### 42.6 Fan-Steuerbereich (komplett)

Über beiden Kacheln: **„Lüfter prüfen & zuordnen …“** → Dialog mit **Messprotokoll** und Speicherdialog für **PWM-Kanal** und **RPM-Zeile** je Kachel (Details **24.2**). Ohne zweite Drehzahl-Quelle zeigt die **CPU-Kachel** keinen zweiten RPM-Wert (ein Lüfter am NAS).

Buttons/Modi (je Kachel):

- Silent
- Standard
- Max
- Manual %
- Übernehmen
- UGOS-Steuerung zurückgeben (Steuer-Link in der ersten Kachel; wirkt wie bisher gemeinsam auf die Rückgabe an UGOS)

Empfohlener Ablauf:

1. Bei neuem oder abweichendem Modell: einmal **„Lüfter prüfen & zuordnen …“** durchlaufen und sinnvolle Kanal-/Anzeige-Wahl speichern.
2. Modus wählen.
3. Übernehmen.
4. 1–2 Minuten beobachten.
5. Bei Konflikten **UGOS-Steuerung zurückgeben**.

---

### Aus dem Bereich: 62. Praxisanleitung: Fansteuerung inklusive Rueckgabe an UGOS

1. Dashboard öffnen.
2. Optional: **„Lüfter prüfen & zuordnen …“** — Scan lesen, **PWM-Kanal** und **RPM-Anzeige** pro Kachel setzen, **Speichern**.
3. Fanbereich lesen (System links, CPU rechts; bei nur einem Lüfter rechts oft keine RPM-Zeile).
4. Gewünschten Modus wählen.
5. **Übernehmen** klicken.
6. 1–2 Minuten Beobachtung.
7. Wenn manuelle Steuerung beendet werden soll: **UGOS-Steuerung zurückgeben**.
8. Optional in der UGOS-Oberfläche das Profil wechseln (Standard/Silent), um die Übergabe zu validieren.

Fehlerfall „UGOS reagiert nicht“:

- Rueckgabe-Button nochmal ausfuehren.
- Health/Servicezustand pruefen.
- kurze Wartezeit einplanen, da Regelung nicht immer sofort visuell springt.

---

---

## 7. Tab Scripte komplett (Editor, Test, Bedienablauf)

### Aus dem Bereich: 25. Vollständige Referenz: Scripts-Tab

### 25.1 Linke Aktionsbuttons

- Backup Scripts lokal
- Aktualisieren
- Test Host
- Test Docker
- Neue Datei
- Löschen
- Zeitpläne
- PowerShell/SSH

### 25.2 Editorbuttons

- Template `rsync`
- Template `restic`
- Template `rclone`
- Speichern (root)
- Speichern (user)

### 25.3 Felder

- Dateiname
- Editorinhalt

### 25.4 Log

- Laufzeit-/Fehlerausgabe zu Test und Save.

---

### Aus dem Bereich: 43. Scripts-Tab komplett: Jede Aktion im Detail

### 43.1 `Backup` (Skripte lokal sichern)

Zweck: lokale Kopie der NAS-Skripte.

Nutzen:

- Versionssicherung vor Änderungen.
- schnelle Wiederherstellung.

### 43.2 `Aktualisieren`

Lädt Skriptliste neu vom NAS.

Immer vor Bearbeitung drücken, wenn parallel Änderungen erfolgt sein könnten.

### 43.3 `Testen (Host)`

Führt ausgewähltes Skript direkt auf dem NAS aus.

Nutzen:

- realistische Laufprüfung ohne Cron.
- schnellster Weg für Syntax-/Pfadfehler.

### 43.4 `Testen (Docker)`

Testet Skript im Docker-Testkontext.

Sinnvoll wenn Skript später tatsächlich als Docker-Job laufen soll.

### 43.5 `Neue Datei`

Leert Bearbeitungszustand für neuen Skriptstart.

### 43.6 `Löschen`

Entfernt Skript. Kritisch.

Vorher:

1. Dateiname prüfen.
2. ggf. lokales Backup machen.

### 43.7 `Zeitpläne`

Öffnet Scheduler-Drawer und übernimmt Zielskript.

### 43.8 `PowerShell/SSH`

Manueller Debug-/Adminzugang.

### 43.9 Templates (`rsync`, `restic`, `rclone`)

Schneller Start für typische Backup-Skripte.

Nach Einfügen immer Parameter prüfen:

- Quellpfad
- Zielpfad
- Credentials
- Excludes

### 43.10 Speichern (root/user)

`root`:

- für systemnahe Pfade, wenn Rechte nötig.

`user`:

- für weniger privilegierte Abläufe.

Nie unklar speichern. Vorher Zielpfad und Rechtekontext verstehen.

---

---

## 8. Scheduler komplett (alle Felder, Cron, Praxis)

### Aus dem Bereich: 26. Vollständige Referenz: Scheduler-Drawer

### 26.1 Eingabefelder

- Minute
- Stunde
- Tag
- Monat
- Wochentag
- Erste Woche (Checkbox)

### 26.2 Ausführungsbuttons

- Als Host-Job
- Als Docker-Job

### 26.3 Anzeige

- Klartext-Zeitbeschreibung
- Zielskript-Info

---

### Aus dem Bereich: 44. Scheduler komplett: Felder, Interpretation, Best Practice

Cron-Felder:

- Minute
- Stunde
- Tag
- Monat
- Wochentag

Option:

- erste Woche (für bestimmte Monatslogik)

Buttons:

- Host-Job
- Docker-Job

Best Practice:

1. Zeit zuerst fachlich definieren („täglich 03:30“).
2. Felder setzen.
3. Klartextkontrolle im Drawer.
4. Job schreiben.
5. Cron-Postcheck beachten.

---

### Aus dem Bereich: 63. Praxisanleitung: Cronjob sauber erstellen und pruefen

1. Scripts-Tab, Zielshellskript oeffnen.
2. `Zeitplaene` oeffnen.
3. Cronfelder setzen.
4. Klartext lesen.
5. `Host-Job` oder `Docker-Job` schreiben.
6. Cron-Postcheck auswerten.
7. Jobliste pruefen.
8. Einmal manuell testen.

Wenn Job nicht laeuft:

- Pfadrechte pruefen.
- Interpreter (`#!/bin/bash` oder `python3`) pruefen.
- Umgebungsvariablen explizit setzen.

---

---

## 9. Tab NAS Explorer komplett

### Aus dem Bereich: 27. Vollständige Referenz: Explorer-Tab

### 27.1 Toolbar

- NAS scannen
- Upload
- Perms 755
- NAS löschen
- PC löschen
- PC->NAS
- NAS->PC
- Suche

### 27.2 NAS-Kontextmenü

- In Editor laden
- Perms 755
- Pfad kopieren
- Upload Dateien
- Upload Ordner
- Löschen

### 27.3 PC-Kontextmenü

- Im Explorer öffnen
- Pfad kopieren
- Löschen

### 27.4 Zusätzliche PC-Buttons

- Laufwerke
- Hoch
- Ordner wählen
- Lokal aktualisieren

---

### Aus dem Bereich: 45. Explorer komplett: Sicher arbeiten

### 45.1 `NAS scannen`

Lädt NAS-Dateibaum neu.

### 45.2 `Upload`

Lädt lokale Dateien auf NAS.

Vorher Zielordner links aktiv auswählen.

### 45.3 `Perms 755`

Setzt Rechte auf Zielpfad.

Nur nutzen, wenn klar ist, warum.

### 45.4 `NAS löschen`

Löscht ausgewählte NAS-Objekte.

Kritisch: Fokus und Auswahl doppelt prüfen.

### 45.5 `PC löschen`

Löscht ausgewählte lokale Dateien.

### 45.6 `PC -> NAS` und `NAS -> PC`

Transfer zwischen rechter und linker Seite.

Vor Transfer immer beide Pfade visuell prüfen.

### 45.7 Suche

Sucht im aktuellen NAS-Kontext.

### 45.8 Kontextmenüs

Die Kontextmenüs sind gleichwertige Aktionsauslöser zu Toolbar-Buttons, nicht nur Anzeigen.

---

---

## 10. Tab NAS↔NAS komplett

### Aus dem Bereich: 28. Vollständige Referenz: NAS↔NAS-Tab

### 28.1 Obere Buttons

- Ugreen scannen
- (Windows) SMB scan

### 28.2 Profil-/Statusbereich

- SMB-Profilcombo
- SMB-Statuslabel

### 28.3 Kontextmenüs

- Upload zur Gegenseite
- Löschen auf aktueller Seite

---

### Aus dem Bereich: 46. NAS↔NAS komplett: SMB-Workflow

### 46.1 Voraussetzungen

- Zweites NAS-Profil in Settings vollständig.
- (Windows) SMB-Mechanismus verfügbar.

### 46.2 Ablauf

1. Ugreen scannen.
2. SMB/Freigaben scannen.
3. Zielpfade links/rechts auswählen.
4. Transfer per Kontextmenü auslösen.
5. Ergebnis/Fehler prüfen.

### 46.3 typische Fehler

- Host nicht erreichbar.
- Auth falsch.
- Share verborgen/nicht freigegeben.
- Rechte für Zielpfad fehlen.

---

---

## 11. Tab Netzwerkgeräte komplett

### Aus dem Bereich: 29. Vollständige Referenz: Geräte-Tab

### 29.1 Aktion

- Geräte suchen

### 29.2 Ergebnis

- Tabelle mit Kind/Name/IP/Detail
- Statuslabel (`scanning`, `empty`, Fehlertext)

---

### Aus dem Bereich: 47. Geräte-Tab komplett

`Geräte suchen` startet Discovery über NAS-SSH.  
Anzeige enthält LAN/USB-Informationen.

Fehlerfall:

- ohne SSH keine Daten.
- bei Discovery-Fehler erscheint Statusausgabe.

---

---

## 12. Tab Docker komplett (Knöpfe + Bedienung direkt zusammen)

### Aus dem Bereich: 30. Vollständige Referenz: Docker-Tab

### 30.1 Erstell-/Kataloggruppe

- Docker erstellen
- Docker Katalog
- Neuer Docker
- Docker Update

### 30.2 Verwaltungsgruppe

- Ausschlussliste
- Liste
- Alle Container stoppen
- Start
- Stop
- Restart
- Liste (zweite Position im Layout)

### 30.3 Diagnosegruppe

- Stats
- Inspect
- Löschen
- Fix 777

### 30.4 Log-/Compose-Bereich

- Live Log Start
- Live Log Stop
- Compose config
- Compose ps
- Compose up -d

### 30.5 Felder

- Compose-Dateipfad
- Container-Treeview-Auswahl

---

### Aus dem Bereich: 48. Docker komplett: Betrieb, Update, Diagnose

### 48.1 Erstellen/Katalog

- Docker erstellen
- Docker Katalog
- Neuer Docker

Nutze **Katalog** fuer Image-Recherche; waehle **Compose** fuer Stacks mit UGREEN-Pfaden. Fertige Presets (Auswahl) u. a. fuer:

| Suche / Image | Zweck | Typische Ports |
|---------------|--------|----------------|
| **MeTube** (`alexta69/metube`, `ghcr.io/alexta69/metube`) | Video/Audio-Download (yt-dlp, Web-UI) | 8081 |
| **Scrutiny** | SMART-Festplatten-Ueberwachung | 8080 |
| **Dozzle** | Docker-Container-Logs im Browser | 8080 |
| **Jellyfin / Plex** | Medienstreaming | 8096 / 32400 |
| **Uptime Kuma** | Erreichbarkeits-Monitoring | 3001 |
| **Homepage** | Homelab-Dashboard | 3000 |
| **Portainer** | Docker-GUI | 9000 |
| **Sonarr / Radarr / Prowlarr** | Media-Automation | 8989 / 7878 / 9696 |

Presets legen Volumes unter **`/volume1/docker/<name>/…`** an — im Assistenten Pfade anpassen, dann deployen.

**Fehlt im App Center** (15 Rezepte): Docker-Tab → **Fehlt im App Center** — kuratierte Stacks für Dienste ohne UGOS-App-Center-Eintrag (MeTube, Jellyfin, Immich, Paperless-ngx, Vaultwarden, Nextcloud, AdGuard Home, Sonarr/Radarr/Prowlarr, qBittorrent, Uptime Kuma, Home Assistant, Syncthing, Portainer). Suche nach Name/Tag; Doppelklick oder **Im Assistenten öffnen**. **Ausführliche Schritt-für-Schritt-Anleitung: §77.**

**Homelab-Stapel** (mehrere Dienste, ein Compose): Docker-Tab → **Homelab-Stapel** → z. B. Monitoring (Uptime Kuma + Dozzle + Homepage) oder Media-Download (MeTube + qBittorrent).

**Compose von GitHub:** Docker-Assistent → **Von GitHub…** — URL zu `raw.githubusercontent.com` oder `github.com/…/blob/…/docker-compose.yml`.

**UGOS API (Dashboard):** Button **UGOS API** — liest Live-Daten über die Web-UI-API (wie die UGOS-App), nicht per SSH. Port/HTTPS: Settings → Verbindung (Standard HTTPS-Port **9443**). Für den Login wird **`cryptography`** benötigt (`pip install cryptography`).

**SSH-Timeouts / Exit-Codes:** Settings → Verbindung → **SSH-Befehl** — **§79**. Migration inkl. Vorab-Prüfung: **§78**. Storage Top-20: **§80**.

### 48.2 Update und Massenaktionen

- Docker Update (selektiv)
- Liste
- Ausschlussliste
- Stop all

Selektive Updates sind produktionssicherer als global.

### 48.3 Laufzeitsteuerung

- Start
- Stop
- Restart

Immer mit frischer Liste arbeiten.

### 48.4 Diagnose

- Stats (Ressourcen)
- Inspect (Struktur)
- Logs (historisch/live)

### 48.5 Compose

- Compose-Datei eintragen
- config prüfen
- ps prüfen
- up -d ausführen

Vor `up -d` immer config gegenprüfen.

### 48.6 Kritische Aktion `Löschen`

Vorher klären:

- persistente Daten liegen wo?
- Wiederherstellungspfad vorhanden?
- abhängige Dienste betroffen?

---

### Aus dem Bereich: 60. Praxisanleitung: Docker Service sicher aktualisieren

Ziel: Ein vorhandener Container soll aktualisiert werden, ohne unkontrollierte Seiteneffekte.

1. Docker-Tab oeffnen.
2. `Liste` klicken.
3. Zielcontainer markieren.
4. `Inspect` aufrufen und kritische Angaben notieren (Volumes, Ports, Env).
5. `Logs` oeffnen und Baseline notieren.
6. `Docker Update` ausfuehren.
7. Zustand erneut mit `Liste` und `Inspect` pruefen.
8. Funktionstest aus Anwendungssicht durchfuehren.
9. Bei Fehlern: Container stoppen/starten; wenn noetig auf vorheriges Image zurueck.

Warum diese Reihenfolge wichtig ist:

Ohne Baseline aus Inspect/Logs ist spaeter oft unklar, ob der Fehler aus dem Update stammt oder vorher schon vorhanden war.

---

### Aus dem Bereich: 77. Praxisanleitung: Docker-Rezepte (Fehlt im App Center)

Ziel: Einen Dienst installieren, der im UGOS App Center nicht angeboten wird — mit fertiger Compose-Vorlage und UGREEN-Pfaden unter `/volume1/docker/…`.

**Voraussetzungen**

1. SSH-Verbindung zur NAS in der App steht (grüner Verbindungsstatus).
2. Docker läuft auf der NAS (Docker-Tab → **Liste** zeigt Container oder leere, aber fehlerfreie Liste).
3. Du kennst den gewünschten Dienst (z. B. Jellyfin, Immich, Vaultwarden).

**Schritt 1 — Rezept öffnen**

1. Sidebar → **Docker Manager** (Tab Docker).
2. In der oberen Werkzeugleiste auf **Fehlt im App Center** klicken.
3. Es öffnet sich ein Fenster mit der Liste aller **15 Rezepte** und einem Suchfeld oben.

**Schritt 2 — Rezept auswählen**

1. Optional im Suchfeld tippen (z. B. `jellyfin`, `photo`, `password`, `8081`) — die Liste filtert sofort.
2. Ein Rezept in der Liste anklicken — darunter erscheint eine **Kurzbeschreibung** (Zweck, Port-Hinweis).
3. Rezept bestätigen mit **Im Assistenten öffnen** (oder **Doppelklick** auf den Listeneintrag).
4. Das Rezept-Fenster schließt sich; der **Docker-Assistent** (Erstellen) öffnet sich mit der fertigen **Compose-YAML** im Editor.

**Schritt 3 — Compose prüfen und anpassen**

1. Im Editor die YAML durchlesen — besonders:
   - **ports:** Host-Port → Container-Port (z. B. `"8096:8096"`). Port-Konflikte mit anderen Diensten vermeiden.
   - **volumes:** Pfade beginnen mit `/volume1/docker/<dienst>/…` — bei Bedarf auf `/volume2/…` ändern, wenn Docker dort liegen soll.
   - **environment:** Passwörter, Secret Keys, `PUID`/`PGID`, Zeitzone (`TZ=Europe/Berlin`).
2. Bei **Immich** und **Paperless-ngx:** unbedingt `change_me_db`, `change_me_secret` o. ä. durch sichere Werte ersetzen.
3. Bei **AdGuard Home:** Port **53** nur nutzen, wenn kein anderer DNS-Dienst auf der NAS oder im Router den Port blockiert.
4. Medienpfade anpassen (z. B. Jellyfin `/volume1/media` — Ordner muss existieren oder wird beim Deploy angelegt).

**Schritt 4 — Variablen scannen (empfohlen)**

1. Im Docker-Assistenten auf **Variablen scannen** klicken.
2. Erkannte Platzhalter, Volume-Host-Pfade und Ports im Formular prüfen.
3. Häkchen **Host-Ordner auf NAS anlegen (chmod 777)** setzen, wenn die App leere Docker-Ordner anlegen soll.
4. **Weiter** — die Werte werden in die YAML eingetragen.

**Schritt 5 — Deployen**

1. Compose prüfen (optional **config**-Schritt im Assistenten, falls angeboten).
2. Deployment starten (**up -d** / Start im Assistenten — je nach UI-Stand des Wizards).
3. Warten, bis die Ausgabe im Log ohne Fehler durchläuft.
4. Docker-Tab → **Liste** — Container sollte **running** sein.

**Schritt 6 — Funktionstest**

1. Im Browser `http://<NAS-IP>:<Port>` aufrufen (Port aus Rezept, z. B. Jellyfin **8096**, MeTube **8081**, Vaultwarden **8222**).
2. Ersteinrichtung im Web-UI des Dienstes durchführen (Admin-Konto, Bibliotheken, etc.).
3. Bei Problemen: Docker-Tab → Container markieren → **Logs** und **Inspect**.

**Schritt 7 — Nach dem ersten Start (Best Practice)**

1. Passwörter/Secrets notieren (Passwortmanager — nicht nur in der Compose lassen).
2. Optional Snapshot im Tab **Snapshots** für den Docker-Datenordner.
3. Compose-Datei auf der NAS dokumentieren (z. B. unter `/volume1/docker/<dienst>/docker-compose.yml` ablegen).

**Rezept-Übersicht (Ports)**

| Rezept | Typischer Port | Besonderheit |
|--------|----------------|--------------|
| MeTube | 8081 | Downloads unter `/volume1/docker/metube/downloads` |
| Jellyfin | 8096 | Medienordner `/volume1/media` |
| Immich | 2283 | Mehrere Container + Postgres — DB-Passwort setzen |
| Paperless-ngx | 8000 | Redis + Postgres — Secret Key setzen |
| Vaultwarden | 8222 | Keine Registrierung (`SIGNUPS_ALLOWED=false`) |
| Nextcloud | 443 | linuxserver-Image, HTTPS |
| AdGuard Home | 3000 (+53 DNS) | DNS-Port prüfen |
| Sonarr / Radarr / Prowlarr | 8989 / 7878 / 9696 | *arr-Stack, gemeinsame `/volume1`-Daten |
| qBittorrent | 8080 | Downloads `/volume1/downloads` |
| Uptime Kuma | 3001 | Monitoring-Dashboard |
| Home Assistant | 8123 | Config persistent |
| Syncthing | 8384 | Sync-Ordner `/volume1/sync` |
| Portainer | 9000 / 9443 | Docker-Socket-Zugriff — nur vertrauenswürdiges Netz |

**Typische Fehler**

- **Port belegt:** Anderen Host-Port in der YAML wählen (z. B. `"8097:8096"`).
- **Permission denied:** PUID/PGID an NAS-User anpassen oder Host-Ordner mit **Host-Ordner anlegen** erzeugen.
- **Container startet nicht:** Logs lesen; bei DB-Images (Immich/Paperless) erst Postgres/Redis healthy abwarten.

---

---

## 13. Tab System & Health komplett

### Aus dem Bereich: 31. Vollständige Referenz: Health-Tab

### 31.1 Hauptbuttons

- Refresh Health
- RAID prüfen
- SMART prüfen
- Storage
- Scheduler-Inventar
- Report speichern
- Neustart
- Herunterfahren

### 31.2 UGOS-Panel

- Titel + Refresh
- Service-Statuslabel

Hinweis:

- `UGOS-Services aktualisieren` liest den aktuellen Status zentraler NAS-Dienste neu ein.
- Das Panel hilft, Fehler schneller einzugrenzen (z. B. ob ein Kernservice ausgefallen ist), bevor man in Docker/Skripte tiefer einsteigt.

### 31.3 Telegram-Block

Felder:

- Enabled
- Intervall
- Disk warn/crit
- Temp
- Cooldown
- Fan min

Buttons:

- Telegram-Test
- Manuelle Prüfung

### 31.4 Watcher-Block

Kanal:

- Telegram / Email / Both

Checkboxen:

- Disk
- RAID
- Netzwerk bereit
- Temp
- Docker
- SMART Dienst
- SMB/NFS Dienste
- Wartungstimer
- systemd failed
- Fan
- Login failures

Felder:

- Fan min
- Login window
- Login min
- Require containers
- Ignore patterns
- Auto restart names

Buttons:

- Lokal speichern
- Auf NAS installieren
- Test auf NAS

### 31.5 Daily-Report-Block

- Enabled Checkbox
- Lokal speichern
- Auf NAS installieren
- Test
- **Berichtsinhalt (NAS-Skript):** Der per Cron auf dem NAS laufende Tagesbericht enthält seit **v23.8.1** einen Abschnitt **OS / UGOS** (Auszug aus **`/etc/os-release`**: u. a. `PRETTY_NAME`, `VERSION_ID`, `OS_VERSION`, `OS_IS_BETA`) — nützlich für Support und Versionsvergleich neben den bestehenden Blöcken (Uptime, Load, SMART, Docker, …).

---

## 14. Tab Login Track komplett

### Aus dem Bereich: Login Track — Zugriffe nach Client-IP

Der Tab **Login Track** (Sidebar-Icon **🔐**, zwischen **System & Health** und **NAS-Verwaltung**) zeigt **Anmeldungen, fehlgeschlagene Logins und aktive Verbindungen** zum NAS — **fokussiert auf die Client-IP** (nicht auf interne NAS-Dienste). Die App liest dazu per **SSH** mehrere Log- und Statusquellen auf dem NAS, normalisiert die Zeilen zu **Einträgen** und listet sie in einem **nur lesbaren** Protokoll (Textfeld). **Echtzeit** ist standardmäßig aktiv: Es werden vor allem **neue** Ereignisse seit **Öffnen des Tabs** bzw. seit **Aktivieren von Echtzeit** angezeigt; mit **Aktualisieren** bzw. abgeschalteter Echtzeit-Option lässt sich stattdessen eine **Historie** (ca. **30 Tage** `journalctl`-Fenster plus Log-Tails) laden.

### 14.1 Zweck und typische Nutzung

- **Wer** hat sich **wann** per **SSH**, **SMB**, **UGOS-App** (iPhone/PC), **UGOS-Web** oder **offener TCP-Verbindung** am NAS gemeldet?
- **Live-Überwachung** während du testweise von Handy/PC aus anmeldest (Echtzeit-Modus).
- **Nachverfolgung** älterer Zugriffe nach **Aktualisieren** mit deaktivierter Echtzeit-Option.
- **Sortieren** nach **Datum/Uhrzeit**, **IP**, **Benutzer**, **Quelle** oder **Ergebnis**; **Export** als Textdatei; optional **IP sperren** über UGOS-Blockliste.

**Abgrenzung:** Login Track ersetzt **nicht** den Telegram-/E-Mail-**Wächter** im Tab **System & Health** (Schwellen, RAID, Temperatur). Es ist ein **eigenes Logbuch** für Zugriffe — ähnlich wie du in der NAS-Oberfläche „Anmeldungen“ siehst, aber **zusammengeführt** und **filterbar** in der App.

### 14.2 Voraussetzungen

- **NAS-IP** (und SSH-Zugang) im **Header** bzw. **Settings** — ohne gültige Verbindung erscheint ein Hinweis statt Einträgen.
- **Lesen** der Logs reicht für die Anzeige; **IP sperren** schreibt auf dem NAS in **`/ugreen/.config/block_ip_list`** und nutzt die App-SSH-Sitzung mit **sudo** (wie andere schreibende Aktionen). **NAS-eigene IP** und **Loopback** lassen sich nicht sperren.
- Beim **Verlassen** des Tabs stoppt die **Live-Abfrage** (kein dauerhaftes Polling im Hintergrund).

### 14.3 Aufbau des Tabs

**Oben**

- **Titel** und **Untertitel** (Kurzbeschreibung der Quellen und des Echtzeit-Modus).
- **Aktualisieren** — bei **Echtzeit an**: setzt die Live-Baseline neu und leert die Liste (wartet auf neue Zeilen). Bei **Echtzeit aus**: einmaliger **Historien-Collect** (mehrere Log-Quellen, ca. 30-Tage-Fenster bei `journalctl`).
- **Export …** — speichert den **aktuell sichtbaren** Bericht (inkl. Kopfzeilen, Sortierung, Diagnosezeilen) als **Textdatei** auf dem PC.
- **IP sperren …** — Dialog zur Eingabe einer **IPv4**; schreibt die Adresse in die UGOS-**Sperrliste** (siehe **14.9**).

**Sortierung und Filter**

- **Sortieren:** Dropdown **Datum / Uhrzeit**, **IP-Adresse**, **Benutzer**, **Quelle**, **Ergebnis**.
- Checkbox **Neueste / Z–A zuerst** — bei **Datum/Uhrzeit** bedeutet aktiv: **neueste** Einträge oben; ohne Häkchen: **älteste** oben. Bei **Datum/Uhrzeit** gilt: zuerst **Kalendertag**, innerhalb desselben Tages **Uhrzeit**; Einträge **ohne** erkennbares Datum bleiben **am Ende** der Liste (auch bei absteigender Sortierung).
- **Echtzeit (nur seit Tab-Start)** — Standard **an**. Nur **neue** Zeilen seit Aktivierung; erste SSH-Runde setzt eine **Baseline** (im Kopf als Diagnosezeile erkennbar).
- **App-Session-Pings ausblenden** — Standard **an**. Blendet **wiederholte UGOS-Sitzungs-/VerifyToken-Rauschen** aus, behält aber **echte Logins** (z. B. „logged in successfully“, **verify/login**).

**Liste (Protokoll)**

- **Nur lesen** (Tastatur blockiert Bearbeitung); **Text markieren** und **Rechtsklick** möglich.
- **Spalten:** `Zeit | IP | Quelle | Ergebnis | Benutzer | Detail`
- Zwischen Einträgen: **Trennlinie** zur besseren Lesbarkeit.
- Kopf: Host, Modus (Live vs. Zeitraum), **Eintragszahl**, **Sortierung**, optional **Diagnose** (gelesene Log-Abschnitte, letzte Live-Delta-Zahlen), bei Problemen **SSH-/Hinweisblock**.

### 14.4 Datenquellen auf dem NAS (technisch)

Die App führt **einen gebündelten SSH-Befehl** aus; Antworten sind in Abschnitte mit Markern **`@@SOURCE:…@@`** gegliedert. Auszug (je nach Modus **Historie** vs. **Live**):

| Abschnitt | Inhalt (Kurz) |
|-----------|----------------|
| `ssh_journal` / `auth_log` | **OpenSSH**: Accepted/Failed/Invalid user, Session open/close, Disconnect |
| `log_serv` | UGOS **log_serv.slog**: `insertLog login`, Samba-Audit |
| `ctl_serv` / `entry_serv` | UGOS **ctl_serv** / **entry_serv**: App/Web-Login, VerifyToken, Biometrie, User-Agent |
| `gateway_serv` | **gateway_serv_gin.slog** (Login/Session-relevante Zeilen) |
| `journal_ctl` | Kurzes **journalctl**-Fenster (Live) |
| `nas_conn` | **`ss`**: etablierte TCP-Verbindungen zu typischen Dienst-Ports (22, 80, 443, 445, …) |
| `last` / `lastlog` | Klassische **last**-Ausgabe (Historien-Modus) |

Eigene **Collect-Befehle** der App (grep/journalctl mit `UGR_LOGIN`-Markern) werden beim Parsen **herausgefiltert**, damit die Live-Ansicht nicht mit **sudo/journalctl-Echo** der App selbst geflutet wird.

### 14.5 Quellen-Spalte (Anzeige)

Typische Werte in **Quelle** (aus Log-Zeilen abgeleitet):

- **SSH** — SSH-Anmeldung / Fehlversuch / Trennung
- **UGOS Samba** — SMB-Anmeldung laut UGOS-Log
- **UGOS iPhone** / **UGOS PC App** / **UGOS Web** — UGOS-Client anhand User-Agent / Modul (Biometrie, Electron, Browser)
- **UGOS login** — sonstige UGOS-Login-Zeilen
- **NAS connection** — aktive Verbindung aus **`ss`** (kein klassischer Login-Logeintrag)
- **last** — Zeile aus **`last`**

**Ergebnis:** u. a. `ok`, `failed`, `info`, `session` — je nach Parser und Rohzeile.

### 14.6 Echtzeit vs. Historie

| Einstellung | Verhalten |
|-------------|-----------|
| **Echtzeit an** (Standard) | Beim **Tab-Betreten** startet Polling (ca. alle **4 s**). Erste Runde = **Baseline**; danach nur **Delta**. Checkbox **Echtzeit** erneut aktivieren oder **Aktualisieren** setzt Baseline zurück. |
| **Echtzeit aus** | **Aktualisieren** lädt **Historie**; Liste bleibt bis zum nächsten Refresh bestehen. Beim erneuten Tab-Betreten ohne gespeicherte Events: automatischer Refresh. |

**Live-Filter:** Nur Ereignisse mit **Ergebnis** `ok`/`failed` oder Zeitstempel **nahe** Tab-Start (Toleranz ca. **2 Minuten**) werden als „neu“ gezählt — verhindert, dass alte Journal-Zeilen die Echtzeit-Liste fluten.

### 14.7 Sortierung im Detail

- **Datum / Uhrzeit:** gemeinsame **chronologische** Sortierung über gemischte Formate (`YYYY-MM-DD HH:MM:SS`, ISO mit `T` und Zeitzone, Journal `Mon DD HH:MM:SS` mit **Jahresannahme**). **Sekundär** stabil über den Original-Zeitstring.
- **IP:** numerisch (IPv4), dann Zeit.
- **Benutzer / Quelle / Ergebnis:** alphabetisch, dann Zeit.
- **Neueste / Z–A zuerst:** kehrt die **Hauptsortierung** um; **ohne Zeitstempel** bleiben **unten**.

### 14.8 Export

- **Export …** — Dateidialog; leerer Inhalt → Hinweis „zuerst laden“.
- Exportiert den **sichtbaren** Bericht (nach Filtern/Sortierung), nicht eine separate Roh-SSH-Datei.

### 14.9 IP sperren

- Button **IP sperren …** oder **Rechtsklick** auf eine Zeile mit erkennbarer IP → **IP sperren**.
- Bestätigungsdialog; Schreiben per **Python** auf dem NAS in **`/ugreen/.config/block_ip_list`** (JSON-Liste). **Doppelte** IPs werden nicht erneut angehängt.
- **Nicht** sperrbar: **127.0.0.1** und die **NAS-IP** aus dem Header.
- Wirkung hängt von **UGOS/Firewall** ab, die diese Liste auswertet — bei Problemen NAS-Logs und UGOS-Dokumentation prüfen.

### 14.10 Fehlerfälle und Tipps

- **„SSH-Antwort ohne erwartete Log-Abschnitte“** — Verbindung/ Rechte / abweichende UGOS-Pfade; SSH-Ausgabe im Hinweisblock lesen.
- **Leere Liste bei Echtzeit** — nach Baseline noch **kein** neuer Login; Test von externem Client; Filter **App-Session-Pings** testweise **aus**.
- **UGOS-App-Login fehlt** — manche Sessions loggen nur **verify/is_login**; Filter kann Rauschen ausblenden, echte Logins sollten in **ctl_serv** / **log_serv** erscheinen.
- **Viele SSH-Zeilen von diesem PC** — eigene Admin-Session erzeugt Log-Einträge; für Fremdzugriffe **IP-Spalte** nutzen.
- **Max. Einträge** in der Session: intern begrenzt (großer Puffer); bei sehr langen Live-Sessions ggf. **Export** zwischenspeichern.

---

## 15. Tab NAS-Verwaltung komplett (aktive Aktionen per SSH/sudo)

Eigenständiger Tab **zwischen** „System & Health“, **Login Track** und „Speicher & Freigaben“. Hier werden **keine reinen Diagnosen** gezeigt, sondern **gezielte Aktionen** am NAS ausgeführt (SSH mit **sudo**).

### 15.1 Aufbau, Scrollen und Fenstergröße

- **Zwei Spalten:** Links alle Bediengruppen (Aktionen), rechts ein **Protokoll** mit der SSH-Ausgabe der jeweiligen Befehle.
- **Scrollen (links):** Der linke Bereich ist **länger als der sichtbare Bereich** — vertikal mit dem **Mausrad** scrollen, während der Mauszeiger **über der linken Spalte** (Formularfelder, Schaltflächen, Überschriften) liegt. Zusätzlich ist die **Scrollleiste** am rechten Rand des linken Bereichs nutzbar (Ziehen/klicken wie gewohnt). Der **Scrollbereich** wird bei jedem Rad-Schritt **direkt** nachgezogen, damit es sich nicht „festfährt“.
- **Protokollbreite / Knopfzeilen:** Zwischen linker Spalte und Protokoll liegt ein **Splitter** (schmale Trennlinie). Per Maus **ziehen**, um die Aufteilung anzupassen. Beim Öffnen erhält die **linke Spalte etwa 85 %** der Breite; mehrzeilige Blöcke und **jeder Schaltfläche eigener Platz** verhindern, dass lange Beschriftungen die ganze Zeile „aufblasen“. Das Protokoll kann schmal starten und bei Bedarf verbreitert werden.

### 15.2 Voraussetzungen und „Volle Rechte“

- **Schreibende oder riskante Aktionen** (Dateien ändern, Dienste neu laden, Tests/Wartung starten, USB auswerfen, SSH-Profile, Samba, earlyOOM, NGINX-Recovery, …): Im Header **„Volle Rechte“** aktiv und SSH-Benutzer mit **sudo** (analog Health: Neustart/Herunterfahren).
- **Nur lesen / Listen / Status ohne Systemeingriff:** z. B. „USB-Liste“, „Laufwerke“, „LED-Slots“, „Freigaben einlesen“, „Cron lesen“, „power.conf lesen“, Anzeige **RAID-Check Status** — oft schon **ohne** freigeschaltete Gefahrenaktionen möglich, sofern **SSH verbunden** ist.
- **Immer:** Ausgaben und Fehlermeldungen im **Protokoll** prüfen; bei unsicherem Zustand zuerst **lesende** Schritte ausführen.

### 15.3 Empfohlene allgemeine Vorgehensweise

1. Oben im Tab Kurzinfo lesen (Hinweis auf sudo / erweiterte Funktionen).
2. Zuerst **Listen aktualisieren** (USB, Laufwerke, Freigaben, …), dann **Auswahl** im Dropdown treffen.
3. Vor **Schreibzugriffen** die angezeigten **Bestätigungsdialoge** lesen.
4. Nach Aktion **Protokoll** prüfen — Exit-Codes und Meldungen von `systemctl`, `smartctl`, `testparm` usw. beachten.

### 15.4 Bereiche: Was macht was? (Kurzüberblick)

| Bereich | Zweck (kurz) | Typische NAS-Objekte |
|--------|----------------|------------------------|
| Energie & WoL | Verhalten nach Stromausfall / Wake-on-LAN | `/etc/power.conf` (per `crudini`) |
| Geplanter Shutdown | Tägliches Herunterfahren zu fester Uhrzeit | `/etc/cron.d/nas_admin_timed_shutdown` |
| USB | USB sicher abmelden (UGOS) | `USBDiskStop`, `umount`, Mount unter u. a. `/mnt/@usb/…` |
| SMART | Selbsttests und Protokoll | `/dev/sd…`, `smartctl` |
| RAID & Dateisystem-Wartung | RAID-Scrub anstoßen, TRIM, ext4-Scrub | `mdcheck`, `fstrim`, `e2scrub_all` (systemd) |
| SSH (Drop-in) | Zusatzregeln für `sshd`, mit Rollback-Sicherung | `/etc/ssh/sshd_config.d/60-ugreen-nas-admin.conf` |
| UGOS-Core-Dienste | Kern-Dienste starten/stoppen/Log; **Service-Liste** wird bei „Alles aktualisieren“ um alle aktiven `*_serv`-Units **ergänzt** | `*_serv.service` |
| NGINX | Konfiguration neu laden oder aus ROM zurücksetzen | `ugnginx-reload`, `/rom/etc/nginx`, … |
| earlyOOM | Speicherüberwachung parametrieren | `/etc/default/earlyoom` |
| Samba | Freigaben, Papierkorb leeren, Schnellanlage | `smb.conf`, `testparm` |
| LED & Summer | Gehäuse-Identifikation | `/sys/class/leds/diskN`, `ugbeep` |

### 15.5 Energie & Wake-on-LAN

- **Lesen:** Liest `power_boot` und `wake_on` (Bereich `[power]`) aus `/etc/power.conf` und zeigt die Komboboxen an; optional Rohauszug im Protokoll.
- **Speichern:** Schreibt die gewählten Werte (typ. `true`/`false`) per **sudo** nach `/etc/power.conf`. Nur ausführen, wenn du die Bedeutung der Optionen kennst (Handbuch des NAS / UGOS).
- **WoL in power.conf:** Übernimmt die **aktuelle Wake-on-LAN-Auswahl** in die Datei (separater Schritt, falls du nur WoL ändern willst).

### 15.6 Geplanter täglicher Shutdown

- **App-eigene Datei:** **„Cron schreiben“** legt (oder überschreibt) nur **`/etc/cron.d/nas_admin_timed_shutdown`**. Wenn du den Shutdown **nie über diese Schaltfläche** gesetzt hast, fehlt diese Datei trotzdem — UGOS kann die Uhrzeit z. B. in **anderen** Dateien unter `/etc/cron.d/`, in der **root-crontab**, unter **`/var/spool/cron/...`** oder in **`/etc/crontab`** speichern (die **klassische System-Oberfläche** des NAS nutzt oft **keine** App-Datei).
- **„Cron lesen“** zeigt deshalb mehrere Blöcke: die App-Datei (falls vorhanden), **Inhalt von `/etc/cron.d/`**, **grep** nach shutdown/poweroff/halt/**TimedShutdown** (UGOS nutzt oft **`/sbin/TimedShutdown`** in der **root-Crontab**, nicht in `/etc/cron.d`), direktes Lesen der **Spool-Dateien** (falls `crontab -l` per SSH leer ist) sowie **`/etc/crontab`** und **systemd-Timers**. Wenn alles leer ist oder nur generische Timer erscheinen: der geplante Shutdown sitzt ggf. **nur in der UGOS-GUI** oder in einem **anderen** Mechanismus — dann dort prüfen. **SSH muss verbunden sein** (sonst siehst du nur „Nicht verbunden“). Die erste erkannte Cron-Zeile mit Herunterfahren-Keyword (inkl. **TimedShutdown**) wird **in die Felder übernommen** (Checkbox aktiv), sofern die App Minute/Stunde parsen kann (bei mehreren Wochentags-Zeilen entspricht das der ersten Treffer-Zeile in der Ausgabe).
- **Aktivieren (über diese App):** Tageszeit im Format **HH:MM** (24 h), dann **Cron schreiben** — wie oben. **Wirkliches Herunterfahren** — Wartungsfenster und Benutzer beachten.
- **Deaktivieren:** nur die **App-Datei** entfernen (Bestätigung) — ein in UGOS anderswo konfigurierter Shutdown läuft dann ggf. **weiter**, bis du ihn auf dem NAS dort änderst.

### 15.7 USB (UGOS)

1. **USB-Liste:** Sucht typische USB-Mounts (Pfade mit `usb`, `@usb`, Volume-USB, …).
2. Mount wählen, dann **UGOS auswerfen:** Zeigt **lsof/fuser**, warnt bei erkennbarer Nutzung; bei Bestätigung **`USBDiskStop`** (sofern vorhanden), danach **`sync`** und **`umount`**. Vorher alle Anwendungen schließen, die auf den Stick zugreifen.

### 15.8 SMART

- **Laufwerke:** Liste der Blockgeräte aktualisieren, Zielplatte wählen.
- **Test:** *short* (Minuten), *long* (sehr lange, hohe Last), *conveyance* (Transportcheck) — je nach Firmware/Platte.
- **Self-Test Log:** Zeigt relevante SMART-/Test-Historie aus den Logs/aus `smartctl`, abhängig vom System.

### 15.9 RAID & Dateisystem-Wartung

- **RAID-Check starten:** Startet den vorgesehenen systemd-Job für den geplanten RAID-Check (`mdcheck_start`), so wie UGOS ihn vorsieht.
- **Status / Fortschritt:** Nur Anzeige — einliest aktuellen Bearbeitungsstand bzw. md/mdadm-relevante Infos, ohne zu schreiben.
- **fstrim / e2scrub_all:** Startet die jeweiligen **systemd**-Einheiten; kann **spürbare IO-Last** erzeugen — zu Wartungszeiten einplanen.

### 14.10 SSH-Härtung (Drop-in)

- **Profil wählen** (*high* / *middle* / *low*): Schreibt eine **Zusatzdatei** unter `sshd_config.d`, ruft **`sshd -t`** und **`systemctl reload ssh`** (bzw. Restart) auf.
- **Auto-Rollback:** Wenn `at` auf dem NAS verfügbar ist, wird ein **verzögertes Rollback** geplant (nur wenn du **nicht** rechtzeitig bestätigst).
- **SSH ok bestätigen:** Legt eine **Kennmarkierung** auf dem NAS an und **entfernt** die geplante Rollback-**at**-Job-ID — nur klicken, wenn eine **zweite** SSH-Sitzung erfolgreich war.
- **Rollback:** Stellt die **Backup-Kopie** der alten Drop-in-Datei wieder her bzw. entfernt die Datei — bei Verbindungsproblemen.

**Wichtig:** Vor *high* immer prüfen, ob alle Clients (SSH-Versionen) mit den Algorithmen klarkommen.

### 15.11 UGOS-Core-Dienste

- **Dropdown:** Enthält eine **fest definierte Kernliste** typischer `*_serv`-Namen (storage, docker, gateway, …). Nach jedem erfolgreichen **„Alles aktualisieren“** (Sidebar) hängt die App **alle weiteren auf dem NAS aktiven** Units an, deren Name auf **`_serv.service`** endet (alphabetisch sortiert, ohne Duplikate) — so erscheinen z. B. zusätzliche UGOS-Paket-Dienste, ohne auf eine App-Aktualisierung zu warten.
- **Start / Stop / Neustart:** `systemctl`-Aktion — kann Verbindungen oder Dienste kurz unterbrechen.
- **Journal:** Letzte Journalzeilen der gewählten Unit — Diagnose bei Fehlern.
- **Support-Snapshot** (neben **Journal**, nur Lesen): Schreibt ins **rechte Protokoll** des Tabs u. a. **`uname -a`**, einen Auszug aus **`/etc/os-release`**, ein kurzes **`journalctl`**-Stück zu **`entry_serv`**, sowie **Tail-Auszüge** aus typischen UGOS-Logs (`storage_serv`, `gateway_serv`, `docker_serv`, `networking.log`, `syslog`). **Kein** Schreibzugriff auf dem NAS; dient der **Einsammel-Hilfe** für Support (Text kopieren). **Voraussetzung:** NAS-IP im Header und SSH; bei fehlender IP erscheint ein Hinweisdialog.

### 15.12 NGINX

- **Reload:** Führt den UGOS-**reload**-Pfad aus (oder Fallback `systemctl reload nginx`) und zeigt Kurzstatus.
- **Config-Recovery:** Nur nach bewusster Bestätigung: Dialog verlangt die Eingabe **`RESTORE`**; spielt die **ROM-/Standard-Konfiguration** nach `/etc/nginx` ein — **bestehende Anpassungen gehen an der Stelle verloren**. Nur mit Backup-Strategie nutzen.

### 15.13 earlyOOM

- **Laden / Speichern:** Bearbeitet `/etc/default/earlyoom` und startet den Dienst neu. Syntax der Kernel-Parameter beachten — Fehler können OOM-Verhalten verschlechtern.

### 15.14 Samba

1. **Freigaben einlesen:** Füllt die Liste aus `testparm`/`smb.conf` (ohne `global` als Ziel).
2. **Papierkorb leeren:** Ermittelt den Pfad der Freigabe und leert typische **Recycle-Ordner** (`@recycle`, …) — **unwiderruflich** für diese Dateien.
3. **Schnell-Freigabe:** Hängt einen **einfachen** Block an `smb.conf` an, prüft mit `testparm`, lädt **`smbd`** neu. Pfad muss zu einem **UGOS-Volume** passen (z. B. `/volume1/...`).

### 15.15 LED & Summer

- **LED-Slots** aktualisieren, `diskN` wählen, **Identify:** kurzes Blinken (~12 s) zur Gehäusezuordnung.
- **Summer:** Testton über UGOS-**beep**-Werkzeug (modellabhängig).

---

### Aus dem Bereich: 49. Health komplett: Alle Blöcke im Zusammenspiel

Health ist Diagnosezentrale, nicht nur Anzeige.

### 49.1 Hauptbuttons

- Refresh = Gesamtzustand
- RAID/SMART/Storage = Teilanalyse
- Scheduler-Inventar = listet geplante Jobs und deren Zustand als Schnellcheck
- Report speichern = Dokumentation

### 49.2 Systembuttons

- Neustart
- Herunterfahren

Nur im geplanten Wartungsfenster.

### 49.3 UGOS-Dashboard

Schneller Blick auf Kernservices.

### 49.4 Telegram-Sofortmonitor

Nützlich für lokalen Test ohne vollständigen Watcher-Deploy.

### 49.5 NAS-Watcher

Konfiguration + Deploy + Test im selben Bereich.

### 49.6 Daily Report

Täglicher Statusbericht (nicht Alarmersatz, sondern Verlauf).

---

### Aus dem Bereich: 59. Praxisanleitung: Telegram Alarmierung wirklich robust

Viele Setups scheitern nicht am Bot, sondern an Randbedingungen. Diese komplette Sequenz sorgt fuer ein robustes Ergebnis:

1. Bot erstellen (`@BotFather`, `/newbot`).
2. Token sichern (nicht in Screenshots posten).
3. Zielchat definieren (Einzelchat oder Gruppe).
4. Chat-ID ueber `getUpdates` ermitteln.
5. Token/Chat-ID in Settings eintragen.
6. Speichern.
7. Telegram-Test im Health-Tab ausfuehren.
8. Testnachricht bestaetigen.
9. NAS Watcher deployen.
10. Watcher-Test senden.
11. Daily Report Test senden.
12. In den naechsten 24h pruefen, ob periodische Meldungen ankommen.

Wenn einzelne Schritte fehlschlagen, nie sofort alles neu machen. Immer den letzten funktionierenden Stand als Referenz behalten.

---

### Aus dem Bereich: 66. Detailkatalog Health-Watcher Schalter

Jeder Schalter definiert, ob ein konkreter Check im Watcher aktiv sein soll.

- UPS check: NUT-Status
- UGOS core services: Kernservices
- SMART daemon: smartd aktiv/enabled
- Network ready: wait-online Dienst
- File services: SMB/NFS/wsdd2
- Maintenance timers: trim/sysstat/logrotate/backups
- RAID checks: mdstat/mdcheck
- Docker runtime checks

Empfehlung:

Aktiviere zunaechst die sicherheits- und verfuegbarkeitskritischen Checks. Danach schrittweise erweitern, um Alarmflut zu vermeiden.

---

---

## 16. Tab Speicher & Freigaben komplett

### Aus dem Bereich: 32. Vollständige Referenz: Storage-Tab

Buttons:

- Volumes/df
- Shares
- Refresh all
- Top20
- Disk scan
- Image to PC
- Image to NAS
- Restore from PC
- Restore from NAS

Felder:

- Top-Path
- Device-Combo
- Remote-Image-Path

---

### Aus dem Bereich: 50. Storage komplett

### 50.1 Volumes/Shares

Buttonreihe für Zustandserfassung.

### 50.2 Top 20 Ordner

Findet die **größten Unterordner** unter einem Pfad (typisch `/volume1`). Lauf kann bis **~5 Minuten** dauern — ab Version **23.8.5** im **Hintergrund**, die App bleibt bedienbar.

**Kurz:** Storage-Tab → Pfad eintragen → **Top 20 Ordner** → Ergebnis erscheint unten im Log.

**Ausführliche Schritt-für-Schritt-Anleitung: §80.**

### 50.3 Disk-Image-Operationen

Starkes Werkzeug für Spezialfälle.

Vor jeder Image-/Restore-Aktion:

1. Device eindeutig wählen.
2. Zielpfad prüfen.
3. genügend Speicher/zeit einplanen.

---

---

## 17. Tab ACL komplett

### Aus dem Bereich: 33. Vollständige Referenz: ACL-Tab

Buttons:

- Anzeigen (stat)
- UGACL-Info
- chmod 755
- chmod 777 rec
- chmod anwenden
- chown anwenden
- Users
- Groups

Felder:

- Zielpfad
- chmod-Modus
- chown-Wert

---

### Aus dem Bereich: 51. ACL komplett

### 51.1 Diagnose zuerst

- Anzeigen
- UGACL-Info

### 51.2 Änderungen danach

- chmod 755 / 777 rec / custom
- chown apply

Regel:

- erst klein testen, dann groß ausrollen.

---

---

## 18. Tab Snapshots komplett

### Aus dem Bereich: 34. Vollständige Referenz: Snapshots-Tab

Buttons:

- detect backend
- btrfs list
- zfs list
- snapper list
- btrfs create
- zfs create
- snapper create
- btrfs delete
- zfs delete
- snapper delete

Feld:

- Basispfad

---

### Aus dem Bereich: 52. Snapshots komplett

### 52.1 Backend erkennen

Nötig um passende Befehle zu wählen.

### 52.2 Listen und Erstellen

Vor Erstellen:

- Basispfad prüfen.

### 52.3 Löschen

Nur mit klarer Identifikation des Snapshots und Rückfallplan.

---

---

## 19. Tab Backup komplett (Backup + Restore + Schedules zusammen)

### Aus dem Bereich: 35. Vollständige Referenz: Backup-Tab

### 35.1 Backup-Block Buttons

- Docker+Scripts Backup
- User Data Backup
- All Data Backup
- Refresh Lists
- **Migrations-Assistent** (rsync für Volume-/NAS-Umzug; auch im Tab NAS↔NAS)

### 35.1a Migrations-Assistent

Szenarien: gleiche NAS (andere Volumes), Push auf andere NAS, Pull von anderer NAS, Vorlage Synology/QNAP. Erzeugt ein Bash-Skript mit `rsync -aHAX` (Dry-Run standardmäßig). Speichern unter `/volume1/scripts/ugreen_migration_rsync.sh`. Für interaktives Kopieren weiterhin **NAS ↔ NAS**.

**Buttons im Dialog:** Skript aktualisieren · **Vorab-Prüfung** · Auf NAS speichern · Auf NAS ausführen · Tab NAS ↔ NAS · Schließen. Lange Läufe (rsync, Speichern) blockieren die UI **nicht** — Buttons sind währenddessen kurz deaktiviert.

**Ausführliche Schritt-für-Schritt-Anleitung: §78.** SSH-Timeouts: **§79.**

### 35.2 Backup-Felder

- Scope combo
- Volume combo
- User combo
- Dest mode combo
- NAS profile combo
- PC path
- USB combo
- optional remove-on-copy checkbox

### 35.3 Restore-Block

Felder:

- Source mode (`nas`/`pc`)
- Archive path
- Target path

Buttons:

- Datei wählen
- Wiederherstellen starten

### 35.4 Scheduled Backup

Buttons:

- Von NAS laden
- Auf NAS speichern
- Entfernen
- Erstellen/Aktualisieren

Felder:

- Joblabel
- Jobtyp
- Cron-Felder
- Zusatzoptionen

---

### Aus dem Bereich: 53. Backup komplett

### 53.1 Scope/Volume/User

Steuert was gesichert wird.

### 53.2 Zielmodus

- NAS
- PC
- USB
- zweites NAS-Profil

### 53.3 Backupbuttons

- Docker+Scripts
- User Data
- All Data

### 53.4 Restore

Felder:

- source mode
- source archive
- target path

Buttons:

- file picker
- restore start

### 53.5 Scheduled Backup

Komplette Jobverwaltung mit Cronlogik.

---

### Aus dem Bereich: 61. Praxisanleitung: Backup und Restore mit Verifikation

### 61.1 Vollbackup erstellen

1. Backup-Tab oeffnen.
2. Scope/Volume/User filtern.
3. Zielmodus setzen (NAS/PC/USB/zweites NAS).
4. Passenden Backupbutton waehlen.
5. Lauf pruefen.
6. Archivpfad dokumentieren.

### 61.2 Restore durchfuehren

1. Source Mode setzen.
2. Source Archive auswaehlen.
3. Target Path festlegen.
4. `Wiederherstellen starten` klicken.
5. Ergebnispruefung:
   - existieren Dateien?
   - stimmen Rechte?
   - sind Dienste wieder lauffaehig?

### 61.3 Nachkontrolle

- Health Refresh
- betroffene App/Container testen
- optional Snapshot fuer neuen stabilen Stand

---

### Aus dem Bereich: 78. Praxisanleitung: Migrations-Assistent (Volume / NAS / Synology)

Ziel: Daten kontrolliert umziehen — auf ein anderes Volume derselben UGREEN-NAS, auf eine zweite NAS, oder von Synology/QNAP importieren — ohne blindes Kopieren.

**Wann welches Werkzeug?**

| Aufgabe | Empfehlung |
|---------|------------|
| Einzelne Ordner/Dateien per GUI zwischen NAS und PC/Peer | Tab **NAS ↔ NAS** oder **Explorer** |
| Große, wiederholbare Datenmigration mit Protokoll | **Migrations-Assistent** (rsync-Skript) |
| Vollbackup als Archiv | Tab **Backup** (tar/Backup-Buttons) |

**Voraussetzungen**

1. SSH-Verbindung zur **Ziel-UGREEN** steht.
2. Genug **freier Speicher** am Ziel (Storage-Tab prüfen).
3. **Snapshot oder Backup** der Quelldaten (Tab Snapshots oder Backup) — vor jedem Live-rsync.
4. Für NAS↔NAS per SSH: **SSH-Key** auf beiden Systemen (Settings → SSH-Key installieren) oder Passwort-SSH möglich.
5. Betroffene **Docker-Container stoppen**, wenn Docker-Volumes migriert werden (Docker-Tab → Stop).

**Schritt 1 — Assistent öffnen**

1. **Backup-Tab** → Button **Migrations-Assistent**, **oder**
2. **NAS ↔ NAS**-Tab → gleicher Button in der linken Toolbar.
3. Fenster **Migrations-Assistent** erscheint mit Szenario-Auswahl, Pfadfeldern und Skript-Vorschau unten.

**Schritt 2 — Szenario wählen**

Eines der vier Optionsfelder aktivieren:

1. **Gleiche NAS — anderes Volume/Pfad**  
   Beispiel: Docker von `/volume1/docker` nach `/volume2/docker`.  
   rsync läuft **lokal auf der NAS** (kein Remote-Host nötig).

2. **Auf andere NAS kopieren (Push)**  
   Daten **von dieser UGREEN weg** auf eine andere NAS.  
   Remote-Host/IP und SSH-Benutzer der **Ziel-NAS** eintragen.

3. **Von anderer NAS importieren (Pull)**  
   Daten **von einer anderen NAS** auf diese UGREEN holen.  
   Remote-Host/IP = **Quell-NAS**, Quellpfad = Pfad auf der Quell-NAS.

4. **Von Synology/QNAP — Vorlage**  
   Wie Pull, aber Pfade manuell an Synology/QNAP anpassen (z. B. `/volume1/photo` → `/volume1/photos` auf UGREEN).

**Schritt 3 — Pfade eintragen**

1. **Quellpfad:** Absoluter Pfad mit führendem `/`, z. B. `/volume1/docker/jellyfin` oder `/volume1/@home/user/Drive`.
2. **Zielpfad:** Absoluter Pfad auf der NAS, die **empfängt** (bei Push: Pfad auf der **Remote-NAS**).
3. **Remote-Host/IP:** Nur bei Push, Pull oder Synology/QNAP — IP oder Hostname der **anderen** NAS.
4. **SSH-Benutzer:** Meist `admin` oder dein NAS-Admin (gleicher Name wie für SSH-Login).

**Schritt 4 — Optionen setzen**

1. **Dry-Run (-n)** — standardmäßig **aktiv**. Erst damit testen; es werden **keine** Dateien geändert, nur simuliert.
2. **--delete** — nur aktivieren, wenn das Ziel **exakt** wie die Quelle werden soll (Extra-Dateien am Ziel werden gelöscht). **Vorsicht** — nur nach erfolgreichem Dry-Run.

**Schritt 5 — Skript erzeugen und prüfen**

1. **Skript aktualisieren** klicken (beim Öffnen schon vorbefüllt).
2. Im Textfeld unten das Bash-Skript lesen:
   - `rsync -aHAX --info=progress2 --numeric-ids`
   - bei Dry-Run: `-n` in der rsync-Zeile
   - Quelle und Ziel mit trailing `/` (kopiert **Inhalt** des Ordners)
   - Variablen `SRC=` / `DST=` / `RSYNC_SRC=` — **Auf NAS ausführen** startet das **gesamte Skript**, nicht nur die rsync-Zeile
3. Checkliste im Dialog beachten: Snapshot → Apps stoppen → Dry-Run → Live → Pfade in Compose anpassen → Dienste starten.

**Schritt 5a — Alle Schaltflächen im Dialog (Referenz)**

| Button | Funktion |
|--------|----------|
| **Skript aktualisieren** | Baut das Bash-Skript aus Szenario, Pfaden und Optionen neu und zeigt es im Textfeld |
| **Vorab-Prüfung** | Prüft Pfade, Speicher und (bei Remote) SSH — Ergebnis im Textfeld + Dialog; läuft im Hintergrund |
| **Auf NAS speichern** | Schreibt das Skript nach `/volume1/scripts/ugreen_migration_rsync.sh` (ausführbar); Hintergrund |
| **Auf NAS ausführen** | Führt **Vorab-Prüfung** aus, dann das Skript per SSH auf der NAS — Hintergrund, kann sehr lange dauern |
| **Tab NAS ↔ NAS** | Schließt den Assistenten und wechselt zum GUI-Kopier-Tab |
| **Schließen** | Dialog schließen ohne weiteren Lauf |

Während ein Hintergrund-Job läuft, sind die Aktions-Buttons kurz **ausgegraut**; die Statuszeile zeigt z. B. „Vorab-Prüfung läuft…“ oder „Migration/rsync läuft…“.

**Schritt 6 — Vorab-Prüfung (empfohlen, auch automatisch vor Ausführen)**

1. **Vorab-Prüfung** klicken (oder direkt **Auf NAS ausführen** — dann läuft die Prüfung zuerst automatisch).
2. Die App prüft per SSH auf der UGREEN (und ggf. per SSH zur Remote-NAS):
   - **Quellpfad vorhanden** (`test -d`)
   - **Zielpfad erreichbar** (Ordner anlegbar)
   - **Quellgröße** (`du -sk`) und **freier Speicher am Ziel** (`df`)
   - bei Push/Pull/Synology: **SSH zur Remote-NAS** (SSH-Key von UGREEN zur anderen NAS nötig — siehe Settings §23.4)
3. Ergebnis unten im Textfeld unter `=== Vorab-Prüfung ===` — jede Zeile mit `•`.
4. Dialog **bestanden** → weiter mit Dry-Run oder Live. Dialog **fehlgeschlagen** → Pfade/Key/Speicher korrigieren, erneut prüfen.

**Was die Vorab-Prüfung meldet**

| Meldung | Bedeutung | Maßnahme |
|---------|-----------|----------|
| Quellpfad vorhanden | OK | — |
| Quellpfad fehlt | Pfad falsch oder nicht gemountet | Pfad im Explorer prüfen |
| Zielpfad erreichbar | OK | — |
| Zielpfad fehlt | Kein Schreibrecht oder falscher Pfad | sudo/ACL, Pfad korrigieren |
| Quellgröße ca. … | Grobe Datenmenge | — |
| Freier Speicher am Ziel ca. … | Platz auf Ziel-Volume | Storage-Tab, anderes Volume |
| Warnung: weniger freier Speicher als Quelle | Migration würde vermutlich scheitern | Speicher freimachen oder anderes Ziel |
| SSH zur Remote-NAS OK | Key/Netzwerk stimmt | — |
| SSH zur Remote-NAS fehlgeschlagen | Kein Key, Firewall, falscher Host | Key auf UGREEN für Remote-NAS, Port 22 |
| Remote-Host/IP fehlt | Bei Push/Pull Host leer | IP eintragen |

**Schritt 7 — Dry-Run auf der NAS ausführen**

1. Sicherstellen: Häkchen **Dry-Run** ist **gesetzt**.
2. **Skript aktualisieren** (damit `-n` in der rsync-Zeile steht).
3. **Auf NAS ausführen** klicken — zuerst Vorab-Prüfung, dann rsync-Simulation.
4. Ausgabe unter `--- NAS ---` im Textfeld prüfen — was **kopiert würde**, ohne zu schreiben.
5. Bei Fehlern: Exit-Code und Text in der Meldung lesen; ggf. **§79** (Timeout) und SSH-Key prüfen.

**Schritt 8 — Live-Migration**

1. Docker/Dienste, die auf die Quelle zugreifen, **gestoppt** lassen.
2. Häkchen **Dry-Run** **entfernen**.
3. **Skript aktualisieren** — `-n` verschwindet aus der rsync-Zeile.
4. **Auf NAS ausführen** — Bestätigungsdialog bei Live-Lauf lesen und bestätigen.
5. rsync kann **Stunden** dauern — Fenster offen lassen; UI bleibt bedienbar (andere Tabs möglich). **Lang-Timeout** in Settings auf **0** lassen (§79).
6. Bei Erfolg: Dialog „rsync abgeschlossen“; bei Fehler: Exit-Code-Meldung — Log unten prüfen.

**Schritt 9 — Skript für später speichern (optional)**

1. **Auf NAS speichern** — legt `/volume1/scripts/ugreen_migration_rsync.sh` an (ausführbar); läuft im Hintergrund.
2. Wiederholung oder Cron: Skript-Tab → Datei öffnen, anpassen, im Scheduler planen.

**Schritt 10 — Nach der Migration**

1. **Compose-/App-Pfade** anpassen, wenn sich Volume geändert hat (Docker-Assistent, Pfade in YAML).
2. Container/Dienste **neu starten** (Docker-Tab → Start).
3. Stichprobe: Dateien am Ziel zählen, App öffnen, Health-Tab aktualisieren.
4. Erst wenn alles läuft: Quelldaten **optional** löschen (nicht sofort — Sicherheitsreserve).

**Beispiel A: Docker von volume1 nach volume2 (gleiche NAS)**

| Feld | Wert |
|------|------|
| Szenario | Gleiche NAS — anderes Volume |
| Quellpfad | `/volume1/docker` |
| Zielpfad | `/volume2/docker` |
| Dry-Run | an → testen → aus für Live |

**Beispiel B: Pull von Synology auf UGREEN**

| Feld | Wert |
|------|------|
| Szenario | Von anderer NAS importieren |
| Quellpfad | `/volume1/photo` (Synology Shared Folder) |
| Zielpfad | `/volume1/photos` |
| Remote-Host | `192.168.1.50` |
| SSH-Benutzer | `admin` |

Synology: SSH unter Systemsteuerung aktivieren; ggf. Pfad `/volume1/<Freigabe>` statt `@home` verwenden.

**GUI-Alternative**

Für kleinere Mengen ohne Skript: Assistent → **Tab NAS ↔ NAS** — dort UGREEN links, Peer rechts, Ordner markieren, Kopieren (SMB). Der Migrations-Assistent ist für **große, vollständige Baum-Kopien** mit rsync gedacht.

**Typische Fehler**

- **Dry-Run vergessen abzuschalten:** Live-Lauf mit `-n` kopiert nichts — Häkchen entfernen, Skript aktualisieren.
- **Trailing Slash:** `/volume1/data/` kopiert den **Inhalt**; Assistent setzt `/` konsistent.
- **SSH zur Remote-NAS fehlgeschlagen:** Key von UGREEN aus auf Remote-NAS eintragen (Settings §23.4), Firewall Port 22.
- **SSH-Befehl abgebrochen (Timeout):** Standard-Timeout zu niedrig — **Lang (s) = 0** für rsync (§79).
- **Befehl fehlgeschlagen (Exit …):** Meldung enthält Exit-Code und Auszug — Pfade, sudo, Speicher prüfen.
- **Vorab-Prüfung: weniger Speicher am Ziel:** Andere Platte/Volume oder Daten vorher löschen/archivieren.

---

### Aus dem Bereich: 79. Praxisanleitung: SSH-Befehl-Timeouts (Settings)

Ziel: Kurze SSH-Aktionen sollen nicht ewig hängen; lange Jobs (rsync, `du`, Backup) dürfen dagegen unbegrenzt laufen.

**Wo einstellen**

1. Tab **Settings** (⚙️).
2. Bereich **Verbindung** — unter UGOS API die Zeile **SSH-Befehl:**.
3. Felder:
   - **Standard (s)** — Timeout für normale Befehle (Listen, Health, Explorer-`ls`, …).
   - **Lang (s)** — Timeout für **Langläufer**; **0 = unbegrenzt** (Standard, empfohlen).
4. Oben **Speichern** klicken (nicht nur „Auf aktuelle UI anwenden“), damit Werte in `app_settings.json` persistieren.

**Empfohlene Werte**

| Situation | Standard (s) | Lang (s) |
|-----------|--------------|----------|
| Normal / Homelab | 120 | 0 |
| Sehr langsame NAS / VPN | 180–300 | 0 |
| Nur kleine Befehle, nie rsync in App | 60 | 3600 (1 h) |

**Welche Aktionen nutzen welchen Timeout?**

| Timeout | Beispiele in der App |
|---------|----------------------|
| **Standard** | Explorer-Verzeichnisliste, Docker-Liste, Health-Einzelbefehle, Vorab-Prüfung (~90 s fest), Skript speichern |
| **Lang** | Migrations-Assistent rsync, Storage **Top 20**, Backup-Läufe |

**Was passiert bei Timeout?**

- Meldung: **„SSH-Befehl abgebrochen (Timeout)…“**
- Die App friert **nicht** ein (Hintergrund-Threads bei Migration/Top-20).
- Verbindung wird ggf. neu aufgebaut beim nächsten Befehl.
- **Maßnahme:** Standard-Wert erhöhen **oder** für den konkreten Langläufer **Lang = 0** setzen.

**Exit-Code-Meldungen (ab 23.8.5)**

Bei fehlgeschlagenen Befehlen (Migration, Top-20) erscheint z. B.:

`Befehl fehlgeschlagen (Exit 23): …`

| Exit | Typische Ursache |
|------|------------------|
| 1 | Allgemeiner Fehler (rsync, Skript) |
| 2 | Syntax / Skript-Fehler |
| 23 | rsync: teilweise Übertragung (Platz, Rechte, unterbrochen) |
| 255 | SSH-Verbindung abgebrochen |

Log-Text unter dem Dialog immer mitlesen.

---

### Aus dem Bereich: 80. Praxisanleitung: Storage Top-20 Ordner

Ziel: Herausfinden, **welche Ordner** unter `/volume1` (oder anderem Pfad) am meisten Platz belegen — z. B. vor Migration oder Aufräumen.

**Schritt 1 — Storage-Tab öffnen**

1. Sidebar → **Storage** (Speicher).
2. Nach unten scrollen, falls nötig — Bereich **Top 20** / Pfadfeld.

**Schritt 2 — Pfad setzen**

1. Feld **Pfad für Top-20** (z. B. `/volume1` oder `/volume1/docker`).
2. Nur Pfade verwenden, die auf der NAS existieren; mit **Volumes (df -h)** oben grob prüfen.

**Schritt 3 — Analyse starten**

1. Button **Top 20 Ordner** klicken.
2. Im Log erscheint eine Überschrift `=== TOP 20 (du unter …) ===`.
3. Statuszeile: **„Berechne größte Ordner (Hintergrund)…“** — App bleibt **bedienbar** (ab 23.8.5).
4. Während des Laufs erneuter Klick auf Top-20 wird ignoriert (Schutz vor Doppelstart).

**Schritt 4 — Ergebnis lesen**

1. Nach Abschluss: Status **„Top-20 fertig“**.
2. Liste sortiert nach Größe (größte zuerst), typisch bis Tiefe 3.
3. Größen in KB/MB/GB — größte Kandidaten für Archiv, Migration (§78) oder Löschen identifizieren.

**Schritt 5 — Bei leerer oder fehlerhafter Ausgabe**

1. Meldung **Exit-Code** oder Timeout lesen (§79).
2. **Permission denied:** App versucht automatisch mit sudo — NAS-User braucht sudo-Rechte.
3. Pfad zu tief/groß: engeren Pfad wählen (z. B. `/volume1/docker` statt `/volume1`).
4. Timeout bei Standard statt Lang: **Lang (s) = 0** in Settings; Top-20 nutzt Lang-Timeout.

**Hinweis:** `du` kann auf sehr großen Bäumen **mehrere Minuten** dauern (NAS-seitig `timeout 300`). Geduld oder kleinerer Startpfad.

---

### Aus dem Bereich: 67. Detailkatalog Backup-Restore Felder

### 67.1 Source Mode

Definiert, aus welchem Kontext die Archivquelle kommt:

- NAS-Dateisystem
- lokales Dateisystem
- USB Medium

### 67.2 Source Archive

Pfad zur konkreten Sicherungsdatei (z. B. tar.gz).  
Muss fuer den gewaehlten Source Mode erreichbar sein.

### 67.3 Target Path

Wiederherstellungsziel auf NAS.

Wichtig:

- Rechte vorhanden?
- genug Platz?
- Ziel leer/ueberschreibbar?

---

### Aus dem Bereich: 76. Vollworkflow D: Backup-Strategie fuer mehrere Ziele

Ziel ist, nicht nur ein Backup zu haben, sondern ein nutzbares Wiederherstellungskonzept.

Strategie:

1. Primaerziel NAS intern (schnell).
2. Sekundaerziel zweites NAS (Risikotrennung).
3. Optional USB/offline fuer Notfall.

Umsetzung in der App:

1. Settings mit zweitem NAS vervollstaendigen.
2. Backup-Tab Zielmodus je Lauf waehlen.
3. Taegliche/wöchentliche Jobs im Scheduler setzen.
4. Monatlich Restore-Test auf Testpfad.

Regel fuer echte Sicherheit:

Ein Backup gilt erst dann als verlässlich, wenn ein Restore erfolgreich getestet wurde.

---

## 20. Info-Dialog komplett

### Aus dem Bereich: 54. Info-Dialog komplett

Dokumentenbuttons:

- README
- Handbuch
- CHANGELOG

Weitere Elemente:

- YouTube
- Supportlink
- E-Mail-Kontakt
- About-Text

---

---

## 21. Gesamtbetrieb, Checklisten, Troubleshooting

### Aus dem Bereich: 19. Vollständige Betriebsreihenfolge (empfohlen)

1. Settings vollständig.
2. Verbindung prüfen.
3. Dashboard + Health.
4. Docker-Dienste aufbauen.
5. Skripte testen, dann Scheduler.
6. Backupziele setzen.
7. Restore-Test in Testpfad.
8. Watcher und Daily deployen.

---

### Aus dem Bereich: 20. Fehlerbehebung nach Bereich

### 20.1 Verbindung

- SSH-Badge rot: IP/Port/User/Auth prüfen.
- Key aktiv, aber Passwort im Feld: Auth-Weg vereinheitlichen.

### 20.2 Docker

- Liste leer trotz erwarteter Container: zuerst `Liste`.
- Start schlägt fehl: Inspect + Logs + Runtime im Health prüfen.

### 20.3 Backup/Restore

- Zielprofil fehlt: Settings-Zweitprofil prüfen.
- Restore ohne Wirkung: Archivpfad/Modus/Zielpfad kontrollieren.

### 20.4 Watcher/Daily

- Deploy ok, aber keine Meldungen: Kanal-Credentials und Trigger prüfen.
- Zu viele Meldungen: Schwellwerte/Checkboxen anpassen.

### 20.5 ACL/Explorer

- Unerwartete Rechteeffekte: zuerst Stat/UGACL lesen, dann gezielt ändern.
- Löschfehler: Fokusbaum und Pfad prüfen.

---

### Aus dem Bereich: 55. Checklisten (operativ)

### 55.1 Vor kritischer Änderung

1. Health Refresh
2. Snapshot/Backup
3. Einzeländerung
4. Logs/Status prüfen
5. ggf. nächste Änderung

### 55.2 Vor Docker-Update

1. Liste aktuell
2. Auswahl prüfen
3. Logs baseline
4. Update
5. Funktionstest

### 55.3 Vor Restore

1. Archiv prüfen
2. Zielpfad prüfen
3. Vorzustand sichern
4. Restore
5. Integrität prüfen

---

### Aus dem Bereich: 56. Große Fehlerbilder und saubere Reaktion

### 56.1 „Alles wirkt kaputt“

Nicht überall klicken. Reihenfolge:

1. SSH
2. Health Refresh
3. Core Services
4. Storage
5. Docker Runtime

### 56.2 „Nur ein Dienst kaputt“

1. betroffenen Tab öffnen
2. Liste/Status aktualisieren
3. Logs/Inspect
4. gezielte Korrektur

### 56.3 „Benachrichtigungen kommen nicht“

1. Settings Credentials
2. Kanalwahl
3. Testbuttons
4. NAS-Netzwerk

---

### Aus dem Bereich: 58. Praxisanleitung: Erste Inbetriebnahme ohne Luecken

Diese Anleitung fuehrt dich vom ersten Start bis zur stabilen Grundkonfiguration, ohne dass ein Bereich uebersprungen wird.

1. App starten und Theme/Sprache waehlen, damit du die Oberflaeche sofort in deinem Arbeitskontext siehst.
2. Settings oeffnen und die Verbindungsdaten zur UGREEN NAS eintragen.
3. SSH-Verbindung testen, damit klar ist, dass die Basis steht.
4. Screenshot-Verzeichnis setzen, damit du bei Bedarf sofort Dokumentation erzeugen kannst.
5. Telegram und/oder SMTP eintragen und mit Test pruefen.
6. Zweites NAS-Profil eintragen, falls du NAS-zu-NAS-Transfers oder Zweitziele fuer Backups nutzen willst.
7. Speichern und direkt danach die relevanten Tabs aktualisieren.
8. Health-Tab oeffnen und einmal vollstaendig `Refresh` laufen lassen.
9. Dashboard pruefen: Last, Volumes, Docker, Fanstatus.
10. Scripts-Tab oeffnen und Backup einer bestehenden Skriptbasis machen.

Wenn diese zehn Punkte sauber durchlaufen wurden, ist die App in der Regel betriebsbereit fuer Alltag und Wartung.

---

### Aus dem Bereich: 68. Sicherheitsregeln fuer produktiven Betrieb

1. Vor grossen Aenderungen immer Health Snapshot.
2. Vor Loesch-/Restore-Aktionen immer Backup/Snapshot.
3. Nie gleichzeitig mehrere kritische Bereiche anfassen (z. B. Docker + ACL + Storage in einem Schritt).
4. Aenderungen sequenziell und pruefbar durchfuehren.
5. Bei Unsicherheit zuerst in kleinerem Scope testen.

Diese Regeln reduzieren Ausfallzeit und machen Fehlerquellen nachvollziehbar.

---

### Aus dem Bereich: 69. Vollstaendige Troubleshooting-Matrix

### 69.1 SSH verbindet nicht

Symptom:

- Keine Daten in Dashboard/Health.

Pruefung:

- Host/Port korrekt?
- Netzwerk erreichbar?
- User/Pass korrekt?
- SSH auf NAS aktiv?

### 69.2 Docker zeigt nichts

Symptom:

- Leere Liste oder Fehlertext.

Pruefung:

- Docker Dienst laeuft?
- User hat noetige Rechte?
- Hostkommunikation stabil?

### 69.3 Backup auf zweites NAS fehlt

Symptom:

- Kein Profil in Auswahl.

Pruefung:

- Settings fuer zweites NAS gespeichert?
- Felder vollstaendig?
- Backup-Quellen aktualisiert?

### 69.4 Telegram meldet nicht

Symptom:

- Keine Nachricht bei Test.

Pruefung:

- Token/Chat-ID
- Netzwerk outbound
- Kanalwahl im Watcher/Daily

### 69.5 Fanprofil reagiert unerwartet

Symptom:

- RPM springt nicht wie erwartet.

Pruefung:

- gewaehlter Modus korrekt?
- Uebernehmen gedrueckt?
- UGOS Rueckgabe ausgefuehrt, falls Konflikt?

---

### Aus dem Bereich: 70. Wartungsplan fuer stabile Langzeitnutzung

Taeglich:

- Dashboard Schnellcheck
- Alerts lesen

Woechentlich:

- Health Vollrefresh
- Docker/Storage Auffaelligkeiten pruefen

Monatlich:

- Backup-Restore Test in kleinem Scope
- Cronjobs und Scriptversionen reviewen
- Notification-Kanaele testweise pruefen

Quartalsweise:

- Rechte/ACL-Konzept aufraeumen
- Snapshot-/Backup-Strategie aktualisieren
- Dokumentation mit Ist-Stand abgleichen

---

### Aus dem Bereich: 71. Glossar in Betriebssprache

- **UGOS**: Betriebssystem der UGREEN NAS.
- **Watcher**: Laufender Pruefprozess mit Alarmausgabe.
- **Daily Report**: Tägliche Zusammenfassung.
- **Cron**: Zeitgesteuerte Jobausfuehrung.
- **SMART**: Laufwerksdiagnose.
- **mdcheck**: RAID-Pruefmechanismus.
- **NUT**: UPS-Managementdienst.
- **SMB/NFS**: Dateifreigabeprotokolle.
- **Inspect**: Detaillierte Containerkonfiguration.
- **Snapshot**: Momentaufnahme des Dateisystemzustands.

---

### Aus dem Bereich: 73. Vollworkflow A: Neue NAS komplett aufsetzen

Dieser Workflow beschreibt eine komplette Erstinbetriebnahme inklusive Monitoring und Backup.

Phase 1 - Verbindung:

1. Settings ausfuellen (SSH, User, Auth, Sudo).
2. Verbindung testen.
3. Speichern.

Phase 2 - Sichtbarkeit:

1. Dashboard laden.
2. Health Refresh.
3. Modellanzeige kontrollieren.

Phase 3 - Benachrichtigung:

1. Telegram einrichten (Token/Chat-ID).
2. SMTP einrichten (optional zusaetzlich).
3. Test aus Health senden.

Phase 4 - Betriebsfunktionen:

1. Scripts sichern.
2. Scheduler-Testjob anlegen.
3. Docker-Liste pruefen.
4. Storage/ACL Snapshot erfassen.

Phase 5 - Datensicherung:

1. Backupziel festlegen.
2. Erstbackup starten.
3. Restore im kleinen Scope pruefen.

Phase 6 - Dauerbetrieb:

1. Watcher deployen.
2. Daily Report aktivieren.
3. Wartungsplan nach Kapitel 70 anwenden.

---

### Aus dem Bereich: 74. Vollworkflow B: Stoerung in Produktion strukturiert beheben

Beispiel: Dienste reagieren verzoegert, Last steigt, User melden Ausfaelle.

Schritt 1 - Lagebild:

- Dashboard lesen (CPU, RAM, Netzwerk, Volumes).
- Health Refresh.

Schritt 2 - Eingrenzung:

- Docker Runtime Zustand pruefen.
- Kernservices pruefen.
- RAID/SMART pruefen.

Schritt 3 - Verifikation:

- Bei Dockerproblemen: Logs + Inspect.
- Bei Storageproblemen: Top20 + Volumes + Shares.
- Bei Skriptproblemen: letzte Cronjobs, Testlauf manuell.

Schritt 4 - Korrektur:

- Nur eine Aenderung gleichzeitig.
- Nach jeder Aenderung direkte Wirkung pruefen.

Schritt 5 - Absicherung:

- Snapshot/Backup nach Stabilisierung.
- Ursache kurz dokumentieren (intern oder im Changelog).

Dieser Ablauf verhindert Aktionismus und reduziert Sekundaerfehler.

---

### Aus dem Bereich: 75. Vollworkflow C: Geplante Wartung ohne Ausfallueberraschung

Vorbereitung:

1. Wartungsfenster definieren.
2. Betroffene Dienste/Container erfassen.
3. Backup/Snapshot erstellen.

Durchfuehrung:

1. Docker selektiv aktualisieren.
2. Scripts/Cronjobs pruefen.
3. Rechteanpassungen nur gezielt.
4. Health nach jedem grossen Schritt aktualisieren.

Abnahme:

1. Kernfunktionstest (Usersicht).
2. Telegram/E-Mail Testnachricht.
3. Performance baseline gegenchecken.

Nacharbeit:

1. offene Punkte notieren.
2. naechstes Wartungsfenster vorbereiten.

---

---

## 22. Abschluss

### Aus dem Bereich: 21. Schluss

Dieses Handbuch ist als vollständige Bediengrundlage für die aktuelle App gedacht.  
Wenn du die beschriebenen Reihenfolgen nutzt und pro Bereich mit den jeweiligen Sicherheitsregeln arbeitest, kannst du die App stabil und kontrolliert produktiv einsetzen.

---

### Aus dem Bereich: 38. Endhinweis

Diese Referenz ist absichtlich vollständig und pro Bereich konkret formuliert.  
Wenn du sie als Arbeitsablauf verwendest, lässt sich die App stabil und reproduzierbar betreiben.

---

### Aus dem Bereich: 57. Abschluss

Dieses Handbuch bildet die aktuelle UI und Funktionslogik ab und beschreibt die App als vollständigen Betriebsworkflow.  
Nutze es als Referenz beim Arbeiten, nicht nur im Fehlerfall. So bleiben Bedienung und Änderungen nachvollziehbar und stabil.

---

### Aus dem Bereich: 72. Schlusswort

Die App ist als Betriebszentrale konzipiert: konfigurieren, pruefen, aendern, verifizieren.  
Dieses Handbuch ist deshalb nicht kurz gehalten, sondern als vollstaendige Arbeitsreferenz geschrieben.  
Wenn du die beschriebenen Ablaeufe konsequent anwendest, bekommst du reproduzierbare Ergebnisse, weniger Ausfaelle und deutlich schnellere Fehlersuche.

---

---
