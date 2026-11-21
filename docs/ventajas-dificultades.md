# Ventajas y dificultades de la arquitectura distribuida y heterogénea

**Entregable 5.** Análisis crítico a partir de lo que vivimos al construir el sistema. Cada punto tiene
un ejemplo concreto del proyecto: un PR, una issue o una medición sobre el sistema levantado con
`docker compose`.

Recordatorio de la arquitectura ([arquitectura.md](arquitectura.md)):
`Navegador → nginx → Java → PHP → Python → PostgreSQL`. Hay cinco contenedores, cuatro lenguajes y
un contrato común ([api-contract.md](api-contract.md)).

## Ventajas

### 1. Independencia de los equipos

Cada integrante fue dueño de una carpeta y de un servicio (CONTRIBUTING §1). Todos pudieron avanzar
**en paralelo sin esperar a la capa de abajo**, porque cada uno la simulaba con un mock que respondía
exactamente los JSON del contrato (§13):

- el frontend con `USE_MOCK = true` en `api.js`;
- Java con `MockRestServiceServer`;
- PHP con `dev/mock-python.php`.

**Ejemplo:** cuando el frontend pasó del mock al backend real (#13), solo hubo que cambiar
`USE_MOCK` a `false`. Los mensajes de error que mostraba la interfaz eran los mismos que imitaba el
mock: 409, 404 y 400 de validación.

### 2. Tecnología adecuada para cada capa

Cada responsabilidad usa una herramienta que la resuelve bien:

- **Spring Boot** da un cliente HTTP con timeouts y un manejo global de errores
  (`GlobalExceptionHandler`).
- **PHP sin frameworks** basta para un intermediario liviano de dos archivos (`index.php` y `PythonClient.php`).
- **FastAPI + Pydantic** validan y documentan solos: Swagger en `http://localhost:8083/docs`.
- **PostgreSQL** garantiza la integridad con `PRIMARY KEY`, `FOREIGN KEY` y `CHECK`.

**Ejemplo:** el orden de las materias con tilde se corrigió **solo en la base de datos**, sin tocar
código (#64). Antes "Álgebra Lineal" aparecía después de la Z; bastó usar la intercalación del español
(`COLLATE "es-x-icu"`).

### 3. Aislamiento de fallos

Una capa caída no tumba a las demás. Cada una responde un error controlado y la interfaz lo muestra.
Lo comprobamos deteniendo contenedores:

| Contenedor detenido | `GET /api/monitores` | `GET /api/health` |
|---------------------|----------------------|-------------------|
| `monitores-db` | `503 {"error": "Base de datos no disponible"}` | 200 (Java sigue vivo) |
| `monitores-python` | `502 {"error": "Servicio de persistencia no disponible"}` | 200 |
| `monitores-php` | `502 {"error": "Servicio PHP no disponible"}` | 200 |

Con `restart: unless-stopped` y los *healthchecks*, Docker reinicia el servicio que se cae sin afectar
a los otros.

### 4. Despliegue y corrección independientes

Cada servicio se construye por separado (`docker compose build <servicio>`), así que un arreglo solo
reconstruye su contenedor.

**Ejemplos:**

- El error de Java que convertía los 409/400/404 de PHP en 502 (#56) se corrigió cambiando **2 líneas
  de `PhpClient.java`**, sin tocar PHP ni Python.
- El orden de materias (#64) se corrigió cambiando solo `database/init.sql`.

### 5. Escalado por componente

Java, PHP y Python no guardan estado entre peticiones (REST sin sesión), así que se podrían ejecutar
varias réplicas de la capa más cargada sin cambiar las demás. Lo mismo vale para la base de datos, que
podría tener réplicas de lectura. En este proyecto no se escaló, por el volumen de datos de un taller.
La arquitectura lo permite porque cada capa está en su propio contenedor y solo se conecta por URL
(`PHP_SERVICE_URL`, `PYTHON_SERVICE_URL`).

### 6. Defensa en profundidad

La validación se repite en cuatro puntos:

1. la interfaz (`app.js`);
2. Java (`MonitorValidator`);
3. Python (`schemas.py`);
4. la base de datos (`CHECK`).

Aunque alguien llame directamente a Python o a PHP sin pasar por Java (por ejemplo, con la colección
de Postman), **ningún dato inválido llega a guardarse**. La colección dio las mismas respuestas en las
cuatro capas ([endpoints.md](endpoints.md#verificación)).

## Dificultades

### 1. Latencia por los saltos de red

Cada operación cruza cuatro conexiones HTTP y una de base de datos. Medimos el promedio de 20
peticiones `GET /monitores/M-001` contra cada capa:

| Entrada | Tiempo promedio | Saltos |
|---------|-----------------|--------|
| Python directo (`:8083`) | 21,8 ms | Python → BD |
| PHP (`:8082`) | 24,8 ms | + PHP → Python |
| Java (`:8081`) | 29,8 ms | + Java → PHP |
| nginx (`:8080/api`) | 31,4 ms | + nginx → Java |

Todo corre en una sola máquina, así que cada salto agrega solo unos 3–5 ms. En una red real, con los
servicios en máquinas distintas, cada salto sumaría su propia latencia de red. Un sistema monolítico
haría la misma consulta en un solo proceso.

### 2. Depuración distribuida

Un error puede nacer en una capa y manifestarse en otra. Las pruebas unitarias de cada servicio, con
mocks, no ven los problemas de la conexión real.

**Ejemplo (#56):** al integrar todo, un `POST` con código repetido llegaba al navegador como
**502 "Servicio PHP no disponible"** en vez de 409. PHP funcionaba bien. El problema estaba en Java:
`PhpClient` leía el cuerpo antes que el código HTTP, y con `HttpURLConnection` eso lanzaba una
excepción en las peticiones **con cuerpo** (POST y PUT), pero no en GET ni DELETE. Las 61 pruebas de
Java pasaban porque `MockRestServiceServer` reemplaza la conexión real.

Para encontrarlo hizo falta:

- el log de una línea por petición en cada servicio (`[servicio] MÉTODO RUTA -> STATUS (ms)`, T2);
- comparar las respuestas capa por capa;
- un programa aparte contra el PHP real.

### 3. Mantener consistente el contrato en varios lenguajes

El contrato dice que "Java y Python aplican la misma normalización" (§6.1), pero cada lenguaje entiende
distinto operaciones básicas:

- **Quitar espacios:** `trim()` de Java quita los caracteres ≤ U+0020; `strip()` de Python quita además
  los espacios Unicode, como el espacio no separable. Python tuvo que replicar a mano el comportamiento
  de Java.
- **Byte NUL (`\u0000`) en el nombre:** Java lo acepta y lo reenvía, y PostgreSQL no puede guardarlo.
  Python responde 400. El contrato no tiene una regla para este caso, así que quedó propuesto un cambio
  (§14).
- **Encabezados:** el `/health` de Java responde `application/json` sin `charset=utf-8`, mientras las
  otras capas sí lo incluyen. Lo detectó la colección de Postman ([endpoints.md](endpoints.md#verificación)).

Cada diferencia obliga a revisar tres implementaciones de la misma regla: JavaScript, Java y Python.

### 4. Propagación de errores a través de la cadena

Un 409 nace en PostgreSQL y debe llegar **intacto** al navegador: Python lo traduce a
`{"error": "Ya existe un monitor con el código ..."}` y PHP, Java y nginx no deben reescribirlo (H7).
Cada capa tuvo que cuidar detalles propios:

- **Orden de validación:** PostgreSQL revisa la clave primaria antes que la foránea. Si el código está
  repetido **y** la materia no existe, respondería 409, pero el contrato exige 400 (§6.3). Python tuvo
  que consultar primero la materia y después insertar.
- **204 sin cuerpo:** PHP agrega `Content-Type: text/html` por defecto. Para que `DELETE` respondiera
  `204` sin cuerpo ni `Content-Type` (H5), hubo que desactivarlo (`ini_set('default_mimetype', '')`).
- **Timeouts encadenados:** si Python tarda más que el timeout de lectura de PHP (10 s, T1), el usuario
  recibe 502 en vez del 503 correcto. Python usa 3 s para conectar y 5 s por consulta. Aun así, con la
  BD detenida, el 503 llegó en **7,9 s**, cerca del límite.

### 5. Configuración y Docker

Levantar cinco contenedores en el orden correcto trajo problemas que no existen en una aplicación de un
solo proceso:

- **Healthchecks:** la imagen JRE de Java no trae `curl` ni `wget`, así que se comprueba el puerto con
  `bash -c '</dev/tcp/localhost/8081'`. En el frontend, `localhost` resolvía a `::1` (IPv6) en Alpine;
  nginx solo escucha en IPv4 y el contenedor quedaba `unhealthy` (#59). Se usa `127.0.0.1`.
- **Puertos ocupados:** en equipos con PostgreSQL instalado, el 5432 ya está en uso. Hubo que hacer
  configurables todos los puertos (`DB_PORT`, `FRONTEND_PORT`…).
- **Datos iniciales:** `init.sql` solo se ejecuta con el volumen vacío. Cada cambio del esquema exige
  `docker compose down -v`, que borra los datos.
- **Saltos de línea:** los scripts `.sh` con CRLF (Windows) fallan dentro de Linux. Se normalizaron a LF
  con `.gitattributes`.

### 6. Varios lenguajes y herramientas que mantener

Cada capa trae su propio ecosistema:

| Capa | Construcción | Pruebas |
|------|--------------|---------|
| Java | Maven | JUnit |
| PHP | Servidor embebido | Pruebas manuales con curl contra un mock |
| Python | pip | pytest |
| Frontend | nginx | Pruebas en el navegador |

Además, el smoke test existe en dos versiones (bash y PowerShell). La misma regla de negocio está
escrita tres veces (JavaScript, Java y Python), y cada cambio del contrato requiere coordinar a varios
responsables (§14).

## Conclusión

La arquitectura distribuida y heterogénea cumplió lo que promete:

- permitió que seis personas trabajaran en paralelo con tecnologías distintas;
- aisló los fallos, de modo que una capa caída produce un error claro y no una aplicación rota;
- permitió corregir cada problema en un solo servicio.

El precio fue alto para un CRUD de dos tablas. Pagamos más latencia (unos 10 ms más que llamar a Python
directamente). La depuración fue más difícil: el error de #56 solo apareció al integrar. Y hubo que
mantener la misma regla en varios lenguajes.

Lo que hizo viable el proyecto fue el **contrato único y detallado**: mensajes exactos, orden de
validación, códigos permitidos y mocks que lo imitan. Sin él, cada capa habría interpretado las reglas
a su manera. Para un sistema de este tamaño, un monolito sería más simple. La arquitectura distribuida
se justifica cuando los equipos, la carga o las tecnologías realmente necesitan evolucionar por
separado, y este taller nos permitió vivir sus ventajas y sus costos.
