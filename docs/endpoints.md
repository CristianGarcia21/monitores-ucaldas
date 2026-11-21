# Documentación de endpoints

**Entregable 4.** Endpoints de cada servicio: la entrada pública `/api` de nginx, Java, PHP y Python.
Fuente: [contrato del sistema](api-contract.md) §3–§8. Todos los ejemplos se verificaron contra el
sistema levantado con `docker compose up --build` (ver [Verificación](#verificación)).

La colección de Postman está en
[postman/monitores.postman_collection.json](postman/monitores.postman_collection.json).

## Contenido

1. [Resumen de los 7 endpoints](#1-resumen-de-los-7-endpoints)
2. [Endpoints por servicio](#2-endpoints-por-servicio)
3. [Detalle de cada endpoint](#3-detalle-de-cada-endpoint)
4. [Códigos HTTP](#4-códigos-http)
5. [Catálogo de errores E01–E18](#5-catálogo-de-errores-e01e18)
6. [Normalización y validación de campos](#6-normalización-y-validación-de-campos)
7. [Colección Postman](#7-colección-postman)

---

## 1. Resumen de los 7 endpoints

Las cuatro capas exponen **exactamente las mismas rutas, métodos, cuerpos y códigos** (A4). La única
diferencia es que nginx las publica con el prefijo `/api` y lo quita antes de reenviar a Java.

| # | Operación | Método | Ruta | Éxito | Requisito |
|---|-----------|--------|------|-------|-----------|
| 1 | Salud del servicio | `GET` | `/health` | 200 | T3 |
| 2 | Listar materias | `GET` | `/materias` | 200 | carga del formulario |
| 3 | Listar monitores | `GET` | `/monitores` | 200 | RF2 |
| 4 | Consultar monitor | `GET` | `/monitores/{codigo}` | 200 | RF3 |
| 5 | Registrar monitor | `POST` | `/monitores` | 201 | RF1, RF6 |
| 6 | Actualizar monitor | `PUT` | `/monitores/{codigo}` | 200 | RF4 |
| 7 | Eliminar monitor | `DELETE` | `/monitores/{codigo}` | 204 | RF5 |

Convenciones comunes (§3 y §4):

- Rutas sin barra final: `/monitores/` responde 404 `Ruta no encontrada` (H1).
- Las respuestas con cuerpo llevan `Content-Type: application/json; charset=utf-8` (H4). Las peticiones
  `POST` y `PUT` envían `Content-Type: application/json`.
- Las listas son arreglos planos (`[ {...} ]`); sin resultados → `200 []` (J3, J4).
- Ningún campo de respuesta es `null` (J5). Los campos extra de las peticiones se ignoran (J6).
- Todo error es `{"error": "<mensaje>"}` con una sola clave (J8).

## 2. Endpoints por servicio

### 2.1 Entrada pública: nginx (`frontend`, puerto 8080)

Es la única URL que usa la interfaz (A2). nginx no tiene lógica propia: reenvía `/api/*` a
`http://java-controller:8081/` quitando `/api`, y devuelve lo que responde Java.

| Método | URL completa | Reenvía a |
|--------|--------------|-----------|
| `GET` | `http://localhost:8080/api/health` | `GET /health` de Java |
| `GET` | `http://localhost:8080/api/materias` | `GET /materias` |
| `GET` | `http://localhost:8080/api/monitores` | `GET /monitores` |
| `GET` | `http://localhost:8080/api/monitores/{codigo}` | `GET /monitores/{codigo}` |
| `POST` | `http://localhost:8080/api/monitores` | `POST /monitores` |
| `PUT` | `http://localhost:8080/api/monitores/{codigo}` | `PUT /monitores/{codigo}` |
| `DELETE` | `http://localhost:8080/api/monitores/{codigo}` | `DELETE /monitores/{codigo}` |

- **Códigos propios:** ninguno; todos vienen de Java.
- Cualquier otra ruta fuera de `/api/` sirve la interfaz (`index.html`).

### 2.2 Java (`java-controller`, puerto 8081)

Normaliza y valida el cuerpo. Si algo falla, responde 400 **sin llamar a PHP**. Si no, reenvía a
`PHP_SERVICE_URL` y propaga la respuesta tal cual (H7).

| Método | URL completa | Qué hace Java | Códigos propios | Códigos propagados |
|--------|--------------|---------------|-----------------|--------------------|
| `GET` | `http://localhost:8081/health` | Responde por sí mismo | 200 | — |
| `GET` | `http://localhost:8081/materias` | Reenvía | 502, 500 | 200, 502, 503 |
| `GET` | `http://localhost:8081/monitores` | Reenvía | 502, 500 | 200, 502, 503 |
| `GET` | `http://localhost:8081/monitores/{codigo}` | Normaliza el código y reenvía | 502, 500 | 200, 404, 502, 503 |
| `POST` | `http://localhost:8081/monitores` | Normaliza y valida (E01–E09) y reenvía | 400, 502, 500 | 201, 400, 409, 502, 503 |
| `PUT` | `http://localhost:8081/monitores/{codigo}` | Normaliza y valida (E01, E04–E09) y reenvía | 400, 502, 500 | 200, 400, 404, 502, 503 |
| `DELETE` | `http://localhost:8081/monitores/{codigo}` | Normaliza el código y reenvía | 502, 500 | 204, 404, 502, 503 |

- **Errores que genera Java:** E01–E09 (validación), E13 (ruta), E14 (método), E15 (PHP no disponible)
  y E18.
- **Implementación:** `MonitorController`, `MonitorValidator`, `PhpClient` y `GlobalExceptionHandler`.

### 2.3 PHP (`php-service`, puerto 8082)

Intermediario. Valida ruta, método y que el cuerpo sea un objeto JSON. Reenvía método, ruta y cuerpo
**sin modificarlos** a `PYTHON_SERVICE_URL` con cURL y propaga la respuesta. No valida campos.

| Método | URL completa | Qué hace PHP | Códigos propios | Códigos propagados |
|--------|--------------|--------------|-----------------|--------------------|
| `GET` | `http://localhost:8082/health` | Responde por sí mismo | 200 | — |
| `GET` | `http://localhost:8082/materias` | Reenvía | 502, 500 | 200, 503 |
| `GET` | `http://localhost:8082/monitores` | Reenvía | 502, 500 | 200, 503 |
| `GET` | `http://localhost:8082/monitores/{codigo}` | Reenvía | 502, 500 | 200, 404, 503 |
| `POST` | `http://localhost:8082/monitores` | Comprueba que el cuerpo sea objeto JSON y reenvía | 400 (E01), 502, 500 | 201, 400, 409, 503 |
| `PUT` | `http://localhost:8082/monitores/{codigo}` | Comprueba que el cuerpo sea objeto JSON y reenvía | 400 (E01), 502, 500 | 200, 400, 404, 503 |
| `DELETE` | `http://localhost:8082/monitores/{codigo}` | Reenvía | 502, 500 | 204, 404, 503 |

- **Errores que genera PHP:** E01, E13, E14, E16 (Python no disponible) y E18.
- **Implementación:** `index.php` (tabla de rutas `obtenerTablaRutas()`) y `PythonClient.php`.

### 2.4 Python (`python-service`, puerto 8083)

Persistencia. Normaliza y valida de nuevo, aunque Java ya lo haya hecho (§9). También verifica que el
monitor y la materia existan y que el código no esté repetido, y ejecuta SQL parametrizado sobre
PostgreSQL.

| Método | URL completa | Qué hace Python | Códigos que genera |
|--------|--------------|-----------------|--------------------|
| `GET` | `http://localhost:8083/health` | Responde por sí mismo (no consulta la BD) | 200 |
| `GET` | `http://localhost:8083/materias` | `SELECT ... ORDER BY nombre` | 200, 503, 500 |
| `GET` | `http://localhost:8083/monitores` | `SELECT ... JOIN materias ORDER BY codigo` | 200, 503, 500 |
| `GET` | `http://localhost:8083/monitores/{codigo}` | Normaliza el código y consulta | 200, 404, 503, 500 |
| `POST` | `http://localhost:8083/monitores` | Valida, comprueba la materia e inserta | 201, 400, 409, 503, 500 |
| `PUT` | `http://localhost:8083/monitores/{codigo}` | Valida y actualiza | 200, 400, 404, 503, 500 |
| `DELETE` | `http://localhost:8083/monitores/{codigo}` | Borra | 204, 404, 503, 500 |

- **Errores que genera Python:** E01–E12, E13, E14, E17 (BD no disponible) y E18.
- **Implementación:** `main.py` (endpoints), `schemas.py` (modelos Pydantic), `repository.py` (SQL) y
  `db.py` (conexión).
- **Documentación interactiva (Swagger):** `http://localhost:8083/docs`. Solo existe en Python y es una
  herramienta de desarrollo, no forma parte del contrato.

## 3. Detalle de cada endpoint

Los ejemplos usan la entrada pública (`http://localhost:8080/api`). Contra Java, PHP o Python se cambia
la base por `http://localhost:8081`, `:8082` u `:8083` y la respuesta es la misma, salvo el campo
`service` de `/health`.

### 3.1 `GET /health`

Salud del servicio que atiende la petición. No consulta la capa siguiente: responde 200 mientras el
proceso esté vivo (T3). La usan los *healthchecks* de Docker.

```http
GET http://localhost:8080/api/health
```

```json
200  {"service": "java-controller", "status": "ok"}
```

`service` vale `java-controller` (por nginx o `:8081`), `php-service` (`:8082`) o `python-service` (`:8083`).

### 3.2 `GET /materias`

Lista las materias ordenadas por nombre (J7). Las materias son de solo lectura: se cargan desde
`database/init.sql`.

```http
GET http://localhost:8080/api/materias
```

```json
200  [
       {"id": 8, "codigo": "ALG1", "nombre": "Álgebra Lineal"},
       {"id": 2, "codigo": "BD1", "nombre": "Bases de Datos I"},
       {"id": 7, "codigo": "CAL1", "nombre": "Cálculo Diferencial"},
       ...
       {"id": 1, "codigo": "SW3", "nombre": "Ingeniería de Software III"},
       ...
     ]
```

Errores posibles: 502 (E15, E16), 503 (E17), 500 (E18).

### 3.3 `GET /monitores` (RF2)

Lista todos los monitores con el nombre de su materia, ordenados por código (J7).

```http
GET http://localhost:8080/api/monitores
```

```json
200  [
       {"codigo": "M-001", "nombre": "Ana María López", "correo": "ana.lopez@ucaldas.edu.co",
        "materia_id": 1, "materia_nombre": "Ingeniería de Software III"},
       {"codigo": "M-002", "nombre": "Carlos Pérez", "correo": "carlos.perez@ucaldas.edu.co",
        "materia_id": 2, "materia_nombre": "Bases de Datos I"},
       ...
     ]
200  []        ← si no hay monitores
```

Errores posibles: 502 (E15, E16), 503 (E17), 500 (E18).

### 3.4 `GET /monitores/{codigo}` (RF3)

Consulta un monitor. El código de la ruta se normaliza (trim + mayúsculas), así que `m-001` encuentra
`M-001`.

```http
GET http://localhost:8080/api/monitores/m-001
```

```json
200  {"codigo": "M-001", "nombre": "Ana María López", "correo": "ana.lopez@ucaldas.edu.co",
      "materia_id": 1, "materia_nombre": "Ingeniería de Software III"}
```

```http
GET http://localhost:8080/api/monitores/X-999
```

```json
404  {"error": "No existe un monitor con el código X-999"}
```

Errores posibles: 404 (E11), 502 (E15, E16), 503 (E17), 500 (E18).

### 3.5 `POST /monitores` (RF1, RF6)

Registra un monitor. Los cuatro campos son obligatorios. No se envía cabecera `Location`.

```http
POST http://localhost:8080/api/monitores
Content-Type: application/json

{"codigo": " dev-001 ", "nombre": "José  Ñúñez Peña", "correo": "Jose.Nunez@UCaldas.edu.co", "materia_id": 1}
```

```json
201  {"codigo": "DEV-001", "nombre": "José Ñúñez Peña", "correo": "jose.nunez@ucaldas.edu.co",
      "materia_id": 1, "materia_nombre": "Ingeniería de Software III"}
```

| Caso | Respuesta | Quién la genera |
|------|-----------|-----------------|
| Éxito | `201` + monitor completo (con `materia_nombre`) | Python, propagado |
| Cuerpo vacío o mal formado | `400 {"error": "JSON inválido"}` | Java (o PHP/Python si se les llama directo) |
| Falta `nombre` | `400 {"error": "El nombre es obligatorio"}` | Java: **PHP no recibe nada** |
| Correo `carlos@ucaldas` | `400 {"error": "El correo no es válido"}` | Java |
| `materia_id: "1"` (texto) | `400 {"error": "La materia es obligatoria"}` | Java |
| `materia_id: 99` | `400 {"error": "La materia indicada no existe"}` | Python, propagado por PHP y Java |
| Código repetido | `409 {"error": "Ya existe un monitor con el código DEV-001"}` | Python, propagado |

> El ejemplo del contrato (§8.5) usa `M-002`, que ya existe en los datos semilla: contra la base real
> responde 409. Por eso aquí y en la colección se usa `DEV-001` (prefijo de pruebas manuales, §12).

### 3.6 `PUT /monitores/{codigo}` (RF4)

Reemplaza los tres campos editables. No hay actualización parcial, y el código **no se puede cambiar**:
si viene en el cuerpo, se ignora (J6).

```http
PUT http://localhost:8080/api/monitores/DEV-001
Content-Type: application/json

{"nombre": "José Ñúñez Peña Ruiz", "correo": "jose.nunez@ucaldas.edu.co", "materia_id": 2}
```

```json
200  {"codigo": "DEV-001", "nombre": "José Ñúñez Peña Ruiz", "correo": "jose.nunez@ucaldas.edu.co",
      "materia_id": 2, "materia_nombre": "Bases de Datos I"}
```

| Caso | Respuesta | Quién la genera |
|------|-----------|-----------------|
| Éxito | `200` + monitor actualizado | Python, propagado |
| Datos inválidos | `400` con el mensaje correspondiente (E01, E04–E09) | Java |
| Monitor inexistente | `404 {"error": "No existe un monitor con el código DEV-404"}` | Python |
| Materia inexistente | `400 {"error": "La materia indicada no existe"}` | Python |

### 3.7 `DELETE /monitores/{codigo}` (RF5)

Elimina un monitor. La interfaz pide confirmación antes de llamar a este endpoint.

```http
DELETE http://localhost:8080/api/monitores/DEV-001
```

```
204  (sin cuerpo y sin Content-Type)
```

```http
DELETE http://localhost:8080/api/monitores/DEV-001     ← otra vez
```

```json
404  {"error": "No existe un monitor con el código DEV-001"}
```

Errores posibles: 404 (E11), 502 (E15, E16), 503 (E17), 500 (E18).

### 3.8 Rutas y métodos no definidos (todas las capas)

| Petición | Respuesta |
|----------|-----------|
| `DELETE /monitores` (ruta existe, método no) | `405 {"error": "Método no permitido"}` |
| `GET /monitores/` (barra final) o cualquier ruta inexistente | `404 {"error": "Ruta no encontrada"}` |

## 4. Códigos HTTP

Solo se usan estos códigos (H6). Nunca 422, 401, 403 ni otros.

| Código | Significado en este sistema | Errores |
|--------|-----------------------------|---------|
| 200 OK | Consulta o actualización exitosa | — |
| 201 Created | Monitor registrado | — |
| 204 No Content | Monitor eliminado (sin cuerpo) | — |
| 400 Bad Request | JSON inválido, campo inválido o materia inexistente | E01–E10 |
| 404 Not Found | Monitor o ruta inexistente | E11, E13 |
| 405 Method Not Allowed | Método no soportado en una ruta que existe | E14 |
| 409 Conflict | Código de monitor repetido | E12 |
| 500 Internal Server Error | Error no previsto (el detalle solo va al log) | E18 |
| 502 Bad Gateway | Java no alcanza a PHP, o PHP no alcanza a Python | E15, E16 |
| 503 Service Unavailable | Python no alcanza a PostgreSQL | E17 |

## 5. Catálogo de errores E01–E18

Los mensajes se copian **textualmente** del contrato (§7). `{codigo}` es el código ya normalizado.

| # | HTTP | Mensaje exacto | Cuándo | Lo genera |
|---|------|----------------|--------|-----------|
| E01 | 400 | `JSON inválido` | Cuerpo vacío, mal formado o que no es un objeto en POST/PUT | Java, PHP, Python |
| E02 | 400 | `El código es obligatorio` | `codigo` vacío (POST) | Java, Python |
| E03 | 400 | `El código solo puede tener letras, números y guiones (máximo 20 caracteres)` | `codigo` no cumple la regex | Java, Python |
| E04 | 400 | `El nombre es obligatorio` | `nombre` vacío | Java, Python |
| E05 | 400 | `El nombre debe tener entre 3 y 150 caracteres` | Longitud inválida | Java, Python |
| E06 | 400 | `El correo es obligatorio` | `correo` vacío | Java, Python |
| E07 | 400 | `El correo no es válido` | No cumple la regex | Java, Python |
| E08 | 400 | `El correo debe tener máximo 150 caracteres` | Más de 150 caracteres | Java, Python |
| E09 | 400 | `La materia es obligatoria` | `materia_id` ausente, `null`, no entero o ≤ 0 | Java, Python |
| E10 | 400 | `La materia indicada no existe` | `materia_id` no está en `materias` | Python |
| E11 | 404 | `No existe un monitor con el código {codigo}` | GET/PUT/DELETE de un código inexistente | Python |
| E12 | 409 | `Ya existe un monitor con el código {codigo}` | POST con código repetido (RF6) | Python |
| E13 | 404 | `Ruta no encontrada` | Ruta que no existe | Java, PHP, Python |
| E14 | 405 | `Método no permitido` | Método no soportado en una ruta que existe | Java, PHP, Python |
| E15 | 502 | `Servicio PHP no disponible` | Java no puede conectar con PHP o vence el timeout | Java |
| E16 | 502 | `Servicio de persistencia no disponible` | PHP no puede conectar con Python o vence el timeout | PHP |
| E17 | 503 | `Base de datos no disponible` | Python no puede conectar con PostgreSQL | Python |
| E18 | 500 | `Error interno del servidor` | Cualquier error no previsto | Todos |

En la interfaz se muestra el texto de `error` tal como llega. La única excepción es un fallo de red
de `fetch`, que muestra `No se pudo conectar con el servidor`.

## 6. Normalización y validación de campos

Java y Python aplican la **misma** normalización y validación (§6), en este orden.

### 6.1 Normalización (antes de validar)

| Campo | Normalización | Ejemplo |
|-------|---------------|---------|
| `codigo` | `trim` + MAYÚSCULAS. También el `{codigo}` de la ruta | `"  m-001 "` → `"M-001"` |
| `nombre` | `trim` + espacios internos múltiples → uno | `" Ana   López "` → `"Ana López"` |
| `correo` | `trim` + minúsculas | `"Ana@UCaldas.edu.co "` → `"ana@ucaldas.edu.co"` |
| `materia_id` | Ninguna: debe llegar como número entero JSON | `1` |

La normalización es idempotente: aplicarla dos veces da lo mismo. Por eso no importa que Java y Python
la apliquen sobre el mismo dato.

### 6.2 Validación (después de normalizar)

| Campo | Obligatorio | Regla | Errores |
|-------|-------------|-------|---------|
| `codigo` | Sí (solo POST) | Regex `^[A-Z0-9-]{1,20}$` | E02, E03 |
| `nombre` | Sí | Entre 3 y 150 caracteres | E04, E05 |
| `correo` | Sí | Regex `^[^@\s]+@[^@\s]+\.[^@\s]+$` y máximo 150 caracteres | E06, E07, E08 |
| `materia_id` | Sí | Entero > 0 que exista en `materias` | E09, E10 |

- "Vacío" significa ausente, `null`, o texto que después del `trim` queda en `""`.
- `materia_id` como texto (`"1"`), decimal (`1.5`) o booleano es inválido: `La materia es obligatoria`.
- En Java no se usa `@Email` de Jakarta, porque acepta `a@b` sin punto: se usa la regex del contrato.

### 6.3 Orden de validación

Si hay varios errores se responde **solo el primero**, en este orden fijo:

1. JSON mal formado o cuerpo que no es objeto → E01
2. `codigo` (solo POST): obligatorio, luego formato
3. `nombre`: obligatorio, luego longitud
4. `correo`: obligatorio, luego formato, luego longitud
5. `materia_id`: obligatorio/tipo
6. (solo Python) existencia del monitor en PUT → 404
7. (solo Python) existencia de la materia → 400
8. (solo Python) código duplicado en POST → 409

La base de datos repite estas reglas con `CHECK`, `PRIMARY KEY` y `FOREIGN KEY` (§10) como última
barrera.

## 7. Colección Postman

Archivo: [postman/monitores.postman_collection.json](postman/monitores.postman_collection.json)
(formato Postman v2.1).

1. En Postman: **Import** → seleccionar el archivo.
2. La variable de colección `baseUrl` indica qué capa se prueba:

   | Capa | `baseUrl` |
   |------|-----------|
   | nginx (entrada pública, por defecto) | `http://localhost:8080/api` |
   | Java | `http://localhost:8081` |
   | PHP | `http://localhost:8082` |
   | Python | `http://localhost:8083` |

3. Ejecutarla completa con el **Collection Runner**, en orden. Tiene 19 peticiones en tres carpetas:
   - **Salud y materias.**
   - **CRUD de monitores:** crea, consulta, actualiza y borra `DEV-001`, y lo deja eliminado.
   - **Errores del contrato:** 400, 404, 405 y 409.

   Cada petición trae pruebas del código HTTP, del `Content-Type` y del cuerpo o mensaje exacto.

## Verificación

Con `docker compose up --build`, la BD recién creada y el 21 de noviembre de 2026 sobre la rama de
documentación, se ejecutaron las mismas 19 peticiones de la colección contra cada capa:

| Capa | Resultado |
|------|-----------|
| nginx `:8080/api` | 18/19: todo coincide salvo el `Content-Type` de `/health` (ver nota) |
| Java `:8081` | 18/19: todo coincide salvo el `Content-Type` de `/health` (ver nota) |
| PHP `:8082` | 19/19 |
| Python `:8083` | 19/19 |

También se comprobaron a mano los errores de disponibilidad:

- con `monitores-db` detenido, `GET /api/monitores` responde `503 Base de datos no disponible` y
  `/api/health` sigue en 200;
- con `monitores-python` detenido, responde `502 Servicio de persistencia no disponible`;
- con `monitores-php` detenido, responde `502 Servicio PHP no disponible`.

> **Nota:** `GET /health` de Java responde `Content-Type: application/json` sin `charset=utf-8`. Las
> demás rutas de Java sí lo incluyen, y H4 lo exige en toda respuesta con cuerpo. El cuerpo es correcto
> y no afecta a la interfaz. Queda reportado para el dueño de `java-controller`.
