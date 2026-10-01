# Restore-Fehler sichtbar melden und temporäre Dateien begrenzen

Der bisherige Fehler-Callback griff verzögert auf die Exception-Variable `e` zu.
Python entfernt diese Bindung nach dem except-Block. Damit konnte die geplante
UI-Fehlermeldung selbst mit `NameError` abbrechen. Der Fehlertext wird jetzt vor
dem Einplanen kopiert; zusätzlich zählt der tatsächliche SSH-Exitstatus.
Ein Textmarker im Ergebnis allein macht einen fehlgeschlagenen Restore nicht
mehr erfolgreich.

Die Extraktion läuft genau einmal mit `tar -xf`. Ein bereits teilweise
fehlgeschlagener Lauf wird nicht noch einmal über dasselbe Ziel gestartet.
Diagnosen bleiben im SSH-Fehlerkanal; die vorhersehbare Umleitung nach
`/tmp/.ug_restore_err.$$` entfällt. PC-Uploads verwenden eine exklusiv durch
`mktemp` angelegte temporäre Datei mit einem zufälligen Namen statt Sekunden-
Zeitstempel. Scheitert deren Erstellung, beginnen weder Upload noch Extraktion.

Sieben lokale Tests prüfen echte verzögerte Callbacks, Fehlerstatus, Upload-
Abbruch und Bereinigung. Einer davon führt drei Extraktionen mit vorhandenem
GNU tar 1.35 aus: kleines künstliches TAR, gzip-TAR und ungültige Eingabe.
Alle Ziele liegen in eigens erzeugten temporären Verzeichnissen. SSH, sudo und
die GUI sind simuliert; das NAS wurde nicht angesprochen.

GNU tar erkennt Kompression beim Lesen regulärer Archivdateien automatisch:
[GNU-tar-Dokumentation](https://www.gnu.org/s/tar/manual/html_node/gzip.html).
Die tar-/mktemp-Version des konkreten UGOS-Geräts ist noch nicht geprüft.

**Offen:** Die Extraktion ist weiterhin privilegiert und darf bestehende
Zieldateien überschreiben. Dieser Fix ist keine Prüfung aller Archivpfade,
Symlinks, Hardlinks, Spezialdateien oder Dateirechte und bietet keinen Rollback
nach teilweise erfolgter Extraktion. Dafür ist ein eigenes Restore-Konzept mit
isolierten Linux-Tests erforderlich.
