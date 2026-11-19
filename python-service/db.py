"""Conexión reutilizable a PostgreSQL (contrato §2: solo este servicio toca la BD)."""

import os
from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

# Ningún valor quemado: se lee de las variables del contrato §2 con su valor por defecto local
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "dbname": os.getenv("DB_NAME", "monitores"),
    "user": os.getenv("DB_USER", "monitores"),
    "password": os.getenv("DB_PASSWORD", "monitores"),
}

# Si PostgreSQL no responde se falla rápido (→ 503) antes de que venza el timeout de lectura de
# PHP (10 s, contrato T1): 3 s para conectar y 5 s como máximo por consulta
TIMEOUT_CONEXION_S = 3
TIMEOUT_CONSULTA_MS = 5000


@contextmanager
def get_connection() -> Iterator[psycopg.Connection]:
    """Abre una conexión cuyas filas son diccionarios.

    Hace commit al salir sin errores y rollback si ocurre una excepción; siempre cierra la
    conexión.
    """
    conexion = psycopg.connect(
        **DB_CONFIG,
        row_factory=dict_row,
        connect_timeout=TIMEOUT_CONEXION_S,
        options=f"-c statement_timeout={TIMEOUT_CONSULTA_MS}",
    )
    try:
        yield conexion
        conexion.commit()
    except BaseException:
        conexion.rollback()
        raise
    finally:
        conexion.close()
