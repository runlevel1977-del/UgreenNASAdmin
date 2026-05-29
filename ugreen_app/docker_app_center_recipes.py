# -*- coding: utf-8 -*-
"""Curated Docker compose recipes for services missing from UGOS App Center."""

from __future__ import annotations

from typing import TypedDict


class AppCenterRecipe(TypedDict):
    id: str
    i18n: str
    port: str
    tags: str
    yaml: str


RECIPES: list[AppCenterRecipe] = [
    {
        "id": "metube",
        "i18n": "docker.recipe.metube",
        "port": "8081",
        "tags": "media download youtube",
        "yaml": """services:
  metube:
    image: ghcr.io/alexta69/metube:latest
    container_name: metube
    restart: unless-stopped
    ports:
      - "8081:8081"
    volumes:
      - /volume1/docker/metube/downloads:/downloads
""",
    },
    {
        "id": "jellyfin",
        "i18n": "docker.recipe.jellyfin",
        "port": "8096",
        "tags": "media streaming video",
        "yaml": """services:
  jellyfin:
    image: jellyfin/jellyfin:latest
    container_name: jellyfin
    restart: unless-stopped
    ports:
      - "8096:8096"
    environment:
      - TZ=Europe/Berlin
    volumes:
      - /volume1/docker/jellyfin/config:/config
      - /volume1/docker/jellyfin/cache:/cache
      - /volume1/media:/media
""",
    },
    {
        "id": "immich",
        "i18n": "docker.recipe.immich",
        "port": "2283",
        "tags": "photos backup mobile",
        "yaml": """services:
  immich-server:
    image: ghcr.io/immich-app/immich-server:release
    container_name: immich-server
    restart: unless-stopped
    ports:
      - "2283:2283"
    environment:
      - TZ=Europe/Berlin
      - DB_HOSTNAME=database
      - DB_USERNAME=postgres
      - DB_PASSWORD=change_me_db
      - DB_DATABASE_NAME=immich
      - REDIS_HOSTNAME=redis
    volumes:
      - /volume1/docker/immich/upload:/usr/src/app/upload
      - /volume1/photos:/usr/src/app/external:ro
    depends_on:
      - redis
      - database
  immich-machine-learning:
    image: ghcr.io/immich-app/immich-machine-learning:release
    container_name: immich-ml
    restart: unless-stopped
    volumes:
      - /volume1/docker/immich/model-cache:/cache
    environment:
      - TZ=Europe/Berlin
  redis:
    image: redis:6.2-alpine
    container_name: immich-redis
    restart: unless-stopped
    healthcheck:
      test: redis-cli ping || exit 1
      interval: 10s
      timeout: 5s
      retries: 5
  database:
    image: tensorchord/pgvecto-rs:pg14-v0.2.0
    container_name: immich-db
    restart: unless-stopped
    environment:
      - POSTGRES_PASSWORD=change_me_db
      - POSTGRES_USER=postgres
      - POSTGRES_DB=immich
    volumes:
      - /volume1/docker/immich/postgres:/var/lib/postgresql/data
    healthcheck:
      test: pg_isready -U postgres -d immich || exit 1
      interval: 10s
      timeout: 5s
      retries: 5
""",
    },
    {
        "id": "paperless",
        "i18n": "docker.recipe.paperless",
        "port": "8000",
        "tags": "documents scan ocr",
        "yaml": """services:
  broker:
    image: docker.io/library/redis:7
    container_name: paperless-redis
    restart: unless-stopped
    volumes:
      - /volume1/docker/paperless/redis:/data
  db:
    image: docker.io/library/postgres:16
    container_name: paperless-db
    restart: unless-stopped
    volumes:
      - /volume1/docker/paperless/postgres:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=paperless
      - POSTGRES_USER=paperless
      - POSTGRES_PASSWORD=change_me_db
  webserver:
    image: ghcr.io/paperless-ngx/paperless-ngx:latest
    container_name: paperless
    restart: unless-stopped
    depends_on:
      - db
      - broker
    ports:
      - "8000:8000"
    volumes:
      - /volume1/docker/paperless/data:/usr/src/paperless/data
      - /volume1/docker/paperless/media:/usr/src/paperless/media
      - /volume1/docker/paperless/export:/usr/src/paperless/export
      - /volume1/docker/paperless/consume:/usr/src/paperless/consume
    environment:
      - PAPERLESS_REDIS=redis://broker:6379
      - PAPERLESS_DBHOST=db
      - PAPERLESS_SECRET_KEY=change_me_secret
      - USERMAP_UID=1000
      - USERMAP_GID=1000
      - TZ=Europe/Berlin
""",
    },
    {
        "id": "vaultwarden",
        "i18n": "docker.recipe.vaultwarden",
        "port": "8222",
        "tags": "passwords bitwarden security",
        "yaml": """services:
  vaultwarden:
    image: vaultwarden/server:latest
    container_name: vaultwarden
    restart: unless-stopped
    ports:
      - "8222:80"
    environment:
      - TZ=Europe/Berlin
      - SIGNUPS_ALLOWED=false
    volumes:
      - /volume1/docker/vaultwarden:/data
""",
    },
    {
        "id": "nextcloud",
        "i18n": "docker.recipe.nextcloud",
        "port": "443",
        "tags": "cloud sync files",
        "yaml": """services:
  nextcloud:
    image: lscr.io/linuxserver/nextcloud:latest
    container_name: nextcloud
    restart: unless-stopped
    ports:
      - "443:443"
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Europe/Berlin
    volumes:
      - /volume1/docker/nextcloud/config:/config
      - /volume1/docker/nextcloud/data:/data
""",
    },
    {
        "id": "adguard",
        "i18n": "docker.recipe.adguard",
        "port": "3000",
        "tags": "dns adblock network",
        "yaml": """services:
  adguardhome:
    image: adguard/adguardhome:latest
    container_name: adguardhome
    restart: unless-stopped
    ports:
      - "3000:3000/tcp"
      - "53:53/tcp"
      - "53:53/udp"
    volumes:
      - /volume1/docker/adguard/work:/opt/adguardhome/work
      - /volume1/docker/adguard/conf:/opt/adguardhome/conf
""",
    },
    {
        "id": "sonarr",
        "i18n": "docker.recipe.sonarr",
        "port": "8989",
        "tags": "media tv automation",
        "yaml": """services:
  sonarr:
    image: lscr.io/linuxserver/sonarr:latest
    container_name: sonarr
    restart: unless-stopped
    ports:
      - "8989:8989"
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Europe/Berlin
    volumes:
      - /volume1/docker/sonarr/config:/config
      - /volume1:/data
""",
    },
    {
        "id": "radarr",
        "i18n": "docker.recipe.radarr",
        "port": "7878",
        "tags": "media movies automation",
        "yaml": """services:
  radarr:
    image: lscr.io/linuxserver/radarr:latest
    container_name: radarr
    restart: unless-stopped
    ports:
      - "7878:7878"
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Europe/Berlin
    volumes:
      - /volume1/docker/radarr/config:/config
      - /volume1:/data
""",
    },
    {
        "id": "prowlarr",
        "i18n": "docker.recipe.prowlarr",
        "port": "9696",
        "tags": "media indexer automation",
        "yaml": """services:
  prowlarr:
    image: lscr.io/linuxserver/prowlarr:latest
    container_name: prowlarr
    restart: unless-stopped
    ports:
      - "9696:9696"
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Europe/Berlin
    volumes:
      - /volume1/docker/prowlarr/config:/config
""",
    },
    {
        "id": "qbittorrent",
        "i18n": "docker.recipe.qbittorrent",
        "port": "8080",
        "tags": "download torrent",
        "yaml": """services:
  qbittorrent:
    image: lscr.io/linuxserver/qbittorrent:latest
    container_name: qbittorrent
    restart: unless-stopped
    ports:
      - "8080:8080"
      - "6881:6881"
      - "6881:6881/udp"
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Europe/Berlin
      - WEBUI_PORT=8080
    volumes:
      - /volume1/docker/qbittorrent/config:/config
      - /volume1/downloads:/downloads
""",
    },
    {
        "id": "uptime_kuma",
        "i18n": "docker.recipe.uptime_kuma",
        "port": "3001",
        "tags": "monitoring uptime",
        "yaml": """services:
  uptime-kuma:
    image: louislam/uptime-kuma:1
    container_name: uptime-kuma
    restart: unless-stopped
    ports:
      - "3001:3001"
    volumes:
      - /volume1/docker/uptime-kuma:/app/data
""",
    },
    {
        "id": "homeassistant",
        "i18n": "docker.recipe.homeassistant",
        "port": "8123",
        "tags": "smarthome iot automation",
        "yaml": """services:
  homeassistant:
    image: ghcr.io/home-assistant/home-assistant:stable
    container_name: homeassistant
    restart: unless-stopped
    ports:
      - "8123:8123"
    environment:
      - TZ=Europe/Berlin
    volumes:
      - /volume1/docker/homeassistant:/config
""",
    },
    {
        "id": "syncthing",
        "i18n": "docker.recipe.syncthing",
        "port": "8384",
        "tags": "sync files backup",
        "yaml": """services:
  syncthing:
    image: lscr.io/linuxserver/syncthing:latest
    container_name: syncthing
    restart: unless-stopped
    ports:
      - "8384:8384"
      - "22000:22000/tcp"
      - "22000:22000/udp"
      - "21027:21027/udp"
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Europe/Berlin
    volumes:
      - /volume1/docker/syncthing/config:/config
      - /volume1/sync:/data
""",
    },
    {
        "id": "portainer",
        "i18n": "docker.recipe.portainer",
        "port": "9000",
        "tags": "docker gui management",
        "yaml": """services:
  portainer:
    image: portainer/portainer-ce:latest
    container_name: portainer
    restart: unless-stopped
    ports:
      - "9000:9000"
      - "9443:9443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - /volume1/docker/portainer:/data
""",
    },
]
