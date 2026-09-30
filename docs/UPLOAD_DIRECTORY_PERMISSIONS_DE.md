# Uploads erhalten Eigentümer bestehender Verzeichnisse

Die beiden bisherigen sudo-Helfer führten vor einem Upload `chown -R` auf dem
Zielverzeichnis aus. Sie werden teilweise bereits vor dem eigentlichen Transfer
aufgerufen. Selbst ein später fehlgeschlagener Upload konnte deshalb Eigentümer
aller vorhandenen Containerdaten, Freigaben und Unterverzeichnisse verändern.

Jetzt werden Pfadbestandteile einzeln geprüft. Nur Verzeichnisse, die dieser
Aufruf erfolgreich neu anlegt, bekommen den SSH-Benutzer und seine primäre Gruppe
als Eigentümer. Bestehende Verzeichnisse und ihre Inhalte werden nicht per chown
oder chmod verändert. Erkannte Symlink-Komponenten und Dateien als Zwischenpfad
führen zum Fehler. Eine fehlgeschlagene Verzeichniserstellung löst kein chown aus.

Ein vorhandenes, für den Benutzer nicht beschreibbares Ziel erhält damit keine
automatische Eigentumsänderung mehr. Die vorhandenen ausdrücklich privilegierten
Datei-Upload-Fallbacks bleiben verfügbar; Zugriffsprobleme sind gegebenenfalls
durch eine gezielte Rechteentscheidung zu lösen.

## Testgrenzen

Acht Offline-Tests führen das erzeugte Bash-Skript mit künstlichen Ordnern und
Dateien aus. chown ist ein harmloser Protokoll-Stellvertreter. Die Tests prüfen
unveränderte bestehende Inhalte, neue Ordner, Sonderzeichen, Fehler und den
Symlink-Abbruchzweig. Kein NAS-Zugriff und keine echte Rechteänderung per chown.

Das ist kein vollständiger Schutz gegen gleichzeitig von anderen Benutzern
ausgetauschte Verzeichnisse. Rennen zwischen Pfadprüfung und Operation, UGOS-ACLs,
das privilegierte Ersetzen einzelner Upload-Dateien und ZIP-Extraktion benötigen
weitere Prüfung. Die separate, explizite Docker-Funktion `chmod -R 777` wird von
dieser Korrektur nicht geändert.
