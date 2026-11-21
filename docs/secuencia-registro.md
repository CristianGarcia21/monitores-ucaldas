# Diagrama de secuencia: registro de un monitor (RF1)

**Entregable 2.** Recorrido completo de `POST /api/monitores`, desde que el usuario pulsa **Guardar**
hasta que el monitor aparece en la tabla. Incluye las dos alternativas que exige el contrato: datos
inválidos (Java responde 400 sin llamar a PHP) y código duplicado (PostgreSQL → Python 409 → se
propaga).

La imagen [img/secuencia-registro.png](img/secuencia-registro.png) se genera desde este diagrama.

## Petición de ejemplo

```http
POST /api/monitores HTTP/1.1
Host: localhost:8080
Content-Type: application/json

{"codigo": " dev-001 ", "nombre": "José  Ñúñez Peña", "correo": "Jose.Nunez@UCaldas.edu.co", "materia_id": 1}
```

Java y Python normalizan el cuerpo (§6.1) antes de validarlo. Se guarda como
`{"codigo": "DEV-001", "nombre": "José Ñúñez Peña", "correo": "jose.nunez@ucaldas.edu.co", "materia_id": 1}`.

Respuesta `201 Created` (`Content-Type: application/json; charset=utf-8`):

```json
{"codigo": "DEV-001", "nombre": "José Ñúñez Peña", "correo": "jose.nunez@ucaldas.edu.co", "materia_id": 1, "materia_nombre": "Ingeniería de Software III"}
```

## Diagrama

```mermaid
sequenceDiagram
    autonumber
    actor U as Usuario
    participant JS as Navegador (app.js / api.js)
    participant NG as nginx (frontend :8080)
    participant J as Java (java-controller :8081)
    participant P as PHP (php-service :8082)
    participant PY as Python (python-service :8083)
    participant DB as PostgreSQL (:5432)

    U->>JS: Llena el formulario y pulsa "Guardar"
    JS->>JS: leerFormulario(): validación visual (obligatorios, formato)
    JS->>NG: POST /api/monitores<br/>{"codigo":" dev-001 ","nombre":"José  Ñúñez Peña",...}
    NG->>J: POST /monitores (quita el prefijo /api)
    J->>J: MonitorValidator.validarCreacion()<br/>normaliza (§6.1) y valida (§6.2)

    alt Datos inválidos (p. ej. correo "jose@ucaldas", enviado desde Postman o curl)
        J-->>NG: 400 {"error": "El correo no es válido"}
        Note over J,PY: Java corta la cadena: PHP y Python no reciben nada
        NG-->>JS: 400 (mismo cuerpo)
        JS-->>U: Muestra el mensaje del backend tal cual
    else Datos válidos
        J->>P: POST /monitores (JSON normalizado)
        P->>P: resolverRuta() y esObjetoJsonValido()
        P->>PY: POST /monitores (mismo método, ruta y cuerpo, por cURL)
        PY->>PY: MonitorCreate: normaliza y valida de nuevo
        PY->>DB: SELECT 1 FROM materias WHERE id = %(id)s
        DB-->>PY: 1 fila (la materia existe)
        PY->>DB: INSERT INTO monitores ... RETURNING (con JOIN a materias)

        alt Camino feliz: el código no existe
            DB-->>PY: fila insertada + materia_nombre
            PY->>DB: COMMIT
            PY-->>P: 201 {monitor completo con materia_nombre}
            P-->>J: 201 (mismo cuerpo)
            J-->>NG: 201 (mismo cuerpo)
            NG-->>JS: 201 (mismo cuerpo)
            JS->>NG: GET /api/monitores (recarga la tabla)
            NG-->>JS: 200 [lista ordenada por código]
            JS-->>U: "Monitor DEV-001 registrado correctamente" y fila nueva
        else Código duplicado (RF6)
            DB-->>PY: UniqueViolation (clave primaria monitores.codigo)
            PY->>DB: ROLLBACK
            PY-->>P: 409 {"error": "Ya existe un monitor con el código DEV-001"}
            P-->>J: 409 (mismo cuerpo, H7)
            J-->>NG: 409 (mismo cuerpo, H7)
            NG-->>JS: 409 (mismo cuerpo)
            JS-->>U: Muestra el mensaje y marca el campo código en rojo
        end
    end
```

## Explicación de los pasos

| Pasos | Qué pasa | Dónde está en el código |
|-------|----------|-------------------------|
| 1–3 | La interfaz valida lo básico y envía el JSON a la ruta relativa `/api/monitores` (A2) | `frontend/app.js` (`guardarMonitor`, `leerFormulario`), `frontend/api.js` (`crearMonitor`) |
| 4 | nginx reenvía a Java quitando `/api` | `frontend/nginx.conf` (`location /api/`) |
| 5 | Java normaliza y valida en el orden del §6.3 | `java-controller/.../validation/MonitorValidator.java` |
| 6–8 | Alternativa 400: Java responde el primer error y **corta la cadena** | `java-controller/.../exception/GlobalExceptionHandler.java` |
| 9–11 | PHP comprueba ruta, método y JSON, y reenvía sin modificar | `php-service/index.php`, `php-service/PythonClient.php` |
| 12–15 | Python valida de nuevo, comprueba que la materia exista (si no, 400 E10) e inserta | `python-service/main.py`, `schemas.py`, `repository.py` |
| 16–24 | Camino feliz: commit, 201 de vuelta por la misma cadena y recarga de la tabla | `python-service/db.py` (`get_connection`), `frontend/app.js` (`cargarMonitores`) |
| 25–31 | Alternativa 409: PostgreSQL rechaza la clave primaria repetida, Python hace *rollback* y responde 409 (E12), y PHP y Java lo propagan sin cambiarlo | `python-service/main.py` (captura `UniqueViolation`) |

**Notas**

- **Orden de validación de Python (§6.3, pasos 7 y 8).** Python consulta primero si la materia existe
  y después inserta. Así, si el código está repetido **y** la materia no existe, gana el 400 de materia,
  como exige el contrato. PostgreSQL, por sí solo, revisaría antes la clave primaria.
- **De dónde viene el 400 de Java.** Desde la interfaz es poco común, porque `app.js` aplica las mismas
  reglas antes de enviar (captura de validación en el documento final). Aparece cuando la petición llega
  directamente a la API, como en la colección de Postman ([endpoints.md](endpoints.md)).
- **Si un servicio de la cadena no responde,** la respuesta es 502 (`Servicio PHP no disponible` o
  `Servicio de persistencia no disponible`) o 503 si la caída es de la base de datos (`Base de datos no
  disponible`). Esos casos se describen en [endpoints.md](endpoints.md#5-catálogo-de-errores-e01e18).
