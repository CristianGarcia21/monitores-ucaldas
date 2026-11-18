"""Servicio Python - capa de persistencia.

Esqueleto inicial: solo expone /health.
Implementar los endpoints definidos en docs/api-contract.md (sección Python).
"""
from fastapi import FastAPI

app = FastAPI(title="Servicio Python - Persistencia")


@app.get("/health")
def health():
    return {"service": "python-service", "status": "ok"}


# TODO: GET    /materias
# TODO: GET    /monitores
# TODO: GET    /monitores/{codigo}
# TODO: POST   /monitores
# TODO: PUT    /monitores/{codigo}
# TODO: DELETE /monitores/{codigo}
