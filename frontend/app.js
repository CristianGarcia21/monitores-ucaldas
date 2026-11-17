// Lógica de la interfaz. Las llamadas HTTP están en api.js (cargado antes que este archivo).

const estado = document.getElementById('estado');

consultarSalud()
    .then((salud) => {
        estado.textContent = USE_MOCK ? 'Modo de prueba (datos simulados)' : `Backend: ${salud.status}`;
    })
    .catch(() => {
        estado.textContent = 'Backend no disponible';
    });

// TODO: listar, buscar por código, registrar, actualizar y eliminar monitores
