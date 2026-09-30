@echo off
chcp 65001 >nul
title Actualizar Web - Fermín Ezcurdia
color 0F

:: Ir al directorio donde se encuentra este archivo .bat
cd /d "%~dp0"

echo ======================================================
echo          PORTFOLIO WEB - FERMÍN EZCURDIA
echo ======================================================
echo.

:: 1. Comprobar si Git está instalado
where git >nul 2>nul
if %errorlevel% neq 0 (
    color 0C
    echo [ERROR] Git no está instalado en este equipo.
    echo Por favor, contacta con Iñigo para instalarlo.
    echo.
    pause
    exit /b 1
)

:: 2. Comprobar si hay cambios en la carpeta
git status --porcelain > "%temp%\git_status_check.txt"
set /p CAMBIOS=<"%temp%\git_status_check.txt"
del "%temp%\git_status_check.txt" >nul 2>nul

if "%CAMBIOS%"=="" (
    color 0E
    echo No has añadido fotos nuevas ni has hecho cambios.
    echo.
    echo Pasos para añadir fotos:
    echo 1. Abre el acceso directo "📸 FOTOS DE MI WEB".
    echo 2. Pega tus fotos en la galería que quieras.
    echo 3. Vuelve a hacer doble clic en este icono.
    echo.
    echo Presiona cualquier tecla para cerrar esta ventana...
    pause >nul
    exit /b 0
)

:: 3. Procesar y subir cambios
echo [1/3] Preparando fotos nuevas y cambios...
git add .

set FECHA=%DATE% %TIME:~0,5%
echo [2/3] Registrando actualizacion (%FECHA%)...
git commit -m "Fotos actualizadas el %FECHA%" >nul 2>nul

echo [3/3] Subiendo a la web... Por favor, espera unos segundos...
echo.

git push origin main
if %errorlevel% neq 0 (
    color 0C
    echo.
    echo ======================================================
    echo [ERROR] No se pudo subir el contenido.
    echo Comprueba que tienes conexion a internet activa.
    echo Si el problema continua, avisa a Iñigo.
    echo ======================================================
    echo.
    pause
    exit /b 1
)

:: 4. Éxito
color 0A
echo.
echo ======================================================
echo    ¡TODO LISTO! TUS FOTOS SE HAN SUBIDO CON ÉXITO
echo ======================================================
echo.
echo El servidor esta procesando y optimizando tus fotos.
echo En aproximadamente 1 minuto ya estaran visibles en:
echo https://ferminezcurdia.com
echo.
echo Puedes cerrar esta ventana con total tranquilidad.
echo Presiona cualquier tecla para salir...
pause >nul
