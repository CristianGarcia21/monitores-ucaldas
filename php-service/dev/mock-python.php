<?php

declare(strict_types=1);

/**
 * Mock del servicio Python para probar php-service sin depender de la persistencia real.
 *
 * Ejecutar desde php-service/:  php -S localhost:8083 dev/mock-python.php
 *
 * Responde JSON fijo con los ejemplos del contrato (docs/api-contract.md, §8). Sin base de datos:
 *   GET    /materias             200 lista de materias
 *   GET    /monitores            200 lista de monitores
 *   GET    /monitores/M-001      200 monitor · cualquier otro código → 404 (E11)
 *   POST   /monitores            201 monitor · codigo M-001 → 409 (E12) · materia_id 99 → 400 (E10)
 *   PUT    /monitores/M-001      200 monitor actualizado · cualquier otro código → 404 (E11)
 *   DELETE /monitores/M-001      204 sin cuerpo · cualquier otro código → 404 (E11)
 */

const MATERIAS = [
    ['id' => 2, 'codigo' => 'BD1', 'nombre' => 'Bases de Datos I'],
    ['id' => 1, 'codigo' => 'SW3', 'nombre' => 'Ingeniería de Software III'],
];

const MONITOR_EJEMPLO = [
    'codigo' => 'M-001',
    'nombre' => 'Ana María López',
    'correo' => 'ana.lopez@ucaldas.edu.co',
    'materia_id' => 1,
    'materia_nombre' => 'Ingeniería de Software III',
];

/**
 * Envía una respuesta JSON; con cuerpo nulo (204) no se imprime nada.
 */
function responderMock(int $estado, mixed $cuerpo = null): void
{
    http_response_code($estado);

    if ($cuerpo === null) {
        return;
    }

    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($cuerpo, JSON_UNESCAPED_UNICODE);
}

function responderErrorMock(int $estado, string $mensaje): void
{
    responderMock($estado, ['error' => $mensaje]);
}

/**
 * Nombre de la materia según su id; null si no existe (solo 1 y 2 están en los datos de prueba).
 */
function buscarNombreMateria(mixed $materiaId): ?string
{
    foreach (MATERIAS as $materia) {
        if ($materia['id'] === $materiaId) {
            return $materia['nombre'];
        }
    }

    return null;
}

function responderMonitorInexistente(string $codigo): void
{
    responderErrorMock(404, 'No existe un monitor con el código ' . $codigo);
}

function manejarPost(): void
{
    $datos = json_decode((string) file_get_contents('php://input'));

    if (!$datos instanceof stdClass) {
        responderErrorMock(400, 'JSON inválido');
        return;
    }

    $codigo = strtoupper(trim((string) ($datos->codigo ?? '')));
    $materiaNombre = buscarNombreMateria($datos->materia_id ?? null);

    if ($materiaNombre === null) {
        responderErrorMock(400, 'La materia indicada no existe');
        return;
    }

    if ($codigo === MONITOR_EJEMPLO['codigo']) {
        responderErrorMock(409, 'Ya existe un monitor con el código ' . $codigo);
        return;
    }

    responderMock(201, [
        'codigo' => $codigo,
        'nombre' => (string) ($datos->nombre ?? ''),
        'correo' => (string) ($datos->correo ?? ''),
        'materia_id' => $datos->materia_id,
        'materia_nombre' => $materiaNombre,
    ]);
}

function manejarPut(string $codigo): void
{
    $datos = json_decode((string) file_get_contents('php://input'));

    if (!$datos instanceof stdClass) {
        responderErrorMock(400, 'JSON inválido');
        return;
    }

    if ($codigo !== MONITOR_EJEMPLO['codigo']) {
        responderMonitorInexistente($codigo);
        return;
    }

    $materiaNombre = buscarNombreMateria($datos->materia_id ?? null);

    if ($materiaNombre === null) {
        responderErrorMock(400, 'La materia indicada no existe');
        return;
    }

    responderMock(200, [
        'codigo' => $codigo,
        'nombre' => (string) ($datos->nombre ?? ''),
        'correo' => (string) ($datos->correo ?? ''),
        'materia_id' => $datos->materia_id,
        'materia_nombre' => $materiaNombre,
    ]);
}

function manejarSolicitudMock(): void
{
    $metodo = $_SERVER['REQUEST_METHOD'];
    $ruta = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
    $ruta = is_string($ruta) ? $ruta : '';

    error_log(sprintf('[mock-python] %s %s', $metodo, $ruta));

    if ($ruta === '/health') {
        responderMock(200, ['service' => 'python-service', 'status' => 'ok']);
        return;
    }

    if ($ruta === '/materias' && $metodo === 'GET') {
        responderMock(200, MATERIAS);
        return;
    }

    if ($ruta === '/monitores') {
        match ($metodo) {
            'GET' => responderMock(200, [MONITOR_EJEMPLO]),
            'POST' => manejarPost(),
            default => responderErrorMock(405, 'Método no permitido'),
        };
        return;
    }

    if (preg_match('#^/monitores/([^/]+)$#D', $ruta, $coincidencias) === 1) {
        $codigo = strtoupper($coincidencias[1]);

        match ($metodo) {
            'GET' => $codigo === MONITOR_EJEMPLO['codigo']
                ? responderMock(200, MONITOR_EJEMPLO)
                : responderMonitorInexistente($codigo),
            'PUT' => manejarPut($codigo),
            'DELETE' => $codigo === MONITOR_EJEMPLO['codigo']
                ? responderMock(204)
                : responderMonitorInexistente($codigo),
            default => responderErrorMock(405, 'Método no permitido'),
        };
        return;
    }

    if ($ruta === '/materias') {
        responderErrorMock(405, 'Método no permitido');
        return;
    }

    responderErrorMock(404, 'Ruta no encontrada');
}

manejarSolicitudMock();
