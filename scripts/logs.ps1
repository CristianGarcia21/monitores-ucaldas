# Muestra en vivo los logs de un servicio (Ctrl+C para salir).
# Uso: .\scripts\logs.ps1 <servicio>   ej.: .\scripts\logs.ps1 php-service
# Texto sin tildes: Windows PowerShell 5.1 lee los .ps1 sin BOM como ANSI.

param(
    [Parameter(Position = 0)]
    [string]$Servicio
)

$ErrorActionPreference = 'Stop'

# docker-compose.yml esta en la raiz del repo, una carpeta arriba de este script
$compose = Join-Path (Split-Path -Parent $PSScriptRoot) 'docker-compose.yml'

$servicios = @(docker compose -f $compose config --services)
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $Servicio -or $servicios -notcontains $Servicio) {
    Write-Host 'Uso: .\scripts\logs.ps1 <servicio>'
    Write-Host 'Servicios disponibles:'
    $servicios | ForEach-Object { Write-Host "  - $_" }
    exit 1
}

docker compose -f $compose logs -f $Servicio
exit $LASTEXITCODE
