# Reproduzierbare Offline-Prüfung

Aus einer vorhandenen Python-Testumgebung mit den Projektabhängigkeiten:

```text
python -B tests/run_offline_suite.py
```

Der Runner benötigt kein pytest. Er führt die unittest-Fälle und zusätzlich die
zehn funktionsbasierten Prüfungen in `test_fan_curve.py` aus. Reines
`unittest discover` erfasst diese zehn Funktionen nicht. Fehler führen zu Exitcode
1. Übersprungene Tests werden im Ergebnis ausgewiesen und müssen bei der
Bewertung berücksichtigt werden. Die Shell-Prüfungen benötigen Bash; unter
Windows verwenden sie vorhandenes Git Bash. GUI-Module benötigen Tkinter zum
Import, ohne dass die App gestartet wird.

Die App-Metadatenprüfung erzeugt ihre eigene `config.json` in einem temporären
Verzeichnis. Das absichtlich nicht veröffentlichte Verzeichnis
`ugreen_developer/` wird nicht benötigt. Der Test prüft weiterhin den echten
Dateileser, die deutsche Namensauswahl und das Ergänzen fehlender Metadaten.

Die HTTPS-Prüfungen verwenden künstliche Zertifikate und TLS über MemoryBIO ohne
Netzwerk-Sockets. Der zusätzliche positive Fall prüft ein selbstsigniertes
Endzertifikat mit `CA=False`, ohne SAN und mit abweichendem Common Name. Im
voreingestellten Pinning-Modus muss dieses exakt gespeicherte Zertifikat
funktionieren. Der optionale CA-Modus und die Ablehnung geänderter Zertifikate
werden weiterhin separat geprüft. Ein gekauftes Zertifikat ist keine
Voraussetzung für den Pinning-Modus.

Die Suite verbindet sich nicht mit einem NAS. SSH, Tresorzugriffe und
privilegierte Systemaufrufe sind simuliert; lokale Datei- und Shelltests nutzen
künstliche temporäre Daten. Ergebnisse unter Windows bestätigen keine echten
UGOS-Mounts, ACLs, sudo-Konfiguration oder Wiederherstellung auf einem NAS.
