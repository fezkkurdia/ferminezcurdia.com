#!/bin/bash
# Configuración inicial en un Mac (la ejecuta Iñigo una vez): accesos en el
# Escritorio, identidad de git y acceso a GitHub.
REPO="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO" || exit 1
ESCRITORIO="$HOME/Desktop"

echo "======================================================"
echo "   INSTALADOR DE ACCESOS DIRECTOS EN EL ESCRITORIO"
echo "======================================================"
echo

if ! command -v git >/dev/null 2>&1; then
    echo "[ERROR] Git no está instalado. Ejecuta 'xcode-select --install' y repite."
    read -r -p "Pulsa Intro para cerrar..."; exit 1
fi

[ -n "$(git config user.name)" ] || git config user.name "Fermín Ezcurdia"
[ -n "$(git config user.email)" ] || git config user.email "fermin@ferminezcurdia.com"
echo "[OK] Los cambios se guardarán a nombre de: $(git config user.name) <$(git config user.email)>"

chmod +x "$REPO/PUBLICAR_WEB.command" "$REPO/scripts/publicar.sh"
ln -sfn "$REPO/content/galleries" "$ESCRITORIO/📸 FOTOS DE MI WEB"
ln -sfn "$REPO/content/home_slides" "$ESCRITORIO/🖼️ FOTOS DE LA PORTADA"
# Un pequeño lanzador (un enlace no serviría: el botón necesita saber dónde está la web)
cat > "$ESCRITORIO/🚀 ACTUALIZAR MI WEB.command" <<LANZADOR
#!/bin/bash
exec /bin/bash "$REPO/scripts/publicar.sh"
LANZADOR
chmod +x "$ESCRITORIO/🚀 ACTUALIZAR MI WEB.command"
echo "[OK] Accesos creados en el Escritorio."

echo
echo "Comprobando el acceso a GitHub (si te pide usuario, inicia sesión)..."
if salida=$(git push --dry-run origin HEAD:main 2>&1); then
    echo "[OK] Este ordenador puede publicar en la web."
else
    echo "[ERROR] Este ordenador todavía no puede publicar en GitHub:"
    echo "$salida" | sed 's/^/   /'
    read -r -p "Pulsa Intro para cerrar..."; exit 1
fi

echo
echo "¡INSTALACIÓN COMPLETADA!"
echo "  1. 📸 FOTOS DE MI WEB      (galerías: pegar o borrar fotos)"
echo "  2. 🖼️ FOTOS DE LA PORTADA  (fotos que pasan en la página de inicio)"
echo "  3. 🚀 ACTUALIZAR MI WEB    (publicar los cambios)"
read -r -p "Pulsa Intro para cerrar..."
