# Documentación del proyecto

## Entregables del taller

| Entregable | Documento |
|------------|-----------|
| 1. Arquitectura | [Diagrama de arquitectura](arquitectura.md) (Mermaid; [PNG](img/arquitectura.png)) · [PDF](arquitectura.pdf) |
| 1. Estilos y patrones | [patrones.md](patrones.md) |
| 2. Diagrama de secuencia (RF1) | [secuencia-registro.md](secuencia-registro.md) (Mermaid; [PNG](img/secuencia-registro.png)) |
| 4. Endpoints | [endpoints.md](endpoints.md) · [colección Postman](postman/monitores.postman_collection.json) |
| 5. Ventajas y dificultades | [ventajas-dificultades.md](ventajas-dificultades.md) |
| Documento final | [documento-final.pdf](documento-final.pdf) |

Los diagramas Mermaid se ven directamente en GitHub. Los PNG de `img/` se generan desde esos mismos
bloques.

## Manuales

- [Manual técnico (PDF)](manual-tecnico.pdf) · [fuente LaTeX](manual-tecnico.tex)
- [Manual de usuario (PDF)](manual-usuario.pdf) · [fuente LaTeX](manual-usuario.tex)
- [Diagrama de arquitectura (PDF)](arquitectura.pdf)
- [Contrato de API](api-contract.md)

## Compilar los manuales

Se requiere una distribución LaTeX con `pdflatex`. Desde esta carpeta, ejecutar dos veces cada comando para actualizar el índice:

```bash
pdflatex -interaction=nonstopmode -halt-on-error manual-tecnico.tex
pdflatex -interaction=nonstopmode -halt-on-error manual-tecnico.tex
pdflatex -interaction=nonstopmode -halt-on-error manual-usuario.tex
pdflatex -interaction=nonstopmode -halt-on-error manual-usuario.tex
```

El preámbulo compartido está en `preambulo-manuales.tex`. Los PDF se generan junto a las fuentes `.tex`.

## Alcance del diagrama

El diagrama presenta el flujo principal entre navegador, frontend/nginx, Java, PHP, Python y PostgreSQL. No detalla rutas CRUD ni utilidades de operación para mantener legible la vista general.
