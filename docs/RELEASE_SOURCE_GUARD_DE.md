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

## Überprüfbarer Build-Ablauf

Das neue tools/reproducible_release.py stellt drei Schritte bereit:

1. In einer dedizierten, bereits eingerichteten Windows-Buildumgebung:
   python tools/reproducible_release.py lock --iscc C:\Pfad\ISCC.exe
   erzeugt packaging/build-environment.lock.json und
   packaging/requirements-build.lock.txt. Alle dort installierten Distributionen,
   einschließlich transitiver Abhängigkeiten, erhalten genaue Versionspins.
   Python-Version, Plattform, Architektur, Python-EXE-Hash und ISCC-Hash werden
   festgehalten. Beide Dateien prüfen und committen; sie dürfen nicht während
   des eigentlichen Builds neu erzeugt werden. Kein Paket wird vom Werkzeug
   installiert. Generische Mindestversionen in requirements.txt bleiben nur für
   Entwicklungsumgebungen bestehen. Die Pins sind Versionspins, keine Wheel-Hashes.
2. Mit derselben Umgebung:
   python tools/reproducible_release.py build --iscc C:\Pfad\ISCC.exe --output release/build-a
   exportiert ausschließlich Git-Quellen in einen frischen temporären Ordner,
   prüft die Umgebung gegen den committed Lock und führt pip check, PyInstaller
   sowie Inno Setup aus. PYTHONHASHSEED und SOURCE_DATE_EPOCH sind festgelegt;
   PYTHONPATH wird entfernt, User-Site-Packages werden deaktiviert. Icons werden
   aus Git übernommen. Nach dem Build werden Quellen und Umgebung erneut
   verglichen. BUILD_MANIFEST.json enthält Quellen-, Werkzeug-, Paket- und
   SHA-256-Nachweise für sämtliche erzeugten Dateien. Vorhandene Buildordner
   werden nicht überschrieben. Der öffentliche Sync nimmt auch diese Werkzeuge
   und beide Lockdateien mit.
3. In einer separat eingerichteten Umgebung aus denselben Pins erneut bauen:
   python tools/reproducible_release.py compare release/build-a release/build-b
   bestätigt nur dann Übereinstimmung, wenn die verzeichneten Eingaben und alle
   tatsächlichen Ausgabebytes identisch sind. Abweichungen werden als Fehler
   gemeldet; Zeitstempel, Pfade, Compiler-DLLs oder andere Umgebungsunterschiede
   können weiterhin unterschiedliche Builds verursachen.

Der ZIP-Packer verlangt jetzt --build-dir release/build-a. Er prüft Manifest,
Quellencommit und die tatsächlichen Artefakthashes und legt BUILD_MANIFEST.json
bei. Der frühere direkte Weg aus einem beliebigen dist-Ordner wird abgewiesen.
Danach eine Kopie des Installers mit tools/sign_release_asset.py signieren und
EXE sowie .sig und (mit PR #21) .release.json zusammen veröffentlichen. Den
vermessenen Buildordner unverändert aufbewahren; zusätzliche Dateien darin
führen beim Vergleich/Packen absichtlich zum Abbruch.

Acht zusätzliche Offline-Tests prüfen vollständigen synthetischen Build-Ablauf,
Eingabeabweichungen, manipulierbare Outputs, Versionspins und Binärvergleiche.
Es wurden keine Buildwerkzeuge installiert und keine realen EXEs gebaut.

## Noch vom Maintainer auszuführen

Die echte Release-Umgebung muss erfasst und ihr Lock committet werden; hier
wurde ausdrücklich kein erfundener Lock aus unvollständigen Release-Metadaten
angelegt. Danach beide Windows-Builds ausführen und vergleichen. Erst ein
übereinstimmender unabhängiger Build ist ein Reproduzierbarkeitsnachweis.
Das Manifest allein ist eine überprüfbare Aufzeichnung, keine unabhängige
Attestation. Auch die signierte Commit-Aussage aus PR #21 ersetzt den Vergleich
nicht. Ein gehärteter CI-Dienst mit signierten Attestationen bleibt optionaler
weiterer Ausbau; Schlüssel gehören nicht ins öffentliche Repository.

Den schon veröffentlichten falsch zugeordneten v23.8.57-Tag verändert dieser
PR nicht. Für die nächste Version einen neuen, korrekten Tag auf den geprüften
Release-Commit setzen; die bisherige Fehlzuordnung in den Release Notes offen
benennen. Ein bestehender falscher Tag stoppt diesen Build-/Packablauf.

Die Dateinamensprüfung erkennt bekannte Laufzeitdateien, nicht beliebige unter
anderen Namen abgelegte Geheimnisse in einer Portable-Ausgabe.
