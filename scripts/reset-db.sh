#!/usr/bin/env bash
# Reinicia la base de datos desde cero: borra el volumen y vuelve a ejecutar database/init.sql.
# Uso: ./scripts/reset-db.sh   (desde cualquier carpeta del repo)
set -euo pipefail

# docker compose debe ejecutarse en la raíz del repo, donde está docker-compose.yml
cd "$(dirname "$0")/.."

echo "Deteniendo los servicios y borrando el volumen de la base de datos..."
docker compose down -v

echo "Levantando la base de datos..."
docker compose up -d --wait database

echo "Listo: base de datos reiniciada con los datos de database/init.sql"
