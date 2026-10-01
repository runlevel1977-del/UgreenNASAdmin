# Konfigurationen erhalten und Benachrichtigungsfehler begrenzen

Sieben lokale JSON-Schreibstellen für Verbindungen, Einstellungen, Telegram,
Wächter und Tagesbericht verwenden jetzt eine gemeinsame atomare Speicherung.
Serialisierung erfolgt vor dem Öffnen einer neuen Datei; Schreiben und fsync
werden vor dem Ersetzen des bisherigen Dokuments abgeschlossen. Scheitert ein
Schritt, bleibt der alte Stand erhalten. Konfigurations-Symlinks werden abgewiesen.
Unter POSIX entsteht die temporäre Datei mit 0600; unter Windows gelten die
geerbten Verzeichnis-ACLs, keine zugesicherte ACL-Härtung durch chmod.

Telegram- und SMTP-Fehlermeldungen übernahmen bisher beliebige Exception- oder
Servertexte. Solche Texte können vollständige Token-URLs oder zurückgespiegelte
Zugangsdaten enthalten. Die Anwendung sowie die eigenständigen Wächter-,
Tagesbericht- und Script-Notify-Helfer geben dafür nur Fehlerklassen bzw.
numerische HTTP-Statuscodes zurück. Rohantworten erscheinen nicht mehr im Log.

Die Tests verwenden ausschließlich künstliche Konfigurationen und simulierte
Netzwerkfehler. Bestehende Tresor-Regressionstests bleiben Bestandteil der Prüfung.
Es werden keine Benachrichtigungen gesendet und keine echten Tresore geöffnet.

Die bestehende bewusste Speicherung von Telegram-/SMTP-Zugangsdaten in lokalen
JSON-Dateien wird dadurch nicht verschlüsselt. Die verdeckte Anzeige im UI ist
kein Tresor. Eine vollständige Migration aller weiteren Geheimnisse einschließlich
NAS-seitiger unbeaufsichtigter Helfer benötigt ein eigenes kompatibles
Speicher-/Migrationskonzept; alte Dateien werden nicht automatisch gelöscht.
Mehrere JSON-Dateien und Tresoränderungen bilden weiterhin keine gemeinsame
Transaktion. Vorhandene Diagnose-/Exportpfade außerhalb der geprüften
Benachrichtigungstransporte sind nicht pauschal als geheimnisfrei bestätigt.
