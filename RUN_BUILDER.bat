@echo off
title NAS-Admin Builder Starter
echo 🚀 Starte Builder...
python builder.py
if %errorlevel% neq 0 (
    echo.
    echo ❌ Da gab es ein Problem!
    pause
)