# Bestehende Archive bleiben erhalten

Die bisherige automatische Bereinigung behielt nach jedem erfolgreichen Backup
nur zwei Dateien mit demselben Präfix. Dieses Präfix beschreibt aber nur die Art
der Sicherung. Beispielsweise verwenden unterschiedliche Jobs vom Typ
„Docker + Skripte“ sowie manuelle Sicherungen denselben Tag `docker_scripts`.
Die Bereinigung konnte dadurch die letzten Sicherungen eines anderen Jobs oder
passend benannte fremde Archive entfernen. Sie hatte kein Besitz-/Jobregister.

Diese Korrektur entfernt die automatische präfixbasierte Löschung sowohl im
manuellen Ablauf als auch im geplanten Python-Runner. Beide verwenden inzwischen
dieselbe Python-Implementierung. Bestehende Archive werden
auch nach erfolgreichen und gleichzeitig laufenden Sicherungen nicht gelöscht.
Der ausdrückliche Schalter zum Entfernen der gerade auf den PC übertragenen
NAS-Datei bleibt eine separate Benutzerentscheidung.

## Geändertes Verhalten

Es gibt vorerst **keine automatische Begrenzung auf zwei Archive**. Alte
Sicherungen und freien Speicherplatz müssen Betreiber manuell verwalten.
Die Oberfläche weist darauf beim Öffnen des Backup-Tabs, vor manuellen Backups
und bei der Zeitplansynchronisierung hin; der Runner meldet es im Laufprotokoll.
Ohne manuelle Aufbewahrung können Archive den Ziel-Datenträger füllen.

Bereits auf einem NAS installierte Runner ändern sich durch dieses Quellcode-PR
nicht von selbst. Erst die Synchronisierung aus einer entsprechend aktualisierten
Anwendung überträgt den neuen Runner. Bestehende Archive werden nicht migriert.

Eine spätere automatische Aufbewahrung benötigt ein verlässliches Job-/Archiv-
Register, eine Sperre für parallele Änderungen, eine explizite Behandlung alter
Archive und Tests gegen fehlende Mounts sowie fremde Dateien. Ein genauerer
Dateinamensfilter allein ersetzt diese Zuordnung nicht.

## Prüfung und Grenzen

Die Korrektur ergänzt die Fehlerbehandlung und temporären Archive in PR #5.
Acht Backup-Tests bestehen gemeinsam: Fehler-/Abbruchfälle, erfolgreiche
wiederholte geplante Läufe sowie vier gleichzeitig gestartete manuelle Läufe.
Alle Inhalte sind künstlich; tar ist ein Stub. Fremde und alte Archive bleiben
bytegleich. Das bestätigt keine konsistenten Live-Datenbank-Backups oder Restores.

Fehlende Teilquellen und ausgefallene Mounts behandelt die ergänzende
[Quellen-/Mountprüfung](BACKUP_SOURCE_MOUNTS_DE.md). Vollständige Restore-Zielgrenzen
und gegenseitige Beeinflussung beim Lesen sich ändernder Quelldaten bleiben offen.
