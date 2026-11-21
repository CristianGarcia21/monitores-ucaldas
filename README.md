# Gestión de Monitores Académicos – Universidad de Caldas

Sistema para registrar, consultar, actualizar y eliminar los monitores académicos de la universidad.
Está construido como una arquitectura **distribuida, multicapa y heterogénea**: cada capa usa un lenguaje
distinto y todas se comunican por APIs REST con JSON.

Proyecto final de Ingeniería de Software III (2026-2).

## Arquitectura

```
Navegador ──► frontend (nginx :8080) ──/api/*──► java-controller (:8081)
                                                    │  normaliza y valida los datos
                                                    ▼
                                               php-service (:8082)
                                                    │  intermediario: reenvía sin modificar
                                                    ▼
                                              python-service (:8083)
                                                    │  valida de nuevo y persiste
                                                    ▼
                                              database (PostgreSQL :5432)
```

Toda operación atraviesa todas las capas en ese orden; solo `python-service` se conecta a la base de datos.

| Carpeta            | Componente                | Tecnología                     | Puerto |
|--------------------|---------------------------|--------------------------------|--------|
| `frontend/`        | Interfaz de usuario       | HTML + CSS + JavaScript, nginx | 8080   |
| `java-controller/` | Controlador y validación  | Java 21 + Spring Boot 3.3      | 8081   |
| `php-service/`     | Intermediario             | PHP 8.3                        | 8082   |
| `python-service/`  | Persistencia              | Python 3.12 + FastAPI          | 8083   |
| `database/`        | Base de datos             | PostgreSQL 16                  | 5432   |
| `scripts/`         | Scripts de utilidad y smoke test | bash y PowerShell       | —      |
| `docs/`            | Contrato, diagramas y documento final | Markdown            | —      |

## Requisitos

- **[Docker Desktop](https://www.docker.com/products/docker-desktop/)** (incluye Docker Compose v2) **abierto y en ejecución**.
- **Git**, para clonar el repositorio.
- Los puertos **8080, 8081, 8082, 8083 y 5432** libres (si alguno está ocupado, ver [Solución de problemas](#solución-de-problemas)).

No hace falta instalar Java, PHP, Python ni PostgreSQL: todo corre dentro de contenedores.

## Levantar el sistema

```bash
git clone https://github.com/CristianGarcia21/monitores-ucaldas.git
cd monitores-ucaldas
docker compose up --build
```

La **primera vez tarda varios minutos** (descarga las imágenes y compila el proyecto Java). Los servicios
arrancan en orden y cada uno espera a que el anterior esté sano: base de datos → Python → PHP → Java → frontend.

Para levantarlo en segundo plano y comprobar que todo está bien:

```bash
docker compose up --build -d
docker compose ps        # los 5 servicios deben aparecer como (healthy)
```

Luego abre **http://localhost:8080**.

| Acción | Comando |
|--------|---------|
| Detener | `docker compose down` |
| Detener y **borrar los datos** de la BD | `docker compose down -v` |
| Ver el estado de los servicios | `docker compose ps` |

La base de datos se crea con `database/init.sql`, que carga 8 materias y 7 monitores de ejemplo
(`M-001` a `M-007`).

## URLs y puertos

| Qué | URL |
|-----|-----|
| **Aplicación** | http://localhost:8080 |
| API (por la puerta de entrada) | http://localhost:8080/api/monitores · http://localhost:8080/api/materias |
| Salud de Java | http://localhost:8081/health |
| Salud de PHP | http://localhost:8082/health |
| Salud de Python | http://localhost:8083/health |
| Documentación interactiva de la API (Swagger) | http://localhost:8083/docs |
| PostgreSQL | `localhost:5432` · base `monitores` · usuario `monitores` · contraseña `monitores` |

Las rutas, los cuerpos JSON, las validaciones y los mensajes de error están definidos en el
[contrato del sistema](docs/api-contract.md).

## Usar la aplicación

En http://localhost:8080 se puede:

- **Registrar** un monitor con código, nombre, correo y materia.
- **Listar** todos los monitores y **buscar** uno por su código (no distingue mayúsculas de minúsculas).
- **Editar** el nombre, el correo o la materia de un monitor (el código no se puede cambiar).
- **Eliminar** un monitor, previa confirmación.

Los errores (código repetido, correo inválido, materia inexistente…) se muestran con el mensaje que devuelve
el backend.

## Verificar que todo funciona (smoke test)

Con el sistema levantado, el smoke test recorre todo el CRUD por http://localhost:8080/api y comprueba el
código HTTP y el mensaje exacto de cada respuesta:

```bash
./scripts/smoke-test.sh            # Linux, Mac o Git Bash (requiere curl)
```

```powershell
.\scripts\smoke-test.ps1           # Windows PowerShell
```

Imprime ✅ o ❌ por cada paso y termina con un resumen:

```
✅ GET /health -> 200 (java-controller)
✅ POST SMOKE-1 -> 201 con materia_nombre
✅ POST SMOKE-1 repetido -> 409 "Ya existe un monitor con el código SMOKE-1"
...
✅ Smoke test OK: 15 pasos correctos
```

- Sale con código distinto de 0 si algún paso falla.
- Crea monitores con código `SMOKE-…` y los elimina al terminar, aunque algún paso falle.
- Para probar otra URL: `./scripts/smoke-test.sh http://localhost:9090/api` (o la variable `SMOKE_API_URL`).

## Scripts de utilidad

En `scripts/`, en versión bash (Linux/Mac y Git Bash) y PowerShell (Windows). Se pueden ejecutar
desde cualquier carpeta del repo.

| Script | Qué hace | bash | PowerShell |
|--------|----------|------|------------|
| `smoke-test` | Prueba de punta a punta del CRUD (ver la sección anterior). | `./scripts/smoke-test.sh` | `.\scripts\smoke-test.ps1` |
| `reset-db` | Detiene todo, **borra los datos** de la BD (`docker compose down -v`) y levanta solo la BD otra vez, ejecutando `database/init.sql` desde cero. | `./scripts/reset-db.sh` | `.\scripts\reset-db.ps1` |
| `logs` | Muestra en vivo los logs de un servicio (`docker compose logs -f`). Sin argumento o con un nombre inválido, lista los servicios. `Ctrl+C` para salir. | `./scripts/logs.sh php-service` | `.\scripts\logs.ps1 php-service` |

Servicios: `database`, `python-service`, `php-service`, `java-controller`, `frontend`.

Cada servicio escribe una línea por petición con el formato `[servicio] MÉTODO RUTA -> STATUS (ms)`.

## Pruebas automáticas de cada servicio

| Servicio | Cómo ejecutarlas |
|----------|------------------|
| Python | `pytest`, con la BD levantada. Ver [python-service/README.md](python-service/README.md#pruebas). |
| Java | Sin instalar Maven, desde la raíz del repo: `docker run --rm -v "${PWD}/java-controller:/app" -w /app maven:3.9-eclipse-temurin-21 mvn -q test` (en Git Bash, anteponer `MSYS_NO_PATHCONV=1`). |
| PHP | Pruebas manuales con curl contra un mock de Python. Ver [php-service/README.md](php-service/README.md). |

## Solución de problemas

**`docker compose` responde "failed to connect to the docker API" o "Cannot connect to the Docker daemon".**
Docker Desktop no está abierto. Ábrelo, espera a que indique que está en ejecución y repite el comando.

**"port is already allocated" o "address already in use".**
Otro programa usa ese puerto. Es frecuente con el **5432** cuando hay un PostgreSQL instalado en el equipo.
Cambia el puerto con una variable de entorno:

```bash
DB_PORT=5433 docker compose up --build            # Linux, Mac o Git Bash
```

```powershell
$env:DB_PORT = "5433"; docker compose up --build  # Windows PowerShell
```

O, para que quede fijo, copia `.env.example` a `.env` y cambia ahí el valor. Las variables disponibles son
`FRONTEND_PORT` (8080), `JAVA_PORT` (8081), `PHP_PORT` (8082), `PYTHON_PORT` (8083) y `DB_PORT` (5432).
Solo cambian el puerto expuesto en tu equipo: si cambias `FRONTEND_PORT`, la aplicación queda en
`http://localhost:<FRONTEND_PORT>` y al smoke test hay que pasarle esa URL.

**Cambié `database/init.sql` pero no veo los cambios, o quiero empezar con datos limpios.**
`init.sql` solo se ejecuta cuando la base de datos está vacía. Reiníciala con `./scripts/reset-db.sh`
(o `.\scripts\reset-db.ps1`), o con `docker compose down -v` y luego `docker compose up --build`.
Esto **borra todos los datos** y vuelve a cargar los de ejemplo.

**La aplicación muestra "No se pudo conectar con el servidor" o un servicio no arranca.**
Revisa el estado con `docker compose ps`: todos deben estar `(healthy)`. Si alguno no lo está, mira sus
logs con `./scripts/logs.sh <servicio>`. Si un servicio queda esperando, es porque el anterior en la cadena
todavía no está sano; la primera vez Java puede tardar hasta un minuto en arrancar.

**PowerShell no deja ejecutar los scripts ("la ejecución de scripts está deshabilitada").**
Ejecútalos así: `powershell -ExecutionPolicy Bypass -File .\scripts\smoke-test.ps1`

## Documentación

- **[docs/](docs/README.md)**: índice de documentación, manuales LaTeX/PDF y diagrama de arquitectura.
- **[Manual técnico (PDF)](docs/manual-tecnico.pdf)** · [fuente LaTeX](docs/manual-tecnico.tex): arquitectura, despliegue, pruebas y diagnóstico.
- **[Manual de usuario (PDF)](docs/manual-usuario.pdf)** · [fuente LaTeX](docs/manual-usuario.tex): guía para operar la interfaz.
- **[Diagrama de arquitectura (PDF)](docs/arquitectura.pdf)**: vista de los componentes y su flujo.
- **[docs/api-contract.md](docs/api-contract.md)**: contrato del sistema: rutas, JSON, validaciones, mensajes de
  error exactos, esquema de la base de datos y responsabilidades de cada capa.
- **[CONTRIBUTING.md](CONTRIBUTING.md)**: reglas de trabajo del equipo (ramas, commits, PRs, versiones y estilo).
- README de cada servicio: [python-service](python-service/README.md) · [php-service](php-service/README.md).

## Equipo

| Integrante       | Responsabilidad                      |
|------------------|--------------------------------------|
| Tania Botina     | Frontend (HTML/CSS/JS)               |
| Cristian Garcia  | Controlador Java                     |
| Juan Fernando    | Servicio PHP                         |
| Juan Diego       | Servicio Python                      |
| Valentina Galvis | Base de datos, Docker e integración  |
| Jose Daniel      | Documentación y diagramas            |
