# Smoke test end-to-end: recorre todo el CRUD por la puerta de entrada (nginx -> Java -> PHP -> Python -> BD)
# y comprueba codigos HTTP y mensajes exactos del contrato (secciones 7, 8 y checklist de integracion 13).
#
# Uso: .\scripts\smoke-test.ps1 [URL_API]     por defecto http://localhost:8080/api
#      (tambien se puede usar la variable de entorno SMOKE_API_URL)
# Funciona en Windows PowerShell 5.1 y PowerShell 7. Docker solo para revisar los logs de PHP.
# Sale con codigo 1 si algun paso falla. Los monitores SMOKE- se eliminan al final aunque algo falle.
#
# Archivo sin tildes: Windows PowerShell 5.1 lee los .ps1 sin BOM como ANSI. Los textos con tildes
# y los emojis se escriben con escapes \u y se convierten con [regex]::Unescape.

param(
    [Parameter(Position = 0)]
    [string]$Api
)

if (-not $Api) { $Api = if ($env:SMOKE_API_URL) { $env:SMOKE_API_URL } else { 'http://localhost:8080/api' } }
$Api = $Api.TrimEnd('/')

# docker-compose.yml esta en la raiz del repo, una carpeta arriba de este script
$compose = Join-Path (Split-Path -Parent $PSScriptRoot) 'docker-compose.yml'

function ConvertFrom-Escapes([string]$Texto) { [regex]::Unescape($Texto) }

$OK = ConvertFrom-Escapes '\u2705'
$FALLO = ConvertFrom-Escapes '\u274c'
$AVISO = ConvertFrom-Escapes '\u26a0\ufe0f'

$codigosSmoke = @('SMOKE-1', 'SMOKE-2', 'SMOKE-3', 'SMOKE-4')
$script:exitosos = 0
$script:fallidos = 0

# Mensajes exactos del catalogo (seccion 7)
$E04 = 'El nombre es obligatorio'
$E07 = ConvertFrom-Escapes 'El correo no es v\u00e1lido'
$E10 = 'La materia indicada no existe'
$E11Smoke1 = ConvertFrom-Escapes 'No existe un monitor con el c\u00f3digo SMOKE-1'
$E11Smoke404 = ConvertFrom-Escapes 'No existe un monitor con el c\u00f3digo SMOKE-404'
$E12Smoke1 = ConvertFrom-Escapes 'Ya existe un monitor con el c\u00f3digo SMOKE-1'

$nombreCreado = ConvertFrom-Escapes 'Jos\u00e9 Pe\u00f1a Mu\u00f1oz'
$nombreActualizado = ConvertFrom-Escapes 'Jos\u00e9 Pe\u00f1a Mu\u00f1oz \u00d1a\u00f1ez'

# --- Utilidades -----------------------------------------------------------------------------------

# Hace la peticion y devuelve Estado (0 si no hubo conexion), Cuerpo, Tipo y Json (objeto o $null)
function Invoke-Api([string]$Metodo, [string]$Ruta, [string]$Cuerpo) {
    $parametros = @{
        Uri             = "$Api$Ruta"
        Method          = $Metodo
        UseBasicParsing = $true
        TimeoutSec      = 15
        ErrorAction     = 'Stop'
    }
    if ($Cuerpo) {
        # Los \u del cuerpo se convierten en las letras reales y se envian como bytes UTF-8 (asi se
        # prueban las tildes de verdad); en PowerShell 5.1 un -Body de texto se enviaria como ISO-8859-1
        $parametros.Body = [System.Text.Encoding]::UTF8.GetBytes((ConvertFrom-Escapes $Cuerpo))
        $parametros.ContentType = 'application/json'
    }
    if ($PSVersionTable.PSVersion.Major -ge 7) { $parametros.SkipHttpErrorCheck = $true }

    $estado = 0
    $texto = ''
    $tipo = ''
    try {
        $respuesta = Invoke-WebRequest @parametros
        $estado = [int]$respuesta.StatusCode
        $texto = [string]$respuesta.Content
        $tipo = [string]($respuesta.Headers['Content-Type'] -join ', ')
    } catch {
        # PowerShell 5.1 lanza excepcion con los 4xx/5xx: el cuerpo se lee de la respuesta
        $respuestaError = $_.Exception.Response
        if ($respuestaError -is [System.Net.HttpWebResponse]) {
            $estado = [int]$respuestaError.StatusCode
            $tipo = [string]$respuestaError.ContentType
            # Si la respuesta trae Content-Length, Invoke-WebRequest ya leyo el flujo: se rebobina
            $flujo = $respuestaError.GetResponseStream()
            if ($flujo.CanSeek) { $flujo.Position = 0 }
            $lector = New-Object System.IO.StreamReader($flujo, [System.Text.Encoding]::UTF8)
            $texto = $lector.ReadToEnd()
            $lector.Close()
        }
    }

    $json = $null
    if ($texto.Trim()) {
        try { $json = $texto | ConvertFrom-Json } catch { $json = $null }
    }
    [pscustomobject]@{ Estado = $estado; Cuerpo = $texto; Tipo = $tipo; Json = $json }
}

# El cuerpo es exactamente {"error": "<mensaje>"} con una sola clave (regla J8)
function Test-ErrorExacto($Respuesta, [string]$Mensaje) {
    if ($null -eq $Respuesta.Json -or $Respuesta.Json -is [array]) { return $false }
    $propiedades = @($Respuesta.Json.PSObject.Properties)
    ($propiedades.Count -eq 1) -and ($propiedades[0].Name -ceq 'error') -and ($propiedades[0].Value -ceq $Mensaje)
}

function Test-Arreglo($Respuesta) {
    $Respuesta.Cuerpo.TrimStart().StartsWith('[')
}

# Imprime OK o FALLO segun la condicion y lleva la cuenta
function Write-Paso([string]$Descripcion, [bool]$Condicion, $Respuesta, [string]$Detalle) {
    if ($Condicion) {
        $script:exitosos++
        Write-Host "$OK $Descripcion"
    } else {
        $script:fallidos++
        Write-Host "$FALLO $Descripcion"
        if (-not $Detalle) { $Detalle = "obtenido: HTTP $($Respuesta.Estado) $($Respuesta.Cuerpo)" }
        Write-Host "     $Detalle"
    }
}

# Cuenta las peticiones POST /monitores que PHP registro (formato T2: [php-service] POST /monitores -> ...)
function Get-PostsEnPhp {
    $lineas = docker compose -f $compose logs --no-log-prefix php-service 2>$null
    @($lineas | Select-String -SimpleMatch '[php-service] POST /monitores ').Count
}

function Test-PhpDisponible {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { return $false }
    $servicios = docker compose -f $compose ps --status running --services 2>$null
    @($servicios) -contains 'php-service'
}

# Elimina los monitores SMOKE- conocidos y cualquier otro SMOKE- que aparezca en el listado
function Remove-MonitoresSmoke {
    $codigos = [System.Collections.ArrayList]@($codigosSmoke)
    $listado = Invoke-Api 'GET' '/monitores'
    if ($listado.Estado -eq 200 -and $listado.Json) {
        foreach ($monitor in @($listado.Json)) {
            if ($monitor.codigo -like 'SMOKE-*' -and -not $codigos.Contains($monitor.codigo)) {
                [void]$codigos.Add($monitor.codigo)
            }
        }
    }
    foreach ($codigo in $codigos) { [void](Invoke-Api 'DELETE' "/monitores/$codigo") }
}

# --- Pruebas --------------------------------------------------------------------------------------

function Invoke-SmokeTest {
    Write-Host "Smoke test contra $Api"
    Write-Host ''

    $r = Invoke-Api 'GET' '/health'
    if ($r.Estado -eq 0) {
        Write-Host "$FALLO No se pudo conectar con $Api"
        Write-Host (ConvertFrom-Escapes '     \u00bfEst\u00e1 levantado el sistema? docker compose up --build')
        $script:fallidos++
        return
    }
    Write-Paso 'GET /health -> 200 (java-controller)' `
        ($r.Estado -eq 200 -and $r.Json.service -eq 'java-controller' -and $r.Json.status -eq 'ok') $r

    # Por si quedaron datos de una ejecucion anterior interrumpida
    Remove-MonitoresSmoke

    $r = Invoke-Api 'GET' '/materias'
    $sw3 = @($r.Json) | Where-Object { $_.id -eq 1 -and $_.codigo -eq 'SW3' }
    Write-Paso 'GET /materias -> 200 con arreglo que incluye SW3 (id 1) y charset UTF-8' `
        ($r.Estado -eq 200 -and (Test-Arreglo $r) -and $sw3 -and $r.Tipo -match 'application/json.*charset=utf-8') $r `
        "obtenido: HTTP $($r.Estado) $($r.Cuerpo) [$($r.Tipo)]"

    $r = Invoke-Api 'GET' '/monitores'
    Write-Paso 'GET /monitores -> 200 con arreglo' ($r.Estado -eq 200 -and (Test-Arreglo $r)) $r

    $monitor = '{"codigo": "SMOKE-1", "nombre": "Jos\u00e9 Pe\u00f1a Mu\u00f1oz", "correo": "jose.pena@ucaldas.edu.co", "materia_id": 1}'

    $r = Invoke-Api 'POST' '/monitores' $monitor
    Write-Paso 'POST SMOKE-1 -> 201 con materia_nombre' `
        ($r.Estado -eq 201 -and $r.Json.codigo -eq 'SMOKE-1' -and $r.Json.materia_id -eq 1 -and
        $r.Json.materia_nombre -ceq (ConvertFrom-Escapes 'Ingenier\u00eda de Software III')) $r

    $r = Invoke-Api 'POST' '/monitores' $monitor
    Write-Paso "POST SMOKE-1 repetido -> 409 `"$E12Smoke1`"" ($r.Estado -eq 409 -and (Test-ErrorExacto $r $E12Smoke1)) $r

    $r = Invoke-Api 'POST' '/monitores' '{"codigo": "SMOKE-2", "nombre": "Carlos P\u00e9rez", "correo": "carlos@ucaldas", "materia_id": 1}'
    Write-Paso "POST con correo invalido -> 400 `"$E07`"" ($r.Estado -eq 400 -and (Test-ErrorExacto $r $E07)) $r

    # Seccion 13: la peticion sin nombre la rechaza Java; en los logs de PHP no debe aparecer
    $phpDisponible = Test-PhpDisponible
    if ($phpDisponible) {
        Start-Sleep -Seconds 1
        $postsAntes = Get-PostsEnPhp
    }
    $r = Invoke-Api 'POST' '/monitores' '{"codigo": "SMOKE-3", "correo": "sin.nombre@ucaldas.edu.co", "materia_id": 1}'
    Write-Paso "POST sin nombre -> 400 `"$E04`"" ($r.Estado -eq 400 -and (Test-ErrorExacto $r $E04)) $r
    if ($phpDisponible) {
        Start-Sleep -Seconds 1
        $postsDespues = Get-PostsEnPhp
        Write-Paso 'POST sin nombre no llega a PHP (logs de php-service)' ($postsDespues -eq $postsAntes) $r `
            "PHP registro $($postsDespues - $postsAntes) POST /monitores nuevos"
    } else {
        Write-Host "$AVISO  POST sin nombre no llega a PHP: omitido (docker compose no ve php-service en ejecucion)"
    }

    $r = Invoke-Api 'POST' '/monitores' '{"codigo": "SMOKE-4", "nombre": "Laura G\u00f3mez", "correo": "laura.gomez@ucaldas.edu.co", "materia_id": 99}'
    Write-Paso "POST con materia_id 99 -> 400 `"$E10`"" ($r.Estado -eq 400 -and (Test-ErrorExacto $r $E10)) $r

    $r = Invoke-Api 'GET' '/monitores/smoke-1'
    Write-Paso (ConvertFrom-Escapes 'GET /monitores/smoke-1 (min\u00fasculas) -> 200 normalizado y con tildes intactas') `
        ($r.Estado -eq 200 -and $r.Json.codigo -eq 'SMOKE-1' -and $r.Json.nombre -ceq $nombreCreado) $r

    $r = Invoke-Api 'PUT' '/monitores/SMOKE-1' '{"nombre": "Jos\u00e9 Pe\u00f1a Mu\u00f1oz \u00d1a\u00f1ez", "correo": "jose.pena@ucaldas.edu.co", "materia_id": 2}'
    Write-Paso 'PUT SMOKE-1 -> 200 actualizado' `
        ($r.Estado -eq 200 -and $r.Json.nombre -ceq $nombreActualizado -and $r.Json.materia_id -eq 2 -and
        $r.Json.materia_nombre -ceq 'Bases de Datos I') $r

    $r = Invoke-Api 'PUT' '/monitores/SMOKE-404' '{"nombre": "No Existe", "correo": "no.existe@ucaldas.edu.co", "materia_id": 1}'
    Write-Paso "PUT inexistente -> 404 `"$E11Smoke404`"" ($r.Estado -eq 404 -and (Test-ErrorExacto $r $E11Smoke404)) $r

    $r = Invoke-Api 'DELETE' '/monitores/SMOKE-1'
    Write-Paso 'DELETE SMOKE-1 -> 204 sin cuerpo' ($r.Estado -eq 204 -and -not $r.Cuerpo) $r

    $r = Invoke-Api 'DELETE' '/monitores/SMOKE-1'
    Write-Paso "DELETE SMOKE-1 otra vez -> 404 `"$E11Smoke1`"" ($r.Estado -eq 404 -and (Test-ErrorExacto $r $E11Smoke1)) $r

    $r = Invoke-Api 'GET' '/monitores/SMOKE-1'
    Write-Paso "GET SMOKE-1 eliminado -> 404 `"$E11Smoke1`"" ($r.Estado -eq 404 -and (Test-ErrorExacto $r $E11Smoke1)) $r

    Write-Host ''
    if ($script:fallidos -eq 0) {
        Write-Host "$OK Smoke test OK: $($script:exitosos) pasos correctos"
    } else {
        Write-Host "$FALLO Smoke test con fallos: $($script:fallidos) de $($script:exitosos + $script:fallidos) pasos fallaron"
    }
}

$codificacionAnterior = [Console]::OutputEncoding
try {
    # Para que los emojis y las tildes se vean bien en la consola de Windows
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    Invoke-SmokeTest
} finally {
    # Se ejecuta aunque un paso falle o se interrumpa con Ctrl+C
    Remove-MonitoresSmoke
    [Console]::OutputEncoding = $codificacionAnterior
}

if ($script:fallidos -gt 0) { exit 1 }
exit 0
