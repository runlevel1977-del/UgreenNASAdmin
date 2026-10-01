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
Modusbits; neue Dateien erhalten 0644. Neue Verzeichnisse starten mit 0700;
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
