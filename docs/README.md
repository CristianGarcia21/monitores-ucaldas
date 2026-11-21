# Documentación del proyecto

## Entregables del taller

Según el enunciado *Diseño e implementación de una arquitectura distribuida, multicapa y heterogénea
mediante servicios REST*.

| Entregable | Documento |
|------------|-----------|
| 1. Arquitectura | [Diagrama de arquitectura](arquitectura.md) (Mermaid; [PNG](img/arquitectura.png)) · [PDF](arquitectura.pdf) |
| 1. Estilos y patrones | [patrones.md](patrones.md) |
| 2. Diagrama de secuencia (RF1) | [secuencia-registro.md](secuencia-registro.md) (Mermaid; [PNG](img/secuencia-registro.png)) |
| 3. Implementación funcional del CRUD | Código en `frontend/`, `java-controller/`, `php-service/`, `python-service/` y `database/`; cómo ejecutarlo en el [README principal](../README.md); capturas y pruebas en el documento final |
| 4. Endpoints | [endpoints.md](endpoints.md) · [colección Postman](postman/monitores.postman_collection.json) |
| 5. Ventajas y dificultades | [ventajas-dificultades.md](ventajas-dificultades.md) |
| Despliegue en tres equipos | [despliegue.md](despliegue.md) (diagrama de despliegue) · [guía paso a paso](../despliegue/README.md) |
| **Documentación general** (todo lo anterior, formato Universidad de Caldas) | [PDF](documentacion-general.pdf) · [Word](documentacion-general.docx) |
| **Manual de usuario** (formato Universidad de Caldas) | [PDF](manual-usuario.pdf) · [Word](manual-usuario.docx) |

Los diagramas Mermaid se ven directamente en GitHub. Los PNG de `img/` se generan desde esos mismos
bloques.

## Documentos para entregar

- **[Documentación general](documentacion-general.pdf)** ([Word](documentacion-general.docx)): un solo documento
  con todo lo que pide el enunciado:
  - arquitectura y patrones;
  - diagrama de secuencia;
  - implementación del CRUD, con instalación, operación y capturas;
  - endpoints;
  - ventajas y dificultades;
  - despliegue en tres equipos;
  - pruebas.
- **[Manual de usuario](manual-usuario.pdf)** ([Word](manual-usuario.docx)): cómo usar la aplicación desde el
  navegador, paso a paso y con capturas.

Los dos usan la plantilla oficial de trabajos de la Universidad de Caldas. Los diagramas que incluyen son los
PNG de `img/`, generados desde los bloques Mermaid de los `.md` de esta carpeta.

## Otros

- [Diagrama de arquitectura (PDF)](arquitectura.pdf): vista gráfica de los componentes y su flujo.
- [Contrato de API](api-contract.md)
