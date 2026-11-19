"""Normalización (§6.1), validación (§6.2), orden (§6.3) y mensajes (§7). No necesitan la BD:
un cuerpo inválido se rechaza antes de abrir la conexión."""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from schemas import MonitorCreate, MonitorUpdate

VALIDO = {
    "codigo": "TEST-001",
    "nombre": "Ana López",
    "correo": "ana@ucaldas.edu.co",
    "materia_id": 1,
}


def primer_error(modelo: type, datos: object) -> str:
    with pytest.raises(ValidationError) as info:
        modelo.model_validate(datos)
    return info.value.errors()[0]["msg"]


def test_normaliza_segun_el_contrato() -> None:
    monitor = MonitorCreate.model_validate(
        {
            "codigo": "  m-001 ",
            "nombre": " Ana   López ",
            "correo": "Ana@UCaldas.edu.co ",
            "materia_id": 1,
        }
    )

    assert monitor.model_dump() == {
        "codigo": "M-001",
        "nombre": "Ana López",
        "correo": "ana@ucaldas.edu.co",
        "materia_id": 1,
    }


def test_la_normalizacion_es_idempotente() -> None:
    una_vez = MonitorCreate.model_validate({**VALIDO, "nombre": "  Ana \t  María  "}).model_dump()

    assert MonitorCreate.model_validate(una_vez).model_dump() == una_vez


def test_put_ignora_codigo_y_campos_extra() -> None:
    monitor = MonitorUpdate.model_validate({**VALIDO, "codigo": "OTRO", "materia_nombre": "X"})

    assert monitor.model_dump() == {
        "nombre": "Ana López",
        "correo": "ana@ucaldas.edu.co",
        "materia_id": 1,
    }


@pytest.mark.parametrize(
    ("cambios", "mensaje"),
    [
        ({"codigo": None}, "El código es obligatorio"),
        ({"codigo": "   "}, "El código es obligatorio"),
        ({"codigo": 123}, "El código es obligatorio"),
        (
            {"codigo": "M 001"},
            "El código solo puede tener letras, números y guiones (máximo 20 caracteres)",
        ),
        (
            {"codigo": "M_001"},
            "El código solo puede tener letras, números y guiones (máximo 20 caracteres)",
        ),
        (
            {"codigo": "A" * 21},
            "El código solo puede tener letras, números y guiones (máximo 20 caracteres)",
        ),
        ({"nombre": ""}, "El nombre es obligatorio"),
        ({"nombre": "  "}, "El nombre es obligatorio"),
        ({"nombre": " ab  "}, "El nombre debe tener entre 3 y 150 caracteres"),
        ({"nombre": "a" * 151}, "El nombre debe tener entre 3 y 150 caracteres"),
        ({"correo": None}, "El correo es obligatorio"),
        ({"correo": "carlos@ucaldas"}, "El correo no es válido"),
        ({"correo": "a@b"}, "El correo no es válido"),
        ({"correo": "a b@c.co"}, "El correo no es válido"),
        ({"correo": "a" * 140 + "@ucaldas.co"}, "El correo debe tener máximo 150 caracteres"),
        ({"materia_id": None}, "La materia es obligatoria"),
        ({"materia_id": "1"}, "La materia es obligatoria"),
        ({"materia_id": 1.5}, "La materia es obligatoria"),
        ({"materia_id": 1.0}, "La materia es obligatoria"),
        ({"materia_id": True}, "La materia es obligatoria"),
        ({"materia_id": 0}, "La materia es obligatoria"),
        ({"materia_id": -3}, "La materia es obligatoria"),
        ({"materia_id": 2**31}, "La materia es obligatoria"),
    ],
)
def test_mensajes_del_catalogo(cambios: dict, mensaje: str) -> None:
    assert primer_error(MonitorCreate, {**VALIDO, **cambios}) == mensaje


@pytest.mark.parametrize(
    ("campo", "mensaje"),
    [
        ("codigo", "El código es obligatorio"),
        ("nombre", "El nombre es obligatorio"),
        ("correo", "El correo es obligatorio"),
        ("materia_id", "La materia es obligatoria"),
    ],
)
def test_campo_ausente_es_obligatorio(campo: str, mensaje: str) -> None:
    datos = {k: v for k, v in VALIDO.items() if k != campo}

    assert primer_error(MonitorCreate, datos) == mensaje


# --- Misma normalización que Java (MonitorValidator: trim(), isBlank() y \s ASCII) ---------------


@pytest.mark.parametrize(
    ("cambios", "esperado"),
    [
        # trim() de Java quita caracteres de control <= U+0020, no los espacios Unicode
        ({"codigo": "\x01dev-x\t"}, {"codigo": "DEV-X"}),
        ({"nombre": "Ana\xa0\xa0López"}, {"nombre": "Ana\xa0\xa0López"}),
        ({"nombre": "Ana \t\n López"}, {"nombre": "Ana López"}),
        # isBlank() de Java no cuenta el espacio no separable: tres NBSP son un nombre de largo 3
        ({"nombre": "\xa0\xa0\xa0"}, {"nombre": "\xa0\xa0\xa0"}),
        # \s de Java es solo ASCII: un NBSP dentro del correo no lo invalida
        ({"correo": "a\xa0b@ucaldas.edu.co"}, {"correo": "a\xa0b@ucaldas.edu.co"}),
    ],
)
def test_normalizacion_igual_a_java(cambios: dict, esperado: dict) -> None:
    monitor = MonitorCreate.model_validate({**VALIDO, **cambios}).model_dump()

    assert {k: monitor[k] for k in esperado} == esperado


@pytest.mark.parametrize(
    ("cambios", "mensaje"),
    [
        (
            {"codigo": "\u2003DEV-X"},
            "El código solo puede tener letras, números y guiones (máximo 20 caracteres)",
        ),
        ({"nombre": "\u2003\u3000 "}, "El nombre es obligatorio"),
    ],
)
def test_validacion_unicode_igual_a_java(cambios: dict, mensaje: str) -> None:
    assert primer_error(MonitorCreate, {**VALIDO, **cambios}) == mensaje


def test_correo_con_nul_no_es_valido() -> None:
    assert (
        primer_error(MonitorCreate, {**VALIDO, "correo": "a\x00b@ucaldas.edu.co"})
        == "El correo no es válido"
    )


def test_nombre_con_nul_es_json_invalido() -> None:
    assert primer_error(MonitorCreate, {**VALIDO, "nombre": "Ana\x00López"}) == "JSON inválido"


def test_nombre_y_correo_en_los_limites_son_validos() -> None:
    MonitorCreate.model_validate({**VALIDO, "nombre": "abc", "correo": "a" * 137 + "@ucaldas.co"})
    MonitorCreate.model_validate({**VALIDO, "nombre": "a" * 150, "codigo": "A" * 20})


def test_orden_de_validacion_responde_solo_el_primero() -> None:
    todo_mal = {"codigo": "", "nombre": "", "correo": "x", "materia_id": "1"}

    assert primer_error(MonitorCreate, todo_mal) == "El código es obligatorio"
    assert primer_error(MonitorCreate, {**todo_mal, "codigo": "M-1"}) == "El nombre es obligatorio"
    assert (
        primer_error(MonitorCreate, {**todo_mal, "codigo": "M-1", "nombre": "Ana"})
        == "El correo no es válido"
    )
    assert primer_error(MonitorUpdate, todo_mal) == "El nombre es obligatorio"


def test_correo_valida_formato_antes_que_longitud() -> None:
    assert primer_error(MonitorCreate, {**VALIDO, "correo": "x" * 200}) == "El correo no es válido"


# --- Por HTTP: 400 (nunca 422) con {"error": ...} ------------------------------------------------


@pytest.mark.parametrize(
    ("cuerpo", "mensaje"),
    [
        (
            {"nombre": "Ana López", "correo": "ana@ucaldas.edu.co", "materia_id": 1},
            "El código es obligatorio",
        ),
        ({**VALIDO, "nombre": None}, "El nombre es obligatorio"),
        ({**VALIDO, "correo": "carlos@ucaldas"}, "El correo no es válido"),
        (
            {**VALIDO, "correo": "a" * 140 + "@ucaldas.co"},
            "El correo debe tener máximo 150 caracteres",
        ),
        ({**VALIDO, "materia_id": "1"}, "La materia es obligatoria"),
    ],
)
def test_post_con_datos_invalidos_responde_400(
    cliente: TestClient, cuerpo: dict, mensaje: str
) -> None:
    respuesta = cliente.post("/monitores", json=cuerpo)

    assert respuesta.status_code == 400
    assert respuesta.json() == {"error": mensaje}


def test_put_con_datos_invalidos_responde_400(cliente: TestClient) -> None:
    respuesta = cliente.put(
        "/monitores/TEST-001", json={"nombre": "Ana López", "correo": "a@b", "materia_id": 1}
    )

    assert respuesta.status_code == 400
    assert respuesta.json() == {"error": "El correo no es válido"}


@pytest.mark.parametrize("cuerpo", ["{mal formado", "", "[]", "null", '"texto"', "42"])
@pytest.mark.parametrize("metodo", ["POST", "PUT"])
def test_cuerpo_que_no_es_un_objeto_json_es_json_invalido(
    cliente: TestClient, metodo: str, cuerpo: str
) -> None:
    ruta = "/monitores" if metodo == "POST" else "/monitores/TEST-001"

    respuesta = cliente.request(
        metodo, ruta, content=cuerpo, headers={"Content-Type": "application/json"}
    )

    assert respuesta.status_code == 400
    assert respuesta.json() == {"error": "JSON inválido"}


@pytest.mark.parametrize("constante", ["NaN", "Infinity", "-Infinity"])
def test_constantes_no_estandar_son_json_invalido(cliente: TestClient, constante: str) -> None:
    cuerpo = (
        '{"codigo": "TEST-001", "nombre": "Ana López", "correo": "ana@ucaldas.edu.co", '
        f'"materia_id": 1, "extra": {constante}}}'
    )

    respuesta = cliente.post(
        "/monitores", content=cuerpo.encode(), headers={"Content-Type": "application/json"}
    )

    assert respuesta.status_code == 400
    assert respuesta.json() == {"error": "JSON inválido"}


def test_cuerpo_con_bytes_que_no_son_utf8_es_json_invalido(cliente: TestClient) -> None:
    respuesta = cliente.post(
        "/monitores", content=b"\xff\xfe{", headers={"Content-Type": "application/json"}
    )

    assert respuesta.status_code == 400
    assert respuesta.json() == {"error": "JSON inválido"}
