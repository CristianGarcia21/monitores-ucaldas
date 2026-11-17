-- Esquema base acordado en docs/api-contract.md
-- Se ejecuta automáticamente la primera vez que arranca el contenedor de PostgreSQL.

CREATE TABLE IF NOT EXISTS materias (
    id      SERIAL PRIMARY KEY,
    codigo  VARCHAR(20)  NOT NULL UNIQUE,
    nombre  VARCHAR(120) NOT NULL
);

CREATE TABLE IF NOT EXISTS monitores (
    codigo      VARCHAR(20)  PRIMARY KEY,
    nombre      VARCHAR(150) NOT NULL,
    correo      VARCHAR(150) NOT NULL,
    materia_id  INTEGER      NOT NULL REFERENCES materias(id)
);

-- Datos mínimos para poder probar desde el día 1
INSERT INTO materias (codigo, nombre) VALUES
    ('SW3', 'Ingeniería de Software III'),
    ('BD1', 'Bases de Datos I')
ON CONFLICT (codigo) DO NOTHING;
