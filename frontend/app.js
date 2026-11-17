// Todas las llamadas van a /api/... (nginx las reenvía al controlador Java).
const API = '/api';

fetch(`${API}/health`)
    .then((r) => r.json())
    .then((d) => { document.getElementById('estado').textContent = `Backend: ${d.status}`; })
    .catch(() => { document.getElementById('estado').textContent = 'Backend no disponible'; });

// TODO: listar, buscar por código, registrar, actualizar y eliminar monitores
