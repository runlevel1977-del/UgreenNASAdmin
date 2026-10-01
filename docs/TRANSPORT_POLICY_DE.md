# Transport von Zugangsdaten

Die UGOS-API setzt HTTPS voraus. Eine alte Einstellung `use_https: false` wird
vor dem ersten Netzwerkzugriff mit einem verständlichen Fehler abgelehnt.
In den Einstellungen HTTPS einschalten und den tatsächlich konfigurierten
HTTPS-Port prüfen. Zertifikatsprüfung und Fingerprint-Bestätigung bleiben erhalten.

SMTP-Anmeldedaten erfordern SSL oder STARTTLS. Das gilt für die Desktop-App,
Watch, Tagesbericht und beide Varianten des Script-Runners. Ein Fehler bei
STARTTLS oder Zertifikatsprüfung führt zum Abbruch, niemals zu einem erneuten
Versuch im Klartext. Bestehende Konfigurationen werden nicht still umgestellt.

Ein ausdrücklich konfigurierter SMTP-Relay ohne Benutzer **und** Passwort kann
weiterhin unverschlüsselt senden. Dabei sind Mailinhalt und Empfänger im Netz
sichtbar; für vertrauliche Berichte ebenfalls TLS einschalten.

Prüfung: synthetische Transporte, kein SMTP-Versand und kein UGOS-Login.
