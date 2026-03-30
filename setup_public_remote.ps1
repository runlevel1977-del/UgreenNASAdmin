# Einmalig: Remote fuer das OEFFENTLICHE Repo setzen und pushen.
# Vorher auf GitHub ein LEERES oeffentliches Repo anlegen (z. B. UgreenNASAdmin).

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
Set-Location $Root

if (-not (Test-Path (Join-Path $Root ".git"))) {
    Write-Host "Fuehre zuerst in diesem Ordner aus: git init" -ForegroundColor Red
    exit 1
}

Write-Host "Aktuelle Remotes:" -ForegroundColor Cyan
git remote -v 2>$null
Write-Host ""
$url = Read-Host "HTTPS-URL des OEFFENTLICHEN Repos (z. B. https://github.com/USER/UgreenNASAdmin.git)"
if (-not $url) { exit 1 }
$url = $url.Trim()

if (git remote get-url origin 2>$null) {
    git remote set-url origin $url
} else {
    git remote add origin $url
}

Write-Host "Pushe main ..." -ForegroundColor Green
git branch -M main
git push -u origin main
