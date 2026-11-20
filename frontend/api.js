// Capa de acceso a la API del sistema de monitores.
// Todo el frontend usa estas funciones; ningún otro archivo llama a fetch directamente.
// Rutas, cuerpos y mensajes según docs/api-contract.md (§8 endpoints, §7 errores).
//
// Con USE_MOCK = false (integración, F7) las funciones llaman al backend real por /api.
// Con USE_MOCK = true responden con datos en memoria que imitan al backend (contrato §13),
// útil para trabajar en la interfaz sin levantar Java, PHP ni Python.

const USE_MOCK = false;

const API_BASE = '/api';
const MENSAJE_SIN_CONEXION = 'No se pudo conectar con el servidor';
const MENSAJE_ERROR_INTERNO = 'Error interno del servidor';

/* ==========================================================================
   Funciones públicas (las usa app.js)
   ========================================================================== */

/** GET /api/health → {service, status}. En modo mock responde sin red. */
async function consultarSalud() {
    return USE_MOCK ? { service: 'mock', status: 'ok' } : peticion('GET', '/health');
}

/** GET /api/materias → [{id, codigo, nombre}] ordenadas por nombre. */
async function listarMaterias() {
    return USE_MOCK ? servidorMock.listarMaterias() : peticion('GET', '/materias');
}

/** GET /api/monitores → [Monitor] ordenados por código ([] si no hay). */
async function listarMonitores() {
    return USE_MOCK ? servidorMock.listarMonitores() : peticion('GET', '/monitores');
}

/** GET /api/monitores/{codigo} → Monitor. Error 404 si no existe. */
async function obtenerMonitor(codigo) {
    return USE_MOCK ? servidorMock.obtenerMonitor(codigo) : peticion('GET', rutaMonitor(codigo));
}

/** POST /api/monitores con {codigo, nombre, correo, materia_id} → Monitor creado. */
async function crearMonitor(datos) {
    return USE_MOCK ? servidorMock.crearMonitor(datos) : peticion('POST', '/monitores', datos);
}

/** PUT /api/monitores/{codigo} con {nombre, correo, materia_id} → Monitor actualizado. */
async function actualizarMonitor(codigo, datos) {
    return USE_MOCK
        ? servidorMock.actualizarMonitor(codigo, datos)
        : peticion('PUT', rutaMonitor(codigo), datos);
}

/** DELETE /api/monitores/{codigo} → 204 sin cuerpo (devuelve null). */
async function eliminarMonitor(codigo) {
    return USE_MOCK ? servidorMock.eliminarMonitor(codigo) : peticion('DELETE', rutaMonitor(codigo));
}

/* ==========================================================================
   Cliente HTTP real
   ========================================================================== */

function rutaMonitor(codigo) {
    return `/monitores/${encodeURIComponent(String(codigo).trim())}`;
}

/** Error con el mensaje del backend y el código HTTP (status) por si la interfaz lo necesita. */
function crearErrorApi(mensaje, status) {
    const error = new Error(mensaje);
    error.status = status;
    return error;
}

async function peticion(metodo, ruta, cuerpo) {
    const opciones = { method: metodo, headers: { Accept: 'application/json' } };
    if (cuerpo !== undefined) {
        opciones.headers['Content-Type'] = 'application/json';
        opciones.body = JSON.stringify(cuerpo);
    }

    let respuesta;
    try {
        respuesta = await fetch(`${API_BASE}${ruta}`, opciones);
    } catch {
        throw crearErrorApi(MENSAJE_SIN_CONEXION, 0);
    }

    // DELETE exitoso: 204 sin cuerpo, no se intenta leer JSON (contrato H5)
    if (respuesta.status === 204) {
        return null;
    }

    let datos = null;
    try {
        datos = await respuesta.json();
    } catch {
        datos = null;
    }

    if (!respuesta.ok) {
        throw crearErrorApi(mensajeDeError(respuesta.status, datos), respuesta.status);
    }
    if (datos === null) {
        throw crearErrorApi(MENSAJE_ERROR_INTERNO, respuesta.status);
    }
    return datos;
}

/** Usa el texto de "error" tal como llega; solo si no viene en formato del contrato se usa uno genérico. */
function mensajeDeError(status, datos) {
    if (datos !== null && typeof datos === 'object' && typeof datos.error === 'string') {
        return datos.error;
    }
    // Respuesta fuera del contrato, p. ej. la página HTML de nginx cuando Java no responde
    return [502, 503, 504].includes(status) ? MENSAJE_SIN_CONEXION : MENSAJE_ERROR_INTERNO;
}

/* ==========================================================================
   Modo mock: imita las respuestas del backend según el contrato
   ========================================================================== */

const servidorMock = (() => {
    const LATENCIA_MS = 150;
    const REGEX_CODIGO = /^[A-Z0-9-]{1,20}$/;
    const REGEX_CORREO = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

    // Materias con id 1 y 2 fijos (contrato §10)
    const materias = [
        { id: 1, codigo: 'SW3', nombre: 'Ingeniería de Software III' },
        { id: 2, codigo: 'BD1', nombre: 'Bases de Datos I' },
    ];

    const monitores = [
        { codigo: 'M-001', nombre: 'Ana María López', correo: 'ana.lopez@ucaldas.edu.co', materia_id: 1 },
        { codigo: 'M-002', nombre: 'Carlos Pérez', correo: 'carlos.perez@ucaldas.edu.co', materia_id: 2 },
        { codigo: 'M-003', nombre: 'Sofía Núñez', correo: 'sofia.nunez@ucaldas.edu.co', materia_id: 1 },
    ];

    function esperar() {
        return new Promise((resolver) => setTimeout(resolver, LATENCIA_MS));
    }

    // Normalización del contrato §6.1
    function normalizarCodigo(valor) {
        return typeof valor === 'string' ? valor.trim().toUpperCase() : valor;
    }

    function normalizarNombre(valor) {
        return typeof valor === 'string' ? valor.trim().replace(/\s+/g, ' ') : valor;
    }

    function normalizarCorreo(valor) {
        return typeof valor === 'string' ? valor.trim().toLowerCase() : valor;
    }

    function estaVacio(valor) {
        return typeof valor !== 'string' || valor === '';
    }

    function error400(mensaje) {
        return crearErrorApi(mensaje, 400);
    }

    function error404(codigo) {
        return crearErrorApi(`No existe un monitor con el código ${codigo}`, 404);
    }

    /** Validación en el orden del contrato §6.3 (pasos 1 a 5). Devuelve los datos normalizados. */
    function validar(datos, esCreacion) {
        if (datos === null || typeof datos !== 'object' || Array.isArray(datos)) {
            throw error400('JSON inválido');
        }

        const limpio = {
            nombre: normalizarNombre(datos.nombre),
            correo: normalizarCorreo(datos.correo),
            materia_id: datos.materia_id,
        };

        if (esCreacion) {
            limpio.codigo = normalizarCodigo(datos.codigo);
            if (estaVacio(limpio.codigo)) {
                throw error400('El código es obligatorio');
            }
            if (!REGEX_CODIGO.test(limpio.codigo)) {
                throw error400('El código solo puede tener letras, números y guiones (máximo 20 caracteres)');
            }
        }

        if (estaVacio(limpio.nombre)) {
            throw error400('El nombre es obligatorio');
        }
        if (limpio.nombre.length < 3 || limpio.nombre.length > 150) {
            throw error400('El nombre debe tener entre 3 y 150 caracteres');
        }

        if (estaVacio(limpio.correo)) {
            throw error400('El correo es obligatorio');
        }
        if (!REGEX_CORREO.test(limpio.correo)) {
            throw error400('El correo no es válido');
        }
        if (limpio.correo.length > 150) {
            throw error400('El correo debe tener máximo 150 caracteres');
        }

        if (!Number.isInteger(limpio.materia_id) || limpio.materia_id <= 0) {
            throw error400('La materia es obligatoria');
        }

        return limpio;
    }

    function buscarMateria(id) {
        return materias.find((materia) => materia.id === id);
    }

    function buscarIndice(codigo) {
        return monitores.findIndex((monitor) => monitor.codigo === codigo);
    }

    /** Respuesta con materia_nombre, como copia para que la interfaz no modifique los datos del mock. */
    function aRespuesta(monitor) {
        return { ...monitor, materia_nombre: buscarMateria(monitor.materia_id).nombre };
    }

    return {
        async listarMaterias() {
            await esperar();
            return materias
                .map((materia) => ({ ...materia }))
                .sort((a, b) => a.nombre.localeCompare(b.nombre, 'es'));
        },

        async listarMonitores() {
            await esperar();
            return monitores
                .map(aRespuesta)
                .sort((a, b) => (a.codigo < b.codigo ? -1 : a.codigo > b.codigo ? 1 : 0));
        },

        async obtenerMonitor(codigo) {
            await esperar();
            const normalizado = normalizarCodigo(String(codigo));
            const indice = buscarIndice(normalizado);
            if (indice === -1) {
                throw error404(normalizado);
            }
            return aRespuesta(monitores[indice]);
        },

        async crearMonitor(datos) {
            await esperar();
            const limpio = validar(datos, true);
            if (!buscarMateria(limpio.materia_id)) {
                throw error400('La materia indicada no existe');
            }
            if (buscarIndice(limpio.codigo) !== -1) {
                throw crearErrorApi(`Ya existe un monitor con el código ${limpio.codigo}`, 409);
            }
            const nuevo = {
                codigo: limpio.codigo,
                nombre: limpio.nombre,
                correo: limpio.correo,
                materia_id: limpio.materia_id,
            };
            monitores.push(nuevo);
            return aRespuesta(nuevo);
        },

        async actualizarMonitor(codigo, datos) {
            await esperar();
            const normalizado = normalizarCodigo(String(codigo));
            const limpio = validar(datos, false);
            const indice = buscarIndice(normalizado);
            if (indice === -1) {
                throw error404(normalizado);
            }
            if (!buscarMateria(limpio.materia_id)) {
                throw error400('La materia indicada no existe');
            }
            // El código no cambia aunque venga en el cuerpo (contrato J6)
            monitores[indice] = {
                codigo: normalizado,
                nombre: limpio.nombre,
                correo: limpio.correo,
                materia_id: limpio.materia_id,
            };
            return aRespuesta(monitores[indice]);
        },

        async eliminarMonitor(codigo) {
            await esperar();
            const normalizado = normalizarCodigo(String(codigo));
            const indice = buscarIndice(normalizado);
            if (indice === -1) {
                throw error404(normalizado);
            }
            monitores.splice(indice, 1);
            return null;
        },
    };
})();
