# Archivgrenzen bei Restore und ZIP-Upload

Restore und gebündelte ZIP-Uploads verwenden denselben mitgelieferten
Python-Helfer. Die bisherige ZIP-Kette versuchte nach jedem Fehler den nächsten
Entpacker, auch wenn der erste das Ziel bereits teilweise verändert hatte.
Jetzt gibt es genau einen Versuch; der ursprüngliche Fehler bleibt sichtbar.

Vor der Zielbearbeitung werden alle Archivnamen und Typen geprüft. Absolute
Pfade, übergeordnete Pfade, doppelte Ziele, Datei-/Verzeichniskollisionen,
Links, Spezialdateien, Sparse-TAR-Einträge und verschlüsselte ZIPs führen zum
Abbruch. Vorhandene Zielverknüpfungen und mehrfach verlinkte Zieldateien werden
ebenfalls abgewiesen. ZIPs aus dem normalen lokalen Datei-Upload bleiben
unterstützt; Fehler werden nicht durch eine andere Entpackmethode umgangen.

Die Zielkomponenten werden ohne Symlink-Folgen geöffnet. Unterpfade und
Dateiveröffentlichungen sind an offene Verzeichnis-Handles gebunden. Eine Datei
wird erst nach vollständigem Lesen und Schreiben atomar ersetzt. Ein CRC-,
Lese- oder Schreibfehler erhält die vorherige Version dieser Datei.

## Bewusste Kompatibilitätsgrenze

Das ist eine konservative Datenwiederherstellung für reguläre Dateien und
Verzeichnisse. Backups mit Symlinks, Hardlinks oder Spezialdateien werden vor
der Zielbearbeitung vollständig abgewiesen, nicht still unvollständig entpackt.
Für solche Backups ist ein gesondert geprüftes Restore-Verfahren nötig.
Der Bestätigungsdialog benennt diese Einschränkung auf Deutsch und Englisch.

Bei TAR werden numerische UID/GID, normale Modusbits und Änderungszeiten
wiederhergestellt. Setuid/Setgid/Sticky-Bits, ACLs und xattrs werden nicht
wiederhergestellt. ZIP-Ersatzdateien behalten vorhandene UID/GID und normale
Modusbits; neue Dateien erhalten 0644. Neue ZIP-Verzeichnisse erhalten 0755,
neue TAR-Verzeichnisse starten mit 0700;
explizite TAR-Verzeichnismetadaten werden nach den Dateien angewendet.

## Verbleibende Grenzen

Es gibt keinen Rollback über das gesamte Archiv. Bei einem späten Fehler können
bereits veröffentlichte Dateien und neu angelegte Verzeichnisse verbleiben.
Atomarer Inode-Ersatz übernimmt keine individuellen ACLs/xattrs einer alten
Zieldatei. Große Archive werden nicht durch eine Speicher-/Entpackquote begrenzt.
Ein anderer privilegierter Prozess kann weiterhin Mounts oder offene
Verzeichnisse verschieben; konkurrierende Zieländerungen sind daher zu vermeiden.

Offline geprüft: künstliche TAR-/ZIP-Indizes, fehlerhafte Namen/Typen,
Zielkonflikte, Abbruch und Erhalt vorhandener Dateien, Befehlsquoting und
sichtbare Restore-Fehler. Lokale Dateiinhalte und Ersetzen werden tatsächlich
ausgeführt; Linux-dir_fd-/Eigentümeraufrufe sind unter Windows simuliert.
Die DXP2800 wurde nur lesend auf Python/API-Verfügbarkeit geprüft: Python
3.11.2, dir_fd und O_NOFOLLOW vorhanden, tarfile.data_filter nicht vorhanden.
Kein Archiv wurde auf dem NAS entpackt.

Vor Übernahme muss der Maintainer die vollständige Extraktion samt Metadaten
und Dateirechten in einer entbehrlichen Linux-/UGOS-Testumgebung abnehmen.
# Ergänzung: Ressourcen und Zusatzmetadaten

Der NAS-Helfer begrenzt vor dem Archivparser seinen virtuellen Adressraum auf
höchstens 1 GiB und CPU-/Wandzeit auf eine Stunde. Ein Archiv darf höchstens
100.000 Einträge, 1 TiB entpackten Inhalt, 256 GiB pro Datei, 4.096 Zeichen pro
Pfad und 64 Pfadebenen enthalten. Vor dem Schreiben wird Platz für den gesamten
entpackten Inhalt plus 512 MiB Reserve verlangt; während des Schreibens wird
freier Platz erneut geprüft. Diese konservativen Standardgrenzen können große
legitime Wiederherstellungen ablehnen; dafür ist ein gesonderter Restoreweg nötig.

TAR wird während der Planung schrittweise gelesen. ZIP muss seinen Index laden;
hier begrenzt zusätzlich das Prozesslimit die Parserallokation. Bei behandelbaren
Zeit-/Schreibfehlern wird nur die eigene Zwischenablage entfernt. SIGKILL oder
Stromverlust können eine private Zwischenablage hinterlassen.

TAR-PAX-Einträge mit ACLs/xattrs sowie vorhandene Zielobjekte mit Zusatzmetadaten
werden vor dem Kopieren abgelehnt, statt diese still zu verlieren. Das ist noch
kein vollständiger ACL-/Systemrestore. UID/GID, gewöhnliche Modi und Zeitstempel
bleiben der unterstützte TAR-Metadatenumfang. Der Restore bleibt pro Datei atomar;
bereits veröffentlichte Dateien werden bei einem späteren Archivfehler nicht
automatisch zurückgerollt. Für einen vollständigen Recovery-Test sind eine
isolierte Zielumgebung und vorherige Snapshots erforderlich.
