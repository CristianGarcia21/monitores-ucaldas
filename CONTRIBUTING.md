# Reglas de trabajo del equipo

Complementa al [contrato del sistema](docs/api-contract.md): el contrato define **qué** se construye; este
documento define **cómo** se trabaja en el repositorio. Ambos son obligatorios.

## 1. Propiedad de carpetas

| Carpeta / archivo                         | Dueño            |
|-------------------------------------------|------------------|
| `frontend/`                               | Tania Botina     |
| `java-controller/`                        | Cristian Garcia  |
| `php-service/`                            | Juan Fernando    |
| `python-service/`                         | Juan Diego       |
| `database/`, `docker-compose.yml`, `scripts/`, `.env.example`, `README.md` | Valentina Galvis |
| `docs/` (excepto `api-contract.md`)       | Jose Daniel      |
| `docs/api-contract.md`, `CONTRIBUTING.md` | Todos (solo con el proceso de cambio del contrato) |

- Cada quien modifica **solo su carpeta**. Si necesitas un cambio en otra, abre un issue o comenta en el issue de su dueño.
- Excepción: el `Dockerfile` de cada servicio es de su dueño, pero **no** se cambia el puerto expuesto ni el comando de arranque sin avisar a Valentina.

## 2. Ramas

- `main` siempre debe levantar con `docker compose up --build`. **Nadie hace push directo a `main`.**
- Una rama por sub-issue (o grupo pequeño de sub-issues): `feature/<carpeta>-<número-issue>`

  ```
  feature/frontend-9
  feature/java-controller-15
  feature/php-service-22
  feature/python-service-28
  feature/database-33
  feature/docs-40
  ```
- Correcciones de errores: `fix/<carpeta>-<número-issue>`.
- Antes de abrir el PR, actualiza tu rama: `git pull origin main`.

## 3. Commits

Formato [Conventional Commits](https://www.conventionalcommits.org/es/) en español, en imperativo:

```
<tipo>(<alcance>): <descripción corta en minúscula>
```

| Tipo       | Uso                                  |
|------------|--------------------------------------|
| `feat`     | Funcionalidad nueva                  |
| `fix`      | Corrección de un error               |
| `test`     | Pruebas                              |
| `docs`     | Documentación                        |
| `refactor` | Cambio interno sin cambiar comportamiento |
| `chore`    | Configuración, Docker, dependencias  |

Alcances: `frontend`, `java`, `php`, `python`, `db`, `docker`, `docs`, `contrato`.

```
feat(python): agregar endpoint POST /monitores
fix(php): propagar 204 sin cuerpo
docs(docs): diagrama de secuencia del registro
```

## 4. Pull Requests

- Título igual al de la sub-issue. Descripción con `Closes #<número>` (una línea por issue que cierre).
- Checklist que debe cumplir todo PR:
  - [ ] Solo toca archivos de mi carpeta
  - [ ] `docker compose up --build` funciona y mi servicio responde `/health`
  - [ ] Respeta rutas, JSON, códigos y mensajes del contrato
  - [ ] No sube secretos, `.env`, `target/`, `venv/`, `__pycache__/` ni `node_modules/`
  - [ ] Si agregué una dependencia, está en el archivo de dependencias de mi servicio
- Lo revisa al menos otra persona. Cristian (dueño del repo) hace el merge.

## 5. Versiones y librerías (no cambiar sin acuerdo)

| Componente | Versión / librerías permitidas |
|------------|--------------------------------|
| Frontend   | HTML5, CSS3, JavaScript ES2020+ **sin frameworks** ni librerías (nada de React, jQuery, Bootstrap) |
| Java       | Java 21 · Spring Boot 3.3.x (`web`, `validation`, `test`) · `RestClient` para HTTP |
| PHP        | PHP 8.3 **sin frameworks** · extensión cURL · servidor embebido `php -S` |
| Python     | Python 3.12 · FastAPI · Uvicorn · psycopg 3 · Pydantic v2 · pytest · **sin ORM** (SQL parametrizado) |
| BD         | PostgreSQL 16 |
| Docker     | Docker Compose v2 (`docker compose`, no `docker-compose`) |

## 6. Estilo de código

| Lenguaje | Reglas |
|----------|--------|
| Todos | Nombres del dominio en **español** y coherentes con el JSON (`monitor`, `materia`, `codigo`, `correo`). Comentarios en español. Indentación con espacios (ver `.editorconfig`). Sin código comentado ni `console.log`/`print` de depuración en el PR. |
| JavaScript | `camelCase` para variables y funciones; `const`/`let` (nunca `var`); `async/await`; usar `textContent` para mostrar datos del usuario (nunca `innerHTML` con datos). |
| Java | Paquete base `co.edu.ucaldas.monitores`; subpaquetes `controller`, `dto`, `client`, `exception`. `PascalCase` clases, `camelCase` métodos. DTOs como `record`. |
| PHP | `declare(strict_types=1);` · funciones en `camelCase` · clases en `PascalCase` · un archivo por clase. |
| Python | PEP 8 · `snake_case` · type hints en funciones · módulos `db.py`, `schemas.py`, `repository.py`, `main.py`. |
| SQL | Palabras clave en MAYÚSCULA, tablas y columnas en `snake_case` minúscula. |

## 7. Docker

- Todo se levanta desde la raíz con `docker compose up --build`.
- Cada servicio debe poder construirse solo: `docker compose build <servicio>`.
- Reiniciar la base de datos desde cero: `docker compose down -v`.
- Los saltos de línea se normalizan a LF con `.gitattributes` (los scripts `.sh` con CRLF fallan dentro de Linux).

## 8. Comunicación

- Avances y dudas técnicas: **en la issue** (no solo por WhatsApp), para que quede registro.
- Cuando termines una tarea que **bloquea** a otra, comenta en la issue bloqueada: "Listo, ya pueden integrar".
- Si te vas a atrasar en una tarea con fecha, avisa en su issue lo antes posible.
