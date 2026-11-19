"""Formato de error uniforme (J8), errores de la BD (§9), log por petición (T2) y salud (T3)."""

import logging
from collections.abc import Iterator

import psycopg
import pytest
from fastapi.testclient import TestClient

import db
import main
import repository


def test_health_responde_200_sin_depender_de_la_bd(
    cliente: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(db.DB_CONFIG, "host", "127.0.0.1")
    monkeypatch.setitem(db.DB_CONFIG, "port", 1)

    respuesta = cliente.get("/health")

    assert respuesta.status_code == 200
    assert respuesta.json() == {"service": "python-service", "status": "ok"}


@pytest.mark.parametrize("ruta", ["/otra", "/monitores/", "/materias/", "/monitores/M-001/extra"])
def test_ruta_inexistente_responde_404(cliente: TestClient, ruta: str) -> None:
    respuesta = cliente.get(ruta, follow_redirects=False)

    assert respuesta.status_code == 404
    assert respuesta.json() == {"error": "Ruta no encontrada"}


@pytest.mark.parametrize(
    ("metodo", "ruta"),
    [
        ("DELETE", "/monitores"),
        ("PUT", "/monitores"),
        ("POST", "/materias"),
        ("PATCH", "/monitores/M-001"),
    ],
)
def test_metodo_no_soportado_responde_405(cliente: TestClient, metodo: str, ruta: str) -> None:
    respuesta = cliente.request(metodo, ruta)

    assert respuesta.status_code == 405
    assert respuesta.json() == {"error": "Método no permitido"}


def test_405_no_anuncia_una_cabecera_allow_incompleta(cliente: TestClient) -> None:
    assert "allow" not in cliente.delete("/monitores").headers


@pytest.mark.parametrize(
    ("metodo", "ruta", "cuerpo"),
    [
        ("GET", "/monitores", None),
        ("GET", "/materias", None),
        (
            "POST",
            "/monitores",
            {"codigo": "TEST-1", "nombre": "Ana", "correo": "a@b.co", "materia_id": 1},
        ),
        ("PUT", "/monitores/TEST-1", {"nombre": "Ana", "correo": "a@b.co", "materia_id": 1}),
        ("DELETE", "/monitores/TEST-1", None),
    ],
)
def test_bd_caida_responde_503(
    cliente: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    metodo: str,
    ruta: str,
    cuerpo: dict | None,
) -> None:
    monkeypatch.setitem(db.DB_CONFIG, "host", "127.0.0.1")
    monkeypatch.setitem(db.DB_CONFIG, "port", 1)

    respuesta = cliente.request(metodo, ruta, json=cuerpo)

    assert respuesta.status_code == 503
    assert respuesta.json() == {"error": "Base de datos no disponible"}


@pytest.mark.parametrize(
    ("metodo", "ruta", "codigo"),
    [
        ("GET", "/monitores/M%00-1", "M\x00-1"),
        ("DELETE", "/monitores/M%20001", "M 001"),
        ("GET", "/monitores/" + "A" * 21, "A" * 21),
    ],
)
def test_codigo_de_ruta_imposible_responde_404_sin_consultar_la_bd(
    cliente: TestClient, monkeypatch: pytest.MonkeyPatch, metodo: str, ruta: str, codigo: str
) -> None:
    # Con la BD "caída" se comprueba que ni siquiera se intenta conectar (si no, daría 503)
    monkeypatch.setitem(db.DB_CONFIG, "host", "127.0.0.1")
    monkeypatch.setitem(db.DB_CONFIG, "port", 1)

    respuesta = cliente.request(metodo, ruta)

    assert respuesta.status_code == 404
    assert respuesta.json() == {"error": f"No existe un monitor con el código {codigo}"}


def test_error_no_previsto_responde_500_sin_detalles(
    cliente: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fallar(conexion: psycopg.Connection) -> list:
        raise RuntimeError("detalle interno secreto")

    monkeypatch.setattr(repository, "listar_materias", fallar)
    monkeypatch.setattr(main, "get_connection", _conexion_falsa)

    respuesta = cliente.get("/materias")

    assert respuesta.status_code == 500
    assert respuesta.json() == {"error": "Error interno del servidor"}
    assert "secreto" not in respuesta.text


class _ConexionFalsa:
    def __enter__(self) -> "_ConexionFalsa":
        return self

    def __exit__(self, *args: object) -> None:
        return None


def _conexion_falsa() -> _ConexionFalsa:
    return _ConexionFalsa()


# --- CheckViolation (restricciones de la BD, §10) ------------------------------------------------


@pytest.mark.parametrize(
    ("restriccion", "mensaje"),
    [
        (
            "monitores_codigo_check",
            "El código solo puede tener letras, números y guiones (máximo 20 caracteres)",
        ),
        ("monitores_nombre_check", "El nombre debe tener entre 3 y 150 caracteres"),
        ("monitores_correo_check", "El correo no es válido"),
        ("otra_restriccion", None),
        (None, None),
    ],
)
def test_mensaje_de_cada_restriccion_check(restriccion: str | None, mensaje: str | None) -> None:
    assert main.mensaje_check(restriccion) == mensaje


def _check_violation_real(restriccion: str) -> psycopg.errors.CheckViolation:
    """Provoca una CheckViolation verdadera en PostgreSQL con el nombre de restricción indicado."""
    with pytest.raises(psycopg.errors.CheckViolation) as info:
        with db.get_connection() as conexion:
            conexion.execute(
                f"CREATE TEMP TABLE t (x INTEGER CONSTRAINT {restriccion} CHECK (x > 0))"
            )
            conexion.execute("INSERT INTO t VALUES (0)")
    return info.value


@pytest.mark.usefixtures("bd")
@pytest.mark.parametrize(
    ("restriccion", "estado", "mensaje"),
    [
        ("monitores_nombre_check", 400, "El nombre debe tener entre 3 y 150 caracteres"),
        ("monitores_correo_check", 400, "El correo no es válido"),
        ("restriccion_desconocida", 500, "Error interno del servidor"),
    ],
)
def test_check_violation_de_la_bd_se_traduce(
    cliente: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    monitor_valido: dict,
    restriccion: str,
    estado: int,
    mensaje: str,
) -> None:
    error = _check_violation_real(restriccion)

    def fallar(conexion: psycopg.Connection, datos: dict) -> dict:
        raise error

    monkeypatch.setattr(repository, "crear_monitor", fallar)

    respuesta = cliente.post("/monitores", json=monitor_valido)

    assert respuesta.status_code == estado
    assert respuesta.json() == {"error": mensaje}


# --- Formato J8 y log T2 -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("metodo", "ruta", "cuerpo"),
    [
        ("GET", "/no-existe", None),
        ("DELETE", "/monitores", None),
        ("POST", "/monitores", {}),
        ("PUT", "/monitores/X", {"nombre": "x"}),
    ],
)
def test_ningun_error_usa_detail(
    cliente: TestClient, metodo: str, ruta: str, cuerpo: dict | None
) -> None:
    respuesta = cliente.request(metodo, ruta, json=cuerpo)

    assert respuesta.status_code in (400, 404, 405)
    assert list(respuesta.json()) == ["error"]
    assert respuesta.headers["content-type"] == "application/json; charset=utf-8"


class _Coleccionista(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.lineas: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.lineas.append(record.getMessage())


@pytest.fixture
def log() -> Iterator[_Coleccionista]:
    coleccionista = _Coleccionista()
    main.logger.addHandler(coleccionista)
    yield coleccionista
    main.logger.removeHandler(coleccionista)


def test_cada_peticion_escribe_una_linea_de_log(cliente: TestClient, log: _Coleccionista) -> None:
    cliente.get("/health")
    cliente.delete("/monitores")

    assert len(log.lineas) == 2
    assert log.lineas[0].startswith("[python-service] GET /health -> 200 (")
    assert log.lineas[0].endswith(" ms)")
    assert log.lineas[1].startswith("[python-service] DELETE /monitores -> 405 (")


def test_el_log_registra_el_500(
    cliente: TestClient, log: _Coleccionista, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fallar(conexion: psycopg.Connection) -> list:
        raise RuntimeError("falla")

    monkeypatch.setattr(repository, "listar_materias", fallar)
    monkeypatch.setattr(main, "get_connection", _conexion_falsa)

    cliente.get("/materias")

    assert log.lineas[-1].startswith("[python-service] GET /materias -> 500 (")
