<?php

declare(strict_types=1);

/**
 * Servicio PHP - intermediario entre Java y Python.
 *
 * Decide qué hacer según el método y la ruta (docs/api-contract.md, sección PHP):
 *   GET /materias · GET|POST /monitores · GET|PUT|DELETE /monitores/{codigo} · GET /health
 * Cualquier otra ruta responde 404 (E13) y un método no soportado en una ruta válida, 405 (E14).
 */

require_once __DIR__ . '/PythonClient.php';

const SERVICIO = 'php-service';

/** Resultados posibles de resolverRuta(). */
const RUTA_ENCONTRADA = 'encontrada';
const RUTA_NO_ENCONTRADA = 'no_encontrada';
const METODO_NO_PERMITIDO = 'metodo_no_permitido';

/**
 * Tabla de rutas permitidas: patrón de la ruta => métodos HTTP aceptados.
 * Sin barra final: "/monitores/" no coincide con ningún patrón (regla H1).
 *
 * @return array<string, list<string>>
 */
function obtenerTablaRutas(): array
{
    return [
        '#^/materias$#D' => ['GET'],
        '#^/monitores$#D' => ['GET', 'POST'],
        '#^/monitores/([^/]+)$#D' => ['GET', 'PUT', 'DELETE'],
    ];
}

/**
 * Busca la ruta en la tabla y valida el método.
 *
 * @return array{estado: string, codigo: ?string}
 */
function resolverRuta(string $metodo, string $ruta): array
{
    foreach (obtenerTablaRutas() as $patron => $metodosPermitidos) {
        if (preg_match($patron, $ruta, $coincidencias) !== 1) {
            continue;
        }

        if (!in_array($metodo, $metodosPermitidos, true)) {
            return ['estado' => METODO_NO_PERMITIDO, 'codigo' => null];
        }

        return ['estado' => RUTA_ENCONTRADA, 'codigo' => $coincidencias[1] ?? null];
    }

    return ['estado' => RUTA_NO_ENCONTRADA, 'codigo' => null];
}

/**
 * Envía la respuesta JSON. Con cuerpo nulo (204) no se imprime nada.
 */
function responder(int $estado, ?string $cuerpo): void
{
    http_response_code($estado);

    if ($cuerpo === null) {
        header_remove('Content-Type');
        return;
    }

    header('Content-Type: application/json; charset=utf-8');
    echo $cuerpo;
}

/**
 * Respuesta de error con el formato único del contrato: {"error": "<mensaje>"}.
 */
function responderError(int $estado, string $mensaje): void
{
    responder($estado, json_encode(['error' => $mensaje], JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR));
}

/**
 * Reenvía la petición a Python y devuelve su respuesta tal cual (contrato H7).
 * Con 204, o cualquier respuesta sin cuerpo, no se imprime nada (H5).
 */
function reenviarAPython(string $metodo, string $ruta): void
{
    $cuerpoEntrante = file_get_contents('php://input');

    [$estado, $cuerpo] = (new PythonClient())->forward(
        $metodo,
        $ruta,
        $cuerpoEntrante === false ? null : $cuerpoEntrante
    );

    responder($estado, $estado === 204 || $cuerpo === '' ? null : $cuerpo);
}

/**
 * Registra una línea por petición: [php-service] MÉTODO RUTA -> STATUS (ms) (contrato T2).
 */
function registrarPeticion(string $metodo, string $ruta, float $inicio): void
{
    $milisegundos = (int) round((microtime(true) - $inicio) * 1000);
    $estado = http_response_code();
    error_log(sprintf('[%s] %s %s -> %d (%d ms)', SERVICIO, $metodo, $ruta, $estado === false ? 200 : $estado, $milisegundos));
}

function manejarPeticion(): void
{
    $inicio = microtime(true);
    $metodo = $_SERVER['REQUEST_METHOD'];
    $ruta = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
    $ruta = is_string($ruta) ? $ruta : '';

    register_shutdown_function('registrarPeticion', $metodo, $ruta, $inicio);

    if ($ruta === '/health') {
        responder(200, json_encode(['service' => SERVICIO, 'status' => 'ok']));
        return;
    }

    $resultado = resolverRuta($metodo, $ruta);

    match ($resultado['estado']) {
        RUTA_ENCONTRADA => reenviarAPython($metodo, $ruta),
        METODO_NO_PERMITIDO => responderError(405, 'Método no permitido'),
        default => responderError(404, 'Ruta no encontrada'),
    };
}

manejarPeticion();
