$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path "$PSScriptRoot\..\..")

$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$target = "deploy\backup\web_$ts"
New-Item -ItemType Directory -Force -Path $target | Out-Null

$configVol = docker volume ls --format "{{.Name}}" | Select-String "nasadmin_config$" | Select-Object -First 1
$reportsVol = docker volume ls --format "{{.Name}}" | Select-String "nasadmin_reports$" | Select-Object -First 1
if (-not $configVol -or -not $reportsVol) { throw "Volumes nasadmin_config / nasadmin_reports nicht gefunden." }

docker run --rm -v "$($configVol.ToString()):/from" -v "${PWD}\$target:/to" alpine sh -c "cp -a /from /to/config"
docker run --rm -v "$($reportsVol.ToString()):/from" -v "${PWD}\$target:/to" alpine sh -c "cp -a /from /to/reports"

Write-Host "Backup erstellt: $target"
