# Lokale Geheimnisse und ältere Kopien

Aktive JSON-Einstellungen nutzen den OS-Tresor. Neue Zwischen- und Zieldateien
bekommen unter Windows bereits **vor dem Schreiben** eine geschützte DACL mit
Vollzugriff nur für den aktuellen Benutzer und SYSTEM. POSIX verwendet 0600.
Schlägt die Rechtevergabe fehl, wird nicht auf breitere Rechte ausgewichen.
Auch neu erzeugte private SSH-Schlüssel verwenden diesen atomaren Schreibweg.
Der Windows-Test liest die tatsächliche DACL einer künstlichen Testdatei zurück.

`python -B tools/secret_inventory.py PFAD` inventarisiert bekannte Einstellungsnamen
und Kopien wie `app_settings.json.bak` unter einem ausdrücklich gewählten Verzeichnis.
Die Ausgabe enthält nur relative Dateinamen und Zähler erkannter Klartextfelder bzw.
Tresorverweise, keine Werte. Es wird nichts gelöscht, migriert oder im Tresor gelesen.
Beliebig umbenannte Sicherungen, freie Logtexte und unbekannte Feldnamen sind nicht
vollständig erfasst. Die Inventur ist kein Nachweis, dass nirgendwo Geheimnisse liegen.

Alte Kopien zunächst einem Besitzer/Zweck zuordnen und ihre Wiederherstellbarkeit
prüfen. Erst danach gezielt migrieren oder entfernen. Ungenutzte Tresoreinträge
werden nicht automatisch gelöscht: externe Sicherungen können noch darauf verweisen.
Wird ein echter Klartextfund als offengelegt bewertet, muss der betreffende Betreiber
den Zugang beim Aussteller rotieren; das kann diese Codeänderung nicht erledigen.

Support-Snapshots und Script-Ausgaben können vertrauliche Inhalte enthalten.
Die App versendet Ausgaben nur gemäß den konfigurierten Benachrichtigungsregeln;
vor öffentlichem Teilen ist eine inhaltliche Prüfung erforderlich. Die vorhandene
Fehleranonymisierung ersetzt keine vollständige Redaktion beliebiger NAS-Logs.
