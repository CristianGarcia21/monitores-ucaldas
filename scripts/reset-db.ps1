# Reinicia la base de datos desde cero: borra el volumen y vuelve a ejecutar database/init.sql.
# Uso: .\scripts\reset-db.ps1   (desde cualquier carpeta del repo)
# Texto sin tildes: Windows PowerShell 5.1 lee los .ps1 sin BOM como ANSI.

$ErrorActionPreference = 'Stop'

# docker-compose.yml esta en la raiz del repo, una carpeta arriba de este script
$compose = Join-Path (Split-Path -Parent $PSScriptRoot) 'docker-compose.yml'

Write-Host 'Deteniendo los servicios y borrando el volumen de la base de datos...'
docker compose -f $compose down -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host 'Levantando la base de datos...'
docker compose -f $compose up -d --wait database
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host 'Listo: base de datos reiniciada con los datos de database/init.sql'
