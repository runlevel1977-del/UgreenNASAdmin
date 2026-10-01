# SSH-Vertrauensspeicher auf Basis von main 23.8.54

Die Anwendung behält den TOFU-Ansatz und die neue Erstkontakt-Bestätigung aus
23.8.54 bei: Erst nach Zustimmung wird der angebotene Schlüssel in
`ssh_known_hosts.json` im Datenordner gespeichert. Ohne Bestätigungsfunktion oder
bei Ablehnung bricht die Verbindung ab. Spätere abweichende Schlüssel werden abgewiesen.
Alle zwölf Paramiko-Verbindungspfade verwenden dieselbe Prüfung.

Ein erster Kontakt ist damit noch keine unabhängige Echtheitsprüfung. Er sollte
über eine vertrauenswürdige Verbindung erfolgen; der gespeicherte SHA-256-
Fingerprint sollte mit einer vertrauenswürdigen NAS-Konsole abgeglichen werden.
OpenSSH `~/.ssh/known_hosts` ist ein separater Speicher und wird nicht importiert.

Diese Korrektur verhindert, dass Lesefehler, ungültiges JSON, fehlerhafte
Speicherstrukturen oder ungültige Schlüssel wie ein neuer Erstkontakt behandelt
werden. Die Verbindung bricht ab, vorhandene Dateien bleiben erhalten. Nur eine
tatsächlich fehlende Datei bzw. ein tatsächlich neuer Host erlaubt Erstvertrauen.
Zwei gleichzeitige Erstkontakte innerhalb derselben App können nicht verschiedene
Schlüssel für denselben Host akzeptieren. Während der Benutzerentscheidung wird
keine Speichersperre gehalten; vor dem Speichern wird der Eintrag erneut geprüft.
Mehrere App-Prozesse werden nicht durch
eine prozessübergreifende Sperre koordiniert.

Bei einem Fehler die Datei sichern und aus einer vertrauenswürdigen Kopie
wiederherstellen oder gezielt reparieren. Nicht allein zur Beseitigung der
Fehlermeldung löschen. Nach einem beabsichtigten NAS-Schlüsselwechsel erst den
neuen Fingerprint unabhängig prüfen, dann die vorhandene Aktion „SSH-Host-Key
vergessen“ verwenden. Ein ungültiger Speicher wird auch dabei nicht still geleert.

Prüfung: `python -m unittest discover -s tests -p "test_ssh_host_verification.py" -v`.
Die Tests verwenden temporäre Dateien und Testdoubles; keine echten Zugangsdaten,
NAS-Verbindungen oder OS-Vertrauensdateien. Ein realer SSH-Handshake und ein
Windows-EXE-Build bleiben separate Integrationsprüfungen.
