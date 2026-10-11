#!/bin/bash
# Botón "ACTUALIZAR MI WEB" para Mac: todo el trabajo lo hace scripts/publicar.sh
exec /bin/bash "$(cd "$(dirname "$0")" && pwd)/scripts/publicar.sh"
