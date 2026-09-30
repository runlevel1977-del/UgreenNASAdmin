# Backup-JSON vor Übernahme in root-Cron prüfen

„Vom NAS laden“ übernimmt Jobs aus `scheduled_backups.json`. Beim anschließenden
Synchronisieren wurden deren Job-IDs und fünf Cron-Felder ohne Inhaltsprüfung in
die root-Cron-Datei geschrieben. Ein Zeilenumbruch in einer importierten ID oder
einem Feld konnte zusätzliche Cron-Zeilen erzeugen. Shell-Quoting allein schützt
nicht vor der vorgelagerten Cron-Syntax. Voraussetzung für dieses Szenario ist
Einfluss auf die geladene JSON und eine anschließende Synchronisierung durch den
Administrator; ein Angriff auf ein reales NAS wurde nicht ausgeführt.

Vor dem ersten Schreibzugriff wird jetzt die gesamte Liste geprüft:

- eindeutige IDs aus Buchstaben, Ziffern, Unterstrich und Bindestrich;
- genau fünf numerische Cron-Felder mit gültigen Wertebereichen; `*`, Listen,
  Bereiche und Schrittweiten bleiben unterstützt;
- ein boolesches `first_week` und einzeilige Kommentare;
- absolute Runner-/JSON-Pfade ohne Steuerzeichen oder `%` (Cron interpretiert
  Prozentzeichen auch innerhalb von Shell-Quotes).

Bei einem ungültigen Eintrag wird die gesamte Synchronisierung abgebrochen.
Benannte Monate/Wochentage und `@reboot` sind in diesem Backup-Import nicht
zulässig; die numerischen Werte der vorhandenen UI bleiben unterstützt.
Der Roh-Cron-Editor für bewusst eingegebene Verwaltungsbefehle bleibt separat.

Zusätzlich wird ein Lesefehler der bestehenden Cron-Datei nicht länger als leere
Datei behandelt. Die Synchronisierung bricht dann vor Dateiänderungen ab.
Der Backup-Verzeichnispfad wird korrekt als ein Argument übergeben; auch ein
fehlgeschlagenes mkdir stoppt vor dem Schreiben von Runner, JSON und Cron-Datei.

Zehn Offline-Tests mit simuliertem UI-/SSH-Ablauf prüfen ungültige Imports,
Sonderzeichen, Wertebereiche, Erhalt fremder Cron-Einträge und Fehlerabbruch.
Sie starten keinen Cron-Daemon und keine NAS-Verbindung. Gleichzeitige Änderungen
der Cron-Datei durch andere Programme und eine atomare Transaktion über mehrere
Dateien sind weiterhin offen. Die Dateirechte und der Schutz der Runner-
Verzeichnisse müssen unabhängig von der Eingabeprüfung gewährleistet sein.
