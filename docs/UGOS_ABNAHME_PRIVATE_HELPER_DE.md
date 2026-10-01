# UGOS-Abnahme: private Helfer und bestehende Backup-Jobs

Diese Abnahme ist für den Maintainer auf einem entbehrlichen Test-NAS vorgesehen.
Sie wurde hier nicht auf UGOS ausgeführt. Die lokale Prüfung verwendet
künstliche Daten und simulierte privilegierte Systemaufrufe. Ein produktives NAS
ist für die folgenden Fehler- und Migrationstests nicht vorgesehen.

## Festzuhaltender Prüfstand

- Quellbasis `f3ff0ad66b5d42e1787847d5fdd24e44d2551bc2` (23.8.57) plus die
  Korrektur aus PR #16; den tatsächlich getesteten Head und Build-Hash notieren.
- UGOS-Version, Python-Version auf NAS und Client, SSH-Authentisierungsart,
  SFTP-Verfügbarkeit und sudo-umask protokollieren, ohne Zugangsdaten.
- Vor jedem Szenario den Ausgangszustand der Testdateien und Test-Cron-Einträge
  festhalten. Nur künstliche Jobdaten und ein eigens dafür angelegtes Test-Volume
  verwenden. Andere Cron-Einträge müssen erhalten bleiben.

## Abnahme der Änderung aus #16

| Szenario | Aufbau und Aktion | Erwartetes Ergebnis |
|---|---|---|
| Erstbereitstellung | Private Runtime fehlt; sudo-umask 022. Einen gültigen künstlichen Backup-Job synchronisieren. | Verzeichnis `/var/lib/ugreen-nas-admin` entsteht durch den geprüften Schreiber als root:root mit 0700. Runner und Job-JSON werden vor Cron veröffentlicht. Keine Meldung „Unsafe root helper directory“. |
| Erneuter Sync | Sicheres privates Verzeichnis und fremder Test-Cron-Eintrag vorhanden. Job ändern und erneut synchronisieren. | Jobstand und eigener Cron-Eintrag werden aktualisiert; fremder Eintrag bleibt bytegleich. |
| Unsicherer Bestand | Separater Testfall mit privatem Verzeichnis 0755, falschem Eigentümer oder Symlink. | Veröffentlichung bricht ab; keine automatische chmod/chown-Reparatur; Job-JSON und Cron bleiben unverändert. |
| Alter Jobstand | Private Jobdatei fehlt, alte Datei unter dem im UI ausgewählten Volume bei `backup/ugreen_admin/scheduled_backups.json` enthält künstliche Jobs. „Vom NAS laden“. | Jobs erscheinen im UI. Alte Datei bleibt bytegleich; es wird noch nichts veröffentlicht. |
| Vorrang neuer Daten | Alte und private Jobdatei enthalten unterschiedliche gültige Jobs. | „Vom NAS laden“ verwendet ausschließlich den privaten Stand. |
| Fehler beim Lesen | Private Jobdatei existiert, ist aber leer, defekt oder nicht lesbar; alternativ zeigt der Pfad auf eine defekte Verknüpfung. | Fehlermeldung; keine Rückkehr zu alten Jobs; bisher im UI geladene Jobs bleiben erhalten. |
| Beide Dateien fehlen | Weder privater noch bisheriger Jobstand vorhanden. | Leere Liste kann geladen werden; kein vorgetäuschter Lesefehler. |
| Explizite Migration | Nach erfolgreichem Laden des alten Stands bewusst synchronisieren. | Gesamte Jobliste und Quellen werden geprüft; neue JSON unter dem privaten Pfad, neue Cron-Verweise ebenfalls privat. Alte Dateien werden nicht gelöscht. |
| Script-Notify-Fehler | Auf dem Test-NAS Helferbereitstellung gezielt scheitern lassen; je einmal Host- und Docker-Zeitplan speichern. | Fehler wird angezeigt; Zeitplan wird nicht gelesen/überschrieben und kein Erfolg gemeldet. Vorherige Cron-Datei bleibt bytegleich. |
| Andere Helfer | Watch, Daily Report und Script-Notify regulär bereitstellen. | Ausschließlich die vorgesehenen privaten Helferpfade werden verwendet; ein fehlendes `/volume1/scripts` wird für diese Bereitstellung nicht mehr vorsorglich angelegt. Eigene Nutzerskripte bleiben am bisherigen Ort. |

Den SFTP-Staging-Pfad und den Base64-Fallback des atomaren Schreibers separat
prüfen. Ein fehlgeschlagener Upload oder eine Hash-Abweichung darf keine
bestehende Zieldatei ersetzen. Eigentümer, Modus und unveränderte Inhalte anhand
von Metadaten und Hashes kontrollieren. Unter UGOS zusätzlich effektive ACLs
berücksichtigen; Modusbits allein beweisen die Zugriffsgrenzen nicht.

## Ergänzende Abnahme der bereits portierten Korrekturen

Diese Punkte gehen über #16 hinaus und vervollständigen die noch ausstehende
Praxiskontrolle des Sicherheitsstands 23.8.57:

- **SSH:** Erstkontakt mit unabhängig geprüftem Fingerprint bestätigen;
  Folgeverbindung akzeptieren; geänderten Schlüssel und beschädigten lokalen
  Test-Vertrauensspeicher vor Authentisierung abweisen.
- **TLS:** Mit dem unveränderten selbstsignierten NAS-Zertifikat im
  voreingestellten Pinning-Modus anmelden. Ein gekauftes Zertifikat oder ein
  Windows-Zertifikatsimport darf dafür nicht nötig sein. Einen Zertifikatswechsel
  ausschließlich auf dem Testgerät bzw. Test-Endpunkt durchführen und seine
  Ablehnung prüfen. Optionalen CA-Modus separat mit passendem Namen prüfen.
- **Backup:** Kleine künstliche Dateien mit Leerzeichen und Umlauten sichern.
  Bei fehlender/ausgetauschter Quelle, geänderter Mount-Identität, tar-Fehler oder
  vollem Test-Ziel darf kein fertiges Archiv veröffentlicht werden. Bestehende
  Archive müssen erhalten bleiben. Dafür keine produktiven Mounts aushängen.
- **Restore:** Gültiges und abgeschnittenes Testarchiv ausschließlich in ein
  leeres entbehrliches Ziel wiederherstellen. Inhalte/Hashes kontrollieren;
  Fehler müssen als Fehler erscheinen. Bereits extrahierte Dateien können bei
  einem späteren Fehler vorhanden bleiben; ein Rollback wird nicht zugesichert.
- **Upload:** Vorhandene Testordner mit unterschiedlichen Eigentümern nutzen;
  nur neu erzeugte Komponenten dürfen den Upload-Eigentümer erhalten.
- **Tresor:** Auf einem getrennten Client-Testkonto Passwort und Passphrase
  speichern, erneut laden und einen Tresorausfall simulieren. Der Fehler darf
  weder Klartext-Fallback noch stillen Verlust gespeicherter Geheimnisse auslösen.

Keine Disk-Restore-, Mount-Ausfall- oder Rechte-Fehlertests auf produktiven
Datenträgern durchführen. Disk-Images benötigen ein getrenntes entbehrliches
Blockgerät; sie sind nicht Teil eines unkritischen Tests auf einem Produktiv-NAS.

## Ergebnis und Grenzen

Für jeden Fall tatsächliches Ergebnis, Test-Commit, Testdatum und bereinigten
Fehlertext notieren. Erst dann „auf UGOS geprüft“ melden. Logs dürfen keine
Passwörter, Tokens, privaten Schlüssel oder produktiven Dateinamen enthalten.

Bekannte Grenzen: bereits falsch angelegte private Verzeichnisrechte werden
nicht automatisch korrigiert. Die alte Jobdatei wird über die bisherige
Volume-Auswahl gefunden, nicht über alle Volumes gesucht. Die Veröffentlichung
von Runner, JSON und Cron ist jeweils atomar, jedoch keine gemeinsame
Transaktion; parallele Änderungen durch andere Verwaltungsprogramme sind damit
nicht vollständig abgedeckt. Testdaten erst nach Prüfung der exakten Testpfade
gezielt entfernen; dieser Plan löscht oder migriert nichts automatisch.
