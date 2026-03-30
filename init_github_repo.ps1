# Git-Repo anlegen + erster Commit. Voraussetzung: Git for Windows installiert.
# Danach auf github.com ein leeres Repo anlegen und remote + push (siehe Ausgabe unten).

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
Set-Location $Root

$gitCmd = $null
$gc = Get-Command git -ErrorAction SilentlyContinue
if ($gc) { $gitCmd = "git" }
else {
    foreach ($c in @(
        "${env:ProgramFiles}\Git\cmd\git.exe",
        "${env:ProgramFiles}\Git\bin\git.exe",
        "${env:ProgramFiles(x86)}\Git\cmd\git.exe"
    )) {
        if (Test-Path $c) {
            $env:Path = "$(Split-Path $c -Parent);$env:Path"
            $gitCmd = "git"
            break
        }
    }
}

if (-not $gitCmd) {
    Write-Host "Git wurde nicht gefunden. Bitte installieren: https://git-scm.com/download/win" -ForegroundColor Red
    Write-Host "PowerShell neu starten, dann dieses Skript erneut ausfuehren." -ForegroundColor Yellow
    exit 1
}

Write-Host "Git OK: $(git --version)" -ForegroundColor Green

if (-not (Test-Path (Join-Path $Root ".git"))) {
    git init
}

$email = git config user.email 2>$null
if (-not $email) {
    Write-Host ""
    Write-Host "Git braucht einmalig Name und E-Mail (nur lokal):" -ForegroundColor Yellow
    Write-Host '  git config --global user.name "Dein Name"'
    Write-Host '  git config --global user.email "deine@email.de"'
    Write-Host ""
}

git add -A
git status

git commit -m "Initial commit: Ugreen NAS Admin (v22 public source)"
if ($LASTEXITCODE -ne 0) {
    Write-Host "(Commit nicht moeglich - evtl. keine Aenderungen oder user.name/email fehlt.)" -ForegroundColor Yellow
    exit $LASTEXITCODE
}

git branch -M main

Write-Host ""
Write-Host "=== Naechste Schritte (manuell im Browser + Terminal) ===" -ForegroundColor Cyan
Write-Host '1. https://github.com/new - neues Repository (ohne README, wenn schon committet).'
Write-Host "2. Im Projektordner ausfuehren (URL anpassen):"
Write-Host '   git remote add origin https://github.com/DEIN_USER/DEIN_REPO.git'
Write-Host '   git push -u origin main'
Write-Host ""
Write-Host 'Anmeldung bei GitHub: Personal Access Token oder GitHub Desktop / Credential Manager.'
