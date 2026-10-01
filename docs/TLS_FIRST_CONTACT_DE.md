# UGOS-Zertifikat vor dem ersten Login bestätigen

Im Pinning-Modus wird ein unbekanntes Zertifikat nur zur Anzeige seines
SHA-256-Fingerprints abgeholt. Dieser TLS-Abruf enthält keine API-Anfrage oder
Anmeldedaten. Erst nach unabhängigem Vergleich und ausdrücklicher Zustimmung
wird der Pin gespeichert und der API-Login freigegeben. Ohne Dialog, bei
Ablehnung, Dialogfehler oder Zeitüberschreitung wird abgebrochen. Die Auswahl
im Dialog steht zunächst auf Nein.

Bereits automatisch gespeicherte Pins haben kein confirmed-Feld und benötigen
einmal dieselbe Bestätigung. Sie werden dabei nicht durch ein frisch
abgeholtes Zertifikat ersetzt. Bestätigte Pins bleiben verbindlich; ein
gleichzeitig geänderter Vertrauensspeicher wird erneut geprüft. Das Vergessen
eines Zertifikats erfordert beim nächsten Kontakt wieder Zustimmung.

Der Vergleich muss über einen unabhängig vertrauenswürdigen Zugang zur NAS
erfolgen. Bloßes Bestätigen ohne Vergleich authentifiziert den Erstkontakt
nicht. Der CA-Modus verwendet weiterhin den System-Vertrauensspeicher mit
Hostname-Prüfung. Diese Änderung benötigt weder neue NAS-Dateien noch Dienste.

Sieben neue Offline-Tests prüfen fehlende/abgelehnte Zustimmung, Dialogfehler,
Alt-Pins, konkurrierende Änderungen, defekte Bestätigungswerte und erneutes
Vertrauen nach Vergessen. Bestehende TLS-Tests verlangen jetzt explizite
Test-Zustimmung. Kein echter NAS-Login und kein GUI-Betriebstest.
