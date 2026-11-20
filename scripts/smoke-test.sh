#!/usr/bin/env bash
# Smoke test end-to-end: recorre todo el CRUD por la puerta de entrada (nginx -> Java -> PHP -> Python -> BD)
# y comprueba códigos HTTP y mensajes exactos del contrato (§7, §8 y checklist de integración §13).
#
# Uso: ./scripts/smoke-test.sh [URL_API]      por defecto http://localhost:8080/api
#      (también se puede usar la variable SMOKE_API_URL)
# Requisitos: bash y curl. Docker solo para comprobar en los logs que PHP no recibe los 400 de Java.
# Sale con código 1 si algún paso falla. Los monitores SMOKE- se eliminan al final aunque algo falle.
#
# Las condiciones de cada paso se pasan entre comillas simples a `todas`, que las evalúa después:
# por eso shellcheck cree que las funciones no se usan (SC2329) y avisa de las comillas (SC2016).
# shellcheck disable=SC2016,SC2329
set -uo pipefail

API="${1:-${SMOKE_API_URL:-http://localhost:8080/api}}"
API="${API%/}"

# docker compose (para leer los logs de PHP) debe ejecutarse en la raíz del repo
cd "$(dirname "$0")/.." || exit 1

CODIGOS_SMOKE=(SMOKE-1 SMOKE-2 SMOKE-3 SMOKE-4)
CUERPO_TMP="$(mktemp)"
PETICION_TMP="$(mktemp)"
EXITOSOS=0
FALLIDOS=0

# Mensajes exactos del catálogo §7
E04="El nombre es obligatorio"
E07="El correo no es válido"
E10="La materia indicada no existe"
E11_SMOKE_1="No existe un monitor con el código SMOKE-1"
E11_SMOKE_404="No existe un monitor con el código SMOKE-404"
E12_SMOKE_1="Ya existe un monitor con el código SMOKE-1"

# --- Utilidades -----------------------------------------------------------------------------------

# peticion MÉTODO RUTA [CUERPO_JSON] -> deja ESTADO (000 si no hubo conexión), CUERPO y TIPO
peticion() {
    local metodo="$1" ruta="$2" datos="${3:-}" salida
    local args=(-sS -o "$CUERPO_TMP" -w '%{http_code}\n%{content_type}' -X "$metodo"
        --connect-timeout 5 --max-time 15)
    if [ -n "$datos" ]; then
        # El cuerpo va por archivo y no como argumento: en Git Bash (Windows) curl recibe los
        # argumentos en la página de códigos ANSI y las tildes llegarían corruptas
        printf '%s' "$datos" > "$PETICION_TMP"
        args+=(-H 'Content-Type: application/json' --data-binary "@$PETICION_TMP")
    fi
    if salida="$(curl "${args[@]}" "$API$ruta" 2>/dev/null)"; then
        ESTADO="$(sed -n 1p <<< "$salida")"
        TIPO="$(sed -n 2p <<< "$salida")"
    else
        ESTADO="000"
        TIPO=""
        : > "$CUERPO_TMP"
    fi
    CUERPO="$(cat "$CUERPO_TMP")"
}

# Escapa un texto para usarlo literal dentro de una regex extendida
literal() {
    sed 's/[][\.*^$+?(){}|/]/\\&/g' <<< "$1"
}

# El cuerpo contiene "clave": "valor" (texto)
tiene_texto() {
    grep -Eq "\"$1\"[[:space:]]*:[[:space:]]*\"$(literal "$2")\"" <<< "$CUERPO"
}

# El cuerpo contiene "clave": número
tiene_numero() {
    grep -Eq "\"$1\"[[:space:]]*:[[:space:]]*$2([^0-9.]|$)" <<< "$CUERPO"
}

# El cuerpo es exactamente {"error": "<mensaje>"} con una sola clave (J8)
es_error() {
    local mensaje
    mensaje="$(sed -n 's/^[[:space:]]*{[[:space:]]*"error"[[:space:]]*:[[:space:]]*"\(.*\)"[[:space:]]*}[[:space:]]*$/\1/p' <<< "$CUERPO")"
    [ "$mensaje" = "$1" ]
}

es_arreglo() {
    grep -Eq '^[[:space:]]*\[' <<< "$CUERPO"
}

# registrar "descripción" "detalle si falla" condición...  -> imprime ✅ o ❌
registrar() {
    local descripcion="$1" detalle="$2"
    shift 2
    if "$@"; then
        EXITOSOS=$((EXITOSOS + 1))
        echo "✅ $descripcion"
    else
        FALLIDOS=$((FALLIDOS + 1))
        echo "❌ $descripcion"
        echo "     $detalle"
    fi
}

# Todas las condiciones de un paso deben cumplirse
todas() {
    local condicion
    for condicion in "$@"; do
        eval "$condicion" || return 1
    done
}

obtenido() {
    echo "obtenido: HTTP $ESTADO $CUERPO"
}

# Cuenta las peticiones POST /monitores que PHP registró (formato T2: [php-service] POST /monitores -> ...)
posts_en_php() {
    docker compose logs --no-log-prefix php-service 2>/dev/null | grep -c '\[php-service\] POST /monitores ' || true
}

php_disponible() {
    command -v docker > /dev/null 2>&1 &&
        docker compose ps --status running --services 2>/dev/null | grep -qx php-service
}

# Elimina los monitores SMOKE- conocidos y cualquier otro SMOKE- que aparezca en el listado
limpiar() {
    local codigo listado
    listado="$(curl -s --max-time 10 "$API/monitores" 2>/dev/null |
        grep -Eo '"codigo"[[:space:]]*:[[:space:]]*"SMOKE-[^"]*"' | grep -Eo 'SMOKE-[^"]*' || true)"
    # $listado sin comillas a propósito: un código por palabra (los códigos no tienen espacios)
    # shellcheck disable=SC2086
    for codigo in "${CODIGOS_SMOKE[@]}" $listado; do
        curl -s -o /dev/null --max-time 10 -X DELETE "$API/monitores/$codigo" 2>/dev/null || true
    done
}

al_salir() {
    limpiar
    rm -f "$CUERPO_TMP" "$PETICION_TMP"
}
trap al_salir EXIT
trap 'exit 130' INT TERM

# --- Pruebas --------------------------------------------------------------------------------------

echo "Smoke test contra $API"
echo

peticion GET /health
if [ "$ESTADO" = "000" ]; then
    echo "❌ No se pudo conectar con $API"
    echo "     ¿Está levantado el sistema? docker compose up --build"
    exit 1
fi
registrar "GET /health -> 200 (java-controller)" "$(obtenido)" \
    todas '[ "$ESTADO" = 200 ]' 'tiene_texto service java-controller' 'tiene_texto status ok'

# Por si quedaron datos de una ejecución anterior interrumpida
limpiar

peticion GET /materias
registrar "GET /materias -> 200 con arreglo que incluye SW3 (id 1) y charset UTF-8" "$(obtenido) [$TIPO]" \
    todas '[ "$ESTADO" = 200 ]' 'es_arreglo' 'tiene_numero id 1' 'tiene_texto codigo SW3' \
    'grep -iq "application/json.*charset=utf-8" <<< "$TIPO"'

peticion GET /monitores
registrar "GET /monitores -> 200 con arreglo" "$(obtenido)" \
    todas '[ "$ESTADO" = 200 ]' 'es_arreglo'

MONITOR='{"codigo": "SMOKE-1", "nombre": "José Peña Muñoz", "correo": "jose.pena@ucaldas.edu.co", "materia_id": 1}'

peticion POST /monitores "$MONITOR"
registrar "POST SMOKE-1 -> 201 con materia_nombre" "$(obtenido)" \
    todas '[ "$ESTADO" = 201 ]' 'tiene_texto codigo SMOKE-1' 'tiene_numero materia_id 1' \
    'tiene_texto materia_nombre "Ingeniería de Software III"'

peticion POST /monitores "$MONITOR"
registrar "POST SMOKE-1 repetido -> 409 \"$E12_SMOKE_1\"" "$(obtenido)" \
    todas '[ "$ESTADO" = 409 ]' 'es_error "$E12_SMOKE_1"'

peticion POST /monitores '{"codigo": "SMOKE-2", "nombre": "Carlos Pérez", "correo": "carlos@ucaldas", "materia_id": 1}'
registrar "POST con correo inválido -> 400 \"$E07\"" "$(obtenido)" \
    todas '[ "$ESTADO" = 400 ]' 'es_error "$E07"'

# §13: la petición sin nombre la rechaza Java; en los logs de PHP no debe aparecer
php_ok=false
if php_disponible; then
    php_ok=true
    sleep 1
    posts_antes="$(posts_en_php)"
fi
peticion POST /monitores '{"codigo": "SMOKE-3", "correo": "sin.nombre@ucaldas.edu.co", "materia_id": 1}'
registrar "POST sin nombre -> 400 \"$E04\"" "$(obtenido)" \
    todas '[ "$ESTADO" = 400 ]' 'es_error "$E04"'
if $php_ok; then
    sleep 1
    posts_despues="$(posts_en_php)"
    registrar "POST sin nombre no llega a PHP (logs de php-service)" \
        "PHP registró $((posts_despues - posts_antes)) POST /monitores nuevos" \
        [ "$posts_despues" = "$posts_antes" ]
else
    echo "⚠️  POST sin nombre no llega a PHP: omitido (docker compose no ve php-service en ejecución)"
fi

peticion POST /monitores '{"codigo": "SMOKE-4", "nombre": "Laura Gómez", "correo": "laura.gomez@ucaldas.edu.co", "materia_id": 99}'
registrar "POST con materia_id 99 -> 400 \"$E10\"" "$(obtenido)" \
    todas '[ "$ESTADO" = 400 ]' 'es_error "$E10"'

peticion GET /monitores/smoke-1
registrar "GET /monitores/smoke-1 (minúsculas) -> 200 normalizado y con tildes intactas" "$(obtenido)" \
    todas '[ "$ESTADO" = 200 ]' 'tiene_texto codigo SMOKE-1' 'tiene_texto nombre "José Peña Muñoz"'

peticion PUT /monitores/SMOKE-1 '{"nombre": "José Peña Muñoz Ñañez", "correo": "jose.pena@ucaldas.edu.co", "materia_id": 2}'
registrar "PUT SMOKE-1 -> 200 actualizado" "$(obtenido)" \
    todas '[ "$ESTADO" = 200 ]' 'tiene_texto nombre "José Peña Muñoz Ñañez"' 'tiene_numero materia_id 2' \
    'tiene_texto materia_nombre "Bases de Datos I"'

peticion PUT /monitores/SMOKE-404 '{"nombre": "No Existe", "correo": "no.existe@ucaldas.edu.co", "materia_id": 1}'
registrar "PUT inexistente -> 404 \"$E11_SMOKE_404\"" "$(obtenido)" \
    todas '[ "$ESTADO" = 404 ]' 'es_error "$E11_SMOKE_404"'

peticion DELETE /monitores/SMOKE-1
registrar "DELETE SMOKE-1 -> 204 sin cuerpo" "$(obtenido)" \
    todas '[ "$ESTADO" = 204 ]' '[ -z "$CUERPO" ]'

peticion DELETE /monitores/SMOKE-1
registrar "DELETE SMOKE-1 otra vez -> 404 \"$E11_SMOKE_1\"" "$(obtenido)" \
    todas '[ "$ESTADO" = 404 ]' 'es_error "$E11_SMOKE_1"'

peticion GET /monitores/SMOKE-1
registrar "GET SMOKE-1 eliminado -> 404 \"$E11_SMOKE_1\"" "$(obtenido)" \
    todas '[ "$ESTADO" = 404 ]' 'es_error "$E11_SMOKE_1"'

echo
if [ "$FALLIDOS" -eq 0 ]; then
    echo "✅ Smoke test OK: $EXITOSOS pasos correctos"
    exit 0
fi
echo "❌ Smoke test con fallos: $FALLIDOS de $((EXITOSOS + FALLIDOS)) pasos fallaron"
exit 1
