# Private Ablage für mitgelieferte root-Helfer

Root-Eigentum einer Datei schützt nicht vor ihrem Austausch, wenn ein anderer
Benutzer das Elternverzeichnis verändern darf. Die Anwendung legte mitgelieferte
root-Runner und Konfigurationen bislang unter gemeinsam genutzten Pfaden ab.
Ein tatsächlicher Schreibzugriff anderer Benutzer unter UGOS wurde nicht gemessen;
der Befund beschreibt die fehlende Schutzprüfung im Code.

Die mitgelieferten Backup-, Skriptbenachrichtigungs-, Wächter- und Tagesbericht-
Helfer sowie ihre Standardkonfigurationen verwenden jetzt
`/var/lib/ugreen-nas-admin`. Auch die geplante Backup-JSON und der Standardzustand
des Wächters liegen dort. Benutzer-Skripte und Backup-Archive werden nicht verschoben.

Vor dem privilegierten Schreiben öffnet der Writer die Komponenten von `/` bis
zum privaten Ordner mit `O_DIRECTORY|O_NOFOLLOW` und prüft die geöffneten Handles:

- Systemeltern müssen root gehören und dürfen für Gruppe/Andere nicht schreibbar sein.
- Nur der neue Anwendungsordner darf erstellt werden, mit Modus 0700. Ein vorhandener
  Ordner muss root gehören und darf Gruppe/Anderen keinerlei Rechte geben.
- Symlinks, fehlende Systemeltern und unsichere bestehende Rechte führen zum Fehler.
  Es gibt keine automatische Rechtekorrektur, kein rekursives chmod/chown.
- Danach veröffentlicht der Writer den Inhalt als neuen root-Inode atomar.
  Scheitert das Benachrichtigungs-Deployment, wird kein neuer Host-/Docker-Cron-Job gespeichert.

## Kontrollierte Umstellung

1. Aktualisierte Anwendung verwenden. Alle Aktionen bleiben ausdrückliche Speicher-/Deploy-Aktionen.
2. **Backups:** Zeitpläne laden und prüfen, dann erneut synchronisieren. Der Import
   liest zuerst die private JSON. Nur wenn sie fehlt, wird die bisherige JSON unter
   dem gewählten Volume eingelesen. Ein Lesefehler aktiviert keine alte Ersatzdatei.
   Beim Synchronisieren werden die markierten Backup-Cron-Blöcke auf den neuen Pfad umgestellt.
3. **Skriptbenachrichtigungen:** Konfiguration synchronisieren und bestehende Host-/
   Docker-Zeitpläne jeweils erneut speichern. Andere alte Cron-Zeilen werden nicht
   automatisch umgeschrieben. Die aufgerufenen Benutzer-Skripte brauchen weiterhin
   separat geprüfte Eigentümer und Zugriffsrechte.
4. **Wächter/Tagesbericht:** Erneut bereitstellen und vorhandene manuell verwaltete
   Cron-Einträge anhand des neuen Pfadhinweises ersetzen. Alte und neue Einträge
   nicht parallel betreiben. Der private Wächterzustand beginnt ohne automatische
   Übernahme des alten Zustands; eine erste Benachrichtigung kann erneut erscheinen.
5. Alte gemeinsame Dateien werden nicht automatisch gelöscht. Insbesondere alte
   Konfigurationen mit Zugangsdaten und noch darauf verweisende Cron-Zeilen nach
   erfolgreicher Umstellung gezielt prüfen. Keine pauschale Verzeichnisbereinigung.

Ein unverändertes altes Cron-Kommando bleibt unverändert gefährdet, bis es gezielt
umgestellt wird. Nur das Installieren der PC-Anwendung führt keine Migration auf dem NAS aus.

## Testgrenzen

23 Offline-Tests auf dem eigenständigen PR-Branch: 10 zur atomaren Veröffentlichung
und 13 zu privaten Verzeichnissen, Import/Synchronisierung und Deployment-Abbruch.
Die Linux-Verzeichnishandles und POSIX-Eigentümer/-Rechte sind simuliert; kein echtes
sudo, kein SSH und keine NAS-Änderung. UGOS-ACLs, Persistenz über Firmwareupdates und
die Verfügbarkeit/sichere Beschreibbarkeit von `/var/lib` sind noch zu validieren.

Der allgemeine Writer schützt andere frei gewählte Zielverzeichnisse damit nicht
automatisch. Explizite alternative Konfigurations-/Zustandspfade der Helfer sowie
Benutzer-Skripte bleiben Admin-Verantwortung. Die mehrteilige Veröffentlichung von
Runner, JSON und Cron ist weiterhin keine Transaktion.
