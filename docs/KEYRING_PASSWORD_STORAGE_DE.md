# SSH-Geheimnisse im Tresor: Speichern und Fehlerfälle

Basis ist main 23.8.54. SSH-Passwörter und SSH-Key-Passphrasen werden weiterhin
nur im Tresor gespeichert. Neue Werte ohne verfügbaren Tresor werden mit
Fehlermeldung abgewiesen; es gibt keinen Klartext-Fallback.

Ein aus dem Tresor geladener oder erfolgreich dort gespeicherter Wert wird anhand
von Host, Benutzer und Inhalt im Arbeitsspeicher wiedererkannt. Unveränderte Werte
bleiben beim Speichern aus JSON ausgeschlossen und werden nicht erneut in den
Tresor geschrieben. Das funktioniert auch bei vorübergehend gesperrtem Tresor.

Schlägt das Speichern eines neuen Werts oder die Bereinigung eines anderen Profils
fehl, bleiben die vorhandene Konfigurationsdatei, die ursprünglichen Profile und
die UI-Eingaben erhalten. Fehlende Host-/Benutzerangaben dürfen neue Geheimnisse
nicht still verwerfen. Die Bereinigung arbeitet mit Profilkopien.

Ein leeres JSON-Feld bedeutet möglicherweise „im Tresor gespeichert“. Nur das
bewusste Leeren eines zuvor geladenen Werts im UI löst dessen Löschung aus.
Ein nicht erreichbarer Tresor beim Laden ist kein Löschauftrag. Fehler des
Lösch-Backends werden gemeldet, sowohl für Passwörter als auch für Passphrasen.

Tresor und JSON bilden keine gemeinsame Transaktion: Bereits erfolgreiche
Tresor-Schreibvorgänge werden bei einem späteren Fehler nicht zurückgerollt.
SMTP-/SMB-Geheimnisse und alte Konfigurationskopien liegen außerhalb dieses PRs.

Prüfung: `python -m unittest discover -s tests -p "test_keyring_resave.py" -v`.
Temporäre Dateien und künstliche Geheimnisse; alle Tresor-, UI-Dialog- und
Verbindungsaktionen sind gemockt. Ein echter Credential-Manager-/EXE-Test steht aus.
