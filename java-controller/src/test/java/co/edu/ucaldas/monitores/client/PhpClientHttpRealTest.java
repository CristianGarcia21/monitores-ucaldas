package co.edu.ucaldas.monitores.client;

import static org.assertj.core.api.Assertions.assertThat;

import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpMethod;
import org.springframework.http.ResponseEntity;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;

/**
 * Pruebas con una conexión HTTP real (la misma configuración que en producción).
 * MockRestServiceServer reemplaza la conexión y no detecta fallos del transporte: así se escapó el
 * 502 que aparecía cuando PHP respondía un error (409, 400, 404) a un POST o PUT con cuerpo.
 */
class PhpClientHttpRealTest {

    private static final String ERROR_409 = "{\"error\":\"Ya existe un monitor con el código M-001\"}";
    private static final String ERROR_404 = "{\"error\":\"No existe un monitor con el código X-9\"}";

    private HttpServer php;
    private PhpClient client;
    private final ObjectNode cuerpo = new ObjectMapper().createObjectNode().put("codigo", "M-001");

    @BeforeEach
    void iniciarPhpFalso() throws IOException {
        php = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        // Imita al servidor embebido de PHP: sin Content-Length y cerrando la conexión
        php.createContext("/monitores", ex -> {
            ex.getRequestBody().readAllBytes();
            switch (ex.getRequestMethod()) {
                case "POST" -> responder(ex, 409, ERROR_409);
                case "PUT" -> responder(ex, 404, ERROR_404);
                default -> responder(ex, 200, "[]");
            }
        });
        php.start();
        String url = "http://127.0.0.1:" + php.getAddress().getPort();
        client = new PhpClient(new PhpClientConfig().phpRestClient(url));
    }

    @AfterEach
    void detenerPhpFalso() {
        php.stop(0);
    }

    private static void responder(HttpExchange ex, int estado, String json) throws IOException {
        byte[] bytes = json.getBytes(StandardCharsets.UTF_8);
        ex.getResponseHeaders().set("Content-Type", "application/json; charset=utf-8");
        ex.getResponseHeaders().set("Connection", "close");
        ex.sendResponseHeaders(estado, 0); // 0 = sin Content-Length (chunked), como PHP
        try (OutputStream o = ex.getResponseBody()) {
            o.write(bytes);
        }
    }

    @Test
    void errorDePhpEnPostConCuerpoSePropagaYNoSeConvierteEn502() {
        ResponseEntity<String> r = client.forward(HttpMethod.POST, "/monitores", cuerpo);

        assertThat(r.getStatusCode().value()).isEqualTo(409);
        assertThat(r.getBody()).isEqualTo(ERROR_409);
    }

    @Test
    void errorDePhpEnPutConCuerpoSePropagaYNoSeConvierteEn502() {
        ResponseEntity<String> r = client.forward(HttpMethod.PUT, "/monitores/{codigo}", cuerpo, "X-9");

        assertThat(r.getStatusCode().value()).isEqualTo(404);
        assertThat(r.getBody()).isEqualTo(ERROR_404);
    }

    @Test
    void getSinCuerpoSigueFuncionando() {
        ResponseEntity<String> r = client.forward(HttpMethod.GET, "/monitores", null);

        assertThat(r.getStatusCode().value()).isEqualTo(200);
        assertThat(r.getBody()).isEqualTo("[]");
    }
}
