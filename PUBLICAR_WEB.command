#!/bin/bash
# Ir al directorio del script
cd "$(dirname "$0")"

echo "======================================================"
echo "         PORTFOLIO WEB - FERMÍN EZCURDIA"
echo "======================================================"
echo ""

# Comprobar si hay cambios
if [ -z "$(git status --porcelain)" ]; then
    echo "No has añadido fotos nuevas ni has hecho cambios."
    echo ""
    echo "Pasos para añadir fotos:"
    echo "1. Abre la carpeta content/galleries."
    echo "2. Pega tus fotos en la galería que quieras."
    echo "3. Vuelve a ejecutar este archivo."
    echo ""
    read -p "Presiona Enter para salir..."
    exit 0
fi

echo "[1/3] Preparando fotos nuevas..."
git add .

FECHA=$(date "+%Y-%m-%d %H:%M")
echo "[2/3] Registrando actualización ($FECHA)..."
git commit -m "Fotos actualizadas el $FECHA" >/dev/null 2>&1

echo "[3/3] Subiendo a la web..."
if git push origin main; then
    echo ""
    echo "======================================================"
    echo "   ¡TODO LISTO! TUS FOTOS SE HAN SUBIDO CON ÉXITO"
    echo "======================================================"
    echo ""
    echo "En aproximadamente 1 minuto estarán visibles en:"
    echo "https://ferminezcurdia.com"
else
    echo ""
    echo "[ERROR] No se pudo subir. Comprueba tu conexión a internet."
fi

echo ""
read -p "Presiona Enter para cerrar esta ventana..."
