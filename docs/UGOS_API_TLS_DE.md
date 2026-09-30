# Sichere Verbindung zur UGOS-API

Neue Einstellungen verwenden HTTPS mit Zertifikats- und Hostnamenprüfung.
Das gilt für die API-Snapshots, das Dashboard und die API-Kamerafunktionen.
Die RSA-Verschlüsselung des Passworts ersetzt die Prüfung der Serveridentität
nicht: Ohne diese Prüfung könnte ein anderer Server seinen eigenen RSA-Schlüssel
anbieten.

Bei einem selbst signierten oder zum Hostnamen unpassenden Zertifikat kann die
API-Verbindung deshalb fehlschlagen. Eine vertrauenswürdige Zertifikatskette und
der zum Zertifikat passende NAS-Hostname sind die bevorzugte Lösung.
Die SSH-Funktionen arbeiten unabhängig davon weiter.

Bereits ausdrücklich gespeicherte Einstellungen `verify_ssl: false` bzw.
`use_https: false` bleiben aus Kompatibilitätsgründen erhalten. Diese Verbindungen
bieten keine verlässliche Prüfung der Serveridentität. Bestehende Nutzer sollten
in Einstellungen die HTTPS- und Zertifikatsprüfung prüfen und aktivieren, sobald
eine passende Vertrauenskonfiguration vorliegt. Die Anwendung verändert keine
NAS-Zertifikate und keine Zertifikatsspeicher des Betriebssystems.

API-Anfragen folgen keinen HTTP-Weiterleitungen. So können Zugangsdaten und
Session-Anfragen nicht über eine Weiterleitung an andere Ziele oder von HTTPS
auf HTTP verschoben werden. Bei Reverse-Proxys muss die konfigurierte Adresse
direkt auf den API-Endpunkt zeigen.

Offline-Tests: `python -m unittest discover -s tests -p "test_ugos_api_transport.py" -v`.
Ein Live-Test mit realem NAS-Zertifikat und ein Windows-EXE-Build stehen zusätzlich aus.
