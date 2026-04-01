param(
  [switch]$BuildFresh
)

$ErrorActionPreference = "Stop"

Set-Location (Resolve-Path "$PSScriptRoot\..\..")

if (-not (Test-Path ".env.web")) {
  Copy-Item ".env.web.example" ".env.web"
  Write-Host ".env.web angelegt (bitte Werte anpassen)." -ForegroundColor Yellow
}

if ($BuildFresh) {
  docker compose -f docker-compose.web.yml build --no-cache
}

docker compose -f docker-compose.web.yml up -d
docker compose -f docker-compose.web.yml ps
