# Estilos y patrones arquitectónicos

**Entregable 1 (segunda parte).** Qué arquitecturas, estilos y patrones usa el sistema de Gestión de
Monitores Académicos y dónde están en el código.

Cada patrón tiene los puntos que pide el enunciado: **nombre**, **características principales**,
**componentes que participan** y **por qué se considera presente** en la solución (con la evidencia
del código o la configuración). Las reglas citadas (A1, H7, §6…) son del
[contrato del sistema](api-contract.md).

Vista general del sistema (detalle en el [diagrama de arquitectura](arquitectura.md)):

```
Navegador ─► nginx (frontend :8080) ─/api─► Java (:8081) ─► PHP (:8082) ─► Python (:8083) ─► PostgreSQL (:5432)
```

| # | Patrón / estilo | Nivel | Dónde se ve |
|---|-----------------|-------|-------------|
| 1 | [Arquitectura en capas (N-tier)](#1-arquitectura-en-capas-n-tier) | Arquitectura | Las 5 capas del sistema |
| 2 | [Cliente-servidor](#2-cliente-servidor) | Arquitectura | Cada salto HTTP |
| 3 | [Arquitectura orientada a servicios / microservicios](#3-arquitectura-orientada-a-servicios--microservicios) | Arquitectura | Un contenedor por servicio |
| 4 | [REST](#4-rest) | Estilo de comunicación | Rutas `/materias` y `/monitores` |
| 5 | [Pipes & Filters / cadena de responsabilidad](#5-pipes--filters--cadena-de-responsabilidad) | Estilo / patrón | Java → PHP → Python |
| 6 | [Proxy / API Gateway](#6-proxy--api-gateway) | Patrón | nginx y PHP |
| 7 | [Repository / DAO](#7-repository--dao) | Patrón de diseño | `python-service/repository.py` |
| 8 | [DTO (Data Transfer Object)](#8-dto-data-transfer-object) | Patrón de diseño | Modelos Pydantic; JSON normalizado en Java |
| 9 | [Arquitectura heterogénea / políglota](#9-arquitectura-heterogénea--políglota) | Arquitectura | 4 lenguajes + SQL |

---

## 1. Arquitectura en capas (N-tier)

**Características principales**

- El sistema se divide en capas apiladas; cada una solo habla con la capa inmediatamente inferior.
- Cada capa tiene una responsabilidad única y no conoce los detalles internos de las demás.
- Las capas son también *tiers* físicos: cada una corre en su propio contenedor.

**Componentes que participan**

| Capa | Componente | Responsabilidad |
|------|------------|-----------------|
| Presentación | `frontend/` (HTML, CSS, JS servidos por nginx) | Formularios, tabla y mensajes al usuario |
| Control / validación | `java-controller/` (Spring Boot) | Normaliza y valida antes de dejar pasar la petición |
| Intermediación | `php-service/` (PHP + cURL) | Enruta y reenvía sin modificar |
| Lógica de negocio y persistencia | `python-service/` (FastAPI) | Valida de nuevo, verifica existencia y duplicados, ejecuta SQL |
| Datos | `database/` (PostgreSQL 16) | Integridad con PK, FK y `CHECK` |

**Por qué está presente**

- Las cinco capas existen como componentes separados y cada una **solo llama a la siguiente**:
  nginx solo conoce a Java (`proxy_pass` en `nginx.conf.template`), Java solo a PHP (`PHP_SERVICE_URL`), PHP
  solo a Python (`PYTHON_SERVICE_URL`) y solo Python abre conexiones con la base de datos (`db.py`).
- Ninguna capa se salta a otra: así lo exige el contrato (A1) y lo cumple el enunciado ("las
  operaciones del CRUD deberán atravesar los componentes definidos").
- Cada capa tiene una responsabilidad distinta que no se repite en las demás. Por ejemplo, solo Python
  sabe si una materia existe.
## 2. Cliente-servidor

**Características principales**

- Un cliente inicia la petición y un servidor la atiende y responde; el servidor no llama al cliente.
- La comunicación es síncrona petición–respuesta sobre HTTP.
- Un mismo componente puede ser servidor de la capa de arriba y cliente de la de abajo.

**Componentes que participan**

- El **navegador** es el cliente de nginx (`frontend/api.js`, función `peticion()` con `fetch`).
- **Java** es servidor del navegador y cliente de PHP (`client/PhpClient.java`, con `RestClient`).
- **PHP** es servidor de Java y cliente de Python (`PythonClient.php`, con cURL).
- **Python** es servidor de PHP y cliente de PostgreSQL (`db.py`, con psycopg 3).

**Por qué está presente**

- Toda interacción es una **petición HTTP iniciada por un cliente** que espera la respuesta de un
  servidor.
- Ningún servidor inicia comunicación hacia su cliente: no hay *websockets*, *callbacks* ni colas (A5).
- Los clientes están en el código: `fetch` en `frontend/api.js`, `RestClient` en
  `client/PhpClient.java`, cURL en `php-service/PythonClient.php` y psycopg en `python-service/db.py`.
## 3. Arquitectura orientada a servicios / microservicios

**Características principales**

- Cada servicio es un proceso independiente, con su propio despliegue, su propia imagen Docker y su
  propio `/health`.
- Los servicios se comunican solo por la red (HTTP/JSON, A5): no comparten memoria, archivos ni colas.
- Cada servicio se construye y prueba por separado (`docker compose build <servicio>`).

**Componentes que participan**

- Cinco contenedores en `docker-compose.yml`: `frontend`, `java-controller`, `php-service`,
  `python-service` y `database`.
- Cada uno tiene un *healthcheck* y arranca solo cuando su dependencia está sana:
  database → python → php → java → frontend.

**Por qué está presente**

- Cada servicio es un **proceso independiente** en su propio contenedor (`docker-compose.yml`), con
  su propia imagen (`Dockerfile`), su propio puerto y su propio `/health`.
- Se comunican **solo por la red**, con URLs configurables.
- Se construyen, reinician y prueban por separado (`docker compose build <servicio>`,
  `restart: unless-stopped`). Con un servicio detenido, los demás siguen respondiendo (ver
  [endpoints.md](endpoints.md#verificación)).

> **Precisión:** no es una arquitectura de microservicios "pura". Los servicios no se reparten
> dominios de negocio distintos: forman una **cadena** sobre un mismo recurso (`monitores`), y solo
> Python tiene base de datos (A3). Es más exacto llamarla **arquitectura orientada a servicios en
> capas**, desplegada con prácticas de microservicios (un contenedor por servicio, comunicación por
> API y salud independiente).

## 4. REST

**Características principales**

- **Recursos** identificados por URI en plural y en español: `/materias`, `/monitores`,
  `/monitores/{codigo}` (H1, H2).
- **Verbos HTTP** con su significado estándar (H3): `GET` consultar, `POST` crear, `PUT` reemplazar,
  `DELETE` eliminar. No se usa `PATCH`.
- **Sin estado**: cada petición lleva todo lo necesario; no hay sesiones ni cookies.
- **Representación JSON** en UTF-8 (H4, H9), con claves `snake_case` y sin envoltorio (J1, J3).
- **Códigos HTTP con significado**: 200, 201, 204, 400, 404, 405, 409, 500, 502, 503 (H6).

**Componentes que participan**

Las cuatro capas de backend exponen **las mismas rutas**: nginx con el prefijo `/api` y Java, PHP y
Python sin él (A4). Los 7 endpoints están en [endpoints.md](endpoints.md).

**Por qué está presente**

- Las rutas son **sustantivos** (`/monitores`, `/materias`) y las operaciones se distinguen solo por
  el **verbo HTTP** sobre la misma URI: `GET`, `POST`, `PUT` y `DELETE` sobre `/monitores/{codigo}`.
- Los códigos de estado tienen su significado estándar: 201 al crear, 204 al borrar, 404 si no existe
  y 409 si hay conflicto.
- Ninguna capa guarda sesión entre peticiones: no hay cookies ni estado en memoria. Todos los datos
  viajan como JSON.
## 5. Pipes & Filters / cadena de responsabilidad

**Características principales**

- La petición atraviesa una **secuencia fija de etapas**. Cada etapa hace su parte y la pasa a la
  siguiente o la corta respondiendo ella misma.
- Cada etapa es independiente y se comunica con la siguiente por la misma interfaz (HTTP/JSON).
- La respuesta regresa por la misma cadena sin ser reescrita (H7).

**Componentes que participan**

| Etapa | Qué filtra | Cuándo corta la cadena |
|-------|------------|------------------------|
| nginx | Quita el prefijo `/api` y reenvía a Java | Nunca (solo archivos estáticos) |
| Java (`MonitorValidator`) | Normaliza (§6.1) y valida formato (§6.2) | Dato inválido → 400 **sin llamar a PHP** |
| PHP (`index.php`) | Valida ruta, método y que el cuerpo sea JSON | Ruta inexistente (404), método no permitido (405), JSON inválido (400) |
| Python (`schemas.py`, `main.py`) | Valida de nuevo y aplica reglas de negocio | Monitor inexistente (404), materia inexistente (400), código repetido (409) |
| PostgreSQL | `PRIMARY KEY`, `FOREIGN KEY`, `CHECK` | Última barrera de integridad |

**Por qué está presente**

- La petición recorre una **cadena fija** (nginx → Java → PHP → Python → BD), y cualquier eslabón
  puede responder sin delegar.
- Ejemplo verificado con el smoke test: un `POST` sin nombre recibe 400 de Java y **no aparece en los
  logs de PHP**.
- PHP corta con 404, 405 o JSON inválido, y Python con 404, 400 o 409.
- Cada etapa transforma o filtra la petición antes de pasarla: nginx quita `/api`, y Java envía a PHP
  el JSON ya normalizado.
## 6. Proxy / API Gateway

**Características principales**

- Un intermediario recibe las peticiones en lugar del servicio real y las reenvía.
- Oculta la ubicación de los servicios internos y centraliza la entrada.

**Componentes que participan**

- **nginx (proxy inverso / puerta de entrada):** `frontend/nginx.conf.template` reenvía
  `location /api/` a `http://java-controller:8081/` quitando el prefijo. El navegador solo conoce
  `http://localhost:8080`, sin CORS (H8) y sin ver los puertos internos.
- **PHP (proxy de reenvío):** `php-service/index.php` compara la ruta con una tabla de rutas
  permitidas, valida que el cuerpo sea JSON y reenvía método, ruta y cuerpo **sin modificarlos**
  (`PythonClient::forward`). Si Python no responde, genera su propio 502 (E16).

**Por qué está presente**

- `frontend/nginx.conf.template` contiene `location /api/ { proxy_pass ${JAVA_SERVICE_URL}/; }`
  (por defecto `http://java-controller:8081`). El
  navegador solo conoce `localhost:8080` y nunca las direcciones internas.
- `php-service/index.php` reenvía a Python el **mismo método, ruta y cuerpo** que recibió (cURL en
  `PythonClient::forward`) y devuelve la respuesta sin cambiarla. Ese es el comportamiento de un proxy.

> nginx actúa como **proxy inverso** más que como API Gateway completo: no hace autenticación,
> límites de tráfico ni agregación. Es el rol de *gateway* que este sistema necesita.

## 7. Repository / DAO

**Características principales**

- Todo el acceso a datos está en un solo módulo con funciones por operación.
- Quien lo llama trabaja con diccionarios, no con SQL.
- Las consultas usan **parámetros** (`%(codigo)s`), nunca concatenación (T4).

**Componentes que participan**

- `python-service/repository.py`: `listar_materias`, `existe_materia`, `listar_monitores`,
  `obtener_monitor`, `crear_monitor`, `actualizar_monitor` y `eliminar_monitor`.
- `python-service/db.py`: `get_connection()` abre la conexión y hace *commit* o *rollback*. Cada función
  del repositorio recibe la conexión, así que el endpoint decide qué operaciones van en la misma
  transacción.

**Por qué está presente**

- **Todo el SQL** del sistema está en `python-service/repository.py`. `main.py` no contiene ninguna
  consulta: llama a funciones como `obtener_monitor(conexion, codigo)` y recibe diccionarios.
- Todas las consultas usan parámetros (`%(codigo)s`).
## 8. DTO (Data Transfer Object)

**Características principales**

- Objetos sin lógica de negocio que definen **qué datos viajan** entre capas y con qué forma.
- Separan el formato de la petición del formato de la respuesta.

**Componentes que participan**

- **Python (DTO explícitos):** en `python-service/schemas.py`, `MonitorCreate` (cuerpo de POST),
  `MonitorUpdate` (cuerpo de PUT, sin `codigo`), `MonitorOut` y `MateriaOut` (respuestas) y `ErrorOut`
  (`{"error": ...}`). Son modelos Pydantic v2 que también normalizan y validan.
- **Java (DTO implícito):** `MonitorValidator` no usa clases DTO. Construye un `ObjectNode` nuevo solo
  con los campos del contrato, ya normalizados (`validarCreacion` / `validarActualizacion`), y ese
  objeto es lo que se envía a PHP. Por eso los campos extra se descartan (J6).
- **Contrato (§5):** define los tres formatos (Monitor petición POST, petición PUT y respuesta).

**Por qué está presente**

- Las clases de `python-service/schemas.py` **solo tienen campos y validación**, sin lógica de
  negocio ni acceso a datos.
- Definen formas distintas para la petición (`MonitorCreate`, `MonitorUpdate`) y para la respuesta
  (`MonitorOut`): `materia_nombre` solo existe en la respuesta, y `codigo` no existe en el cuerpo del
  PUT.
- En Java cumple ese papel el objeto que arma `MonitorValidator`, con solo los campos del contrato.

> Java no usa clases DTO con anotaciones de validación: el contrato exige responder solo el primer
> error en un orden fijo (§6.3), y por eso `MonitorValidator` valida a mano.

## 9. Arquitectura heterogénea / políglota

**Características principales**

- Cada capa usa un lenguaje y un entorno distintos, y todas interoperan mediante un formato neutral
  (HTTP + JSON en UTF-8).
- La interoperabilidad depende de un **contrato común** y no de librerías compartidas.

**Componentes que participan**

| Capa | Lenguaje / tecnología |
|------|-----------------------|
| Frontend | HTML5, CSS3, JavaScript ES2020 sin frameworks; nginx |
| Controlador | Java 21 + Spring Boot 3.3 |
| Intermediario | PHP 8.3 sin frameworks + cURL |
| Persistencia | Python 3.12 + FastAPI + psycopg 3 + Pydantic v2 |
| Datos | PostgreSQL 16 (SQL) |

**Por qué está presente**

- Cada componente está escrito en un **lenguaje distinto** (ver la tabla) y se ejecuta en su propio
  entorno: JVM, intérprete de PHP, intérprete de Python y motor de PostgreSQL.
- No comparten librerías ni código: se integran solo por HTTP/JSON, según el contrato común.