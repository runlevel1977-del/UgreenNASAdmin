# Backup-JSON vor Übernahme in root-Cron prüfen

„Vom NAS laden“ übernimmt Jobs aus `scheduled_backups.json`. Main 23.8.54 prüft
bereits einige Felder, überspringt ungültige Jobs aber erst nach dem Schreiben von
Runner und JSON. Wertebereiche, doppelte IDs und die genaue Anzahl der Cron-Felder
werden nicht vollständig geprüft. Dieser PR prüft den gesamten Import vor
Remote-Aufrufen und bricht bei einem Fehler ab. Shell-Quoting allein schützt
nicht vor der vorgelagerten Cron-Syntax. Ein Angriff auf ein reales NAS wurde
nicht ausgeführt.

Vor dem ersten Schreibzugriff wird jetzt die gesamte Liste geprüft:

- eindeutige IDs aus 1–64 Buchstaben, Ziffern, Unterstrich und Bindestrich;
- gültige absolute Volume-Ziele ohne Pfad-Aliase oder Steuerzeichen;
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

Elf Offline-Tests mit simuliertem UI-/SSH-Ablauf prüfen ungültige Imports,
Sonderzeichen, Wertebereiche, Erhalt fremder Cron-Einträge und Fehlerabbruch.
Sie starten keinen Cron-Daemon und keine NAS-Verbindung. Gleichzeitige Änderungen
der Cron-Datei durch andere Programme und eine atomare Transaktion über mehrere
Dateien sind weiterhin offen. Die Dateirechte und der Schutz der Runner-
Verzeichnisse müssen unabhängig von der Eingabeprüfung gewährleistet sein.
