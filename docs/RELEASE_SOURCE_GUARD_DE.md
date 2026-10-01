# Veröffentlichte Quellen und Release-Zuordnung prüfen

Der bisherige ZIP-Packer kopierte den lokalen Anwendungsordner mit einer
unvollständigen Ausschlussliste. Beispielsweise war `qnap_smb_prefs.json` zwar
in Git ausgeschlossen, aber nicht in dieser Kopierliste. Auch im vollständig
kopierten Portable-Ordner konnten nach einem App-Start lokale Einstellungen liegen.

Der Quellteil kommt jetzt ausschließlich aus regulären Git-Blobs des geprüften
HEAD, einschließlich Tests, Buildwerkzeugen und Installerskripten. Lokale,
ignorierte Dateien gelangen nicht in diesen Quellteil. Ein
`SOURCE_MANIFEST.json` nennt Commit, Version, Tagstatus und SHA-256 jedes
exportierten Quellfiles. Bekannte lokale Konfigurations-/Geheimnisdateien und
Symlinks im Portable-Ordner führen zum Abbruch.

Ein bereits vorhandener Versionstag muss auf denselben Commit zeigen. Ein noch
nicht angelegter Tag ist erlaubt und wird ausdrücklich so im Manifest vermerkt;
vor Veröffentlichung muss der Maintainer ihn auf den verzeichneten Commit setzen.
Geänderte versionierte Dateien verhindern das Packen. Der Packer ersetzt ein
bestehendes Release-ZIP erst nach erfolgreicher Erstellung des neuen Archivs.
Der bestehende falsch zugeordnete Tag wird durch diesen PR nicht verschoben.

Das Buildskript beendet keine laufende Anwendung mehr per pauschalem taskkill.
Bei gesperrten Dateien muss der Benutzer die betreffende App selbst schließen.
Die pauschale Empfehlung einer Defender-Ausnahme entfällt.
Das vorhandene `tools/split_ugreen_manager.py` war als UTF-16 gespeichert und
deshalb für Python nicht parsebar. Es wird ohne Änderung des dekodierten
Quelltexts als UTF-8 gespeichert; das Werkzeug wird dabei nicht ausgeführt.

Sieben Offline-Tests prüfen Tagzuordnung, geänderte Quellen, bekannte private
Dateien, Git-Export, Hashmanifest und das Verhalten bei gesperrter EXE. Kein
Builder, Installer oder ausführbares Release wurde gestartet.

Das Quellenmanifest ist kein signierter Buildnachweis und belegt nicht, dass
die beigepackte EXE aus genau diesem Commit gebaut wurde. Ein vollständiges
Buildmanifest mit aufgelösten Abhängigkeiten, Buildwerkzeugversionen und
reproduzierbarem Binärvergleich bleibt eine Aufgabe des Release-Prozesses.
Die Dateinamensprüfung erkennt bekannte Laufzeitdateien, nicht beliebige unter
anderen Namen abgelegte Geheimnisse in einer Portable-Ausgabe.
