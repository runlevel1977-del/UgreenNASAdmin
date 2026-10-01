# Laufende Sicherheitsprüfung und Release-Grenzen

Die CI führt die Offline-Regressionssuite auf Windows und Linux aus. Anschließend
prüft pip-audit die konkret installierten Python-Abhängigkeiten und, sobald
vorhanden, die vom Maintainer festgeschriebene Release-Umgebung. Ein Schwachstellenfund
oder fehlgeschlagener Audit bleibt ein Fehler; es gibt keine globale Ignore-Liste.
Die CycloneDX-Berichte werden als CI-Artefakte aufbewahrt. Das ist keine Prüfung
eines bereits veröffentlichten Installers mit anderen eingebetteten Versionen.

Die Workflows verwenden `pull_request`, ausschließlich Leserechte, keine Secrets,
keine selbst betriebenen Runner und auf vollständige Commit-IDs festgelegte Actions.
Sie installieren nur auf den kurzlebigen GitHub-Runnern. Fork-PRs können zunächst
eine Freigabe durch den Maintainer benötigen.
Grundlage: [GitHub Secure use](https://docs.github.com/en/actions/reference/security/secure-use)
und [PyPA pip-audit](https://github.com/pypa/pip-audit).

Der reproduzierbare Build erzeugt zusätzlich `NATIVE_INVENTORY.json`: sämtliche
DLL-, PYD- und EXE-Dateien mit SHA-256, Größe und auslesbarer Windows-Dateiversion,
zusammen mit der Python-Paketliste. Fehlende Versionsangaben sind ausdrücklich
offene Prüfpunkte. Ein vollständiges Dateiinventar identifiziert nicht automatisch
statisch eingebettete OpenSSL-, Tcl/Tk-, SQLite- oder andere C-Komponenten. Diese
muss der Maintainer anhand der tatsächlich verwendeten Wheels/Runtime zuordnen und
gegen Hersteller-Advisories prüfen. Es wurde kein Installer ausgeführt.

Der Release-Export sperrt nun auch den tatsächlichen Laufzeitnamen `transfer.log`
und bekannte Konfigurations-/Logkopien (`.bak`, `.old`, nummerierte Varianten).
Unbekannt benannte private Dateien verlangen weiterhin einen sauberen Buildbaum.

## Signierschlüssel

Der aktuelle Client vertraut einem eingebetteten öffentlichen Schlüssel. Einen
unabhängigen Online-Widerruf oder vertrauenswürdigen Ersatzschlüssel gibt es noch
nicht. Eine Rotation darf daher nicht durch einen beliebigen neuen Netzwerkkey
ersetzt werden. Der Maintainer muss einen neuen, getrennt verwahrten Schlüssel
erzeugen, seinen Fingerprint unabhängig veröffentlichen und eine Übergangsversion
mit bewusst festgelegtem Vertrauenssatz signieren. Alte Schlüssel anschließend aus
dem Client entfernen. Bei kompromittiertem altem Schlüssel reicht eine nur mit
diesem Schlüssel signierte „Widerrufsdatei“ nicht; der Ersatz benötigt einen
unabhängig verifizierten Installations-/Verteilungskanal.

Private Schlüssel, Recovery-Zugänge und eine reale Rotation wurden nicht angefasst.
Diese organisatorischen Vertrauensentscheidungen sind Voraussetzung für einen
späteren Protokollwechsel, keine erledigte Eigenschaft des jetzigen Updaters.

## Installer und Rechte

Quellprüfung: Inno installiert nach Program Files und fordert dafür Administratorrechte.
Die App wird nicht automatisch gestartet (Option ist abgewählt); es gibt hier keine
UAC-Anforderung im PyInstaller-Spec, keine zusätzliche Autostart-/Firewallanlage und
keine breite Schreibfreigabe auf das Programmverzeichnis. Die ausführbare Release-Datei
wurde damit weder auf wirksame Windows-Rechte noch auf ihre Übereinstimmung zum Quellcode
bewiesen. Authenticode-Signierung, Build-Lock, zwei reale Vergleichsbuilds und ein
frischer korrekter Release-Tag bleiben Aufgaben des Release-Verantwortlichen.
