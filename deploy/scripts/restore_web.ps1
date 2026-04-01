param(
  [Parameter(Mandatory=$true)]
  [string]$BackupPath
)

$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path "$PSScriptRoot\..\..")

if (-not (Test-Path $BackupPath)) { throw "BackupPath nicht gefunden: $BackupPath" }

$configVol = docker volume ls --format "{{.Name}}" | Select-String "nasadmin_config$" | Select-Object -First 1
$reportsVol = docker volume ls --format "{{.Name}}" | Select-String "nasadmin_reports$" | Select-Object -First 1
if (-not $configVol -or -not $reportsVol) { throw "Volumes nasadmin_config / nasadmin_reports nicht gefunden." }

docker run --rm -v "$($configVol.ToString()):/to" -v "${PWD}\$BackupPath:/from" alpine sh -c "cp -a /from/config/. /to/"
docker run --rm -v "$($reportsVol.ToString()):/to" -v "${PWD}\$BackupPath:/from" alpine sh -c "cp -a /from/reports/. /to/"

Write-Host "Restore abgeschlossen."
