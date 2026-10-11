@echo off
chcp 65001 >nul
title Configurar Accesos Directos - Fermín Ezcurdia
color 0F
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\instalar.ps1"
if %errorlevel% geq 9000 (
    echo.
    echo [ERROR] No se ha podido abrir PowerShell.
    pause
)
