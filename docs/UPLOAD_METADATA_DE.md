# Datei-Upload ohne stillen Verlust von Zusatzrechten

Die Entscheidung in 23.8.69, gewöhnliche UGOS-ACLs nicht generell zu sperren,
bleibt erhalten: `user.*`, `system.posix_acl_access` und `security.selinux` werden
beim Ersetzen kopiert. Das gilt jetzt auch für den ZIP-Sammelweg ab acht Dateien,
der bisher nur Besitzer und normale Modusbits übernommen hat.

Unbekannte `trusted.*`-/`security.*`-Attribute können Zugriffsrechte,
Integritätsnachweise oder Sonderrechte enthalten. Sie ungeprüft auf neue Inhalte
zu kopieren wäre ebenfalls falsch (etwa Dateifähigkeiten oder IMA-Signaturen).
Sie still zu entfernen und Erfolg zu melden ist deshalb keine ausreichende
Kompatibilitätslösung. Ohne dokumentierte, getestete Semantik bleibt das Original
erhalten. Der Fehler nennt den Attributnamen, niemals dessen Wert, und empfiehlt
einen neuen Dateinamen mit anschließender bewusster Rechteprüfung.

Bei ZIP werden bereits vorhandene Ziele vor dem ersten Schreiben auf unbekannte
Attribute geprüft. Unterstützte Attribute werden pro Datei kopiert; Fehler beim
Setzen oder eine beobachtete Änderung der Originaldatei/Metadaten verhindern
deren Austausch. ZIP bleibt eine Folge einzelner atomarer Dateiwechsel; ein
späterer Fehler rollt zuvor erfolgreich übertragene Dateien nicht zurück.

## Verbleibende Abnahme

Die Offline-Tests verwenden echte temporäre Dateien mit simulierten POSIX-ACL-
Aufrufen. Vor dem Release auf einem isolierten UGOS-Testgerät eine künstliche
Datei mit normalen ACLs über beide Wege überschreiben und anschließend den
Zugriff als unbeteiligter Nutzer prüfen. Unbekannte Attribute und Setzfehler
müssen Inhalt und Rechte der alten Datei erhalten. Für ein bestimmtes
UGOS-Sonderattribut kann danach eine belegte, eng begrenzte Unterstützung ergänzt
werden. Keine pauschale Ausnahme für alle `trusted.*`-/`security.*`-Attribute.

Gleichzeitige externe Schreiber sind weiterhin nicht vollständig ausgeschlossen:
Identitäts-/Metadatenvergleiche verkleinern das Zeitfenster, ersetzen aber keine
von allen Schreibenden eingehaltene Sperre. Produktivdaten wurden nicht berührt.
