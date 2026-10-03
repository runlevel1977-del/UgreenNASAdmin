# TAR-Wiederherstellung ohne Überschreiben vorhandener Daten

UGOS-Verzeichnisse tragen häufig ACLs/xattrs. Ihre bloße Existenz darf nicht
jeden Daten-Restore verhindern. Das Entfernen der Sperre in 23.8.69 erlaubte
jedoch, vorhandene Dateien samt nicht kopierten Zugriffsrechten zu ersetzen.
Dieser Weg bleibt deshalb ausschließlich als Wiederherstellung in einen **neuen**
Ordner verfügbar. Ein bestehendes Ziel wird unabhängig von seinen ACLs abgewiesen.

Das Archiv wird zuerst vollständig strukturell geprüft. Alle Dateien entstehen
danach in einem eigenen privaten Zwischenordner unter dem bereits vorhandenen
Elternordner. Erst nach Erfolg wird dieser als neues Ziel atomar veröffentlicht.
Linux `renameat2(RENAME_NOREPLACE)` verhindert auch das Ersetzen eines inzwischen
von anderer Seite angelegten leeren Ordners. Fehlt diese Fähigkeit, bricht der
Vorgang ab; es gibt keinen unsicheren Rename-Fallback.

Die Nutzdaten liegen innerhalb einer weiteren privaten Zwischenablage. Der
Rename liest seine Quelle über deren gebundenen Deskriptor: Ein anderer Nutzer
mit Schreibrecht im gemeinsamen Elternordner kann durch Umbenennen/Austauschen
des äußeren Namens keine fremden Inhalte als fertiges Ergebnis unterschieben.
Ein solcher Austausch wird bei der Bereinigung gemeldet, ohne den fremden
Ersatzordner zu löschen; die Meldung nennt, ob das Ergebnis bereits publiziert ist.

Bei einem gewöhnlichen Fehler wird nur die eigene Zwischenablage über gebundene
Verzeichnisdeskriptoren bereinigt. Bei SIGKILL/Stromausfall kann sie als privater
`.ugreen-recovery-*`-Ordner zurückbleiben. Nicht pauschal löschen: zuerst prüfen,
ob noch ein Vorgang läuft. Nach einem Fehler beim abschließenden Verzeichnis-fsync
wird ausdrücklich gemeldet, dass das vollständige Ziel bereits veröffentlicht
ist, seine dauerhafte Speicherung jedoch nicht bestätigt wurde.

Die Wurzel des Ergebnisses bleibt zunächst rootprivat (0700). Normale TAR-
Eigentümer, Modi und Zeitstempel werden im Ergebnis übernommen. Archiv-ACLs,
xattrs, besondere Rechtebits, Links und Spezialdateien bleiben ausgeschlossen.
Es gibt weder automatisches Zurückkopieren in Produktivpfade noch eine
System-/Datenbank-Recovery-Zusage. ZIP-Dateiübertragung ist ein anderer Aufrufer
und wird durch diese TAR-Transaktion nicht zu einem Gesamtrollback.

## Abnahme auf einem isolierten UGOS-Testgerät

Die Windows-Prüfungen simulieren dir_fd/UID und belegen Dateiinhalt, Fehlerpfade,
Bereinigung und Zustandswechsel. Der Linux-CI-Test prüft den echten No-Replace-
Rename. Vor produktivem Release zusätzlich mit ausschließlich künstlichen Daten:

1. Bestehender Zielordner mit abweichenden ACLs: Abbruch; Daten und Rechte identisch.
2. Neues Ziel unter üblicher UGOS-Freigabe: vollständige Dateien, private Wurzel;
   Zugriff zusätzlich als unbeteiligter NAS-Nutzer prüfen.
3. Beschädigtes spätes Archivmitglied, voller Datenträger, Verbindungsabbruch:
   kein teilweise fertig benanntes Ziel und keine Änderung alter Daten.
4. Ziel während des Laufs anlegen: fremden Ordner und Inhalt erhalten.
5. Prozess hart beenden: ausschließlich eigene private Zwischenablage;
   beim Wiederanlauf keine automatische Veröffentlichung oder Löschung.
6. Eigentümer-/Modus-/Zeitstempelbehandlung und anschließend bewusste Übernahme
   in einen separaten Test-Anwendungsordner prüfen.

Diese Abnahme ist eine offene Maintainer-Aufgabe. Es wurde kein Produktiv-NAS
verändert und kein erfolgreiches Live-UGOS-Ergebnis vorweggenommen.
