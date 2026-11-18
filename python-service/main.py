"""Servicio Python - capa de persistencia (docs/api-contract.md).

Normaliza y valida de nuevo los datos (§6, sin confiar en que Java ya validó), verifica existencia
y duplicados, ejecuta SQL parametrizado y traduce los errores de la BD al catálogo §7.
"""
import logging
import sys
import time
from collections.abc import Awaitable, Callable
from typing import Any

import psycopg
from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

import repository
from db import get_connection
from schemas import (
    CODIGO_FORMATO,
    CORREO_FORMATO,
    NOMBRE_LONGITUD,
    TIPO_ERROR_CONTRATO,
    ErrorOut,
    MateriaOut,
    MonitorCreate,
    MonitorOut,
    MonitorUpdate,
    normalizar_codigo,
)

SERVICIO = "python-service"

# Catálogo de errores §7 que genera esta capa (además de E02–E09 en schemas.py)
JSON_INVALIDO = "JSON inválido"  # E01
MATERIA_NO_EXISTE = "La materia indicada no existe"  # E10
MONITOR_NO_EXISTE = "No existe un monitor con el código {codigo}"  # E11
MONITOR_DUPLICADO = "Ya existe un monitor con el código {codigo}"  # E12
RUTA_NO_ENCONTRADA = "Ruta no encontrada"  # E13
METODO_NO_PERMITIDO = "Método no permitido"  # E14
BD_NO_DISPONIBLE = "Base de datos no disponible"  # E17
ERROR_INTERNO = "Error interno del servidor"  # E18

# Errores HTTP que genera el propio framework: 404/405 del enrutador y 400 si el cuerpo no se
# puede leer como JSON (por ejemplo, bytes que no son UTF-8)
MENSAJES_HTTP = {
    400: JSON_INVALIDO,
    404: RUTA_NO_ENCONTRADA,
    405: METODO_NO_PERMITIDO,
}

# CheckViolation → mensaje del campo cuya restricción falló (el nombre de la restricción lo incluye)
MENSAJES_CHECK = (
    ("codigo", CODIGO_FORMATO),
    ("nombre", NOMBRE_LONGITUD),
    ("correo", CORREO_FORMATO),
)


def _crear_logger() -> logging.Logger:
    """Logger a la salida estándar con el mensaje tal cual (formato T2)."""
    log = logging.getLogger(SERVICIO)
    if not log.handlers:
        manejador = logging.StreamHandler(sys.stdout)
        manejador.setFormatter(logging.Formatter("%(message)s"))
        log.addHandler(manejador)
    log.setLevel(logging.INFO)
    log.propagate = False
    return log


logger = _crear_logger()
# T2 exige una sola línea por petición: se apaga el log de acceso propio de uvicorn
logging.getLogger("uvicorn.access").disabled = True


class RespuestaJson(JSONResponse):
    """H4: toda respuesta con cuerpo declara charset=utf-8. JSONResponse ya conserva tildes y ñ (H9)."""

    media_type = "application/json; charset=utf-8"


class ErrorApi(Exception):
    """Error del catálogo §7 que se responde como {"error": mensaje}."""

    def __init__(self, estado: int, mensaje: str) -> None:
        super().__init__(mensaje)
        self.estado = estado
        self.mensaje = mensaje


def respuesta_error(estado: int, mensaje: str, headers: dict[str, str] | None = None) -> RespuestaJson:
    """J8: el error siempre es un objeto con una sola clave."""
    return RespuestaJson({"error": mensaje}, status_code=estado, headers=headers)


def mensaje_check(restriccion: str | None) -> str | None:
    """Mensaje 400 del campo al que pertenece la restricción CHECK, o None si no se identifica."""
    for columna, mensaje in MENSAJES_CHECK:
        if restriccion and columna in restriccion:
            return mensaje
    return None


def mensaje_validacion(errores: list[dict[str, Any]]) -> str:
    """§6.3: se responde solo el primer error.

    Los errores de campo traen ya el mensaje del catálogo (schemas.py). Cualquier otro (JSON mal
    formado, cuerpo vacío o que no es un objeto) es E01.
    """
    primero = errores[0] if errores else {}
    if primero.get("type") == TIPO_ERROR_CONTRATO:
        return primero["msg"]
    return JSON_INVALIDO


app = FastAPI(
    title="Servicio Python - Persistencia",
    default_response_class=RespuestaJson,
    # H1: /monitores/ no es una ruta válida (404); sin esto FastAPI redirigiría con 307
    redirect_slashes=False,
    # Documenta en Swagger el formato real de los errores (en lugar del 422 que FastAPI agrega)
    responses={
        "4XX": {"model": ErrorOut, "description": "Error del catálogo §7 del contrato"},
        "5XX": {"model": ErrorOut, "description": "Error del catálogo §7 del contrato"},
    },
)


@app.exception_handler(Exception)
async def error_interno(request: Request, exc: Exception) -> Response:
    """E18: el detalle solo va al log (T2, T4)."""
    logger.error("[%s] Error no previsto en %s %s", SERVICIO, request.method, request.url.path, exc_info=exc)
    return respuesta_error(500, ERROR_INTERNO)


@app.exception_handler(StarletteHTTPException)
async def manejar_error_http(request: Request, exc: StarletteHTTPException) -> Response:
    """E13/E14 (y E01): reemplaza el {"detail": ...} de FastAPI por {"error": ...}."""
    mensaje = MENSAJES_HTTP.get(exc.status_code)
    if mensaje is None:
        return await error_interno(request, exc)
    return respuesta_error(exc.status_code, mensaje, headers=exc.headers)


@app.exception_handler(RequestValidationError)
async def manejar_error_validacion(request: Request, exc: RequestValidationError) -> Response:
    """Datos inválidos → 400 (nunca 422, H6) con el mensaje del catálogo."""
    return respuesta_error(400, mensaje_validacion(exc.errors()))


@app.exception_handler(ErrorApi)
async def manejar_error_api(request: Request, exc: ErrorApi) -> Response:
    return respuesta_error(exc.estado, exc.mensaje)


@app.exception_handler(psycopg.errors.ForeignKeyViolation)
async def manejar_materia_inexistente(request: Request, exc: psycopg.errors.ForeignKeyViolation) -> Response:
    return respuesta_error(400, MATERIA_NO_EXISTE)


@app.exception_handler(psycopg.errors.CheckViolation)
async def manejar_check(request: Request, exc: psycopg.errors.CheckViolation) -> Response:
    mensaje = mensaje_check(exc.diag.constraint_name)
    if mensaje is None:
        return await error_interno(request, exc)
    return respuesta_error(400, mensaje)


@app.exception_handler(psycopg.OperationalError)
async def manejar_bd_no_disponible(request: Request, exc: psycopg.OperationalError) -> Response:
    return respuesta_error(503, BD_NO_DISPONIBLE)


@app.middleware("http")
async def registrar_peticion(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    """T2: una línea por petición, `[python-service] MÉTODO RUTA -> STATUS (ms)`."""
    inicio = time.perf_counter()
    try:
        respuesta = await call_next(request)
    except Exception as exc:
        # Lo no previsto se responde aquí (E18) para que la línea del log muestre el 500
        respuesta = await error_interno(request, exc)
    duracion_ms = round((time.perf_counter() - inicio) * 1000)
    logger.info("[%s] %s %s -> %d (%d ms)", SERVICIO, request.method, request.url.path, respuesta.status_code, duracion_ms)
    return respuesta


@app.get("/health")
def health() -> dict[str, str]:
    """T3: responde sin depender de la base de datos."""
    return {"service": SERVICIO, "status": "ok"}


@app.get("/materias", response_model=list[MateriaOut])
def listar_materias() -> list[dict[str, Any]]:
    with get_connection() as conexion:
        return repository.listar_materias(conexion)


@app.get("/monitores", response_model=list[MonitorOut])
def listar_monitores() -> list[dict[str, Any]]:
    """RF2."""
    with get_connection() as conexion:
        return repository.listar_monitores(conexion)


@app.get("/monitores/{codigo}", response_model=MonitorOut)
def obtener_monitor(codigo: str) -> dict[str, Any]:
    """RF3."""
    codigo = normalizar_codigo(codigo)
    with get_connection() as conexion:
        monitor = repository.obtener_monitor(conexion, codigo)
    if monitor is None:
        raise ErrorApi(404, MONITOR_NO_EXISTE.format(codigo=codigo))
    return monitor


@app.post("/monitores", status_code=201, response_model=MonitorOut)
def crear_monitor(monitor: MonitorCreate) -> dict[str, Any]:
    """RF1 y RF6."""
    with get_connection() as conexion:
        # §6.3: la materia (400) se revisa antes que el duplicado (409); el INSERT solo
        # reportaría primero el código repetido
        if not repository.existe_materia(conexion, monitor.materia_id):
            raise ErrorApi(400, MATERIA_NO_EXISTE)
        try:
            return repository.crear_monitor(conexion, monitor.model_dump())
        except psycopg.errors.UniqueViolation:
            raise ErrorApi(409, MONITOR_DUPLICADO.format(codigo=monitor.codigo)) from None


@app.put("/monitores/{codigo}", response_model=MonitorOut)
def actualizar_monitor(codigo: str, monitor: MonitorUpdate) -> dict[str, Any]:
    """RF4. El código de la ruta es el que manda (J6)."""
    codigo = normalizar_codigo(codigo)
    with get_connection() as conexion:
        # §6.3: primero la existencia del monitor (404). Si no existe, el UPDATE no toca filas y la
        # FK no se evalúa; si existe y la materia no, la FK responde 400 (E10)
        if repository.actualizar_monitor(conexion, codigo, monitor.model_dump()) == 0:
            raise ErrorApi(404, MONITOR_NO_EXISTE.format(codigo=codigo))
        return repository.obtener_monitor(conexion, codigo)


@app.delete("/monitores/{codigo}", status_code=204, response_class=Response)
def eliminar_monitor(codigo: str) -> Response:
    """RF5. H5: 204 sin cuerpo."""
    codigo = normalizar_codigo(codigo)
    with get_connection() as conexion:
        if repository.eliminar_monitor(conexion, codigo) == 0:
            raise ErrorApi(404, MONITOR_NO_EXISTE.format(codigo=codigo))
    return Response(status_code=204)
