package co.edu.ucaldas.monitores.controller;

import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import co.edu.ucaldas.monitores.client.PhpClient;
import co.edu.ucaldas.monitores.exception.ApiException;
import co.edu.ucaldas.monitores.validation.MonitorValidator;

/**
 * Endpoints del contrato §8. Normaliza y valida los datos (respondiendo 400 sin llamar a PHP)
 * y reenvía todo lo demás a PHP, devolviendo su respuesta sin modificarla (H7).
 */
@RestController
public class MonitorController {

    static final MediaType JSON_UTF8 = MediaType.parseMediaType("application/json;charset=UTF-8");

    private final PhpClient php;
    private final MonitorValidator validator;
    private final ObjectMapper mapper;

    public MonitorController(PhpClient php, MonitorValidator validator, ObjectMapper mapper) {
        this.php = php;
        this.validator = validator;
        this.mapper = mapper;
    }

    @GetMapping("/materias")
    public ResponseEntity<String> listarMaterias() {
        return responder(php.forward(HttpMethod.GET, "/materias", null));
    }

    @GetMapping("/monitores")
    public ResponseEntity<String> listarMonitores() {
        return responder(php.forward(HttpMethod.GET, "/monitores", null));
    }

    @GetMapping("/monitores/{codigo}")
    public ResponseEntity<String> consultarMonitor(@PathVariable String codigo) {
        return responder(php.forward(HttpMethod.GET, "/monitores/{codigo}", null, validator.normalizarCodigo(codigo)));
    }

    @PostMapping("/monitores")
    public ResponseEntity<String> registrarMonitor(@RequestBody(required = false) String body) {
        JsonNode monitor = validator.validarCreacion(leerJson(body));
        return responder(php.forward(HttpMethod.POST, "/monitores", monitor));
    }

    @PutMapping("/monitores/{codigo}")
    public ResponseEntity<String> actualizarMonitor(@PathVariable String codigo,
                                                    @RequestBody(required = false) String body) {
        JsonNode cambios = validator.validarActualizacion(leerJson(body));
        return responder(php.forward(HttpMethod.PUT, "/monitores/{codigo}", cambios, validator.normalizarCodigo(codigo)));
    }

    @DeleteMapping("/monitores/{codigo}")
    public ResponseEntity<String> eliminarMonitor(@PathVariable String codigo) {
        return responder(php.forward(HttpMethod.DELETE, "/monitores/{codigo}", null, validator.normalizarCodigo(codigo)));
    }

    /** Body ausente o vacío → null (el validador responde "JSON inválido"); mal formado → 400. */
    private JsonNode leerJson(String body) {
        if (body == null || body.isBlank()) {
            return null;
        }
        try {
            return mapper.readTree(body);
        } catch (JsonProcessingException e) {
            throw new ApiException(400, "JSON inválido");
        }
    }

    /** Devuelve el código y el cuerpo de PHP tal cual; sin cuerpo (204) no se envía Content-Type (H5). */
    private static ResponseEntity<String> responder(ResponseEntity<String> respuestaPhp) {
        ResponseEntity.BodyBuilder r = ResponseEntity.status(respuestaPhp.getStatusCode());
        if (respuestaPhp.getBody() == null) {
            return r.build();
        }
        return r.contentType(JSON_UTF8).body(respuestaPhp.getBody());
    }
}
