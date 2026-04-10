@echo off
setlocal
chcp 65001 >nul
title NAS-Admin Builder Starter

echo ==========================================
echo Ugreen NAS Admin - Windows Build Starter
echo ==========================================

set "PYTHON_EXE="
where py >nul 2>nul
if %errorlevel%==0 (
    set "PYTHON_EXE=py -3"
) else (
    where python >nul 2>nul
    if %errorlevel%==0 set "PYTHON_EXE=python"
)

if "%PYTHON_EXE%"=="" (
    echo.
    echo [FEHLER] Kein Python im PATH gefunden.
    echo Bitte Python installieren oder PATH korrigieren.
    pause
    exit /b 1
)

echo Starte mit: %PYTHON_EXE%
%PYTHON_EXE% builder.py
if %errorlevel% neq 0 (
    echo.
    echo [FEHLER] Build fehlgeschlagen.
    pause
    exit /b %errorlevel%
)

echo.
echo [OK] Build abgeschlossen.
pause