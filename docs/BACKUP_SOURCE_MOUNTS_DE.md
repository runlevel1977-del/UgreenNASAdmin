# Backups an vorhandene Quellen und Dateisysteme binden

Eine vorhandene Verzeichnisstruktur beweist nicht, dass das erwartete Volume noch
eingehängt ist. Bisher wurden fehlende Teilquellen übersprungen; ein fehlendes
Zielverzeichnis konnte auf dem darunterliegenden Dateisystem neu angelegt werden.

Manuelle Backups und Cron verwenden jetzt dieselbe mitgelieferte Python-Implementierung:

- Vor dem Anlegen des Archivverzeichnisses müssen Zielmount und Pflichtquellen
  vorhanden sein. `/volumeN` wird anhand von `/proc/self/mountinfo` erkannt;
  eine andere Volume-Auswahl wird nicht still als Ersatz verwendet.
- Die möglichen Benutzerverzeichnisse unter `/home` und `/volumeN/homes` sind
  nur bei der ersten Ermittlung optional. Es muss mindestens eine Quelle bleiben.
- Bei der ausdrücklichen Zeitplansynchronisierung wird die tatsächlich gewählte
  Quellenliste mit Mountpunkt, Dateisystem, Subvolume-Wurzel und Quelle gespeichert.
  Für Blockgeräte wird `findmnt --noheadings --output UUID --mountpoint …` verwendet.
  Fehlende oder mehrdeutige Identität führt zum Abbruch vor der Veröffentlichung.
- Folgeläufe müssen diesen Stand erfüllen. Ein verschwundenes Quellvolume und
  eine andere Dateisystem-UUID werden abgewiesen. Geänderte `/dev/sdX`-Namen nach
  einem Neustart sind bei gleicher UUID erlaubt. „Alle Volumes“ umfasst bei einem
  gespeicherten Job die beim Einrichten erfassten Volumes; neue kommen nicht
  unbemerkt hinzu.
- Nach tar werden Quellen, Identität und Mount-IDs erneut geprüft. Ein erkannter
  Mountwechsel oder tar-Fehler veröffentlicht keine erfolgreiche Sicherung.

## Umstellung

Vorhandene Jobs aus dem NAS laden, Quellen und Ziel kontrollieren, dann mit der
aktualisierten Anwendung erneut synchronisieren. Der neue Cron-Runner verweigert
alte Jobs ohne Quellen-/Mountnachweis mit einer Aufforderung zur Synchronisierung.
Nur die Runner-Datei auszutauschen reicht deshalb nicht.

Wenn ein Datenträger absichtlich ersetzt oder die Auswahl „Alle Volumes“ erweitert
wird, den betroffenen Job nach Kontrolle der Auswahl neu anlegen. Ein unveränderter
Job darf beim erneuten Speichern eine abweichende Identität nicht still übernehmen.
Nicht erreichbare UUIDs, nicht direkt eingehängte Zielordner und Symlink-Aliase
werden konservativ abgelehnt; den tatsächlichen Mountpfad auswählen.

## Prüfung und Grenzen

18 zusätzliche Offline-Tests prüfen die Auswahl- und Mountlogik; Linux-Mountdaten,
UUID-Abfragen und tar-Erstellung sind simuliert. Zusammen mit den bisherigen
Backup-/Restore-Tests bestehen auf dem eigenständigen PR-Branch 33 Tests.
Die vorhandene Python- und findmnt-Version auf UGOS wurde nicht ausgeführt.

Die Prüfungen vor und nach tar sind **keine atomare Sperre gegen Mountwechsel**.
Ein Aushängen während des Schreibens kann weiterhin Zwischenzustände erzeugen.
Verzeichnisaustausch im beschreibbaren Archivziel, verschachtelte Mounts unter
einer Quelle, geklonte UUIDs und gleichzeitig veränderte Quelldaten benötigen
weitere Behandlung. Das Archiv ist kein konsistenter Datenbank-Snapshot.
Manuelle Läufe binden die Identität nur für diesen Lauf, nicht über mehrere Starts.

Die private Ablage von Runner und Job-JSON ergänzt PR #8; die vollständige
Cron-Eingabeprüfung ergänzt PR #10. Beim Zusammenführen müssen alle drei Prüfungen
erhalten bleiben: Cron-Validierung, Quellenaufnahme vor Schreibzugriffen und
private Veröffentlichung. Der gemeinsame Referenzbranch im Fork heißt
`review/security-round3-integration`.

Technische Referenzen: [Linux mountinfo](https://man7.org/linux/man-pages/man5/proc_pid_mountinfo.5.html),
[findmnt](https://man7.org/linux/man-pages/man8/findmnt.8.html).
