# Abgesicherter SSH-Profilwechsel

Der Profilwechsel benötigt Python 3, systemd-run, eine aktive `ssh.service`
mit Reload-Unterstützung und eine bereits gültige sshd-Konfiguration.
Vor dem Ersetzen des Drop-ins wird ein systemd-Timer für vier Minuten gestartet
und sein aktiver Zustand geprüft. Fehlt diese Voraussetzung, bleibt die
SSH-Konfiguration unverändert. Es wird kein Dienst installiert oder aktiviert.

Backup, Transaktionskennung und Sperre liegen unter dem geprüften, rootprivaten
Verzeichnis `/var/lib/ugreen-nas-admin`. Alle Pfadkomponenten werden ohne
Symlink-Folgen geöffnet; Dateien werden über festgehaltene Verzeichnisdeskriptoren
atomar ersetzt. Eine zweite App darf keine noch offene Transaktion überschreiben.
Syntax- und Reloadfehler lösen sofort die Wiederherstellung aus. Ein Timerdienst
wiederholt fehlgeschlagene Rückfälle; ein SSH-Restart als Ausweichweg entfällt.

„SSH ok bestätigen“ schließt zuerst die bisherige SSH-Verbindung. Erst eine neue
erfolgreiche Verbindung darf die zugehörige, noch nicht abgelaufene Transaktion
bestätigen. Alte Timer können keine neue Transaktion zurückrollen. Fremde Änderungen
am Drop-in werden nicht still überschrieben. Der letzte bestätigte Zustand kann
über „Rollback“ auf seinen Vorgänger zurückgesetzt werden.

Auch die Shutdown-Crondatei verwendet den atomaren Root-Schreiber. Deaktivieren
ersetzt sie durch eine Kommentarzeile, ohne ungeschütztes Umleiten oder Löschen.

## Prüfumfang und Grenzen

Am 01.10.2026 auf einer DXP2800 **nur lesend** festgestellt: systemd 252,
`systemd-run` vorhanden, `ssh.service` aktiv, `sshd_config.d` vorhanden;
`at`/`atq`/`atrm` nicht verfügbar und `atd.service` inaktiv. Kein Profilwechsel,
kein sudo, keine Timeranlage und kein Reload wurden auf dem NAS ausgeführt.

Die Fehlerszenarien werden offline gegen einen synthetischen Konfigurationsspeicher
und Befehlsersatz geprüft. Das beweist weder die UGOS-Dienstintegration noch einen
erfolgreichen SSH-Wiederzugang. Transiente systemd-Timer überleben einen Neustart
nicht: während der Bestätigungsfrist nicht neu starten. Der private Zustand bleibt
für manuelles Rollback erhalten. Ein Stromausfall oder externe Änderungen an anderen
sshd-Dateien verlangen weiterhin einen unabhängigen administrativen Zugangsweg.

Das Drop-in erhält root-Eigentum und Modus 0644; individuelle ACLs/xattrs dieses
von der App verwalteten Drop-ins werden nicht als Wiederherstellungsformat unterstützt.
