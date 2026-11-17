# Contrato del sistema – Gestión de Monitores Académicos

**Versión 1.0 · 16 de noviembre de 2026**

Este documento es **la única fuente de verdad** del proyecto. Define cómo se comunican los componentes,
qué datos se intercambian, cómo se validan y qué responde cada capa en cada caso.

> **Regla principal:** si una issue, un comentario o un mensaje de WhatsApp dice algo distinto a este
> documento, **manda este documento**. Si algo no está aquí, se pregunta en el grupo y se agrega aquí
> antes de programarlo (ver [§14 Cambios al contrato](#14-cambios-al-contrato)).

Las reglas de Git, ramas, commits y estilo de código están en [CONTRIBUTING.md](../CONTRIBUTING.md).

## Índice

1. [Arquitectura y flujo](#1-arquitectura-y-flujo)
2. [Servicios, puertos y variables de entorno](#2-servicios-puertos-y-variables-de-entorno)
3. [Convenciones HTTP](#3-convenciones-http)
4. [Convenciones JSON](#4-convenciones-json)
5. [Modelo de datos](#5-modelo-de-datos)
6. [Normalización y validación de campos](#6-normalización-y-validación-de-campos)
7. [Catálogo de errores](#7-catálogo-de-errores)
8. [Endpoints en detalle](#8-endpoints-en-detalle)
9. [Responsabilidades por capa](#9-responsabilidades-por-capa)
10. [Esquema de base de datos](#10-esquema-de-base-de-datos)
11. [Timeouts, logs y salud](#11-timeouts-logs-y-salud)
12. [Datos de prueba](#12-datos-de-prueba)
13. [Cómo trabajar en paralelo (mocks)](#13-cómo-trabajar-en-paralelo-mocks)
14. [Cambios al contrato](#14-cambios-al-contrato)

---

## 1. Arquitectura y flujo

```
Navegador ──► frontend (nginx :8080) ──/api/*──► java-controller (:8081)
                                                    │  normaliza + valida datos básicos
                                                    ▼
                                               php-service (:8082)
                                                    │  intermediario: reenvía sin modificar
                                                    ▼
                                              python-service (:8083)
                                                    │  normaliza + valida + persiste
                                                    ▼
                                              database (PostgreSQL :5432)
```

Reglas de arquitectura (obligatorias, las exige el enunciado):

- **A1.** Toda operación del CRUD atraviesa **todas** las capas en este orden. Nadie se salta una capa.
- **A2.** El frontend **solo** llama a rutas relativas `/api/...`. Nunca a `localhost:8081/8082/8083` ni a la BD.
- **A3.** Solo `python-service` se conecta a la base de datos.
- **A4.** Los tres servicios backend exponen **exactamente las mismas rutas, métodos, cuerpos y códigos HTTP**.
  nginx quita el prefijo `/api` antes de enviar a Java (`/api/monitores` → `/monitores`).
- **A5.** Comunicación solo por HTTP con JSON. Nada de colas, archivos compartidos ni sockets.

## 2. Servicios, puertos y variables de entorno

| Servicio          | Host en Docker     | Puerto | Responsable      |
|-------------------|--------------------|--------|------------------|
| `frontend`        | `frontend`         | 8080 → 80 | Tania Botina  |
| `java-controller` | `java-controller`  | 8081   | Cristian Garcia  |
| `php-service`     | `php-service`      | 8082   | Juan Fernando    |
| `python-service`  | `python-service`   | 8083   | Juan Diego       |
| `database`        | `database`         | 5432   | Valentina Galvis |

**Los puertos y nombres de host no se cambian.** Dentro de Docker se usa el nombre del servicio
(`http://php-service:8082`); fuera de Docker se usa `localhost`.

| Servicio        | Variable             | Valor en Docker               | Valor por defecto (local) |
|-----------------|----------------------|-------------------------------|---------------------------|
| java-controller | `PHP_SERVICE_URL`    | `http://php-service:8082`     | `http://localhost:8082`   |
| php-service     | `PYTHON_SERVICE_URL` | `http://python-service:8083`  | `http://localhost:8083`   |
| python-service  | `DB_HOST`            | `database`                    | `localhost`               |
| python-service  | `DB_PORT`            | `5432`                        | `5432`                    |
| python-service  | `DB_NAME`            | `monitores`                   | `monitores`               |
| python-service  | `DB_USER`            | `monitores`                   | `monitores`               |
| python-service  | `DB_PASSWORD`        | `monitores`                   | `monitores`               |

- Ninguna URL, puerto o credencial se escribe "quemada" en el código: siempre se lee de la variable con ese valor por defecto.
- Las URLs base **no** terminan en `/`.

## 3. Convenciones HTTP

| Regla | Detalle |
|-------|---------|
| **H1. Rutas** | En minúscula, en plural y en español: `/monitores`, `/materias`. **Sin barra final** (`/monitores/` no es válida → 404). |
| **H2. Parámetro de ruta** | El código del monitor va en la ruta: `/monitores/{codigo}`. No se usan query params (`?codigo=`) en esta versión. |
| **H3. Métodos** | `GET` consultar · `POST` crear · `PUT` actualizar (reemplazo completo de los campos editables) · `DELETE` eliminar. No se usa `PATCH`. |
| **H4. Content-Type** | Toda respuesta con cuerpo lleva `Content-Type: application/json; charset=utf-8`. Las peticiones `POST`/`PUT` envían `Content-Type: application/json`. |
| **H5. 204** | `DELETE` exitoso responde `204 No Content` **sin cuerpo** (ni siquiera `{}` o `null`). |
| **H6. Códigos permitidos** | Solo se usan: `200, 201, 204, 400, 404, 405, 409, 500, 502, 503`. No usar `422`, `401`, `403` ni otros. |
| **H7. Propagación** | Java y PHP devuelven **el mismo código y el mismo cuerpo** que recibieron de la capa siguiente (no lo reescriben, no lo envuelven). Solo generan respuestas propias en los casos que les asigna el [§7](#7-catálogo-de-errores). |
| **H8. CORS** | No se configura CORS: el navegador solo habla con nginx (mismo origen). |
| **H9. Encoding** | Todo en UTF-8 (tildes y ñ deben llegar intactas hasta la BD y volver). |
| **H10. Métodos no definidos** | Una ruta existente con un método no soportado → `405` (ej. `DELETE /monitores`). Una ruta inexistente → `404`. |

## 4. Convenciones JSON

| Regla | Detalle |
|-------|---------|
| **J1. Nombres** | Claves en `snake_case` y en español: `codigo`, `nombre`, `correo`, `materia_id`, `materia_nombre`. Exactamente como aparecen en este documento. |
| **J2. Tipos** | `materia_id` e `id` son **números** (`1`, no `"1"`). Todo lo demás es string. |
| **J3. Sin envoltorio** | Las listas se devuelven como arreglo plano: `[ {...}, {...} ]`. Nada de `{"data": [...]}` ni `{"monitores": [...]}`. Un objeto se devuelve tal cual. |
| **J4. Lista vacía** | Sin resultados → `200` con `[]` (no `404`). |
| **J5. Sin null** | Ningún campo de respuesta es `null`; todos los campos son obligatorios. |
| **J6. Campos extra** | En peticiones, los campos que no estén en el contrato **se ignoran** (no generan error). En `PUT`, si el body trae `codigo`, se ignora: el código que manda es el de la ruta. |
| **J7. Orden** | `GET /monitores` ordena por `codigo` ascendente. `GET /materias` ordena por `nombre` ascendente. |
| **J8. Errores** | Siempre `{"error": "<mensaje>"}` con **una sola clave**. Nada de `detail`, `message`, `status`, `timestamp` ni trazas. |

## 5. Modelo de datos

### Monitor (respuesta)

```json
{
  "codigo": "M-001",
  "nombre": "Ana María López",
  "correo": "ana.lopez@ucaldas.edu.co",
  "materia_id": 1,
  "materia_nombre": "Ingeniería de Software III"
}
```

### Monitor (petición POST)

```json
{ "codigo": "M-001", "nombre": "Ana María López", "correo": "ana.lopez@ucaldas.edu.co", "materia_id": 1 }
```

### Monitor (petición PUT)

```json
{ "nombre": "Ana María López Ruiz", "correo": "ana.lopez@ucaldas.edu.co", "materia_id": 2 }
```

### Materia (respuesta, solo lectura)

```json
{ "id": 1, "codigo": "SW3", "nombre": "Ingeniería de Software III" }
```

- Las materias **no** tienen CRUD: se cargan desde `database/init.sql` y solo se consultan.
- `materia_nombre` existe **solo en respuestas**; si llega en una petición se ignora (J6).

## 6. Normalización y validación de campos

### 6.1 Normalización (se aplica ANTES de validar)

Java y Python aplican **la misma** normalización (es idempotente: aplicarla dos veces da lo mismo).
El frontend puede aplicarla también para mostrar el valor final al usuario.

| Campo        | Normalización                                                       |
|--------------|---------------------------------------------------------------------|
| `codigo`     | `trim` + convertir a **MAYÚSCULAS**. Aplica también al `{codigo}` de la ruta. |
| `nombre`     | `trim` + reemplazar espacios múltiples internos por uno solo.       |
| `correo`     | `trim` + convertir a **minúsculas**.                               |
| `materia_id` | Ninguna (debe llegar como número entero JSON).                       |

Ejemplo: `{"codigo": "  m-001 ", "nombre": " Ana   López ", "correo": "Ana@UCaldas.edu.co "}` se guarda como
`{"codigo": "M-001", "nombre": "Ana López", "correo": "ana@ucaldas.edu.co"}`.

### 6.2 Reglas de validación (después de normalizar)

| Campo        | Obligatorio | Regla                                                         |
|--------------|-------------|---------------------------------------------------------------|
| `codigo`     | Sí (solo POST) | Regex `^[A-Z0-9-]{1,20}$` (mayúsculas, dígitos y guion, 1 a 20) |
| `nombre`     | Sí          | Longitud entre **3 y 150** caracteres                         |
| `correo`     | Sí          | Regex `^[^@\s]+@[^@\s]+\.[^@\s]+$` y máximo **150** caracteres |
| `materia_id` | Sí          | Entero mayor que 0 que exista en la tabla `materias`          |

- **Todos usan exactamente estas regex.** En Java **no** usar `@Email` de Jakarta (acepta correos sin punto como `a@b`): usar `@Pattern` con la regex de arriba.
- "Vacío" = ausente, `null`, o string que después del `trim` queda en `""`.
- `materia_id` que llega como string (`"1"`), decimal (`1.5`) o booleano → se trata como inválido (mensaje `La materia es obligatoria`).

### 6.3 Orden de validación

Si hay varios errores, se responde **solo el primero**, revisando en este orden fijo:

1. JSON mal formado o body que no es objeto → `JSON inválido`
2. `codigo` (solo en POST): primero obligatorio, luego formato
3. `nombre`: obligatorio, luego longitud
4. `correo`: obligatorio, luego formato, luego longitud
5. `materia_id`: obligatorio/tipo
6. (solo Python) existencia del monitor (PUT) → 404
7. (solo Python) existencia de la materia → 400
8. (solo Python) código duplicado (POST) → 409

## 7. Catálogo de errores

**Los mensajes se copian textualmente** (con tildes, mayúscula inicial y sin punto final). `{codigo}` se reemplaza
por el código ya normalizado.

| # | HTTP | Mensaje exacto | Cuándo | Lo genera |
|---|------|----------------|--------|-----------|
| E01 | 400 | `JSON inválido` | Body vacío, mal formado o que no es un objeto en POST/PUT | Java, PHP, Python |
| E02 | 400 | `El código es obligatorio` | `codigo` vacío (POST) | Java, Python |
| E03 | 400 | `El código solo puede tener letras, números y guiones (máximo 20 caracteres)` | `codigo` no cumple la regex | Java, Python |
| E04 | 400 | `El nombre es obligatorio` | `nombre` vacío | Java, Python |
| E05 | 400 | `El nombre debe tener entre 3 y 150 caracteres` | Longitud inválida | Java, Python |
| E06 | 400 | `El correo es obligatorio` | `correo` vacío | Java, Python |
| E07 | 400 | `El correo no es válido` | No cumple la regex | Java, Python |
| E08 | 400 | `El correo debe tener máximo 150 caracteres` | Más de 150 | Java, Python |
| E09 | 400 | `La materia es obligatoria` | `materia_id` ausente, null, no entero o ≤ 0 | Java, Python |
| E10 | 400 | `La materia indicada no existe` | `materia_id` no está en `materias` | Python |
| E11 | 404 | `No existe un monitor con el código {codigo}` | GET/PUT/DELETE de un código inexistente | Python |
| E12 | 409 | `Ya existe un monitor con el código {codigo}` | POST con código repetido (RF6) | Python |
| E13 | 404 | `Ruta no encontrada` | Ruta que no existe | Java, PHP, Python |
| E14 | 405 | `Método no permitido` | Método no soportado en una ruta que sí existe | Java, PHP, Python |
| E15 | 502 | `Servicio PHP no disponible` | Java no puede conectar con PHP o hay timeout | Java |
| E16 | 502 | `Servicio de persistencia no disponible` | PHP no puede conectar con Python o hay timeout | PHP |
| E17 | 503 | `Base de datos no disponible` | Python no puede conectar con PostgreSQL | Python |
| E18 | 500 | `Error interno del servidor` | Cualquier error no previsto (el detalle solo va al log) | Todos |

En el frontend se muestra el texto de `error` **tal como llega**; no se traduce ni se reemplaza por mensajes propios
(excepto si `fetch` falla por red: `No se pudo conectar con el servidor`).

## 8. Endpoints en detalle

Rutas vistas por cada capa:

| Operación | Navegador → nginx | nginx → Java / Java → PHP / PHP → Python |
|-----------|-------------------|------------------------------------------|
| Salud | `GET /api/health` | `GET /health` (cada servicio responde el suyo, no se encadena) |
| Listar materias | `GET /api/materias` | `GET /materias` |
| Listar monitores (RF2) | `GET /api/monitores` | `GET /monitores` |
| Consultar monitor (RF3) | `GET /api/monitores/{codigo}` | `GET /monitores/{codigo}` |
| Registrar (RF1) | `POST /api/monitores` | `POST /monitores` |
| Actualizar (RF4) | `PUT /api/monitores/{codigo}` | `PUT /monitores/{codigo}` |
| Eliminar (RF5) | `DELETE /api/monitores/{codigo}` | `DELETE /monitores/{codigo}` |

### 8.1 `GET /health`

Cada servicio responde por sí mismo (no consulta a la capa siguiente).

```
200  {"service": "java-controller", "status": "ok"}
```

`service` vale `java-controller`, `php-service` o `python-service` según quién responda.

### 8.2 `GET /materias`

```
200  [
       {"id": 2, "codigo": "BD1", "nombre": "Bases de Datos I"},
       {"id": 1, "codigo": "SW3", "nombre": "Ingeniería de Software III"}
     ]
```

Errores posibles: E15, E16, E17, E18.

### 8.3 `GET /monitores` (RF2)

```
200  [
       {"codigo": "M-001", "nombre": "Ana María López", "correo": "ana.lopez@ucaldas.edu.co",
        "materia_id": 1, "materia_nombre": "Ingeniería de Software III"}
     ]
200  []        ← si no hay monitores
```

Errores posibles: E15, E16, E17, E18.

### 8.4 `GET /monitores/{codigo}` (RF3)

```
GET /monitores/m-001          ← se normaliza a M-001
200  {"codigo": "M-001", "nombre": "Ana María López", "correo": "ana.lopez@ucaldas.edu.co",
      "materia_id": 1, "materia_nombre": "Ingeniería de Software III"}

GET /monitores/X-999
404  {"error": "No existe un monitor con el código X-999"}
```

Errores posibles: E11, E15, E16, E17, E18.

### 8.5 `POST /monitores` (RF1, RF6)

```
POST /monitores
Content-Type: application/json

{"codigo": "M-002", "nombre": "Carlos Pérez", "correo": "carlos.perez@ucaldas.edu.co", "materia_id": 2}
```

| Caso | Respuesta |
|------|-----------|
| Éxito | `201` + Monitor completo (con `materia_nombre`) |
| Falta `nombre` | `400 {"error": "El nombre es obligatorio"}` → **lo responde Java, PHP no recibe nada** |
| Correo `carlos@ucaldas` | `400 {"error": "El correo no es válido"}` → Java |
| `materia_id: 99` | `400 {"error": "La materia indicada no existe"}` → Python, propagado por PHP y Java |
| Código repetido | `409 {"error": "Ya existe un monitor con el código M-002"}` → Python, propagado |

No se envía cabecera `Location`.

### 8.6 `PUT /monitores/{codigo}` (RF4)

```
PUT /monitores/M-002
Content-Type: application/json

{"nombre": "Carlos Andrés Pérez", "correo": "carlos.perez@ucaldas.edu.co", "materia_id": 1}
```

| Caso | Respuesta |
|------|-----------|
| Éxito | `200` + Monitor completo actualizado |
| Datos inválidos | `400` con el mensaje correspondiente (E04–E09) → Java |
| Monitor inexistente | `404 {"error": "No existe un monitor con el código M-002"}` → Python |
| Materia inexistente | `400 {"error": "La materia indicada no existe"}` → Python |

- `PUT` exige **los tres** campos editables (`nombre`, `correo`, `materia_id`). No hay actualización parcial.
- El código **no se puede cambiar** (si viene en el body se ignora, J6).

### 8.7 `DELETE /monitores/{codigo}` (RF5)

```
DELETE /monitores/M-002
204  (sin cuerpo)

DELETE /monitores/M-002       ← otra vez
404  {"error": "No existe un monitor con el código M-002"}
```

## 9. Responsabilidades por capa

| Capa | SÍ hace | NO hace |
|------|---------|---------|
| **Frontend** | Formularios y tablas; validación visual (`required`, `type=email`, `maxlength`); mostrar el `error` recibido; pedir confirmación antes de eliminar; cargar materias con `GET /api/materias` | Llamar a otro host que no sea `/api`; quemar ids de materias en el HTML; inventar mensajes de error del backend |
| **nginx** | Servir archivos estáticos; reenviar `/api/*` a Java quitando `/api` | Lógica de negocio |
| **Java** | Normalizar (§6.1); validar formato (§6.2) y responder 400 **sin llamar a PHP**; reenviar a PHP; propagar la respuesta (H7); E13–E15, E18 | Consultar si la materia existe o si el código está duplicado (no tiene acceso a la BD) |
| **PHP** | Enrutar; validar que el body sea JSON (E01); reenviar con cURL método, ruta y body **sin modificar**; propagar la respuesta; E13, E14, E16, E18 | Validar campos o reglas de negocio; cambiar mensajes de error |
| **Python** | Normalizar y validar de nuevo (§6, por si se llama directamente); verificar existencia y duplicados; ejecutar SQL parametrizado; mapear errores de BD a E10–E12, E17 | Confiar en que Java ya validó |
| **Base de datos** | Garantizar integridad con PK, FK, `UNIQUE` y `CHECK` equivalentes a §6.2 | — |

Python debe mapear las excepciones de `psycopg` así: `UniqueViolation` → E12 (409),
`ForeignKeyViolation` → E10 (400), `CheckViolation` → el error 400 del campo correspondiente
(o E18 si no se puede identificar), `OperationalError` de conexión → E17 (503).

## 10. Esquema de base de datos

El esquema definitivo (lo implementa Valentina en `database/init.sql`) debe ser equivalente a:

```sql
CREATE TABLE materias (
    id      SERIAL PRIMARY KEY,
    codigo  VARCHAR(20)  NOT NULL UNIQUE,
    nombre  VARCHAR(120) NOT NULL
);

CREATE TABLE monitores (
    codigo      VARCHAR(20)  PRIMARY KEY CHECK (codigo ~ '^[A-Z0-9-]{1,20}$'),
    nombre      VARCHAR(150) NOT NULL    CHECK (char_length(nombre) BETWEEN 3 AND 150),
    correo      VARCHAR(150) NOT NULL    CHECK (correo ~ '^[^@\s]+@[^@\s]+\.[^@\s]+$' AND correo = lower(correo)),
    materia_id  INTEGER      NOT NULL    REFERENCES materias(id) ON DELETE RESTRICT
);

CREATE INDEX idx_monitores_materia ON monitores(materia_id);
```

- Nombres de tablas y columnas **exactamente** así (los usa Python en sus consultas).
- Las materias con `id = 1` (`SW3`) e `id = 2` (`BD1`) **siempre existen** y conservan esos ids:
  las pruebas pueden contar con ellas. Las demás materias semilla se agregan después.
- El correo **no** es único (un estudiante podría monitorear dos materias con distinto código).

## 11. Timeouts, logs y salud

| Regla | Detalle |
|-------|---------|
| **T1. Timeouts** | Java → PHP y PHP → Python: conexión **3 s**, lectura **10 s**. Al vencer → 502 (E15 / E16). |
| **T2. Logs** | Cada servicio escribe **una línea por petición** en la salida estándar: `[servicio] MÉTODO RUTA -> STATUS (ms)`. Ej.: `[php-service] POST /monitores -> 201 (42 ms)`. Los errores 500 registran además el detalle (stack trace). Ver logs: `docker compose logs -f <servicio>`. |
| **T3. Salud** | `GET /health` siempre responde `200` mientras el proceso esté vivo, sin depender de otras capas. Lo usan los healthchecks de Docker. No se elimina ni se cambia. |
| **T4. Seguridad** | Nunca devolver trazas, SQL ni nombres de clases al cliente. SQL **siempre** parametrizado. |

## 12. Datos de prueba

| Uso | Prefijo de `codigo` | Quién | Regla |
|-----|---------------------|-------|-------|
| Datos semilla (demo) | `M-` (`M-001`…) | Valentina (`init.sql`) | No se borran en pruebas |
| Pruebas automáticas de Python | `TEST-` | Juan Diego | Se eliminan al terminar cada prueba |
| Pruebas de Java (mocks) | `TEST-` | Cristian | No tocan la BD |
| Smoke test end-to-end | `SMOKE-` | Valentina | El script los elimina al final aunque falle |
| Pruebas manuales | `DEV-` | Todos | Borrarlos después; reiniciar la BD con `docker compose down -v` si hace falta |

Correos de prueba siempre con dominio `@ucaldas.edu.co`.

## 13. Cómo trabajar en paralelo (mocks)

| Si trabajas en… | Simula la capa de abajo con… | Debe responder… |
|-----------------|------------------------------|-----------------|
| frontend | Modo mock en `api.js` (`USE_MOCK = true`) | Los ejemplos de §8 incluidos los errores 400/404/409 |
| java-controller | `MockRestServiceServer` (tests) o WireMock / Postman Mock en `:8082` | Los ejemplos de §8 |
| php-service | `php -S localhost:8083 dev/mock-python.php` | Los ejemplos de §8 |
| python-service | Nada: `docker compose up -d database` | — |
| database | Nada | — |
| docs | Este documento + `docker-compose.yml` | — |

**Los mocks responden exactamente los JSON y mensajes de este documento**; así, al conectar las capas reales no hay sorpresas.

Checklist antes de dar por terminada una integración (ejecutar contra `http://localhost:8080/api`):

- [ ] `GET /materias` → 200 con arreglo
- [ ] `POST` válido → 201 con `materia_nombre`
- [ ] `POST` repetido → 409 con el mensaje E12
- [ ] `POST` sin nombre → 400 E04 (y en los logs de PHP **no** aparece la petición)
- [ ] `POST` con `materia_id: 99` → 400 E10
- [ ] `GET /monitores/{codigo}` en minúsculas → 200 (normalización)
- [ ] `PUT` → 200 · `PUT` inexistente → 404 E11
- [ ] `DELETE` → 204 sin cuerpo · otra vez → 404 E11
- [ ] Nombres con tildes y ñ se guardan y se muestran bien

## 14. Cambios al contrato

1. Nadie programa algo que contradiga este documento.
2. Para cambiarlo: abrir un PR que modifique **solo** `docs/api-contract.md`, explicando el motivo.
3. Se avisa en el grupo y deben aprobarlo los responsables de **todas** las capas afectadas.
4. Al aprobarse se sube la versión (1.0 → 1.1) y se anota en el historial.

### Historial

| Versión | Fecha | Cambio |
|---------|-------|--------|
| 1.0 | 16 nov 2026 | Versión inicial completa |
