@echo off
REM Doppelklick = Installer bauen (ohne .ps1 im Editor zu oeffnen)
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0BUILD_INSTALLER.ps1"
if errorlevel 1 pause
exit /b %ERRORLEVEL%
