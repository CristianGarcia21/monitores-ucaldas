# Gestión de Monitores Académicos – Universidad de Caldas

Arquitectura distribuida, multicapa y heterogénea comunicada por APIs REST (JSON).
Proyecto final de Ingeniería de Software III (2026-2).

## Estructura del monorepo

| Carpeta            | Componente              | Tecnología                 | Puerto |
|--------------------|-------------------------|----------------------------|--------|
| `frontend/`        | Interfaz de usuario     | HTML + CSS + JS (nginx)    | 8080   |
| `java-controller/` | Controlador / validación| Java 21 + Spring Boot      | 8081   |
| `php-service/`     | Intermediario           | PHP 8.3                    | 8082   |
| `python-service/`  | Persistencia            | Python 3.12 + FastAPI      | 8083   |
| `database/`        | Base de datos           | PostgreSQL 16              | 5432   |
| `docs/`            | Entregables y contrato  | Markdown / diagramas       | —      |

El contrato que deben cumplir todos los servicios está en **[docs/api-contract.md](docs/api-contract.md)**.

## Ejecutar todo

Requisito: Docker Desktop.

```bash
docker compose up --build
```

- App: http://localhost:8080
- Java: http://localhost:8081/health
- PHP: http://localhost:8082/health
- Python: http://localhost:8083/health (docs Swagger en `/docs`)

Detener: `docker compose down` · Borrar también la BD: `docker compose down -v`

### Levantar solo una parte

```bash
docker compose up --build database python-service   # solo persistencia
docker compose up --build php-service                # PHP (+ sus dependencias)
```

## Flujo de trabajo del equipo

1. Cada integrante tiene un issue asignado y trabaja **solo en su carpeta**.
2. Crea una rama `feature/<carpeta>` (ej. `feature/php-service`).
3. Abre un Pull Request hacia `main` que cierre su issue (`Closes #N`).
4. Nadie cambia el contrato sin avisar (ver `docs/api-contract.md`).

## Equipo

| Integrante       | Responsabilidad                      | Issue | Sub-issues | Horas |
|------------------|--------------------------------------|-------|------------|-------|
| Tania Botina     | Frontend (HTML/CSS/JS)               | #1    | #7 – #13   | 15.5  |
| Cristian Garcia  | Controlador Java                     | #2    | #14 – #19  | 13    |
| Juan Fernando    | Servicio PHP                         | #3    | #20 – #25  | 11.5  |
| Juan Diego       | Servicio Python                      | #4    | #26 – #31  | 13    |
| Valentina Galvis | Base de datos, Docker e integración  | #5    | #32 – #38  | 12    |
| Jose Daniel      | Documentación y diagramas            | #6    | #39 – #44  | 17.5  |

## Cronograma (entrega: sábado 21 de noviembre)

| Día        | Qué se hace                                                                 |
|------------|-----------------------------------------------------------------------------|
| mar 17 nov | Estructura base de cada componente (sin bloqueos)                           |
| mié 18 nov | Lógica principal de cada servicio, trabajando contra mocks (sin bloqueos)   |
| jue 19 nov | Validaciones, manejo de errores y pruebas. **Python debe terminar #29**      |
| vie 20 nov | Integración en cadena: Python → PHP → Java → Frontend → verificación final  |
| sáb 21 nov | Documento final consolidado y entrega                                       |

## Dependencias entre tareas

Casi todo se puede hacer en paralelo gracias al [contrato de API](docs/api-contract.md).
Solo las tareas de **integración** esperan a otras:

```
#29 Python endpoints (Juan Diego)
  └─► #25 Integración PHP ↔ Python (Juan Fernando)
        └─► #19 Integración Java ↔ PHP (Cristian)
              ├─► #13 Integración frontend (Tania)
              └─► #37 Verificación end-to-end (Valentina) ◄── #13
                    ├─► #38 README final (Valentina)
                    └─► #44 Documento final (Jose Daniel) ◄── #39 #40 #41 #42 #43
```

Quien termina una tarea que bloquea a otra debe comentar en la issue bloqueada para avisar.
