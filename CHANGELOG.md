# Changelog — Ugreen NAS Admin

## Unreleased (Web/Docker Preview)

### Neu

- Docker-Web-Stack hinzugefügt (`docker-compose.web.yml`) mit separatem API-Container und Web-Container.
- Browser-UI mit linker Navigation und rechtem Funktionsbereich (`web/ui/src/index.html`).
- API-Endpunkte für Verbindung, Health/SMART, Docker, Explorer, Scheduler, ACL, Snapshots (`web/api/app/routers/`).
- Persistente Konfiguration und Reports über Docker-Volumes (`/app_data/config`, `/app_data/reports`).

### Betrieb/Sicherheit

- Session-Login mit Cookie für LAN-Betrieb.
- Reverse-Proxy-Beispiele (Nginx/Caddy) unter `deploy/proxy/`.
- Install/Update/Backup/Restore-Skripte unter `deploy/scripts/`.
- Smoke-Test für Basisverfügbarkeit unter `tests/web/smoke_test_web.py`.

### Migration Notes

- Desktop-App bleibt unverändert nutzbar; Web-Version ist zusätzlicher Betriebsmodus.
- Für Web-Betrieb `.env.web` anlegen (aus `.env.web.example`) und starke Secrets setzen.

## 22.0.0 (Public) — 2026-03-30

### Neu

- Ordner **`öffentlich/`**: enthält alle zum **Starten** und **Bauen** der App nötigen Dateien (Release-Quelle für öffentliche Versionen). Siehe `öffentlich/README.md` — **Ordner nicht löschen**; bei Änderungen im Hauptprojekt Inhalt bei Bedarf spiegeln.
- **Öffentliche Version** mit zweisprachiger Oberfläche **Deutsch / Englisch**.
- **Sprach-Umschalter** `DE / EN` unten links in der Statusleiste; Umschalten lädt die UI neu (gleiche Session, Verbindungsdaten bleiben erhalten).
- **Persistenz:** `ui_lang` wird in `nas_admin_connection.json` neben IP/User/Passwort gespeichert (beim „Verbindung speichern“ mit abgelegt).
- **Übersetzungen** zentral in `ugreen_app/i18n.py` (UI-Texte, Cron-Klartext-Mappings, häufige Dialoge).
- **Versionsnummer** und Fenstertitel nutzen die gleiche Quelle (`__version__`).
- **NAS Explorer (Tab):** Zwei-Spalten-Ansicht (NAS-Baum / **Dieser PC**) zum **Hoch- und Herunterladen** sowie **Kopieren** zwischen NAS und lokalem Rechner — über Werkzeugleiste, Kontextmenü und Direktaktionen (z. B. Upload einzelner Dateien oder ganzer Ordner, „Auf NAS kopieren“ / „Auf PC kopieren“), inkl. Fortschrittsanzeige bei Übertragungen.

### Geändert (gegenüber 21.2.0)

- Hauptfenster, Sidebar, alle Tab-Bereiche (Scripts, Explorer, Docker, Health/Telegram, Speicher, ACL, Snapshots, Planer), Statuszeile und viele Meldungen sind **sprachabhängig**.
- Cron-/Planer-Klartext und Combobox-Bezeichnungen folgen der gewählten Sprache.
- Abgerundete Buttons (Pillow) unverändert nutzbar; PyInstaller: `ugreen_app.i18n` als Hidden Import ergänzt.

### Hinweis

- Einzelne tiefe Dialoge (z. B. einige Snapper/Btrfs-Eingaben) können noch deutsche Standardtexte zeigen; die zentralen Pfade sind übersetzt.

---

## 21.2.0 und älter

- Vorherige Versionen ohne integrierte DE/EN-Umschaltung; siehe Git/Backup bzw. interne Release-Notizen.
