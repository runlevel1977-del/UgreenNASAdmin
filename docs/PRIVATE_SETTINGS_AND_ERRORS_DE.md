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

Telegram-Token, SMTP-Passwörter und Passwörter weiterer NAS-/SMB-Profile werden
jetzt ebenfalls im nativen OS-Tresor gespeichert. Lokale JSON-Dateien enthalten
nur zufällige Referenzen. Ein Klartext-Dateibackend wird nicht akzeptiert;
unter Windows wird der native Credential Manager verwendet. Für andere
Plattformen werden die nativen macOS-/SecretService-/KWallet-/libsecret-Backends
akzeptiert; generische Chainer-/Fremdbackends werden konservativ abgewiesen.

Die aktiven app_settings-, Telegram-, Wächter-, Tagesbericht- und alten
qnap_smb_prefs-Dateien werden beim Laden bzw. Start übernommen. Erst nach
Tresor-Schreiben, Rücklesen und atomarem Dateiersatz verschwindet Klartext.
Fehler lassen die bisherige Datei bestehen. Nach einem Ladefehler bleibt
Speichern gesperrt, bis dieselbe Datei erfolgreich neu geladen wurde; dadurch
können UI-Ersatzwerte keine nicht verfügbaren Geheimnisse überschreiben.
Auch Fensterposition, Docker- und Lüftereinstellungen verwenden denselben
Speicherweg. Unveränderte Geheimnisse behalten ihre Referenz. Geänderte Werte
bekommen neue Referenzen, damit ein fehlgeschlagener Dateiersatz den bisherigen
Tresorwert nicht verändert. Nur beim aktuellen Fehlschlag neu angelegte
Einträge werden bereinigt; ältere Tresoreinträge bleiben für vorhandene
Konfigurationskopien erhalten.

Migration und Sicherung: JSON allein ist kein transportables Credential-Backup
mehr. Auf einem anderen Benutzerkonto/PC müssen Geheimnisse neu eingegeben
oder über die Wiederherstellungsfunktion des jeweiligen OS-Tresors übernommen
werden. Alte App-Versionen verstehen die Referenzen nicht. Historische Kopien
in anderen Ordnern/Backups werden nicht durchsucht oder gelöscht; nach
geprüfter Migration müssen Benutzer dortige Klartextkopien separat behandeln.
Ein fehlender Tresor blockiert Migration/Speichern statt auf Klartext auszuweichen.

NAS-seitige unbeaufsichtigte Helfer können den PC-Tresor nicht verwenden. Ihre
notwendigen Laufzeit-Geheimnisse werden weiterhin erst zur Bereitstellung
aufgelöst und in root-geschützten NAS-Dateien abgelegt (0600/privater Ordner).
PR #18 schützt den Transport über stdin. Kein echter Tresor, NAS-Zugang oder
Benachrichtigungsdienst wurde für die Tests geöffnet.

Elf zusätzliche Offline-Tests prüfen Migration, Referenzwiederverwendung,
Lesefehler, fehlende Geheimnisse, Rücklesefehler, fehlgeschlagenen Dateiersatz,
Legacy-Dateien und den echten Docker-Einstellungsspeicherweg. Die bisherigen
neun Datei-/Fehlermeldungstests und 22 SSH-Tresortests bleiben bestehen.
Mehrere Dateien und Tresoränderungen bilden keine gemeinsame Transaktion;
externe parallele App-Instanzen werden nicht global gesperrt.
