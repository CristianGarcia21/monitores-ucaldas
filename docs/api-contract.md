# Contrato de API (fuente de verdad)

Este documento es **el acuerdo entre todos los componentes**. Si cada quien respeta este contrato,
puede trabajar sin esperar a los demás: basta con simular (mockear) la capa de abajo.

> Si alguien necesita cambiar el contrato, lo propone en un issue/PR que modifique **solo este archivo**
> y avisa al grupo antes de tocar código.

## Flujo

```
Navegador ──► frontend (nginx :8080) ──/api/*──► java-controller (:8081)
                                                    │  valida datos básicos
                                                    ▼
                                               php-service (:8082)
                                                    │  intermediario / reenvío
                                                    ▼
                                              python-service (:8083)
                                                    │  persistencia
                                                    ▼
                                              database (PostgreSQL :5432)
```

**Regla de oro:** los tres servicios backend exponen **las mismas rutas y el mismo JSON**.
Cada capa recibe la petición, hace su parte y la reenvía tal cual a la siguiente.
El frontend llama a `/api/...`; nginx quita el prefijo `/api` y lo envía a Java.

## Modelo de datos

### Monitor

```json
{
  "codigo": "M001",
  "nombre": "Ana María López",
  "correo": "ana.lopez@ucaldas.edu.co",
  "materia_id": 1,
  "materia_nombre": "Ingeniería de Software III"
}
```

| Campo            | Tipo    | Reglas                                              |
|------------------|---------|-----------------------------------------------------|
| `codigo`         | string  | Obligatorio, máx. 20 caracteres, único (PK)         |
| `nombre`         | string  | Obligatorio, máx. 150 caracteres                     |
| `correo`         | string  | Obligatorio, formato de correo válido, máx. 150      |
| `materia_id`     | integer | Obligatorio, debe existir en `materias`             |
| `materia_nombre` | string  | **Solo en respuestas** (no se envía al crear/editar) |

### Materia

```json
{ "id": 1, "codigo": "SW3", "nombre": "Ingeniería de Software III" }
```

## Endpoints (iguales en Java, PHP y Python)

| Método | Ruta                   | Body (JSON)                                   | Éxito                    | Errores               |
|--------|------------------------|-----------------------------------------------|--------------------------|-----------------------|
| GET    | `/health`              | —                                             | 200 `{"service","status"}` | —                   |
| GET    | `/materias`            | —                                             | 200 `[Materia]`          | —                     |
| GET    | `/monitores`           | —                                             | 200 `[Monitor]`          | —                     |
| GET    | `/monitores/{codigo}`  | —                                             | 200 `Monitor`            | 404                   |
| POST   | `/monitores`           | `{codigo, nombre, correo, materia_id}`        | 201 `Monitor`            | 400, 409              |
| PUT    | `/monitores/{codigo}`  | `{nombre, correo, materia_id}`                | 200 `Monitor`            | 400, 404              |
| DELETE | `/monitores/{codigo}`  | —                                             | 204 (sin body)           | 404                   |

Desde el navegador las mismas rutas llevan el prefijo `/api` (ej. `GET /api/monitores`).

### Formato de error (todas las capas)

```json
{ "error": "Mensaje legible para el usuario" }
```

| Código | Cuándo                                                                 |
|--------|------------------------------------------------------------------------|
| 400    | Campos faltantes/vacíos, correo inválido, `materia_id` inexistente     |
| 404    | No existe un monitor con ese código                                    |
| 409    | Ya existe un monitor con ese código (RF6 – código duplicado)           |
| 502    | La capa siguiente no respondió (lo devuelve Java o PHP)                 |

### Quién valida qué (RF6)

- **Frontend:** validación visual (campos `required`, tipo email) para buena experiencia.
- **Java:** validación básica obligatoria → responde **400** sin llamar a PHP si faltan datos o el correo es inválido.
- **PHP:** no valida reglas de negocio; reenvía y propaga el código HTTP y el body de Python.
- **Python:** validación final contra la BD → **409** si el código ya existe, **400** si la materia no existe, **404** si no existe el monitor.

## Variables de entorno

| Servicio        | Variable             | Valor en docker-compose          | Valor local por defecto  |
|-----------------|----------------------|----------------------------------|--------------------------|
| java-controller | `PHP_SERVICE_URL`    | `http://php-service:8082`        | `http://localhost:8082`  |
| php-service     | `PYTHON_SERVICE_URL` | `http://python-service:8083`     | `http://localhost:8083`  |
| python-service  | `DB_HOST` / `DB_PORT` / `DB_NAME` / `DB_USER` / `DB_PASSWORD` | `database` / `5432` / `monitores` / `monitores` / `monitores` | `localhost` / ... |

## Cómo trabajar sin depender de los demás

| Si trabajas en… | Simula la capa de abajo con…                                                              |
|-----------------|-------------------------------------------------------------------------------------------|
| frontend        | Un arreglo en memoria / `fetch` a un JSON local con datos de ejemplo de este documento     |
| java-controller | Un mock HTTP (WireMock, Postman Mock Server o `MockRestServiceServer` en tests)           |
| php-service     | `php -S` con un script que devuelva JSON fijo, o Postman Mock Server                      |
| python-service  | Nada: solo necesita la BD → `docker compose up database`                                   |
| database        | Nada                                                                                       |
