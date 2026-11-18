# python-service – Capa de persistencia

Servicio FastAPI (Python 3.12) que recibe las peticiones de `php-service`, **normaliza y valida de nuevo**
los datos, ejecuta SQL parametrizado sobre PostgreSQL y traduce los errores de la BD al catálogo del
[contrato](../docs/api-contract.md). Es la única capa que se conecta a la base de datos (regla A3).

| | |
|---|---|
| Puerto | `8083` |
| Salud | `GET /health` → `{"service": "python-service", "status": "ok"}` |
| Swagger | http://localhost:8083/docs |

## Estructura

| Archivo | Responsabilidad |
|---|---|
| `db.py` | `get_connection()`: conexión con filas como `dict`, commit al salir sin error y rollback ante excepción |
| `schemas.py` | Modelos Pydantic (`MonitorCreate`, `MonitorUpdate`, `MonitorOut`, `MateriaOut`), normalización §6.1 y mensajes E02–E09 |
| `repository.py` | Todas las consultas SQL (patrón Repository), siempre con parámetros `%(nombre)s` |
| `main.py` | Endpoints, mapeo de errores (E01, E10–E18) y log por petición |
| `tests/` | Pruebas con `pytest` + `TestClient` |

## Endpoints

| Método | Ruta | Éxito | Errores propios |
|---|---|---|---|
| `GET` | `/materias` | 200 (orden por `nombre`) | 503, 500 |
| `GET` | `/monitores` | 200 (orden por `codigo`) | 503, 500 |
| `GET` | `/monitores/{codigo}` | 200 | 404 E11 |
| `POST` | `/monitores` | 201 + Monitor completo | 400 E01–E10, 409 E12 |
| `PUT` | `/monitores/{codigo}` | 200 + Monitor actualizado | 400 E01, E04–E10, 404 E11 |
| `DELETE` | `/monitores/{codigo}` | 204 sin cuerpo | 404 E11 |

Además: ruta inexistente → 404 `Ruta no encontrada`, método no soportado → 405 `Método no permitido`,
BD caída → 503 `Base de datos no disponible`, error no previsto → 500 `Error interno del servidor`.
Todos los errores son `{"error": "<mensaje>"}`.

Errores de PostgreSQL: `UniqueViolation` → 409, `ForeignKeyViolation` → 400 E10, `CheckViolation` → 400
del campo según el nombre de la restricción (`monitores_codigo_check`, `monitores_nombre_check`,
`monitores_correo_check`; cualquier otra → 500), `OperationalError` → 503.

## Ejecutar

Con Docker (desde la raíz del repo):

```bash
docker compose up --build database python-service
```

Sin Docker para el servicio (la BD sí en Docker):

```bash
docker compose up -d database
cd python-service
python -m venv .venv
.venv/Scripts/activate        # Windows (en Linux/macOS: source .venv/bin/activate)
pip install -r requirements-dev.txt
uvicorn main:app --port 8083 --reload
```

Variables de entorno (contrato §2): `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`; por defecto
`localhost:5432`, base, usuario y clave `monitores`.

## Pruebas

Requieren la BD de Docker levantada (`docker compose up -d database`); si no responde, las pruebas que la
necesitan se marcan como *skipped* y las de validación se ejecutan igual.

```bash
cd python-service
pip install -r requirements-dev.txt
pytest
```

- Usan códigos `TEST-...` y los borran antes y después de cada prueba (contrato §12); no tocan los datos
  semilla `M-...`.
- Cubren el CRUD (201, 409, 400 materia inexistente, 200/404, 204/404), el catálogo de validación y su
  orden, `JSON inválido`, 404/405, 503 con la BD caída, 500 sin detalles, `CheckViolation` y el log.

> **Puerto 5432 ocupado** (por ejemplo, un PostgreSQL instalado en Windows): levante la BD en otro puerto
> y use la misma variable para las pruebas:
>
> ```bash
> DB_PORT=5544 docker compose up -d database
> DB_PORT=5544 pytest
> ```

## Logs

Una línea por petición en la salida estándar (contrato T2); los 500 agregan la traza:

```
[python-service] POST /monitores -> 201 (42 ms)
```

Ver: `docker compose logs -f python-service`.
