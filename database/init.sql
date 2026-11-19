-- Esquema base acordado en docs/api-contract.md
-- Se ejecuta automáticamente la primera vez que arranca el contenedor de PostgreSQL.
-- Para volver a aplicarlo: docker compose down -v && docker compose up --build

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

-- Datos semilla de materias (contrato §10).
-- SW3 y BD1 van primero para que reciban id = 1 e id = 2: las pruebas cuentan con esos ids.
-- Un solo INSERT asigna los ids del SERIAL en el orden de la lista.
INSERT INTO materias (codigo, nombre) VALUES
    ('SW3',  'Ingeniería de Software III'),
    ('BD1',  'Bases de Datos I'),
    ('PRG1', 'Programación I'),
    ('ED1',  'Estructuras de Datos'),
    ('SO1',  'Sistemas Operativos'),
    ('RED1', 'Redes de Computadores'),
    ('CAL1', 'Cálculo Diferencial'),
    ('ALG1', 'Álgebra Lineal')
ON CONFLICT (codigo) DO NOTHING;

-- Monitores de demostración (contrato §12: prefijo M-, no se borran en las pruebas).
-- Correos en minúscula con dominio @ucaldas.edu.co. La materia se busca por su código
-- para no depender de los ids asignados. M-007 repite el correo de M-001 con otra materia:
-- el correo no es único (contrato §10).
INSERT INTO monitores (codigo, nombre, correo, materia_id)
SELECT semilla.codigo, semilla.nombre, semilla.correo, materias.id
FROM (VALUES
    ('M-001', 'Ana María López',        'ana.lopez@ucaldas.edu.co',      'SW3'),
    ('M-002', 'Carlos Pérez',           'carlos.perez@ucaldas.edu.co',   'BD1'),
    ('M-003', 'Sofía Núñez',            'sofia.nunez@ucaldas.edu.co',    'SW3'),
    ('M-004', 'Andrés Felipe Ramírez',  'andres.ramirez@ucaldas.edu.co', 'PRG1'),
    ('M-005', 'Valeria Gómez Muñoz',    'valeria.gomez@ucaldas.edu.co',  'ED1'),
    ('M-006', 'Julián Castaño Ospina',  'julian.castano@ucaldas.edu.co', 'SO1'),
    ('M-007', 'Ana María López',        'ana.lopez@ucaldas.edu.co',      'CAL1')
) AS semilla (codigo, nombre, correo, materia_codigo)
JOIN materias ON materias.codigo = semilla.materia_codigo
ON CONFLICT (codigo) DO NOTHING;
