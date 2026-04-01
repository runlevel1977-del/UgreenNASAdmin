# Docker Web Version (LAN)

## Schnellstart

1. Datei kopieren:
   - `.env.web.example` -> `.env.web`
2. `.env.web` anpassen:
   - `APP_ADMIN_PASSWORD`
   - `APP_SESSION_SECRET`
   - optional `WEB_PORT`
3. Starten:
   - `docker compose -f docker-compose.web.yml up -d --build`
4. Browser:
   - `http://NAS-IP:8088` (oder dein `WEB_PORT`)

## Login

- Beim ersten Start wird der Admin-User aus ENV erzeugt:
  - `APP_ADMIN_USER`
  - `APP_ADMIN_PASSWORD`
- Im Browser auf **Login** klicken und mit diesen Daten anmelden.

## Reverse Proxy (HTTPS)

- Beispielkonfigurationen:
  - `deploy/proxy/nginx_reverse_proxy.conf`
  - `deploy/proxy/Caddyfile.example`

## Betrieb / Update

- Status:
  - `docker compose -f docker-compose.web.yml ps`
- Logs:
  - `docker compose -f docker-compose.web.yml logs -f`
- Update:
  - `deploy/scripts/update_web.ps1`

## Backup / Restore

- Backup:
  - `deploy/scripts/backup_web.ps1`
- Restore:
  - `deploy/scripts/restore_web.ps1 -BackupPath "deploy/backup/web_YYYYMMDD_HHMMSS"`

## Enthaltene Web-Module

- Verbindung + SSH-Key/Port
- Health/SMART + Report
- Docker (Liste, Start/Stop, Logs)
- Explorer (List, Copy, Delete, Upload, Download)
- Scheduler (read/save cron file)
- ACL (stat/chmod/chown)
- Snapshots (list/create/delete)

## Hinweise

- Die Web-Version nutzt die bestehende SSH-Logik (`nas_ssh.py`) und führt Befehle auf dem NAS aus.
- Für sudo-Aktionen bleibt das NAS-Passwort relevant, sofern `sudo` auf dem NAS ein Passwort verlangt.
