# Vorhandene Dateien bei Upload-Abbruch erhalten

Die bisherige UGOS-Vorbereitung führte vor einer Übertragung `rm -f`, `touch`
und `chown` am endgültigen Ziel aus. Zusätzlich öffneten SFTP und SSH-cat das
endgültige Ziel direkt zum Überschreiben. Bereits ein späterer Übertragungsfehler
konnte deshalb die vorherige Datei zerstören.

Alle Datei-Uploads der Warteschlange und der bisherige SSH-cat-Weg verwenden
jetzt einen gemeinsamen Empfänger. Er benötigt wie die privilegierte
Upload-Vorbereitung sudo und `/usr/bin/python3`. Er öffnet die Zielkomponenten
ohne Symlink-Folgen, legt im Zielverzeichnis eine zufällige private
Zwischenablage mit 0700 an und schreibt dort eine neue Datei mit 0600.
Erst bei vollständiger Übertragung, passender Größe und SHA-256 sowie
unverändertem Ziel wird die Datei atomar veröffentlicht. Der SHA-256 kommt
zusammen mit dem Inhalt über SSH-Standardeingabe, nicht über Prozessargumente.

Bestehende UID/GID und normale Modusbits bleiben erhalten; neue Dateien gehören
dem SSH-Benutzer mit dessen tatsächlicher primärer Gruppe und erhalten 0600.
Vorhandene Ziel-Symlinks, Hardlinks und Spezialdateien werden abgewiesen.
Ein geschlossener Kanal führt zum Fehler statt zu einer endlosen Sendeschleife.
Die vorherige rm/touch-Vorbereitung verändert das Ziel nicht mehr.

Sechs Offline-Tests mit künstlichen Dateien prüfen erfolgreiche, leere,
unvollständige, beschädigte und zu lange Übertragungen, beide sudo-Eingabevarianten
und die Aufrufer. Lokale Dateischreibvorgänge sind real; Linux-dir_fd, Eigentümer
und Modusaufrufe werden auf Windows simuliert. Kein NAS-Upload wurde ausgeführt.

Grenzen: Ein atomarer Inode-Ersatz übernimmt individuelle ACLs/xattrs nicht
automatisch. Das muss insbesondere auf UGOS vor Übernahme abgenommen werden.
Gleichzeitige externe Schreiber sind zu vermeiden; die abschließende
Identitätsprüfung ist keine systemweite Sperre. Für neue Uploads ist jetzt
auch bei einem sonst direkt beschreibbaren Ziel sudo erforderlich. Platz für
alte und neue Dateiversion muss bis zur Veröffentlichung verfügbar sein.
