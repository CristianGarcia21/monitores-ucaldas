package co.edu.ucaldas.monitores.client;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.content;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withException;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withStatus;

import java.io.IOException;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;

import co.edu.ucaldas.monitores.exception.ApiException;

/** El cliente reenvía a PHP y devuelve el mismo código y cuerpo (contrato H7). */
class PhpClientTest {

    private static final String PHP = "http://php-service:8082";

    private MockRestServiceServer php;
    private PhpClient client;

    @BeforeEach
    void setUp() {
        RestClient.Builder builder = RestClient.builder().baseUrl(PHP);
        php = MockRestServiceServer.bindTo(builder).build();
        client = new PhpClient(builder.build());
    }

    @Test
    void getDevuelveElMismoCodigoYCuerpoQuePhp() {
        php.expect(requestTo(PHP + "/monitores")).andExpect(method(HttpMethod.GET))
                .andRespond(withStatus(HttpStatus.OK).contentType(MediaType.APPLICATION_JSON).body("[{\"codigo\":\"M-001\"}]"));

        ResponseEntity<String> r = client.forward(HttpMethod.GET, "/monitores", null);

        assertThat(r.getStatusCode().value()).isEqualTo(200);
        assertThat(r.getBody()).isEqualTo("[{\"codigo\":\"M-001\"}]");
        php.verify();
    }

    @Test
    void postEnviaElCuerpoComoJson() {
        ObjectNode body = new ObjectMapper().createObjectNode().put("codigo", "M-001");
        php.expect(requestTo(PHP + "/monitores")).andExpect(method(HttpMethod.POST))
                .andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_JSON))
                .andExpect(content().json("{\"codigo\":\"M-001\"}"))
                .andRespond(withStatus(HttpStatus.CREATED).contentType(MediaType.APPLICATION_JSON).body("{\"codigo\":\"M-001\"}"));

        ResponseEntity<String> r = client.forward(HttpMethod.POST, "/monitores", body);

        assertThat(r.getStatusCode().value()).isEqualTo(201);
        php.verify();
    }

    @Test
    void erroresDePhpSePropaganSinLanzarExcepcion() {
        String error = "{\"error\":\"Ya existe un monitor con el código M-001\"}";
        php.expect(requestTo(PHP + "/monitores"))
                .andRespond(withStatus(HttpStatus.CONFLICT).contentType(MediaType.APPLICATION_JSON).body(error));

        ResponseEntity<String> r = client.forward(HttpMethod.POST, "/monitores", new ObjectMapper().createObjectNode());

        assertThat(r.getStatusCode().value()).isEqualTo(409);
        assertThat(r.getBody()).isEqualTo(error);
    }

    @Test
    void respuesta204NoTieneCuerpo() {
        php.expect(requestTo(PHP + "/monitores/M-001")).andExpect(method(HttpMethod.DELETE))
                .andRespond(withStatus(HttpStatus.NO_CONTENT));

        ResponseEntity<String> r = client.forward(HttpMethod.DELETE, "/monitores/{codigo}", null, "M-001");

        assertThat(r.getStatusCode().value()).isEqualTo(204);
        assertThat(r.getBody()).isNull();
    }

    @Test
    void codigoDeRutaSeCodificaEnLaUrl() {
        php.expect(requestTo(PHP + "/monitores/A%20B")).andRespond(withStatus(HttpStatus.NOT_FOUND).body("{}"));

        client.forward(HttpMethod.GET, "/monitores/{codigo}", null, "A B");

        php.verify();
    }

    @Test
    void siPhpNoRespondeLanza502() {
        php.expect(requestTo(PHP + "/monitores")).andRespond(withException(new IOException("Connection refused")));

        assertThatThrownBy(() -> client.forward(HttpMethod.GET, "/monitores", null))
                .isInstanceOf(ApiException.class)
                .hasMessage("Servicio PHP no disponible")
                .extracting("status").isEqualTo(502);
    }
}
