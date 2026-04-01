$ErrorActionPreference = "Stop"

Set-Location (Resolve-Path "$PSScriptRoot\..\..")
docker compose -f docker-compose.web.yml pull
docker compose -f docker-compose.web.yml up -d --build
docker compose -f docker-compose.web.yml ps
