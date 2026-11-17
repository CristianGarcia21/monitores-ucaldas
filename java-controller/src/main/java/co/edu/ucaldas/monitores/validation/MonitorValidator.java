package co.edu.ucaldas.monitores.validation;

import java.util.Locale;
import java.util.regex.Pattern;

import org.springframework.stereotype.Component;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;

import co.edu.ucaldas.monitores.exception.ApiException;

/**
 * Normaliza (contrato §6.1) y valida (§6.2) el cuerpo de un monitor.
 * Responde solo el primer error, en el orden fijo del §6.3, con los mensajes del catálogo §7.
 * Se valida a mano (no con Bean Validation) porque el contrato exige un orden determinista
 * y rechazar materia_id enviado como texto, cosas que las anotaciones no garantizan.
 */
@Component
public class MonitorValidator {

    private static final Pattern CODIGO = Pattern.compile("^[A-Z0-9-]{1,20}$");
    private static final Pattern CORREO = Pattern.compile("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$");

    static final String JSON_INVALIDO = "JSON inválido";
    static final String CODIGO_OBLIGATORIO = "El código es obligatorio";
    static final String CODIGO_FORMATO = "El código solo puede tener letras, números y guiones (máximo 20 caracteres)";
    static final String NOMBRE_OBLIGATORIO = "El nombre es obligatorio";
    static final String NOMBRE_LONGITUD = "El nombre debe tener entre 3 y 150 caracteres";
    static final String CORREO_OBLIGATORIO = "El correo es obligatorio";
    static final String CORREO_FORMATO = "El correo no es válido";
    static final String CORREO_LONGITUD = "El correo debe tener máximo 150 caracteres";
    static final String MATERIA_OBLIGATORIA = "La materia es obligatoria";

    private final ObjectMapper mapper;

    public MonitorValidator(ObjectMapper mapper) {
        this.mapper = mapper;
    }

    /** Cuerpo de POST /monitores: exige codigo, nombre, correo y materia_id. */
    public ObjectNode validarCreacion(JsonNode body) {
        exigirObjeto(body);
        ObjectNode salida = mapper.createObjectNode();
        salida.put("codigo", validarCodigo(body.get("codigo")));
        agregarCamposEditables(body, salida);
        return salida;
    }

    /** Cuerpo de PUT /monitores/{codigo}: exige nombre, correo y materia_id; ignora codigo. */
    public ObjectNode validarActualizacion(JsonNode body) {
        exigirObjeto(body);
        ObjectNode salida = mapper.createObjectNode();
        agregarCamposEditables(body, salida);
        return salida;
    }

    /** Normalización del {codigo} de la ruta: trim + mayúsculas. */
    public String normalizarCodigo(String codigo) {
        return codigo.trim().toUpperCase(Locale.ROOT);
    }

    private void exigirObjeto(JsonNode body) {
        if (body == null || !body.isObject()) {
            throw error(JSON_INVALIDO);
        }
    }

    private void agregarCamposEditables(JsonNode body, ObjectNode salida) {
        salida.put("nombre", validarNombre(body.get("nombre")));
        salida.put("correo", validarCorreo(body.get("correo")));
        salida.put("materia_id", validarMateria(body.get("materia_id")));
    }

    private String validarCodigo(JsonNode nodo) {
        String codigo = texto(nodo);
        if (codigo == null) {
            throw error(CODIGO_OBLIGATORIO);
        }
        codigo = normalizarCodigo(codigo);
        if (!CODIGO.matcher(codigo).matches()) {
            throw error(CODIGO_FORMATO);
        }
        return codigo;
    }

    private String validarNombre(JsonNode nodo) {
        String nombre = texto(nodo);
        if (nombre == null) {
            throw error(NOMBRE_OBLIGATORIO);
        }
        nombre = nombre.trim().replaceAll("\\s+", " ");
        int largo = nombre.codePointCount(0, nombre.length());
        if (largo < 3 || largo > 150) {
            throw error(NOMBRE_LONGITUD);
        }
        return nombre;
    }

    private String validarCorreo(JsonNode nodo) {
        String correo = texto(nodo);
        if (correo == null) {
            throw error(CORREO_OBLIGATORIO);
        }
        correo = correo.trim().toLowerCase(Locale.ROOT);
        if (!CORREO.matcher(correo).matches()) {
            throw error(CORREO_FORMATO);
        }
        if (correo.codePointCount(0, correo.length()) > 150) {
            throw error(CORREO_LONGITUD);
        }
        return correo;
    }

    private int validarMateria(JsonNode nodo) {
        if (nodo == null || !nodo.isIntegralNumber() || !nodo.canConvertToInt() || nodo.intValue() <= 0) {
            throw error(MATERIA_OBLIGATORIA);
        }
        return nodo.intValue();
    }

    /** Devuelve el texto si el nodo es un string no vacío tras el trim; si no, null ("vacío" según §6.2). */
    private static String texto(JsonNode nodo) {
        if (nodo == null || !nodo.isTextual() || nodo.asText().isBlank()) {
            return null;
        }
        return nodo.asText();
    }

    private static ApiException error(String mensaje) {
        return new ApiException(400, mensaje);
    }
}
