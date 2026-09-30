# SSH-Serveridentität prüfen

Alle SSH-Verbindungen der Anwendung prüfen den Server-Schlüssel anhand von
`~/.ssh/known_hosts` (unter Windows normalerweise `%USERPROFILE%\.ssh\known_hosts`).
Das gilt auch für Transfers, Datenträgerabbilder, Docker und das zweite NAS.
Die Anwendung liest diese Datei und übernimmt keine Schlüssel automatisch.

## Erstmalige Verbindung

1. Den SSH-Host-Key-Fingerprint des NAS über einen unabhängig vertrauenswürdigen
   Weg ermitteln, etwa über eine lokale Konsole oder eine bereits verifizierte
   Administrationsverbindung. Eine unbestätigte Netzabfrage allein genügt nicht.
2. Im eigenen Terminal mit OpenSSH dieselbe NAS-Adresse und denselben Port wie
   in der Anwendung verwenden: `ssh -p PORT BENUTZER@NAS-ADRESSE`.
3. Den angezeigten Fingerprint mit dem unabhängig ermittelten Wert vergleichen.
   Nur bei Übereinstimmung bestätigen. Danach kann das Terminal beendet werden.
4. Die Verbindung in Ugreen NAS Admin erneut aufbauen.

Ein unbekannter Schlüssel führt vor der Passwortauthentifizierung zum Abbruch.
Die Meldung zeigt den angebotenen SHA-256-Fingerprint zur Prüfung, sie bestätigt
nicht dessen Echtheit. Bei verändertem Schlüssel wird ebenfalls abgebrochen;
ein NAS-Neuaufsetzen oder Schlüsselwechsel muss unabhängig verifiziert werden.
Bekannte Schlüssel nicht allein zum Beseitigen einer Fehlermeldung löschen.

## Kompatibilität und Prüfung

Bereits in OpenSSH bestätigte Schlüssel werden weiterverwendet, einschließlich
Einträgen für abweichende Ports. Wer bisher ausschließlich die automatische
Übernahme in der Anwendung verwendet hat, muss die Erstprüfung nachholen.
Es werden keine Benutzerdateien automatisch migriert oder verändert.

Die Offline-Regressionsprüfungen laufen mit
`python -m unittest discover -s tests -p "test_ssh_host_verification.py" -v`.
Sie prüfen die Einbindung in sämtliche Paramiko-Verbindungspfade, den Abbruch
bei unbekannten Schlüsseln und die Behandlung fehlerhafter Trust-Stores mittels
Testdoubles. Ein echter SSH-Handshake und ein EXE-Build gehören zur zusätzlichen
Integrationsprüfung vor einer Veröffentlichung.
