// Lógica de la interfaz. Las llamadas HTTP están en api.js (cargado antes que este archivo).

const estado = document.getElementById('estado');
const mensajes = document.getElementById('mensajes');
const selectMateria = document.getElementById('materia');
const formBusqueda = document.getElementById('form-busqueda');
const inputBusqueda = document.getElementById('buscar-codigo');
const btnVerTodos = document.getElementById('btn-ver-todos');
const cuerpoTabla = document.getElementById('cuerpo-tabla');
const formMonitor = document.getElementById('form-monitor');
const tituloFormulario = document.getElementById('titulo-formulario');
const inputCodigo = document.getElementById('codigo');
const inputNombre = document.getElementById('nombre');
const inputCorreo = document.getElementById('correo');
const btnGuardar = document.getElementById('btn-guardar');
const btnCancelar = document.getElementById('btn-cancelar');

const COLUMNAS_TABLA = 5;
// Reglas del contrato §6.2
const REGEX_CORREO = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
const NOMBRE_MIN = 3;
const NOMBRE_MAX = 150;
const CORREO_MAX = 150;
// Formato de código del contrato §6.2 (se acepta minúscula porque el backend normaliza a MAYÚSCULAS)
const REGEX_CODIGO = /^[A-Za-z0-9-]{1,20}$/;
const MENSAJE_CODIGO_INVALIDO = 'El código solo puede tener letras, números y guiones (máximo 20 caracteres)';

// Cada carga de la tabla recibe un número; solo se pinta la respuesta de la más reciente,
// para que una respuesta lenta no reemplace el resultado de una acción posterior.
let ultimaPeticionTabla = 0;

// Código del monitor que se está editando; null = el formulario está en modo registro
let codigoEnEdicion = null;

/* ==========================================================================
   Mensajes
   ========================================================================== */

/** Muestra un mensaje de éxito ('ok') o de error ('error') en #mensajes. */
function mostrarMensaje(texto, tipo) {
    mensajes.textContent = texto;
    mensajes.className = `mensajes ${tipo}`;
}

function limpiarMensaje() {
    mensajes.textContent = '';
    mensajes.className = 'mensajes';
}

/* ==========================================================================
   Tabla de monitores
   ========================================================================== */

/** Reemplaza el contenido de la tabla por una sola fila con un texto (vacío, cargando...). */
function mostrarFilaUnica(texto) {
    const fila = document.createElement('tr');
    const celda = document.createElement('td');
    celda.colSpan = COLUMNAS_TABLA;
    celda.className = 'tabla-vacia';
    celda.textContent = texto;
    fila.append(celda);
    cuerpoTabla.replaceChildren(fila);
}

function crearBotonAccion(texto, clase, accion, codigo) {
    const boton = document.createElement('button');
    boton.type = 'button';
    boton.className = `btn ${clase} btn-pequeno`;
    boton.textContent = texto;
    boton.dataset.accion = accion;
    boton.dataset.codigo = codigo;
    boton.setAttribute('aria-label', `${texto} monitor ${codigo}`);
    return boton;
}

function crearFila(monitor) {
    const fila = document.createElement('tr');

    for (const valor of [monitor.codigo, monitor.nombre, monitor.correo, monitor.materia_nombre]) {
        const celda = document.createElement('td');
        celda.textContent = valor;
        fila.append(celda);
    }

    const acciones = document.createElement('div');
    acciones.className = 'acciones';
    acciones.append(
        crearBotonAccion('Editar', 'btn-secundario', 'editar', monitor.codigo),
        crearBotonAccion('Eliminar', 'btn-peligro', 'eliminar', monitor.codigo),
    );
    const celdaAcciones = document.createElement('td');
    celdaAcciones.append(acciones);
    fila.append(celdaAcciones);

    return fila;
}

/** Pinta los monitores en la tabla (usa textContent, nunca innerHTML con datos del usuario). */
function renderTabla(monitores) {
    if (monitores.length === 0) {
        mostrarFilaUnica('No hay monitores registrados');
        return;
    }
    cuerpoTabla.replaceChildren(...monitores.map(crearFila));
}

/* ==========================================================================
   Carga de datos
   ========================================================================== */

async function cargarMaterias() {
    try {
        const materias = await listarMaterias();
        const opciones = materias.map((materia) => new Option(materia.nombre, String(materia.id)));
        selectMateria.replaceChildren(new Option('Seleccione una materia', ''), ...opciones);
    } catch (error) {
        mostrarMensaje(error.message, 'error');
    }
}

/** RF2: lista todos los monitores. */
async function cargarMonitores() {
    const peticion = ++ultimaPeticionTabla;
    mostrarFilaUnica('Cargando monitores...');
    try {
        const monitores = await listarMonitores();
        if (peticion !== ultimaPeticionTabla) {
            return;
        }
        renderTabla(monitores);
    } catch (error) {
        if (peticion !== ultimaPeticionTabla) {
            return;
        }
        mostrarFilaUnica('No se pudieron cargar los monitores');
        mostrarMensaje(error.message, 'error');
    }
}

/** RF3: busca un monitor por su código y muestra solo esa fila. */
async function buscarMonitor(evento) {
    evento.preventDefault();
    const codigo = inputBusqueda.value.trim();

    if (codigo === '') {
        mostrarMensaje('Escriba un código para buscar', 'error');
        inputBusqueda.focus();
        return;
    }
    // Un código con otros caracteres (p. ej. "/") no puede existir y alteraría la ruta de la API
    if (!REGEX_CODIGO.test(codigo)) {
        mostrarMensaje(MENSAJE_CODIGO_INVALIDO, 'error');
        inputBusqueda.focus();
        return;
    }

    const peticion = ++ultimaPeticionTabla;
    limpiarMensaje();
    mostrarFilaUnica('Buscando...');
    try {
        const monitor = await obtenerMonitor(codigo);
        if (peticion !== ultimaPeticionTabla) {
            return;
        }
        renderTabla([monitor]);
    } catch (error) {
        if (peticion !== ultimaPeticionTabla) {
            return;
        }
        // "Sin resultados" solo si el monitor no existe; otros errores no significan que no exista
        mostrarFilaUnica(error.status === 404 ? 'Sin resultados' : 'No se pudo realizar la búsqueda');
        mostrarMensaje(error.message, 'error');
    }
}

async function verTodos() {
    inputBusqueda.value = '';
    limpiarMensaje();
    await cargarMonitores();
}

/* ==========================================================================
   Formulario: registro (RF1) y edición (RF4)
   ========================================================================== */

/**
 * Lee el formulario normalizado como el contrato §6.1 y lo valida en el orden de §6.3.
 * Devuelve { datos } si es válido o { error, campo } con el mensaje del catálogo §7.
 */
function leerFormulario() {
    const codigo = inputCodigo.value.trim().toUpperCase();
    const nombre = inputNombre.value.trim().replace(/\s+/g, ' ');
    const correo = inputCorreo.value.trim().toLowerCase();
    const materiaId = Number(selectMateria.value);

    if (codigoEnEdicion === null) {
        if (codigo === '') {
            return { error: 'El código es obligatorio', campo: inputCodigo };
        }
        if (!REGEX_CODIGO.test(codigo)) {
            return { error: MENSAJE_CODIGO_INVALIDO, campo: inputCodigo };
        }
    }
    if (nombre === '') {
        return { error: 'El nombre es obligatorio', campo: inputNombre };
    }
    if (nombre.length < NOMBRE_MIN || nombre.length > NOMBRE_MAX) {
        return { error: 'El nombre debe tener entre 3 y 150 caracteres', campo: inputNombre };
    }
    if (correo === '') {
        return { error: 'El correo es obligatorio', campo: inputCorreo };
    }
    if (!REGEX_CORREO.test(correo)) {
        return { error: 'El correo no es válido', campo: inputCorreo };
    }
    if (correo.length > CORREO_MAX) {
        return { error: 'El correo debe tener máximo 150 caracteres', campo: inputCorreo };
    }
    if (!Number.isInteger(materiaId) || materiaId <= 0) {
        return { error: 'La materia es obligatoria', campo: selectMateria };
    }

    return { datos: { codigo, nombre, correo, materia_id: materiaId } };
}

function limpiarErroresCampos() {
    for (const campo of [inputCodigo, inputNombre, inputCorreo, selectMateria]) {
        campo.removeAttribute('aria-invalid');
    }
}

/** Vuelve al modo registro con el formulario vacío. */
function salirDeEdicion() {
    codigoEnEdicion = null;
    formMonitor.reset();
    limpiarErroresCampos();
    inputCodigo.disabled = false;
    tituloFormulario.textContent = 'Registrar monitor';
    btnGuardar.textContent = 'Guardar';
    btnCancelar.hidden = true;
}

/** Carga un monitor en el formulario para editarlo (el código no se puede cambiar). */
function entrarEnEdicion(monitor) {
    limpiarErroresCampos();
    codigoEnEdicion = monitor.codigo;
    inputCodigo.value = monitor.codigo;
    inputCodigo.disabled = true;
    inputNombre.value = monitor.nombre;
    inputCorreo.value = monitor.correo;
    selectMateria.value = String(monitor.materia_id);
    tituloFormulario.textContent = `Editar monitor ${monitor.codigo}`;
    btnGuardar.textContent = 'Guardar cambios';
    btnCancelar.hidden = false;
    formMonitor.scrollIntoView({ behavior: 'smooth', block: 'start' });
    inputNombre.focus({ preventScroll: true });
}

async function guardarMonitor(evento) {
    // Sin esto el navegador envía el formulario por GET y recarga la página
    evento.preventDefault();
    limpiarErroresCampos();

    const validacion = leerFormulario();
    if (validacion.error) {
        mostrarMensaje(validacion.error, 'error');
        validacion.campo.setAttribute('aria-invalid', 'true');
        validacion.campo.focus();
        return;
    }

    const { datos } = validacion;
    const enEdicion = codigoEnEdicion !== null;
    btnGuardar.disabled = true;
    try {
        if (enEdicion) {
            // En PUT el código va en la ruta, no en el cuerpo (contrato)
            const cambios = { nombre: datos.nombre, correo: datos.correo, materia_id: datos.materia_id };
            const monitor = await actualizarMonitor(codigoEnEdicion, cambios);
            mostrarMensaje(`Monitor ${monitor.codigo} actualizado correctamente`, 'ok');
        } else {
            const monitor = await crearMonitor(datos);
            mostrarMensaje(`Monitor ${monitor.codigo} registrado correctamente`, 'ok');
        }
        salirDeEdicion();
        inputBusqueda.value = '';
        await cargarMonitores();
    } catch (error) {
        // Errores 400/404/409 del backend tal como llegan
        mostrarMensaje(error.message, 'error');
    } finally {
        btnGuardar.disabled = false;
    }
}

/** Botón Editar de una fila: trae el monitor actualizado del backend y lo carga en el formulario. */
async function editarMonitor(codigo) {
    try {
        const monitor = await obtenerMonitor(codigo);
        limpiarMensaje();
        entrarEnEdicion(monitor);
    } catch (error) {
        mostrarMensaje(error.message, 'error');
    }
}

function cancelarEdicion() {
    salirDeEdicion();
    limpiarMensaje();
}

/** Un solo listener para los botones de todas las filas (la tabla se vuelve a pintar a menudo). */
function manejarAccionTabla(evento) {
    const boton = evento.target.closest('button[data-accion]');
    if (!boton) {
        return;
    }
    if (boton.dataset.accion === 'editar') {
        editarMonitor(boton.dataset.codigo);
    }
}

/** Deja en un texto solo los caracteres válidos para un código (§6.2), en MAYÚSCULAS. */
function limpiarCodigo(texto) {
    return texto.toUpperCase().replace(/[^A-Z0-9-]/g, '');
}

/**
 * Al escribir o pegar en el código: pasa a MAYÚSCULAS y descarta lo que no sea letra
 * (sin tildes ni ñ), número o guion. El cursor se queda donde estaba.
 */
function filtrarCodigo() {
    const valor = inputCodigo.value;
    const limpio = limpiarCodigo(valor);
    if (limpio === valor) {
        return;
    }
    const cursor = limpiarCodigo(valor.slice(0, inputCodigo.selectionStart)).length;
    inputCodigo.value = limpio;
    inputCodigo.setSelectionRange(cursor, cursor);
}

async function comprobarBackend() {
    try {
        const salud = await consultarSalud();
        estado.textContent = USE_MOCK ? 'Modo de prueba (datos simulados)' : `Backend: ${salud.status}`;
    } catch {
        estado.textContent = 'Backend no disponible';
    }
}

/* ==========================================================================
   Inicio
   ========================================================================== */

formBusqueda.addEventListener('submit', buscarMonitor);
btnVerTodos.addEventListener('click', verTodos);
formMonitor.addEventListener('submit', guardarMonitor);
btnCancelar.addEventListener('click', cancelarEdicion);
inputCodigo.addEventListener('input', filtrarCodigo);
cuerpoTabla.addEventListener('click', manejarAccionTabla);

comprobarBackend();
cargarMaterias();
cargarMonitores();
