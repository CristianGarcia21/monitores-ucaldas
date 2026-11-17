<?php
/**
 * Servicio PHP - intermediario entre Java y Python.
 *
 * Esqueleto inicial: solo expone /health.
 * Implementar el reenvío de los endpoints definidos en docs/api-contract.md (sección PHP).
 */

header('Content-Type: application/json; charset=utf-8');

$pythonUrl = getenv('PYTHON_SERVICE_URL') ?: 'http://localhost:8083';
$method = $_SERVER['REQUEST_METHOD'];
$path = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);

if ($path === '/health') {
    echo json_encode(['service' => 'php-service', 'status' => 'ok']);
    exit;
}

// TODO: reenviar /materias y /monitores[/{codigo}] a $pythonUrl con cURL
http_response_code(404);
echo json_encode(['error' => 'Ruta no encontrada']);
