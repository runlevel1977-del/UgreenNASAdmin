@echo off
setlocal
chcp 65001 >nul
title NAS-Admin Builder Starter

echo ==========================================
echo Ugreen NAS Admin - Windows Build Starter
echo ==========================================

cd /d "%~dp0.."

set "PYTHON_EXE="
where py >nul 2>nul
if %errorlevel%==0 (
    rem Prefer 3.12 — PyInstaller + python3xx.dll is unstable on 3.13/3.14
    py -3.12 -c "import sys" >nul 2>nul
    if %errorlevel%==0 (
        set "PYTHON_EXE=py -3.12"
    ) else (
        set "PYTHON_EXE=py -3"
    )
) else (
    where python >nul 2>nul
    if %errorlevel%==0 set "PYTHON_EXE=python"
)

if "%PYTHON_EXE%"=="" (
    echo.
    echo [FEHLER] Kein Python im PATH gefunden.
    echo Bitte Python 3.12 installieren oder PATH korrigieren.
    echo Optional: set UGREEN_BUILD_PYTHON=C:\Pfad\zu\python.exe
    pause
    exit /b 1
)

echo Starte mit: %PYTHON_EXE% packaging\builder.py
%PYTHON_EXE% packaging\builder.py
if %errorlevel% neq 0 (
    echo.
    echo [FEHLER] Build fehlgeschlagen.
    pause
    exit /b %errorlevel%
)

echo.
echo [OK] Build abgeschlossen.
pause
