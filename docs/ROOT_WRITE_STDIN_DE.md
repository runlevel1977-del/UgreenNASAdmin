# Root-Dateien ohne Konfigurationsinhalte in Prozessargumenten

Der SFTP-Ersatzweg kodierte den vollständigen Dateiinhalt als Base64 im
Argument von `python3 -c`. Benachrichtigungskonfigurationen können dabei
Telegram-Tokens oder SMTP-Passwörter enthalten. Base64 schützt diese Werte
nicht vor Prozesslisten und Protokollen, die Befehlsargumente erfassen.

Der vorhandene atomare Schreiber bleibt erhalten. Sein Programm wird jetzt
über SSH-Standardeingabe übertragen; die Befehlszeile enthält nur einen
kleinen Empfänger, eine zufällige Rahmenmarkierung und den SHA-256-Sollwert.
Der Empfänger funktioniert sowohl bei einer Passwortabfrage durch sudo als
auch bei bereits gültiger Autorisierung oder NOPASSWD. Beschädigte oder
abgeschnittene Eingaben werden vor der Ausführung abgewiesen.

Vier Offline-Tests führen den wirklichen Empfänger mit künstlichen Daten aus,
einschließlich eines großen Inhalts und beider sudo-Eingabevarianten.
Aufruf: `python -B -m unittest discover -s tests -p test_root_write_stdin.py -v`.
Ein echter sudo-Aufruf wurde dafür nicht ausgeführt.

Diese Änderung verschlüsselt keine gespeicherten Konfigurationsdateien und
schützt nicht vor root, Debuggern oder ausdrücklich aktivierter
sudo-Eingabeprotokollierung. SSH transportiert die Daten verschlüsselt;
Dateirechte und die private Helferablage bleiben weiterhin erforderlich.
