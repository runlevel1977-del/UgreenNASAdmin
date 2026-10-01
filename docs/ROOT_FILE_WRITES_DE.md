# Privilegierte Dateien sicher veröffentlichen

Der bisherige SFTP-Weg verschob eine Datei des SSH-Benutzers mit `sudo mv`
an das Ziel. Dadurch blieb der SSH-Benutzer Eigentümer, auch bei Cron-Dateien,
Runnern und Benachrichtigungskonfigurationen. Der Base64-Fallback schrieb direkt
in das Ziel: Ein Abbruch konnte vorhandene Inhalte zerstören; ein Symlink wurde
verfolgt. Das ist ein Quellcodebefund, keine auf einem NAS demonstrierte Übernahme.

Beide Wege schreiben nun zunächst eine neue temporäre Datei im Zielverzeichnis,
setzen vor der Veröffentlichung Eigentümer/Gruppe auf `root:root` und den
angeforderten Modus und ersetzen dann den Verzeichniseintrag atomar. Schreib-,
Rechte- und Veröffentlichungsfehler lassen den alten Inhalt bestehen. Erkannte
Symlink-Ziele werden abgewiesen; ein vorhandener Hardlink wird beim Austausch
nicht inhaltlich verändert. Das ist keine Zusicherung gegen Stromausfall.

Das SFTP-Staging wird exklusiv angelegt und vor dem ersten Nutzdatenbyte auf 0600
gesetzt. Der privilegierte Leser akzeptiert nur eine reguläre Datei, folgt keinem
Symlink am letzten Pfadbestandteil und prüft die Daten gegen den lokal erwarteten
SHA-256-Wert. Ein fehlgeschlagener Upload wird nicht veröffentlicht.

## Kompatibilität und Grenzen

- `/usr/bin/python3` wird jetzt für beide Wege benötigt; bisher nur im Fallback.
- Ein als root gespeichertes Skript lässt sich anschließend nicht allein aufgrund
  früherer Eigentümerschaft als normaler Benutzer überschreiben. Dafür erneut die
  ausdrücklich privilegierte Speicherfunktion verwenden.
- Neue Dateiinodes erhalten die angeforderten Unix-Rechte; bisherige individuelle
  ACLs, xattrs und Labels werden nicht übernommen. UGOS-Vererbung ist separat zu prüfen.
- Root-Eigentum schützt nicht vor Austausch durch Benutzer mit Schreibzugriff auf
  Elternverzeichnisse. Mitgelieferte Runner und Konfigurationen verwenden jetzt
  eine [geprüfte private Ablage samt Migrationshinweisen](PRIVATE_ROOT_RUNTIME_DE.md).
  Andere frei gewählte Ziele sind weiterhin keine abgesicherten Verzeichnispfade.
- Der bereits vorhandene Base64-Fallback transportiert Daten im Remote-Befehl.
  Sichtbarkeit in Prozessargumenten bzw. Befehlsprotokollen bleibt ein separates
  Geheimnisspeicherungsthema.
- 10 Offline-Tests prüfen Inhalte, Fehlerfälle, Hardlinks, Staging und Reihenfolge
  vor Veröffentlichung. POSIX-Eigentümer-/Modusaufrufe sind unter Windows simuliert;
  echte SSH-/SFTP-, sudo-, ACL- und UGOS-Prüfungen stehen aus.

Referenzen: [Paramiko SFTP](https://docs.paramiko.org/en/stable/api/sftp.html),
[Python os.replace/fchown](https://docs.python.org/3/library/os.html),
[Debian cron-Dateirechte](https://manpages.debian.org/bookworm/cron/cron.8.en.html).
