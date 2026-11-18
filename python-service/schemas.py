"""Esquemas de entrada y salida del contrato (§5).

Cada campo se normaliza (§6.1) y se valida (§6.2) en un validador `mode="before"` que lanza el
mensaje exacto del catálogo (§7). Pydantic valida los campos en el orden en que se declaran, así
que el primer error de la lista respeta el orden fijo del §6.3.
"""
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_core import PydanticCustomError

# Catálogo de errores §7 (E02–E09): se copian textualmente
CODIGO_OBLIGATORIO = "El código es obligatorio"
CODIGO_FORMATO = "El código solo puede tener letras, números y guiones (máximo 20 caracteres)"
NOMBRE_OBLIGATORIO = "El nombre es obligatorio"
NOMBRE_LONGITUD = "El nombre debe tener entre 3 y 150 caracteres"
CORREO_OBLIGATORIO = "El correo es obligatorio"
CORREO_FORMATO = "El correo no es válido"
CORREO_LONGITUD = "El correo debe tener máximo 150 caracteres"
MATERIA_OBLIGATORIA = "La materia es obligatoria"

# Tipo de error de Pydantic cuyo mensaje es uno del catálogo y se responde tal cual
TIPO_ERROR_CONTRATO = "contrato"

# Regex del §6.2 (se usan con fullmatch, equivalente a ^...$)
PATRON_CODIGO = re.compile(r"[A-Z0-9-]{1,20}")
PATRON_CORREO = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
PATRON_ESPACIOS = re.compile(r"\s+")

# materia_id es INTEGER en PostgreSQL: un número mayor no puede ser una materia válida
MAX_ENTERO_BD = 2_147_483_647


def normalizar_codigo(codigo: str) -> str:
    """§6.1: trim + mayúsculas. Se usa también para el {codigo} de la ruta."""
    return codigo.strip().upper()


def normalizar_nombre(nombre: str) -> str:
    """§6.1: trim + espacios internos múltiples reemplazados por uno solo."""
    return PATRON_ESPACIOS.sub(" ", nombre.strip())


def normalizar_correo(correo: str) -> str:
    """§6.1: trim + minúsculas."""
    return correo.strip().lower()


def _error(mensaje: str) -> PydanticCustomError:
    return PydanticCustomError(TIPO_ERROR_CONTRATO, mensaje)


def _texto(valor: Any) -> str | None:
    """Devuelve el string o None si está "vacío" (§6.2): ausente, null, no string o '' tras el trim."""
    if not isinstance(valor, str) or not valor.strip():
        return None
    return valor


def _obligatorio() -> Any:
    # El valor por defecto None hace que el validador "before" también se ejecute cuando el
    # campo no viene, para responder el mensaje del catálogo en vez del "Field required" de Pydantic
    return Field(default=None, validate_default=True)


class _ValidacionMonitor(BaseModel):
    """Normalización y validación compartida por las peticiones POST y PUT."""

    # J6: los campos que no están en el contrato (incluido materia_nombre) se ignoran
    model_config = ConfigDict(extra="ignore")

    @field_validator("codigo", mode="before", check_fields=False)
    @classmethod
    def _validar_codigo(cls, valor: Any) -> str:
        codigo = _texto(valor)
        if codigo is None:
            raise _error(CODIGO_OBLIGATORIO)
        codigo = normalizar_codigo(codigo)
        if not PATRON_CODIGO.fullmatch(codigo):
            raise _error(CODIGO_FORMATO)
        return codigo

    @field_validator("nombre", mode="before", check_fields=False)
    @classmethod
    def _validar_nombre(cls, valor: Any) -> str:
        nombre = _texto(valor)
        if nombre is None:
            raise _error(NOMBRE_OBLIGATORIO)
        nombre = normalizar_nombre(nombre)
        if not 3 <= len(nombre) <= 150:
            raise _error(NOMBRE_LONGITUD)
        return nombre

    @field_validator("correo", mode="before", check_fields=False)
    @classmethod
    def _validar_correo(cls, valor: Any) -> str:
        correo = _texto(valor)
        if correo is None:
            raise _error(CORREO_OBLIGATORIO)
        correo = normalizar_correo(correo)
        if not PATRON_CORREO.fullmatch(correo):
            raise _error(CORREO_FORMATO)
        if len(correo) > 150:
            raise _error(CORREO_LONGITUD)
        return correo

    @field_validator("materia_id", mode="before", check_fields=False)
    @classmethod
    def _validar_materia_id(cls, valor: Any) -> int:
        # Entero JSON estricto: "1", 1.5, 1.0 y true se rechazan (bool es subclase de int en Python)
        if type(valor) is not int or not 0 < valor <= MAX_ENTERO_BD:
            raise _error(MATERIA_OBLIGATORIA)
        return valor


class MonitorCreate(_ValidacionMonitor):
    """Cuerpo de POST /monitores. El orden de los campos es el orden de validación del §6.3."""

    model_config = ConfigDict(
        json_schema_extra={
            "required": ["codigo", "nombre", "correo", "materia_id"],
            "examples": [
                {
                    "codigo": "M-002",
                    "nombre": "Carlos Pérez",
                    "correo": "carlos.perez@ucaldas.edu.co",
                    "materia_id": 2,
                }
            ],
        }
    )

    codigo: str = _obligatorio()
    nombre: str = _obligatorio()
    correo: str = _obligatorio()
    materia_id: int = _obligatorio()


class MonitorUpdate(_ValidacionMonitor):
    """Cuerpo de PUT /monitores/{codigo}: reemplazo completo; un `codigo` en el body se ignora (J6)."""

    model_config = ConfigDict(
        json_schema_extra={
            "required": ["nombre", "correo", "materia_id"],
            "examples": [
                {
                    "nombre": "Carlos Andrés Pérez",
                    "correo": "carlos.perez@ucaldas.edu.co",
                    "materia_id": 1,
                }
            ],
        }
    )

    nombre: str = _obligatorio()
    correo: str = _obligatorio()
    materia_id: int = _obligatorio()


class MonitorOut(BaseModel):
    """Monitor en las respuestas (§5): incluye materia_nombre."""

    codigo: str
    nombre: str
    correo: str
    materia_id: int
    materia_nombre: str


class MateriaOut(BaseModel):
    """Materia en las respuestas (§5), solo lectura."""

    id: int
    codigo: str
    nombre: str


class ErrorOut(BaseModel):
    """Cuerpo de todo error (J8): una sola clave."""

    error: str
