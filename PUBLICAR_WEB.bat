@echo off
chcp 65001 >nul
title Actualizar Web - Fermín Ezcurdia
color 0F
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\publicar.ps1"
if %errorlevel% geq 9000 (
    echo.
    echo [ERROR] No se ha podido abrir el programa de publicacion.
    echo Avisa a Iñigo.
    pause
)
