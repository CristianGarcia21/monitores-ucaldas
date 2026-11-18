"""CRUD completo contra la BD de Docker (contrato §8)."""
import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.usefixtures("bd")

JSON_UTF8 = "application/json; charset=utf-8"


def crear(cliente: TestClient, monitor: dict) -> dict:
    respuesta = cliente.post("/monitores", json=monitor)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


# --- GET /materias -------------------------------------------------------------------------------


def test_listar_materias_ordenadas_por_nombre(cliente: TestClient) -> None:
    respuesta = cliente.get("/materias")

    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"] == JSON_UTF8
    materias = respuesta.json()
    assert isinstance(materias, list)
    assert {"id": 1, "codigo": "SW3", "nombre": "Ingeniería de Software III"} in materias
    assert {"id": 2, "codigo": "BD1", "nombre": "Bases de Datos I"} in materias
    codigos = [m["codigo"] for m in materias]
    # J7: por nombre ("Bases de Datos I" antes que "Ingeniería de Software III"), no por id
    assert codigos.index("BD1") < codigos.index("SW3")


# --- POST /monitores -----------------------------------------------------------------------------


def test_crear_monitor_responde_201_con_monitor_completo(cliente: TestClient, monitor_valido: dict) -> None:
    respuesta = cliente.post("/monitores", json=monitor_valido)

    assert respuesta.status_code == 201
    assert respuesta.headers["content-type"] == JSON_UTF8
    assert "location" not in respuesta.headers
    assert respuesta.json() == {**monitor_valido, "materia_nombre": "Ingeniería de Software III"}


def test_crear_normaliza_los_datos_antes_de_guardar(cliente: TestClient) -> None:
    creado = crear(
        cliente,
        {"codigo": "  test-002 ", "nombre": " Ana   López ", "correo": "Ana@UCaldas.edu.co ", "materia_id": 2},
    )

    assert creado == {
        "codigo": "TEST-002",
        "nombre": "Ana López",
        "correo": "ana@ucaldas.edu.co",
        "materia_id": 2,
        "materia_nombre": "Bases de Datos I",
    }
    assert cliente.get("/monitores/TEST-002").json() == creado


def test_crear_ignora_campos_extra(cliente: TestClient, monitor_valido: dict) -> None:
    creado = crear(cliente, {**monitor_valido, "materia_nombre": "Otra", "edad": 20})

    assert creado["materia_nombre"] == "Ingeniería de Software III"
    assert "edad" not in creado


def test_crear_duplicado_responde_409(cliente: TestClient, monitor_valido: dict) -> None:
    crear(cliente, monitor_valido)

    respuesta = cliente.post("/monitores", json={**monitor_valido, "codigo": " test-001"})

    assert respuesta.status_code == 409
    assert respuesta.json() == {"error": "Ya existe un monitor con el código TEST-001"}


def test_crear_con_materia_inexistente_responde_400(cliente: TestClient, monitor_valido: dict) -> None:
    respuesta = cliente.post("/monitores", json={**monitor_valido, "materia_id": 99999})

    assert respuesta.status_code == 400
    assert respuesta.json() == {"error": "La materia indicada no existe"}
    assert cliente.get("/monitores/TEST-001").status_code == 404


def test_materia_inexistente_se_reporta_antes_que_el_duplicado(cliente: TestClient, monitor_valido: dict) -> None:
    crear(cliente, monitor_valido)

    respuesta = cliente.post("/monitores", json={**monitor_valido, "materia_id": 99999})

    assert respuesta.status_code == 400
    assert respuesta.json() == {"error": "La materia indicada no existe"}


def test_tildes_y_enie_llegan_intactas(cliente: TestClient, monitor_valido: dict) -> None:
    crear(cliente, {**monitor_valido, "nombre": "Ñoño Pérez Güiza"})

    respuesta = cliente.get("/monitores/TEST-001")

    assert respuesta.json()["nombre"] == "Ñoño Pérez Güiza"
    assert "Ñoño Pérez Güiza".encode() in respuesta.content


# --- GET /monitores ------------------------------------------------------------------------------


def test_listar_monitores_es_arreglo_plano_ordenado_por_codigo(cliente: TestClient, monitor_valido: dict) -> None:
    crear(cliente, {**monitor_valido, "codigo": "TEST-B"})
    crear(cliente, {**monitor_valido, "codigo": "TEST-A", "materia_id": 2})

    respuesta = cliente.get("/monitores")

    assert respuesta.status_code == 200
    monitores = respuesta.json()
    assert isinstance(monitores, list)
    # J7: por código (TEST-A antes que TEST-B aunque se creó después)
    de_prueba = [m for m in monitores if m["codigo"].startswith("TEST-")]
    assert de_prueba == [
        {
            "codigo": "TEST-A",
            "nombre": "Ana María López",
            "correo": "ana.lopez@ucaldas.edu.co",
            "materia_id": 2,
            "materia_nombre": "Bases de Datos I",
        },
        {
            "codigo": "TEST-B",
            "nombre": "Ana María López",
            "correo": "ana.lopez@ucaldas.edu.co",
            "materia_id": 1,
            "materia_nombre": "Ingeniería de Software III",
        },
    ]


# --- GET /monitores/{codigo} ---------------------------------------------------------------------


def test_obtener_monitor_normaliza_el_codigo_de_la_ruta(cliente: TestClient, monitor_valido: dict) -> None:
    creado = crear(cliente, monitor_valido)

    respuesta = cliente.get("/monitores/test-001")

    assert respuesta.status_code == 200
    assert respuesta.json() == creado


def test_obtener_monitor_inexistente_responde_404(cliente: TestClient) -> None:
    respuesta = cliente.get("/monitores/test-999")

    assert respuesta.status_code == 404
    assert respuesta.json() == {"error": "No existe un monitor con el código TEST-999"}


# --- PUT /monitores/{codigo} ---------------------------------------------------------------------


def test_actualizar_monitor_responde_200_con_monitor_actualizado(cliente: TestClient, monitor_valido: dict) -> None:
    crear(cliente, monitor_valido)
    cambios = {
        "codigo": "TEST-OTRO",
        "nombre": "Ana María López Ruiz",
        "correo": "ANA.RUIZ@ucaldas.edu.co",
        "materia_id": 2,
    }

    respuesta = cliente.put("/monitores/test-001", json=cambios)

    esperado = {
        "codigo": "TEST-001",
        "nombre": "Ana María López Ruiz",
        "correo": "ana.ruiz@ucaldas.edu.co",
        "materia_id": 2,
        "materia_nombre": "Bases de Datos I",
    }
    assert respuesta.status_code == 200
    assert respuesta.json() == esperado
    assert cliente.get("/monitores/TEST-001").json() == esperado
    assert cliente.get("/monitores/TEST-OTRO").status_code == 404


def test_actualizar_monitor_inexistente_responde_404(cliente: TestClient) -> None:
    respuesta = cliente.put(
        "/monitores/test-999",
        json={"nombre": "Carlos Pérez", "correo": "carlos@ucaldas.edu.co", "materia_id": 1},
    )

    assert respuesta.status_code == 404
    assert respuesta.json() == {"error": "No existe un monitor con el código TEST-999"}


def test_monitor_inexistente_se_reporta_antes_que_la_materia(cliente: TestClient) -> None:
    respuesta = cliente.put(
        "/monitores/TEST-999",
        json={"nombre": "Carlos Pérez", "correo": "carlos@ucaldas.edu.co", "materia_id": 99999},
    )

    assert respuesta.status_code == 404


def test_actualizar_con_materia_inexistente_responde_400(cliente: TestClient, monitor_valido: dict) -> None:
    crear(cliente, monitor_valido)

    respuesta = cliente.put(
        "/monitores/TEST-001",
        json={"nombre": "Carlos Pérez", "correo": "carlos@ucaldas.edu.co", "materia_id": 99999},
    )

    assert respuesta.status_code == 400
    assert respuesta.json() == {"error": "La materia indicada no existe"}
    assert cliente.get("/monitores/TEST-001").json()["materia_id"] == 1


def test_actualizar_con_datos_invalidos_responde_400(cliente: TestClient, monitor_valido: dict) -> None:
    crear(cliente, monitor_valido)

    respuesta = cliente.put("/monitores/TEST-001", json={"nombre": "Carlos Pérez", "materia_id": 1})

    assert respuesta.status_code == 400
    assert respuesta.json() == {"error": "El correo es obligatorio"}


# --- DELETE /monitores/{codigo} ------------------------------------------------------------------


def test_eliminar_monitor_responde_204_sin_cuerpo_y_luego_404(cliente: TestClient, monitor_valido: dict) -> None:
    crear(cliente, monitor_valido)

    respuesta = cliente.delete("/monitores/test-001")

    assert respuesta.status_code == 204
    assert respuesta.content == b""
    assert "content-type" not in respuesta.headers

    otra_vez = cliente.delete("/monitores/TEST-001")
    assert otra_vez.status_code == 404
    assert otra_vez.json() == {"error": "No existe un monitor con el código TEST-001"}
