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

| Integrante       | Responsabilidad                              |
|------------------|----------------------------------------------|
| Tania Botina     | Frontend (HTML/CSS/JS)                        |
| Jose Daniel      | Controlador Java                              |
| Juan Fernando    | Servicio PHP                                  |
| Juan Diego       | Servicio Python                               |
| Cristian Garcia  | Base de datos, Docker e integración           |
| Valentina Galvis | Documentación y diagramas                     |
