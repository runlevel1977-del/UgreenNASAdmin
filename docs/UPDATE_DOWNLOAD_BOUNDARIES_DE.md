# Downloadgrenzen zusätzlich zur Installersignatur

Der vorhandene Ed25519-Signaturcheck bleibt die Voraussetzung zum Starten des
Installers. Dieser PR ergänzt die davor liegenden Dateischreib- und Downloadgrenzen:

- Installernamen müssen flache `UgreenNASAdmin_setup_<Version>.exe`-Namen sein.
  Ein Name aus Release-Metadaten darf keine beliebigen lokalen Pfade auswählen.
- Jeder Updateversuch verwendet ein eigenes zufälliges Unterverzeichnis.
- Der erste Download muss zum konfigurierten GitHub-Repository gehören.
  Weiterleitungen werden vor der Folgeanfrage auf HTTPS und bekannte
  GitHub-Downloadhosts begrenzt; Benutzerinformationen und fremde Ports sind verboten.
- Die tatsächliche Länge muss zu den Release-Metadaten und einem vorhandenen
  Content-Length passen. Installer sind auf 512 MiB, Signaturen auf 4096 Byte begrenzt.
- Downloads werden in einer eigenen temporären Datei geschrieben. Fehler und
  Abbruch entfernen nur diese Datei; ein vorhandenes Ziel bleibt erhalten.

Neun Offline-Tests verwenden künstliche HTTP-Antworten und lokale Testdateien.
Kein Installer und kein Updateprozess wurde gestartet. Die bestehende
Signaturprüfung wird durch Größenprüfung und GitHub-Digest nicht ersetzt.

Die Beschränkung auf GitHub-Hosts muss bei Änderungen der GitHub-Auslieferung
gegebenenfalls angepasst werden. Es gibt keine Zusicherung eines vollständigen
reproduzierbaren EXE-Builds. Zusätzlich ist jetzt <Installer>.release.json erforderlich: Ed25519 bindet
Produkt, Version, Dateiname, Größe, SHA-256 und Quellencommit gemeinsam.
Die signierte Version muss zum angebotenen Release passen und strikt neuer
als die laufende Anwendung sein. Alte signierte Installer mit gefälschter
neuer Versionsangabe werden abgewiesen. Fehlende/defekte Metadaten führen
zum Abbruch; ein Fallback auf die alte Hash-Signatur würde den Schutz umgehen.

tools/sign_release_asset.py erzeugt sowohl die bisherige .sig für alte Clients
als auch die neuen Metadaten aus einem sauberen Quellencheckout. Beide
Begleitdateien müssen zusammen mit dem Installer veröffentlicht werden.
Bestehende Releases ohne Metadaten können von neuen Clients nicht automatisch
installiert werden. Alte Clients erhalten diesen zusätzlichen Schutz erst
nach Installation der korrigierten Version.

Der Quellencommit ist eine signierte Aussage des Herausgebers, kein Beweis
eines reproduzierbaren Builds. Ein kompromittierter Signierschlüssel, ein
manuell gestarteter fremder Installer oder manipulierte lokale App-Dateien
werden dadurch nicht abgesichert. Ein früher noch nicht installierter,
legitim signierter Zwischenstand oberhalb der lokalen Version bleibt gültig;
Ablaufzeiten und ein unabhängiger Aktualitätsdienst sind nicht implementiert.
Neun zusätzliche Offline-Tests prüfen Manipulation, Replay, falsche Schlüssel,
Dateizuordnung, strikte Versionsformate und kaputte Metadaten.
