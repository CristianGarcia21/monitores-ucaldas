// Lógica de la interfaz. Las llamadas HTTP están en api.js (cargado antes que este archivo).

const estado = document.getElementById('estado');
const mensajes = document.getElementById('mensajes');
const selectMateria = document.getElementById('materia');
const formBusqueda = document.getElementById('form-busqueda');
const inputBusqueda = document.getElementById('buscar-codigo');
const btnVerTodos = document.getElementById('btn-ver-todos');
const cuerpoTabla = document.getElementById('cuerpo-tabla');

const COLUMNAS_TABLA = 5;

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
    mostrarFilaUnica('Cargando monitores...');
    try {
        renderTabla(await listarMonitores());
    } catch (error) {
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

    limpiarMensaje();
    mostrarFilaUnica('Buscando...');
    try {
        renderTabla([await obtenerMonitor(codigo)]);
    } catch (error) {
        mostrarFilaUnica('Sin resultados');
        mostrarMensaje(error.message, 'error');
    }
}

async function verTodos() {
    inputBusqueda.value = '';
    limpiarMensaje();
    await cargarMonitores();
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

comprobarBackend();
cargarMaterias();
cargarMonitores();
