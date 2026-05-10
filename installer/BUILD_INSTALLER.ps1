# Baut UgreenNASAdmin_setup_<Version>.exe (Inno Setup 6).
# Voraussetzung: https://jrsoftware.org/isdl.php — "Inno Setup 6".
# Doppelklick (Explorer): BUILD_INSTALLER.bat  (damit nicht der Editor die .ps1 oeffnet)
# Aufruf (PowerShell):  cd installer ; .\BUILD_INSTALLER.ps1

$ErrorActionPreference = "Stop"
$InstallerDir = $PSScriptRoot
$RepoRoot = Split-Path -Parent $InstallerDir
Set-Location $InstallerDir

$versionPath = Join-Path $RepoRoot "ugreen_app\nas_manager.py"
$ver = $null
if (Test-Path $versionPath) {
    $m = Select-String -Path $versionPath -Pattern '^\s*__version__\s*=\s*"([^"]+)"' | Select-Object -First 1
    if ($m) { $ver = $m.Matches.Groups[1].Value }
}
if (-not $ver) {
    Write-Error "Konnte __version__ in ugreen_app\nas_manager.py nicht lesen."
    exit 1
}

$distExe = Join-Path $RepoRoot "dist\UgreenNASAdmin.exe"
if (-not (Test-Path $distExe)) {
    Write-Host "dist\UgreenNASAdmin.exe fehlt — starte builder.py im Projektroot …" -ForegroundColor Yellow
    Push-Location $RepoRoot
    try {
        python builder.py
    } finally {
        Pop-Location
    }
}
if (-not (Test-Path $distExe)) {
    Write-Error "dist\UgreenNASAdmin.exe fehlt nach builder.py — Build pruefen."
    exit 1
}

$iscc = @(
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $iscc) {
    Write-Error @"
Inno Setup 6 nicht gefunden (ISCC.exe).
Installieren: https://jrsoftware.org/isdl.php
Erwartet z. B.: …\Local\Programs\Inno Setup 6\ISCC.exe (winget)
  oder …\Program Files (x86)\Inno Setup 6\ISCC.exe
"@
    exit 1
}

New-Item -ItemType Directory -Path (Join-Path $InstallerDir "output") -Force | Out-Null
Write-Host "ISCC: $iscc" -ForegroundColor Cyan
Write-Host "Version: $ver" -ForegroundColor Cyan
& $iscc "/DMyAppVersion=$ver" (Join-Path $InstallerDir "UgreenNASAdmin_installer.iss")
if ($LASTEXITCODE -ne 0) {
    Write-Error "ISCC beendete mit Code $LASTEXITCODE"
    exit $LASTEXITCODE
}
$out = Join-Path $InstallerDir "output\UgreenNASAdmin_setup_$ver.exe"
Write-Host ""
Write-Host "Fertig: $out" -ForegroundColor Green
