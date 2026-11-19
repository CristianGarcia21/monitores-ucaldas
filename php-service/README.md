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
