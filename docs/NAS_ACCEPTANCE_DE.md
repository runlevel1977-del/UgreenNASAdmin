# Offene Betriebsgrenzen und nachweisbare Abnahme

## Datenarchiv ist kein automatisches Datenbank-Backup

Der manuelle und der zeitgesteuerte Runner prüfen vor und nach tar lesend den
lokalen Docker-Daemon. Überlappen schreibbare Mounts laufender Container die
Quellen, wird kein erfolgreiches Archiv veröffentlicht. Abweichende Docker-
Kontexte werden nicht verwendet. Ist die CLI vorhanden, aber die lokale Prüfung
unmöglich, bricht das Backup ab. Die Abfrage enthält keine Container-Umgebungswerte.

Das ist eine zusätzliche Fehlersperre, kein Konsistenzbeweis: kurze Schreibphasen
zwischen den Prüfungen, Nicht-Docker-Datenbanken, SMB-Schreiber, andere Prozesse
und interne Docker-Schichten sind dadurch nicht vollständig erfasst. Auch ein
stiller Container ist kein Beweis einer korrekt heruntergefahrenen Datenbank.
tar kann einzelne Änderungen erkennen; sein Exitcode 0 beweist keinen gemeinsamen
logischen Stand mehrerer Dateien. Die gespeicherte Mount-Identität ist ausdrücklich
kein Dateisystem-Snapshot.

Vor jedem Lauf müssen abgeschlossene Anwendungsexporte vorliegen oder die
Quellen extern während des gesamten Backups stillgelegt sein. Bei Zeitplänen
gilt das für jeden Termin. Bestätigungsdialoge machen das sichtbar, ersetzen
aber diese Vorbereitung nicht. Die App stoppt keine Container und führt keine
beliebigen Root-Hooks aus. Ausschlussmuster lockern die Docker-Prüfung bewusst
nicht: eine sicherheitsrelevante Interpretation aller tar-Globregeln fehlt.
Gegebenenfalls einen eigenen, unveränderlichen Exportpfad sichern. Alte NAS-
Zeitpläne müssen den aktualisierten Runner durch erneutes Synchronisieren erhalten.

Für PostgreSQL: [File System Level Backup](https://www.postgresql.org/docs/current/backup-file.html).
Für Paperless ist der dokumentierte Export/Import der jeweiligen installierten
Version zu verwenden und auf einer getrennten Testinstanz wiederherzustellen.
Dateien erfolgreich zu entpacken belegt noch keinen funktionierenden Import.

## Abnahmeprotokoll für ein isoliertes Test-NAS

Alle folgenden Live-Ergebnisse sind **offen**, bis der Maintainer sie tatsächlich
ausführt. Nur künstliche Daten und Testkonten einsetzen; Versions-/Commitstand,
UGOS-Version, Dateisystem und anonymisiertes Ergebnis notieren. Keine Produktion
anschließen, um eine fehlende Laborumgebung zu ersetzen.

| Bereich | Versuch | Geforderter Nachweis |
|---|---|---|
| Backup/Restore | Reguläre Dateien, Unicode, Leerzeichen, große Datei und Hardlink sichern; in neues Testziel wiederherstellen | Inhalte/Hashes vollständig; deklarierte Grenzen sichtbar; keine Erfolgsmeldung für abgelehnte Inhalte |
| Abbruch | Später Lesefehler/CRC, voller Testdatenträger, Verbindungsabbruch, SIGKILL | Ursprungsdaten unverändert; Teilzustand nicht als fertige Wiederherstellung ausgewiesen; private Reste erkennbar |
| Konkurrenz | Ziel während Restore anlegen; Datei/ACL während Upload ändern | Fremdes Ziel erhalten; beobachtete Metadatenänderung führt zum Abbruch; verbleibendes Rennfenster dokumentiert |
| Rechte | Übliche UGOS-Freigabe-ACL, user-xattrs, unbekanntes Sicherheitsattribut; Einzel- und ZIP-Upload | Bekannte Rechte erhalten, unbekannte nicht still entfernt; Zugriff zusätzlich als unbeteiligter Nutzer testen |
| Container | Laufender Testcontainer mit Bind-Mount und benanntem Volume; danach sauber stoppen | Überschneidende Schreiber blockieren; vorbereitete stille Quelle sicherbar; kein automatischer Dienststopp |
| Anwendung | Datenbankexport plus zugehörige Dateien auf separater Instanz importieren | Dokumente/Datensätze vollständig, Integritätsprüfung erfolgreich, Wiederanlauf möglich |
| Cron/Mount | Test-USB fehlt/ersetzt, Quelle fehlt, konkurrierendes Synchronisieren | Kein falsches Ziel und keine teilweise aktivierte Generation; alter gültiger Plan erhalten |
| SSH-Profil | Zweite Testsitzung offenhalten; absichtlich unzulässige Test-Konfiguration | Rollback-Timer nachweisbar vorher aktiv; zweite Anmeldung nach Rückfall möglich; keine Produktions-SSH-Konfiguration testen |
| Release | Öffentlicher Tag, Quellen, Build-Manifest, installierte Artefakte vergleichen | Exakter Commit/Version/Hash zusammenpassend; unabhängigen Wiederholungsbuild separat ausweisen |

Ein grüner Windows-Test mit simulierten dir_fd-/ACL-Aufrufen ersetzt diese
Abnahme nicht. Linux-CI prüft native Plattformteile nur soweit die jeweiligen
Tests sie wirklich aufrufen. Übersprungene Tests nicht als bestanden zählen.
Das Protokoll soll jeder entsprechenden PR-Abnahme beigefügt werden.

## Alte Konfigurationskopien und Zugangsdaten

Der Tresor beseitigt keine früheren JSON-Kopien, Archive oder bereits geteilten
Zugangsdaten. Mit der vorhandenen Python-Umgebung gezielt einen eigenen alten
App-/Backupordner lesend prüfen:

```text
python -B tools/secret_inventory.py <ausdruecklich-ausgewaehlter-Ordner>
```

Das Werkzeug zählt bekannte Klartextfelder und Tresorverweise ohne Geheimniswerte
auszugeben. Es untersucht nur bekannte Namen/Felder, keine vollständigen Logs
oder jeden möglichen Speicherort. Für Weitergabe nur anonymisierte Dateiklassen
und Zähler verwenden. `review-plaintext` bedeutet persönliche Nachprüfung, nicht
automatisch ein Datenleck. Benötigte Wiederherstellungsmöglichkeiten erhalten;
anschließend Kopien gezielt bereinigen und tatsächlich offengelegte Passwörter/
Tokens beim jeweiligen Dienst wechseln. Keine pauschale automatische Löschung.

## Noch kein vollständiges App-Audit

Diese Nacharbeit deckt konkrete PR-Ziele und ihre Wechselwirkungen ab. Für
weitere Prüfungen zuerst destruktive Speicheraktionen (Formatieren/Löschen),
Netzwerk-/Dienständerungen mit Aussperrungsrisiko und privilegierte Docker-/
Skriptaktionen priorisieren. Jeweils Eingaben, Rechte, Fehlerpfade, Rücknahme und
unabhängige Bestätigung der Wirkung prüfen. Ohne solche Nachweise keine allgemeine
Sicherheitsfreigabe der App oder der UGOS-Firmware behaupten.
