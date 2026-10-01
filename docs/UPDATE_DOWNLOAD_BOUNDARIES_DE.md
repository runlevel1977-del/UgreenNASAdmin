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
reproduzierbaren EXE-Builds. Die bestehende Signatur bindet den Datei-Hash,
aber keine separat signierte Versions-/Release-Metadatenstruktur.
