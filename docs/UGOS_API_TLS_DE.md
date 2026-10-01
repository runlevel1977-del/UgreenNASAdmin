# UGOS-API: TOFU, Zertifikatsprüfung und Redirect-Schutz

Die ab 23.8.49 eingeführten Verbindungsmodi bleiben erhalten: HTTPS mit
TOFU-Zertifikatsspeicher ist der Standard, „SSL prüfen (CA)“ verwendet zusätzlich
den System-Vertrauensspeicher mit Hostnamenprüfung. Explizit konfiguriertes HTTP
bleibt möglich und bietet keine TLS-Absicherung.

TOFU übernimmt beim ersten Kontakt das angebotene Zertifikat. Dieser initiale
Abruf ist unauthentifiziert und muss über eine vertrauenswürdige Verbindung
erfolgen. Eine unabhängige Fingerprint-Prüfung bleibt sinnvoll. Das Zertifikat
liegt in `ugos_tls_certs.json` im Datenordner der Anwendung. OS-Zertifikatsspeicher
und NAS-Einstellungen werden nicht verändert.

Beim eigentlichen API-Handshake ist CERT_REQUIRED aktiv. Zusätzlich wird das
Zertifikat der tatsächlich verbundenen Gegenstelle vor dem Senden der ersten
HTTP-Anfrage mit dem gespeicherten SHA-256-Fingerprint verglichen. Das verhindert,
dass ein anderes, vom gespeicherten Zertifikat signiertes Zertifikat allein wegen
einer gültigen Kette akzeptiert wird. Bei CA-Modus bleibt die normale CA- und
Hostnamenprüfung aktiv.

Fehler beim Lesen des Speichers, ungültiges JSON, falsche Struktur und ungültige
Zertifikate führen zum Abbruch. Sie lösen kein neues automatisches Vertrauen aus.
Vorhandene Daten bleiben erhalten. Bei Fehlern den Speicher sichern und gezielt
reparieren oder aus einer vertrauenswürdigen Kopie wiederherstellen. Bei einem
beabsichtigten Zertifikatwechsel erst die neue Identität unabhängig prüfen,
danach „TLS-Zertifikat vergessen“ verwenden.

Login- und Datenanfragen folgen keinen HTTP-Weiterleitungen, auch nicht zum selben
Host. Ein Reverse-Proxy muss daher direkt auf den API-Endpunkt zeigen. Ein TLS-
Fehler führt nicht zu einem Wiederholungsversuch mit ungeprüftem HTTPS oder HTTP.

Prüfung: `python -m unittest discover -s tests -p "test_ugos_api_transport.py" -v`.
Die Tests führen echte TLS-Handshakes zwischen MemoryBIO-Objekten mit erzeugten
Testzertifikaten aus, ohne Netzwerk-Sockets. Die HTTP-Verbindungsprüfungen verwenden
Testdoubles. Reales UGOS, NAS-Zertifikate, Proxys und EXE-Packaging sind zusätzlich
zu prüfen. TOFU-Erstvertrauen bleibt eine Grenze; mehrere App-Prozesse sind nicht
durch eine prozessübergreifende Speichersperre koordiniert.
