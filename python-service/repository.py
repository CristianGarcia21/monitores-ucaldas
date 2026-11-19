"""Repositorio (DAO): toda la lógica SQL del servicio.

Cada función recibe una conexión abierta con `db.get_connection()`, así quien la llama decide qué
operaciones van en la misma transacción. Los valores **siempre** viajan como parámetros de psycopg
(`%(nombre)s`); nunca se concatenan en el SQL (contrato T4).
"""

from typing import Any

import psycopg

# Columnas del Monitor de respuesta (§5): incluye el nombre de la materia
SELECT_MONITOR = """
    SELECT mo.codigo, mo.nombre, mo.correo, mo.materia_id, ma.nombre AS materia_nombre
    FROM monitores mo
    JOIN materias ma ON ma.id = mo.materia_id
"""


def listar_materias(conexion: psycopg.Connection) -> list[dict[str, Any]]:
    """Todas las materias ordenadas por nombre (J7)."""
    return conexion.execute("SELECT id, codigo, nombre FROM materias ORDER BY nombre").fetchall()


def existe_materia(conexion: psycopg.Connection, materia_id: int) -> bool:
    fila = conexion.execute(
        "SELECT 1 FROM materias WHERE id = %(id)s", {"id": materia_id}
    ).fetchone()
    return fila is not None


def listar_monitores(conexion: psycopg.Connection) -> list[dict[str, Any]]:
    """Todos los monitores con su materia, ordenados por código (J7)."""
    return conexion.execute(SELECT_MONITOR + " ORDER BY mo.codigo").fetchall()


def obtener_monitor(conexion: psycopg.Connection, codigo: str) -> dict[str, Any] | None:
    """El monitor con ese código (ya normalizado) o None si no existe."""
    return conexion.execute(
        SELECT_MONITOR + " WHERE mo.codigo = %(codigo)s", {"codigo": codigo}
    ).fetchone()


def crear_monitor(conexion: psycopg.Connection, datos: dict[str, Any]) -> dict[str, Any]:
    """Inserta el monitor y lo devuelve completo (con materia_nombre) en una sola sentencia.

    Lanza UniqueViolation si el código ya existe y ForeignKeyViolation si la materia no existe.
    """
    return conexion.execute(
        """
        WITH nuevo AS (
            INSERT INTO monitores (codigo, nombre, correo, materia_id)
            VALUES (%(codigo)s, %(nombre)s, %(correo)s, %(materia_id)s)
            RETURNING codigo, nombre, correo, materia_id
        )
        SELECT nuevo.codigo, nuevo.nombre, nuevo.correo, nuevo.materia_id,
               ma.nombre AS materia_nombre
        FROM nuevo
        JOIN materias ma ON ma.id = nuevo.materia_id
        """,
        datos,
    ).fetchone()


def actualizar_monitor(conexion: psycopg.Connection, codigo: str, datos: dict[str, Any]) -> int:
    """Reemplaza los campos editables (el código no cambia). Devuelve las filas afectadas."""
    cursor = conexion.execute(
        """
        UPDATE monitores
        SET nombre = %(nombre)s, correo = %(correo)s, materia_id = %(materia_id)s
        WHERE codigo = %(codigo)s
        """,
        {**datos, "codigo": codigo},
    )
    return cursor.rowcount


def eliminar_monitor(conexion: psycopg.Connection, codigo: str) -> int:
    """Borra el monitor. Devuelve las filas afectadas (0 o 1)."""
    cursor = conexion.execute(
        "DELETE FROM monitores WHERE codigo = %(codigo)s", {"codigo": codigo}
    )
    return cursor.rowcount
