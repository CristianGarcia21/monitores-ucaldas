"""Fixtures compartidas. Las pruebas de integración usan la BD de Docker (contrato §13)."""

from collections.abc import Iterator

import psycopg
import pytest
from fastapi.testclient import TestClient

from db import get_connection
from main import app

# Contrato §12: las pruebas automáticas de Python usan códigos TEST- y los borran al terminar
PREFIJO = "TEST-"


def borrar_datos_de_prueba() -> None:
    with get_connection() as conexion:
        conexion.execute(
            "DELETE FROM monitores WHERE codigo LIKE %(prefijo)s", {"prefijo": PREFIJO + "%"}
        )


@pytest.fixture
def cliente() -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="session")
def bd_disponible() -> None:
    try:
        with get_connection() as conexion:
            conexion.execute("SELECT 1")
    except psycopg.OperationalError as exc:
        pytest.skip(f"La BD no responde ({exc}). Levántela con: docker compose up -d database")


@pytest.fixture
def bd(bd_disponible: None) -> Iterator[None]:
    """Deja la tabla sin datos TEST- antes y después de cada prueba, aunque la prueba falle."""
    borrar_datos_de_prueba()
    yield
    borrar_datos_de_prueba()


@pytest.fixture
def monitor_valido() -> dict:
    return {
        "codigo": "TEST-001",
        "nombre": "Ana María López",
        "correo": "ana.lopez@ucaldas.edu.co",
        "materia_id": 1,
    }
