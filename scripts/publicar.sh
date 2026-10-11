#!/bin/bash
# Publica en ferminezcurdia.com las fotos de la carpeta content/ (versión Mac).
# Lo lanza PUBLICAR_WEB.command. Hace lo mismo que scripts/publicar.ps1:
# preparar fotos -> guardar (commit) -> traer cambios de Iñigo (rebase) ->
# subir (push) -> esperar a que la web muestre la nueva versión.

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO" || exit 1

WEB="${FERMIN_WEB_URL:-https://ferminezcurdia.com}"
RAMA=main
LADO_MAXIMO=3000
TAMANO_MAXIMO_MB=45
MINUTOS_ESPERA="${FERMIN_MINUTOS_ESPERA:-12}"

ROJO=$'\033[31m'; VERDE=$'\033[32m'; AMARILLO=$'\033[33m'; CIAN=$'\033[36m'; GRIS=$'\033[90m'; NORMAL=$'\033[0m'

linea() { echo "======================================================"; }
paso() { echo; echo "${CIAN}$1${NORMAL}"; }
info() { echo "   $1"; }
aviso() { echo "${AMARILLO}   $1${NORMAL}"; }

terminar() {
    echo
    if [ -z "$FERMIN_SIN_PAUSA" ]; then read -r -p "Pulsa Intro para cerrar esta ventana..."; fi
    exit "$1"
}

# fallo "título" "explicación 1" "explicación 2" "detalle técnico"
fallo() {
    echo; linea
    echo "${ROJO}  NO SE HA PUBLICADO: $1${NORMAL}"
    linea
    echo "  $2"
    [ -n "$3" ] && echo "  $3"
    if [ -n "$4" ]; then
        echo; echo "${GRIS}  Detalle técnico (para Iñigo):"
        echo "$4" | sed 's/^/    /'
        echo -n "${NORMAL}"
    fi
    terminar 1
}

# Cómo ve Fermín una ruta: «08_japon/foto.jpg» o «portada/foto.jpg»
ruta_amable() { echo "$1" | sed -e 's#^content/galleries/##' -e 's#^content/home_slides/#portada/#' -e 's#^content/##'; }

clear
linea
echo "         PORTFOLIO WEB - FERMÍN EZCURDIA"
linea

# --- 0. Comprobaciones -------------------------------------------------------
command -v git >/dev/null 2>&1 || fallo "falta un programa" "Git no está instalado en este ordenador." "Avisa a Iñigo para que lo instale."
[ -d .git ] || fallo "la carpeta de la web no está bien instalada" "Avisa a Iñigo." "" "No hay repositorio git en $REPO"

# Si una publicación anterior se quedó a medias, deshacerla (no se pierde ninguna foto)
if [ -d .git/rebase-merge ] || [ -d .git/rebase-apply ]; then git rebase --abort >/dev/null 2>&1; fi

rama_actual="$(git rev-parse --abbrev-ref HEAD 2>/dev/null)"
[ "$rama_actual" = "$RAMA" ] || fallo "la carpeta de la web no está en su estado normal" "Avisa a Iñigo." "" "Rama actual: $rama_actual (se esperaba $RAMA)"

# Sin nombre y correo, git no puede guardar los cambios: se configuran solos
[ -n "$(git config user.name)" ] || git config user.name "Fermín Ezcurdia"
[ -n "$(git config user.email)" ] || git config user.email "fermin@ferminezcurdia.com"

# --- 1. Preparar fotos -------------------------------------------------------
paso "[1/4] Revisando tus fotos..."

reducidas=0
reducir_foto() {
    # Reduce a tamaño web (y convierte TIFF/BMP en JPG) con sips, que viene con macOS
    # y conserva los datos de la foto (orientación, título, perfil de color).
    local ruta="$1" ext ancho alto lado destino base n
    command -v sips >/dev/null 2>&1 || return 0
    ext="$(echo "${ruta##*.}" | tr '[:upper:]' '[:lower:]')"
    case "$ext" in
        jpg|jpeg|png)
            ancho=$(sips -g pixelWidth "$ruta" 2>/dev/null | awk '/pixelWidth/{print $2}')
            alto=$(sips -g pixelHeight "$ruta" 2>/dev/null | awk '/pixelHeight/{print $2}')
            [ -n "$ancho" ] && [ -n "$alto" ] || return 0
            lado=$(( ancho > alto ? ancho : alto ))
            if [ "$lado" -gt "$LADO_MAXIMO" ]; then
                if sips -Z "$LADO_MAXIMO" -s formatOptions 92 "$ruta" >/dev/null 2>&1; then
                    reducidas=$((reducidas + 1))
                else
                    aviso "No se ha podido reducir «$(basename "$ruta")»; se subirá tal cual."
                fi
            fi ;;
        tif|tiff|bmp)
            base="${ruta%.*}"; destino="$base.jpg"; n=2
            while [ -e "$destino" ]; do destino="$base-$n.jpg"; n=$((n + 1)); done
            if sips -Z "$LADO_MAXIMO" -s format jpeg -s formatOptions 92 "$ruta" --out "$destino" >/dev/null 2>&1; then
                rm -f "$ruta"; reducidas=$((reducidas + 1))
            else
                aviso "No se ha podido convertir «$(basename "$ruta")»; se subirá tal cual."
            fi ;;
    esac
}

while IFS= read -r -d '' rel; do
    [ -f "$rel" ] && reducir_foto "$rel"
done < <(git -c core.quotepath=false ls-files -z --others --modified --exclude-standard -- content)
command -v sips >/dev/null 2>&1 || aviso "No se pueden reducir fotos grandes en este ordenador; se suben tal cual."
[ "$reducidas" -gt 0 ] && info "$reducidas foto(s) reducidas a tamaño web (las originales de tu cámara o Lightroom no se tocan)."

# Archivos que no son fotos: no se publican, pero se avisa
primero=1
while IFS= read -r -d '' rel; do
    case "$(basename "$rel")" in .DS_Store|Thumbs.db|desktop.ini|*.tmp) continue ;; esac
    [ $primero = 1 ] && aviso "Estos archivos no son fotos que la web pueda mostrar y NO se publican:" && primero=0
    nota=""
    echo "$rel" | grep -qiE '\.(cr2|cr3|nef|arw|dng|raf|orf|rw2|pef|srw)$' && nota=" (es un RAW: expórtalo como JPG)"
    aviso "   - $(ruta_amable "$rel")$nota"
done < <(git -c core.quotepath=false ls-files -z --others --ignored --exclude-standard -- content)

git add -A -- content

# Archivos enormes: GitHub no los acepta, se quedan fuera
while IFS= read -r -d '' rel; do
    if [ -f "$rel" ] && [ "$(wc -c < "$rel")" -gt $((TAMANO_MAXIMO_MB * 1024 * 1024)) ]; then
        git reset -q -- "$rel"
        aviso "«$(ruta_amable "$rel")» es demasiado grande y NO se publica. Expórtala más pequeña (JPG)."
    fi
done < <(git -c core.quotepath=false diff --cached --name-only -z --diff-filter=AM)

# --- 2. Guardar los cambios --------------------------------------------------
paso "[2/4] Guardando los cambios..."
if ! git diff --cached --quiet; then
    if ! salida=$(git commit -q -m "Fotos actualizadas el $(date '+%d/%m/%Y %H:%M')" 2>&1); then
        fallo "no se han podido guardar los cambios" "Tus fotos siguen en la carpeta, no se ha perdido nada." "Avisa a Iñigo." "$salida"
    fi
    altas=$(git diff --name-only --diff-filter=AM HEAD~1 HEAD -- content | wc -l | tr -d ' ')
    bajas=$(git diff --name-only --diff-filter=D HEAD~1 HEAD -- content | wc -l | tr -d ' ')
    info "Fotos nuevas o cambiadas: $altas   Fotos retiradas: $bajas"
fi

# --- 3. Subir ----------------------------------------------------------------
paso "[3/4] Subiendo a internet..."
if ! salida=$(git fetch -q origin "$RAMA" 2>&1); then
    fallo "no hay conexión con GitHub" "Comprueba que tienes internet y vuelve a abrir este icono." "Tus cambios están guardados y se subirán la próxima vez." "$salida"
fi

pendientes=$(git rev-list --count "origin/$RAMA..HEAD")
atrasados=$(git rev-list --count "HEAD..origin/$RAMA")

if [ "$pendientes" -eq 0 ]; then
    # Nada que subir: ponerse al día con lo último de la web y salir
    [ "$atrasados" -gt 0 ] && git merge -q --ff-only "origin/$RAMA" >/dev/null 2>&1
    echo; linea
    echo "${AMARILLO}  No has añadido, cambiado ni borrado fotos.${NORMAL}"
    linea
    echo "  Para publicar fotos:"
    echo "   1. Abre la carpeta \"FOTOS DE MI WEB\" (o \"FOTOS DE LA PORTADA\")."
    echo "   2. Pega tus fotos en la galería que quieras."
    echo "   3. Vuelve a abrir \"ACTUALIZAR MI WEB\"."
    terminar 0
fi

if [ "$atrasados" -gt 0 ]; then
    # Iñigo ha cambiado algo de la web: traerlo y colocar las fotos encima
    if ! salida=$(git rebase -q --autostash "origin/$RAMA" 2>&1); then
        git rebase --abort >/dev/null 2>&1
        fallo "Iñigo ha cambiado lo mismo que tú a la vez" "Tus fotos están guardadas en tu ordenador, no se ha perdido nada." "Avisa a Iñigo para que lo junte; después vuelve a abrir el icono." "$salida"
    fi
fi

if ! salida=$(git push -q origin "HEAD:$RAMA" 2>&1); then
    if echo "$salida" | grep -qiE 'authentication|403|denied|could not read username|permission|401'; then
        fallo "GitHub no ha aceptado tu usuario" "Tus cambios están guardados en tu ordenador." "Avisa a Iñigo para que revise el acceso a GitHub." "$salida"
    elif echo "$salida" | grep -qiE 'resolve host|unable to access|timed out|could not connect|network|connection'; then
        fallo "no hay conexión con GitHub" "Comprueba que tienes internet y vuelve a abrir este icono." "Tus cambios están guardados y se subirán la próxima vez." "$salida"
    else
        fallo "GitHub no ha aceptado la subida" "Tus cambios están guardados en tu ordenador." "Vuelve a abrir el icono; si vuelve a fallar, avisa a Iñigo." "$salida"
    fi
fi
mi_version=$(git rev-parse HEAD)

# --- 4. Esperar a que la web se actualice ------------------------------------
paso "[4/4] Esperando a que la web se actualice (suele tardar entre 2 y 5 minutos)..."
info "Puedes cerrar esta ventana si quieres: la web se actualizará igualmente."

publicado=""; estado=""; ya_descargado=0
limite=$(( $(date +%s) + ${MINUTOS_ESPERA%.*} * 60 ))
while [ "$(date +%s)" -lt "$limite" ]; do
    estado=$(curl -fsS --max-time 20 -H 'Cache-Control: no-cache' "$WEB/estado-publicacion.json?t=$(date +%s)" 2>/dev/null)
    version=$(printf '%s' "$estado" | sed -n 's/.*"commit": *"\([0-9a-f]*\)".*/\1/p' | head -n1)
    if [ -n "$version" ]; then
        if [ "$version" = "$mi_version" ] || git merge-base --is-ancestor "$mi_version" "$version" 2>/dev/null; then
            publicado=1; break
        fi
        # La web puede tener ya una versión posterior que incluye la nuestra
        if [ $ya_descargado = 0 ] && ! git cat-file -e "$version^{commit}" 2>/dev/null; then
            git fetch -q origin "$RAMA" 2>/dev/null; ya_descargado=1
            git merge-base --is-ancestor "$mi_version" "$version" 2>/dev/null && { publicado=1; break; }
        fi
    fi
    printf '.'
    sleep 15
done
echo

if [ -z "$publicado" ]; then
    echo; linea
    echo "${AMARILLO}  TUS FOTOS ESTÁN SUBIDAS, PERO LA WEB AÚN NO HA CAMBIADO${NORMAL}"
    linea
    echo "  A veces tarda más de lo normal. Mira la web dentro de un rato:"
    echo "  $WEB"
    echo "  Si mañana sigue sin verse lo nuevo, avisa a Iñigo."
    terminar 0
fi

echo; linea
echo "${VERDE}   ¡TODO LISTO! TUS FOTOS YA ESTÁN EN LA WEB${NORMAL}"
linea
echo "  $WEB"
echo "  (si no ves los cambios, recarga la página con Cmd + Mayúsculas + R)"
avisos=$(printf '%s' "$estado" | python3 -c 'import json,sys
try:
    [print(a) for a in json.load(sys.stdin).get("avisos", [])]
except Exception:
    pass' 2>/dev/null)
if [ -n "$avisos" ]; then
    echo
    aviso "Pero ojo, la web ha avisado de esto:"
    while IFS= read -r a; do aviso " - $a"; done <<< "$avisos"
fi
terminar 0
