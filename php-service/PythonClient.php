<?php

declare(strict_types=1);

/**
 * Cliente cURL hacia python-service.
 *
 * Reenvía método, ruta y cuerpo tal como llegaron y devuelve el estado y el cuerpo que respondió Python,
 * sin interpretarlos (contrato H7). Timeouts según T1: conexión 3 s, lectura 10 s.
 */
final class PythonClient
{
    private const TIMEOUT_CONEXION_SEGUNDOS = 3;
    private const TIMEOUT_TOTAL_SEGUNDOS = 10;
    private const URL_POR_DEFECTO = 'http://localhost:8083';

    private string $urlBase;

    /**
     * @param string|null $urlBase URL base de Python; por defecto PYTHON_SERVICE_URL (sin "/" final).
     */
    public function __construct(?string $urlBase = null)
    {
        $url = $urlBase ?? (getenv('PYTHON_SERVICE_URL') ?: self::URL_POR_DEFECTO);
        $this->urlBase = rtrim($url, '/');
    }

    /**
     * Reenvía la petición a Python.
     *
     * @param string      $method Método HTTP original (GET, POST, PUT, DELETE).
     * @param string      $path   Ruta original, por ejemplo "/monitores/M-001".
     * @param string|null $body   Cuerpo original; null o vacío si la petición no trae.
     *
     * @return array{0: int, 1: string} [estado HTTP, cuerpo]. Si Python no responde (caído o
     *                                  timeout) devuelve [502, {"error": "Servicio de persistencia no disponible"}] (E16).
     */
    public function forward(string $method, string $path, ?string $body): array
    {
        $ch = curl_init($this->urlBase . $path);

        if ($ch === false) {
            return $this->errorDeConexion('no se pudo inicializar cURL');
        }

        $opciones = [
            CURLOPT_CUSTOMREQUEST => $method,
            CURLOPT_HTTPHEADER => ['Content-Type: application/json', 'Accept: application/json'],
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_CONNECTTIMEOUT => self::TIMEOUT_CONEXION_SEGUNDOS,
            CURLOPT_TIMEOUT => self::TIMEOUT_TOTAL_SEGUNDOS,
        ];

        if ($body !== null && $body !== '') {
            $opciones[CURLOPT_POSTFIELDS] = $body;
        }

        curl_setopt_array($ch, $opciones);

        $respuesta = curl_exec($ch);
        $estado = (int) curl_getinfo($ch, CURLINFO_HTTP_CODE);

        if (curl_errno($ch) !== 0 || !is_string($respuesta) || $estado === 0) {
            return $this->errorDeConexion(curl_error($ch));
        }

        return [$estado, $respuesta];
    }

    /**
     * Error E16: Python no responde. El detalle técnico solo va al log, nunca al cliente (T4).
     *
     * @return array{0: int, 1: string}
     */
    private function errorDeConexion(string $detalle): array
    {
        error_log('[php-service] No se pudo conectar con python-service (' . $this->urlBase . '): ' . $detalle);

        $cuerpo = json_encode(
            ['error' => 'Servicio de persistencia no disponible'],
            JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR
        );

        return [502, $cuerpo];
    }
}
