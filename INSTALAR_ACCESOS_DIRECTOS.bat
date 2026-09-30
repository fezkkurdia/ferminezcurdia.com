@echo off
chcp 65001 >nul
title Configurar Accesos Directos - Fermín Ezcurdia
color 0F

cd /d "%~dp0"

echo ======================================================
echo    INSTALADOR DE ACCESOS DIRECTOS EN EL ESCRITORIO
echo ======================================================
echo.
echo Creando los accesos directos en tu Escritorio...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$desktop = [Environment]::GetFolderPath('Desktop');" ^
    "$ws = New-Object -ComObject WScript.Shell;" ^
    "$repo = (Get-Item .).FullName;" ^
    "$galleries = Join-Path $repo 'content\galleries';" ^
    "$bat = Join-Path $repo 'PUBLICAR_WEB.bat';" ^
    "$s1 = $ws.CreateShortcut((Join-Path $desktop '📸 FOTOS DE MI WEB.lnk'));" ^
    "$s1.TargetPath = $galleries;" ^
    "$s1.IconLocation = 'shell32.dll,3'; " ^
    "$s1.Save();" ^
    "$s2 = $ws.CreateShortcut((Join-Path $desktop '🚀 ACTUALIZAR MI WEB.lnk'));" ^
    "$s2.TargetPath = $bat;" ^
    "$s2.WorkingDirectory = $repo;" ^
    "$s2.IconLocation = 'imageres.dll,229';" ^
    "$s2.Save();"

if %errorlevel% equ 0 (
    color 0A
    echo ======================================================
    echo           ¡INSTALACIÓN COMPLETADA!
    echo ======================================================
    echo.
    echo Se han creado 2 accesos directos en tu Escritorio:
    echo.
    echo   1. 📸 FOTOS DE MI WEB   (para pegar o borrar fotos)
    echo   2. 🚀 ACTUALIZAR MI WEB (para publicar los cambios)
    echo.
    echo Ya puedes cerrar esta ventana.
) else (
    color 0C
    echo [ERROR] No se pudieron crear los accesos directos.
)

echo.
pause
