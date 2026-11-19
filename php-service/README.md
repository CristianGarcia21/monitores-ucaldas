# php-service – Intermediario

Servicio PHP 8.3 (sin frameworks, solo cURL) que recibe las peticiones de `java-controller` y las **reenvía sin
modificar** a `python-service`, devolviendo su respuesta intacta ([contrato](../docs/api-contract.md), §9).

| | |
|---|---|
| Puerto | `8082` |
| Salud | `GET /health` → `{"service": "php-service", "status": "ok"}` |
| Variable | `PYTHON_SERVICE_URL` (por defecto `http://localhost:8083`, sin `/` final) |

## Ejecutar contra el mock de Python

El mock `dev/mock-python.php` simula a `python-service` con JSON fijo del contrato, así que PHP se puede probar
completo sin base de datos ni Python. Se necesitan dos terminales, ambas dentro de `php-service/`:

```bash
# Terminal 1 – mock de Python en el puerto 8083
php -S localhost:8083 dev/mock-python.php

# Terminal 2 – servicio PHP en el puerto 8082 (apunta al mock por defecto)
php -S localhost:8082 index.php
```

Si el mock corre en otro puerto: `PYTHON_SERVICE_URL=http://localhost:9000 php -S localhost:8082 index.php`.

### Qué responde el mock

| Petición | Respuesta |
|---|---|
| `GET /materias` | 200 con las materias 1 (`SW3`) y 2 (`BD1`) |
| `GET /monitores` | 200 con el monitor `M-001` |
| `GET /monitores/M-001` | 200 con el monitor · cualquier otro código → 404 E11 |
| `POST /monitores` | 201 con el monitor creado · `codigo` `M-001` → 409 E12 · `materia_id` distinto de 1 o 2 → 400 E10 |
| `PUT /monitores/M-001` | 200 con el monitor actualizado · otro código → 404 E11 · materia inexistente → 400 E10 |
| `DELETE /monitores/M-001` | 204 sin cuerpo · otro código → 404 E11 |

El mock no guarda nada: cada petición responde lo mismo. Está en `dev/`, que se excluye de la imagen Docker
(`.dockerignore`).

### Pruebas rápidas

```bash
curl -i http://localhost:8082/materias
curl -i http://localhost:8082/monitores/M-001
curl -i -X POST http://localhost:8082/monitores -H 'Content-Type: application/json' \
  -d '{"codigo":"DEV-001","nombre":"Carlos Pérez","correo":"carlos.perez@ucaldas.edu.co","materia_id":2}'
curl -i -X DELETE http://localhost:8082/monitores/M-001
```

## Errores propios de PHP

PHP solo genera respuestas propias en estos casos del [catálogo de errores](../docs/api-contract.md#7-catálogo-de-errores);
todo lo demás es la respuesta de Python tal cual. Todos tienen el formato `{"error": "<mensaje>"}`.

| Caso | Respuesta | Error |
|---|---|---|
| Ruta inexistente (incluida `/monitores/` con barra final) | `404 Ruta no encontrada` | E13 |
| Método no soportado en una ruta que existe | `405 Método no permitido` | E14 |
| Body de `POST`/`PUT` vacío, mal formado o que no es un objeto JSON | `400 JSON inválido` | E01 |
| Python caído o sin responder (conexión 3 s, lectura 10 s) | `502 Servicio de persistencia no disponible` | E16 |
| Error no previsto (el detalle solo va al log) | `500 Error interno del servidor` | E18 |

PHP solo comprueba que el body sea JSON: no valida campos ni reglas de negocio (eso es de Java y Python).
Cada error queda registrado con `error_log` (en Docker: `docker compose logs -f php-service`).

### Probar los errores con curl

Con PHP corriendo en `localhost:8082` (el mock o Python real en `:8083` solo hace falta para el caso 502):

```bash
# 404 Ruta no encontrada
curl -i http://localhost:8082/otra-ruta
curl -i http://localhost:8082/monitores/          # barra final

# 405 Método no permitido
curl -i -X DELETE http://localhost:8082/monitores
curl -i -X POST http://localhost:8082/materias
curl -i -X POST http://localhost:8082/monitores/M-001

# 400 JSON inválido (mal formado, vacío y que no es un objeto)
curl -i -X POST http://localhost:8082/monitores -H 'Content-Type: application/json' -d '{"codigo": "DEV-001",'
curl -i -X POST http://localhost:8082/monitores -H 'Content-Type: application/json' -d ''
curl -i -X PUT  http://localhost:8082/monitores/M-001 -H 'Content-Type: application/json' -d '[1, 2]'

# 502 Servicio de persistencia no disponible: apagar el mock/Python y repetir cualquier petición válida
curl -i http://localhost:8082/materias
```

Y los casos que PHP solo propaga (con el mock, ver tabla de arriba):

```bash
curl -i http://localhost:8082/monitores/X-999      # 404 E11 de Python
curl -i -X POST http://localhost:8082/monitores -H 'Content-Type: application/json' \
  -d '{"codigo":"M-001","nombre":"Ana López","correo":"ana@ucaldas.edu.co","materia_id":1}'   # 409 E12
curl -i -X DELETE http://localhost:8082/monitores/M-001   # 204 sin cuerpo
```
