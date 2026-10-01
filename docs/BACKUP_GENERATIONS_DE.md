# Backup-Synchronisierung als Generation

Runner und Jobliste werden unter neuen, zufälligen Dateinamen im rootprivaten
Verzeichnis geschrieben und synchronisiert. Erst danach aktiviert ein einzelner
atomarer Austausch der Crondatei das zusammengehörige Paar. Bereits laufende Jobs
und Cron-Aufrufe mit der bisherigen Befehlszeile behalten ihre bisherigen Dateien.

Eine NAS-seitige Dateisperre serialisiert parallele Generationstransaktionen.
Der Inhalt der Crondatei muss vor der Vorbereitung **und** unmittelbar vor der
Aktivierung mit dem zuvor gelesenen Stand übereinstimmen. Anderenfalls wird
abgebrochen. Nach „Von NAS laden“ erkennt die App außerdem Änderungen seit dem
Laden und verlangt erneutes Laden. Fremde Cronzeilen bleiben erhalten.

Die aktive Jobliste wird aus der Generationsmarkierung der Crondatei ermittelt.
Eine fehlende aktive Datei führt zum Fehler, niemals zum Rückgriff auf alte Jobs.
Ohne Generationsmarkierung bleibt die bisherige Migration privater/älterer
Jobdateien möglich. Andere, ältere App-Versionen verstehen diese Markierung nicht
und dürfen danach nicht zum Bearbeiten dieser Zeitpläne verwendet werden.

Schreib-, Versions- und Renamefehler vor der Aktivierung entfernen nur die in
dieser Transaktion angelegten Dateien. Nach erfolgreichem Rename bleibt das Paar
auch bei einem anschließenden fsync-Fehler erhalten. Bei Verbindungsabbruch zuerst
„Von NAS laden“, um den tatsächlich aktiven Stand festzustellen.

Alte Generationen werden absichtlich nicht automatisch gelöscht: Cron kann noch
eine alte Befehlszeile starten, und ein Job kann länger laufen. Ein späteres
Aufräumen benötigt eine gesonderte Prüfung auf laufende Jobs. Nicht kooperierende
externe Croneditoren lassen sich durch die App-Sperre nicht vollständig ausschließen;
es bleibt ein enges Rennen zwischen abschließendem Vergleich und Rename. Die
Generation selbst bleibt auch dann vollständig. Crashverwaiste Vorbereitungspaare
können Speicher belegen, werden aber nicht aktiviert.

Offline geprüft: echte lokale Dateiinhalte/Renames, simulierte POSIX-Deskriptoren,
Sperrkonflikt, veralteter Stand, externes Schreiben während der Vorbereitung,
voller Datenträger, Renamefehler und Fehler nach Aktivierung. Kein NAS-Schreibtest.
