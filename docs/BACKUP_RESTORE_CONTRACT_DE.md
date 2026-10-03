# Erfolg erst nach Prüfung gegen den eigenen Daten-Restore

Ein erfolgreicher GNU-tar-Lauf allein beweist keine Kompatibilität mit dem
eingeschränkten Daten-Restore. Insbesondere Hardlinks konnten bisher ein als
erfolgreich gemeldetes, vom Restore abgelehntes Archiv erzeugen.

Manuelle und geplante Backups verwenden jetzt dieselbe eingebettete Fassung
des Restore-Prüfers. Vor der Veröffentlichung werden Archivpfade, Mitgliedstypen,
Größen und Ressourcengrenzen sowie tatsächliche Dateilängen und der gzip-Abschluss
geprüft. Scheitert die Prüfung, bleibt die Erfolgsmeldung aus; die eigene
Zwischendatei wird entfernt und alte Archive bleiben erhalten. NAS-Zeitpläne
müssen erneut synchronisiert werden, damit sie den neuen Runner erhalten.

`--hard-dereference` sichert Hardlinks als mehrere normale Dateien mit gleichem
Inhalt. Das braucht gegebenenfalls mehr Speicher; die gemeinsame Inode-Identität
wird nicht wiederhergestellt. Symbolische Links werden ausdrücklich nicht
verfolgt. Links und Spezialdateien, die der Daten-Restore nicht unterstützt,
führen zum Abbruch statt zu einer scheinbar brauchbaren Komplettsicherung.
Für solche Quellen ist ein anderes, dafür ausgelegtes Backupverfahren nötig.

Die vollständige Lesekontrolle kostet einen zusätzlichen Archivdurchlauf.
Die bestehenden Restore-Grenzen (unter anderem 100000 Einträge, 1 TiB insgesamt,
256 GiB pro Datei und Zeitlimit) gelten damit auch für als erfolgreich gemeldete
Backups. Das ist ein Datenarchiv, kein vollständiges NAS-/ACL-Systemabbild.

## Was diese Prüfung nicht beweist

- Zeitlich konsistente Datenbanken oder während des Backups veränderte Quellen.
  Dafür braucht es anwendungseigene Exporte oder abgestimmtes Stilllegen und
  gegebenenfalls einen anschließenden Dateisystem-Snapshot. Mount-Identitätsdaten
  im Job sind **kein Dateisystem-Snapshot**.
- Erfolgreichen Import in Paperless oder andere Anwendungen. Ein Archiv-Restore
  und ein Anwendungs-Recovery-Test sind unterschiedliche Nachweise.
- UGOS-spezifische ACLs, Dateisystem-/Mount-Rennen oder Hardwareausfälle.

Vor dem Release auf einem isolierten Testgerät: normale Dateien plus Hardlink
sichern, Inhalt im neuen Testziel vergleichen; Symlink/Spezialdatei und defektes
spätes gzip-Ende müssen ohne Erfolgsmeldung abbrechen. Bestehende Archive dürfen
dabei nicht verändert werden. Hierfür wurden keine Produktiv-NAS-Zugriffe gemacht.
