# NAS: Docker-Web-Stack (nasadmin) entfernen

Auf dem **Ugreen NAS** per SSH (z. B. User `papa`). Pfade anpassen, falls dein Projekt woanders liegt.

## 1. Container stoppen und entfernen

```bash
cd /volume1/docker/nas-admin-web/NAS_Admin_Project
docker compose -f docker-compose.web.yml down
```

Falls die Compose-Datei **schon gelöscht** ist oder der Befehl fehlschlägt:

```bash
docker stop nasadmin-web nasadmin-api 2>/dev/null
docker rm nasadmin-web nasadmin-api 2>/dev/null
```

## 2. Docker-Volumes löschen (Web-Konfiguration & Daten)

**Achtung:** Damit sind gespeicherte Web-Admin-Zugangsdaten, `settings.json`, Reports und Logs aus den Volumes weg.

```bash
docker volume rm nasadmin_config nasadmin_reports nasadmin_logs 2>/dev/null
```

Falls die Namen mit **Projektpräfix** existieren (Compose hängt oft den Ordnernamen voran):

```bash
docker volume ls | grep -i nasadmin
```

Dann z. B.:

```bash
docker volume rm nas-admin-web_nasadmin_config nas-admin-web_nasadmin_reports nas-admin-web_nasadmin_logs
```

(Exakte Namen aus der `docker volume ls`-Ausgabe übernehmen.)

## 3. Images optional entfernen

```bash
docker images | grep -i nasadmin
docker rmi <IMAGE_ID_oder_NAME> …
```

Nur löschen, wenn du die Images wirklich nicht mehr brauchst.

## 4. Projektordner auf dem NAS (optional)

Repository/Kopie löschen, wenn du den Web-Stack komplett weg haben willst:

```bash
rm -rf /volume1/docker/nas-admin-web/NAS_Admin_Project
```

Vorher sichern, falls du noch etwas aus `.env.web` brauchst.

## 5. Port & Firewall

Port **8088** (oder dein `WEB_PORT`) war für den Web-Container. In der NAS-Firewall/Oberfläche ggf. Regeln für diesen Port entfernen, falls du sie nur dafür angelegt hattest.

## 6. Reverse Proxy (falls genutzt)

Wenn du Nginx/Caddy auf dem NAS oder einem anderen Rechner für diese App konfiguriert hattest: `server`-Block / Site für diese URL entfernen und Dienst neu laden.

---

**Danach:** Weiterarbeit nur noch mit der **Desktop-App** (`python ugreen_nas_admin.py` bzw. Release aus `öffentlich/`).
