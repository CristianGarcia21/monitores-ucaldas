"""Servicio Python - capa de persistencia.

Esqueleto inicial: solo expone /health.
Implementar los endpoints definidos en docs/api-contract.md (sección Python).
"""
import os

from fastapi import FastAPI

app = FastAPI(title="Servicio Python - Persistencia")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "dbname": os.getenv("DB_NAME", "monitores"),
    "user": os.getenv("DB_USER", "monitores"),
    "password": os.getenv("DB_PASSWORD", "monitores"),
}


@app.get("/health")
def health():
    return {"service": "python-service", "status": "ok"}


# TODO: GET    /materias
# TODO: GET    /monitores
# TODO: GET    /monitores/{codigo}
# TODO: POST   /monitores
# TODO: PUT    /monitores/{codigo}
# TODO: DELETE /monitores/{codigo}
