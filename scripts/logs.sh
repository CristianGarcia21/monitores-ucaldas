#!/usr/bin/env bash
# Muestra en vivo los logs de un servicio (Ctrl+C para salir).
# Uso: ./scripts/logs.sh <servicio>   ej.: ./scripts/logs.sh php-service
set -euo pipefail

# docker compose debe ejecutarse en la raíz del repo, donde está docker-compose.yml
cd "$(dirname "$0")/.."

servicios="$(docker compose config --services)"

if [ "$#" -ne 1 ] || ! grep -qx -- "$1" <<< "$servicios"; then
    echo "Uso: ./scripts/logs.sh <servicio>" >&2
    echo "Servicios disponibles:" >&2
    echo "$servicios" | sed 's/^/  - /' >&2
    exit 1
fi

docker compose logs -f "$1"
