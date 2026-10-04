# Öffentlich prüfbare Zuordnung von Quelle, Build und Signatur

`--local-dist` verband bisher einen sauberen Quellbaum mit beliebigen älteren
Dateien aus `dist/` und `installer/output/`, ohne Build-Manifest. Zudem signierte
der Signierhelfer den aktuellen Checkout-Commit als Herkunft, ohne zu prüfen,
ob die Installer-Bytes aus dessen Build stammten oder dieser Commit öffentlich
zugänglich war. Eine gültige Signatur allein schließt diese Lücke nicht.

## Neuer Release-Ablauf

1. Öffentliche Quellen einschließlich Version, Build-Lock und Tests fertigstellen,
   prüfen und committen. Aus diesem öffentlichen Checkout bauen; der private
   Entwicklungsbaum darf weiterhin als Arbeitsbaum dienen, aber nicht als
   unbelegbare Herkunft einer öffentlichen EXE.
2. Mit der bereits vorhandenen, geprüften Build-Umgebung bauen:
   `python tools/reproducible_release.py build --iscc <ISCC.exe> --output <neuer-Buildordner>`.
   Das installiert keine neue Umgebung und umgeht den vorhandenen Lock nicht.
3. Den korrekten Versions-Tag bewusst veröffentlichen. Bestehende falsche Tags
   nicht automatisch verschieben. Vorhandene Release-Fehler transparent erklären
   und eine eindeutig korrigierte Version veröffentlichen.
4. Lesend prüfen: `python tools/release_source_guard.py <Version>`.
   HEAD, lokaler Tag und tatsächlicher Tag im öffentlichen Repository müssen
   übereinstimmen. Annotierte Tags werden auf ihren Commit aufgelöst. Netzwerk-
   und Prüfprobleme führen zum Abbruch, nicht zu einer angenommenen Bestätigung.
5. `python tools/build_release_zip.py --build-dir <Buildordner>` prüft Bytes,
   Quell-Hashes und öffentliche Zuordnung vor dem Packen. Das Manifest und das
   vorhandene native Inventar werden beigefügt. Der alte `--local-dist`-Aufruf
   erklärt den Umstieg und erzeugt kein Release-ZIP.
6. Den unveränderten Installer aus dem Buildordner in den Release-Ordner kopieren;
   dort `python tools/sign_release_asset.py <Installer-Kopie> --build-dir <Buildordner>`.
   Der Helfer prüft die exakten Bytes und Quellen **vor** dem Lesen des privaten
   Schlüssels. Signatur und `.release.json` entstehen bei der Kopie; der geprüfte
   Buildordner bleibt unverändert. Diese drei Dateien gemeinsam veröffentlichen.

Bereits laufende private Release-Automation muss an diesen Ablauf angepasst
werden. Die öffentliche Release-Prüfung ist absichtlich eine Voraussetzung für
Packen/Signieren, nicht für einen lokalen Entwicklungsbuild.

## Grenzen und Abnahme

Ein Build-Manifest ist ein aufgezeichneter Build, kein unabhängiger Beweis, dass
eine Binärdatei mathematisch aus dem Quelltext folgt. Ein zweiter sauberer Build
mit `reproducible_release.py compare` bleibt erforderlich, bevor Byteidentität
behauptet werden darf. Auch native Bibliotheken müssen anhand des Inventars
bewertet werden. Authenticode-Vertrauen wird hierdurch nicht erzeugt.

Offline-Tests verwenden künstliche Dateien/Hashes und simulierte öffentliche
Git-Antworten, keine Signierschlüssel. Es wurde kein Windows-Installer gebaut,
ausgeführt, signiert oder veröffentlicht und kein bestehender Tag verändert.
Vor dem Release den gesamten Ablauf mit einem eigenen Test-Tag und künstlichen
Artefakten in einer separaten Testumgebung abnehmen. Anschließend die tatsächlichen
veröffentlichten Dateien unabhängig herunterladen und Hash/Signatur prüfen.
