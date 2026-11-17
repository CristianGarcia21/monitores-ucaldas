package co.edu.ucaldas.monitores.client;

import java.nio.charset.StandardCharsets;

import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClient;

import com.fasterxml.jackson.databind.JsonNode;

import co.edu.ucaldas.monitores.exception.ApiException;

/**
 * Reenvía peticiones al servicio PHP y devuelve el mismo código y cuerpo que este responda
 * (contrato H7). Solo genera una respuesta propia si PHP no está disponible (E15).
 */
@Component
public class PhpClient {

    static final String PHP_NO_DISPONIBLE = "Servicio PHP no disponible";

    private final RestClient restClient;

    public PhpClient(RestClient phpRestClient) {
        this.restClient = phpRestClient;
    }

    /**
     * @param uriTemplate ruta relativa, ej. {@code /monitores/{codigo}} (las variables se codifican)
     * @param body        cuerpo JSON o {@code null} si la petición no lleva cuerpo
     */
    public ResponseEntity<String> forward(HttpMethod method, String uriTemplate, JsonNode body, Object... uriVars) {
        RestClient.RequestBodySpec request = restClient.method(method).uri(uriTemplate, uriVars);
        if (body != null) {
            request.contentType(MediaType.APPLICATION_JSON).body(body.toString().getBytes(StandardCharsets.UTF_8));
        }
        try {
            return request.exchange((req, res) -> {
                byte[] bytes = res.getBody().readAllBytes();
                String texto = bytes.length == 0 ? null : new String(bytes, StandardCharsets.UTF_8);
                return ResponseEntity.status(res.getStatusCode()).body(texto);
            });
        } catch (ResourceAccessException e) {
            throw new ApiException(502, PHP_NO_DISPONIBLE);
        }
    }
}
