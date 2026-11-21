# Estilos y patrones arquitectónicos

**Entregable 1 (segunda parte).** Qué arquitecturas, estilos y patrones usa el sistema de Gestión de
Monitores Académicos y dónde están en el código.

Cada patrón tiene los cuatro puntos que pide el enunciado: **nombre**, **características principales**,
**componentes que lo implementan** y **justificación**. Las reglas citadas (A1, H7, §6…) son del
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

**Componentes que lo implementan**

| Capa | Componente | Responsabilidad |
|------|------------|-----------------|
| Presentación | `frontend/` (HTML, CSS, JS servidos por nginx) | Formularios, tabla y mensajes al usuario |
| Control / validación | `java-controller/` (Spring Boot) | Normaliza y valida antes de dejar pasar la petición |
| Intermediación | `php-service/` (PHP + cURL) | Enruta y reenvía sin modificar |
| Lógica de negocio y persistencia | `python-service/` (FastAPI) | Valida de nuevo, verifica existencia y duplicados, ejecuta SQL |
| Datos | `database/` (PostgreSQL 16) | Integridad con PK, FK y `CHECK` |

**Justificación**

- El contrato lo exige (A1): toda operación atraviesa **todas** las capas en orden y nadie se salta una.
- Separar responsabilidades permitió que seis personas trabajaran en paralelo, cada una en su carpeta.
- Un error se puede ubicar en la capa que lo produce. Por ejemplo, un 400 de formato siempre viene de Java;
  uno de materia inexistente, de Python.

## 2. Cliente-servidor

**Características principales**

- Un cliente inicia la petición y un servidor la atiende y responde; el servidor no llama al cliente.
- La comunicación es síncrona petición–respuesta sobre HTTP.
- Un mismo componente puede ser servidor de la capa de arriba y cliente de la de abajo.

**Componentes que lo implementan**

- El **navegador** es el cliente de nginx (`frontend/api.js`, función `peticion()` con `fetch`).
- **Java** es servidor del navegador y cliente de PHP (`client/PhpClient.java`, con `RestClient`).
- **PHP** es servidor de Java y cliente de Python (`PythonClient.php`, con cURL).
- **Python** es servidor de PHP y cliente de PostgreSQL (`db.py`, con psycopg 3).

**Justificación**

El navegador solo necesita conocer una URL relativa (`/api/...`, regla A2). Los servidores pueden
cambiar por dentro mientras respeten el contrato. Los timeouts del cliente (T1: 3 s de conexión y 10 s
de lectura) delimitan cuánto espera cada salto.

## 3. Arquitectura orientada a servicios / microservicios

**Características principales**

- Cada servicio es un proceso independiente, con su propio despliegue, su propia imagen Docker y su
  propio `/health`.
- Los servicios se comunican solo por la red (HTTP/JSON, A5): no comparten memoria, archivos ni colas.
- Cada servicio se construye y prueba por separado (`docker compose build <servicio>`).

**Componentes que lo implementan**

- Cinco contenedores en `docker-compose.yml`: `frontend`, `java-controller`, `php-service`,
  `python-service` y `database`.
- Cada uno tiene un *healthcheck* y arranca solo cuando su dependencia está sana:
  database → python → php → java → frontend.

**Justificación**

Permite desplegar, reiniciar (`restart: unless-stopped`) y escalar cada pieza por separado. Cada
tecnología queda aislada en su contenedor con sus versiones.

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

**Componentes que lo implementan**

Las cuatro capas de backend exponen **las mismas rutas**: nginx con el prefijo `/api` y Java, PHP y
Python sin él (A4). Los 7 endpoints están en [endpoints.md](endpoints.md).

**Justificación**

Una interfaz uniforme hace que el contrato sea idéntico en todas las capas: el mismo `curl` o la misma
colección de Postman sirve para probar Java, PHP o Python cambiando solo el puerto.

## 5. Pipes & Filters / cadena de responsabilidad

**Características principales**

- La petición atraviesa una **secuencia fija de etapas**. Cada etapa hace su parte y la pasa a la
  siguiente o la corta respondiendo ella misma.
- Cada etapa es independiente y se comunica con la siguiente por la misma interfaz (HTTP/JSON).
- La respuesta regresa por la misma cadena sin ser reescrita (H7).

**Componentes que lo implementan**

| Etapa | Qué filtra | Cuándo corta la cadena |
|-------|------------|------------------------|
| nginx | Quita el prefijo `/api` y reenvía a Java | Nunca (solo archivos estáticos) |
| Java (`MonitorValidator`) | Normaliza (§6.1) y valida formato (§6.2) | Dato inválido → 400 **sin llamar a PHP** |
| PHP (`index.php`) | Valida ruta, método y que el cuerpo sea JSON | Ruta inexistente (404), método no permitido (405), JSON inválido (400) |
| Python (`schemas.py`, `main.py`) | Valida de nuevo y aplica reglas de negocio | Monitor inexistente (404), materia inexistente (400), código repetido (409) |
| PostgreSQL | `PRIMARY KEY`, `FOREIGN KEY`, `CHECK` | Última barrera de integridad |

**Justificación**

Cada capa detiene el error lo antes posible: un correo inválido no consume ni la red hacia PHP ni una
consulta a la BD. Es una *cadena de responsabilidad*: cada eslabón decide si atiende la petición o la
delega. La validación se repite a propósito en Python, porque Python no confía en que Java ya validó
(§9).

## 6. Proxy / API Gateway

**Características principales**

- Un intermediario recibe las peticiones en lugar del servicio real y las reenvía.
- Oculta la ubicación de los servicios internos y centraliza la entrada.

**Componentes que lo implementan**

- **nginx (proxy inverso / puerta de entrada):** `frontend/nginx.conf` reenvía
  `location /api/` a `http://java-controller:8081/` quitando el prefijo. El navegador solo conoce
  `http://localhost:8080`, sin CORS (H8) y sin ver los puertos internos.
- **PHP (proxy de reenvío):** `php-service/index.php` compara la ruta con una tabla de rutas
  permitidas, valida que el cuerpo sea JSON y reenvía método, ruta y cuerpo **sin modificarlos**
  (`PythonClient::forward`). Si Python no responde, genera su propio 502 (E16).

**Justificación**

nginx da un único origen al navegador y aísla los servicios internos; la base de datos nunca queda
expuesta a la interfaz. PHP desacopla a Java de la ubicación de Python: Java solo conoce
`PHP_SERVICE_URL`. Además, PHP aísla los fallos de persistencia, porque los traduce a un 502 propio.

> nginx actúa como **proxy inverso** más que como API Gateway completo: no hace autenticación,
> límites de tráfico ni agregación. Es el rol de *gateway* que este sistema necesita.

## 7. Repository / DAO

**Características principales**

- Todo el acceso a datos está en un solo módulo con funciones por operación.
- Quien lo llama trabaja con diccionarios, no con SQL.
- Las consultas usan **parámetros** (`%(codigo)s`), nunca concatenación (T4).

**Componentes que lo implementan**

- `python-service/repository.py`: `listar_materias`, `existe_materia`, `listar_monitores`,
  `obtener_monitor`, `crear_monitor`, `actualizar_monitor` y `eliminar_monitor`.
- `python-service/db.py`: `get_connection()` abre la conexión y hace *commit* o *rollback*. Cada función
  del repositorio recibe la conexión, así que el endpoint decide qué operaciones van en la misma
  transacción.

**Justificación**

Los endpoints (`main.py`) no contienen SQL: solo deciden qué responder según lo que devuelve el
repositorio. El SQL parametrizado evita la inyección SQL. Si el esquema cambia, solo se toca este
módulo.

## 8. DTO (Data Transfer Object)

**Características principales**

- Objetos sin lógica de negocio que definen **qué datos viajan** entre capas y con qué forma.
- Separan el formato de la petición del formato de la respuesta.

**Componentes que lo implementan**

- **Python (DTO explícitos):** en `python-service/schemas.py`, `MonitorCreate` (cuerpo de POST),
  `MonitorUpdate` (cuerpo de PUT, sin `codigo`), `MonitorOut` y `MateriaOut` (respuestas) y `ErrorOut`
  (`{"error": ...}`). Son modelos Pydantic v2 que también normalizan y validan.
- **Java (DTO implícito):** `MonitorValidator` no usa clases DTO. Construye un `ObjectNode` nuevo solo
  con los campos del contrato, ya normalizados (`validarCreacion` / `validarActualizacion`), y ese
  objeto es lo que se envía a PHP. Por eso los campos extra se descartan (J6).
- **Contrato (§5):** define los tres formatos (Monitor petición POST, petición PUT y respuesta).

**Justificación**

Fija la forma de los datos en cada frontera. `materia_nombre` solo existe en respuestas. El `codigo`
del cuerpo de un PUT se ignora (J6), y una respuesta nunca tiene campos `null` (J5).

> En Java no se usaron `record` con Bean Validation, aunque CONTRIBUTING los sugiere. El contrato
> exige responder **solo el primer error en un orden fijo** (§6.3) y rechazar `materia_id` enviado
> como texto. Las anotaciones no garantizan ninguna de las dos cosas (ver el comentario de
> `MonitorValidator.java`).

## 9. Arquitectura heterogénea / políglota

**Características principales**

- Cada capa usa un lenguaje y un entorno distintos, y todas interoperan mediante un formato neutral
  (HTTP + JSON en UTF-8).
- La interoperabilidad depende de un **contrato común** y no de librerías compartidas.

**Componentes que lo implementan**

| Capa | Lenguaje / tecnología |
|------|-----------------------|
| Frontend | HTML5, CSS3, JavaScript ES2020 sin frameworks; nginx |
| Controlador | Java 21 + Spring Boot 3.3 |
| Intermediario | PHP 8.3 sin frameworks + cURL |
| Persistencia | Python 3.12 + FastAPI + psycopg 3 + Pydantic v2 |
| Datos | PostgreSQL 16 (SQL) |

**Justificación**

Es un requisito del enunciado y muestra que la integración no depende del lenguaje. El costo es
mantener reglas idénticas en lenguajes distintos. Por ejemplo, el `trim()` de Java, el `strip()` de
Python y el `trim()` de JavaScript no quitan los mismos caracteres. Python tuvo que replicar
exactamente el comportamiento de Java para que la normalización fuera "la misma" (§6.1). El análisis
completo está en [ventajas-dificultades.md](ventajas-dificultades.md).
