package co.edu.ucaldas.monitores.controller;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.content;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withException;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withStatus;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.io.IOException;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.test.system.CapturedOutput;
import org.springframework.boot.test.system.OutputCaptureExtension;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Primary;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import org.springframework.web.client.RestClient;

/**
 * Pruebas de punta a punta del controlador: petición HTTP real a Spring MVC y PHP simulado.
 * Cubre los endpoints del contrato §8 y los errores que genera Java (§7).
 */
@SpringBootTest(properties = "php.service.url=http://php-mock")
@AutoConfigureMockMvc
@ExtendWith(OutputCaptureExtension.class)
class MonitorControllerTest {

    private static final String PHP = "http://php-mock";
    private static final String JSON = "application/json";
    private static final String MONITOR =
            "{\"codigo\":\"M-001\",\"nombre\":\"Ana López\",\"correo\":\"ana@ucaldas.edu.co\",\"materia_id\":1,"
                    + "\"materia_nombre\":\"Ingeniería de Software III\"}";

    @TestConfiguration
    static class PhpSimulado {
        private final RestClient.Builder builder = RestClient.builder().baseUrl(PHP);

        @Bean
        MockRestServiceServer php() {
            return MockRestServiceServer.bindTo(builder).build();
        }

        @Bean
        @Primary
        RestClient phpRestClientSimulado(MockRestServiceServer php) {
            return builder.build();
        }
    }

    @Autowired
    private MockMvc mvc;

    @Autowired
    private MockRestServiceServer php;

    @BeforeEach
    void reset() {
        php.reset();
    }

    @AfterEach
    void verificarPhp() {
        php.verify();
    }

    // ---------------------------------------------------------------- consultas

    @Test
    void listarMateriasReenviaAPhp() throws Exception {
        String materias = "[{\"id\":1,\"codigo\":\"SW3\",\"nombre\":\"Ingeniería de Software III\"}]";
        php.expect(requestTo(PHP + "/materias")).andExpect(method(HttpMethod.GET))
                .andRespond(withStatus(HttpStatus.OK).contentType(MediaType.APPLICATION_JSON).body(materias));

        MvcResult r = mvc.perform(get("/materias"))
                .andExpect(status().isOk())
                .andExpect(header().string("Content-Type", "application/json;charset=UTF-8"))
                .andReturn();

        assertThat(r.getResponse().getContentAsString()).isEqualTo(materias);
    }

    @Test
    void listarMonitoresReenviaAPhp() throws Exception {
        php.expect(requestTo(PHP + "/monitores")).andExpect(method(HttpMethod.GET))
                .andRespond(withStatus(HttpStatus.OK).contentType(MediaType.APPLICATION_JSON).body("[" + MONITOR + "]"));

        mvc.perform(get("/monitores")).andExpect(status().isOk()).andExpect(jsonPath("$[0].codigo").value("M-001"));
    }

    @Test
    void consultarMonitorNormalizaElCodigoDeLaRuta() throws Exception {
        php.expect(requestTo(PHP + "/monitores/M-001")).andExpect(method(HttpMethod.GET))
                .andRespond(withStatus(HttpStatus.OK).contentType(MediaType.APPLICATION_JSON).body(MONITOR));

        mvc.perform(get("/monitores/m-001")).andExpect(status().isOk());
    }

    @Test
    void monitorInexistenteSePropagaComo404DePython() throws Exception {
        String error = "{\"error\":\"No existe un monitor con el código X-9\"}";
        php.expect(requestTo(PHP + "/monitores/X-9"))
                .andRespond(withStatus(HttpStatus.NOT_FOUND).contentType(MediaType.APPLICATION_JSON).body(error));

        MvcResult r = mvc.perform(get("/monitores/X-9")).andExpect(status().isNotFound()).andReturn();

        assertThat(r.getResponse().getContentAsString()).isEqualTo(error);
    }

    // ---------------------------------------------------------------- registrar

    @Test
    void registrarReenviaElCuerpoNormalizado() throws Exception {
        php.expect(requestTo(PHP + "/monitores")).andExpect(method(HttpMethod.POST))
                .andExpect(content().json(
                        "{\"codigo\":\"M-001\",\"nombre\":\"Ana López\",\"correo\":\"ana@ucaldas.edu.co\",\"materia_id\":1}", true))
                .andRespond(withStatus(HttpStatus.CREATED).contentType(MediaType.APPLICATION_JSON).body(MONITOR));

        mvc.perform(post("/monitores").contentType(JSON)
                        .content("{\"codigo\":\" m-001\",\"nombre\":\"Ana  López\",\"correo\":\"ANA@ucaldas.edu.co\",\"materia_id\":1}"))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.materia_nombre").value("Ingeniería de Software III"));
    }

    @Test
    void registrarConDatosInvalidosResponde400SinLlamarAPhp() throws Exception {
        // sin expectativas en el mock: si Java llamara a PHP, php.verify() fallaría
        mvc.perform(post("/monitores").contentType(JSON)
                        .content("{\"codigo\":\"M-001\",\"correo\":\"ana@ucaldas.edu.co\",\"materia_id\":1}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error").value("El nombre es obligatorio"))
                .andExpect(jsonPath("$.length()").value(1));
    }

    @Test
    void registrarConJsonMalFormadoResponde400() throws Exception {
        mvc.perform(post("/monitores").contentType(JSON).content("{\"codigo\":"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error").value("JSON inválido"));
    }

    @Test
    void registrarSinCuerpoResponde400() throws Exception {
        mvc.perform(post("/monitores").contentType(JSON))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error").value("JSON inválido"));
    }

    @Test
    void codigoDuplicadoSePropagaComo409() throws Exception {
        String error = "{\"error\":\"Ya existe un monitor con el código M-001\"}";
        php.expect(requestTo(PHP + "/monitores"))
                .andRespond(withStatus(HttpStatus.CONFLICT).contentType(MediaType.APPLICATION_JSON).body(error));

        MvcResult r = mvc.perform(post("/monitores").contentType(JSON)
                        .content("{\"codigo\":\"M-001\",\"nombre\":\"Ana López\",\"correo\":\"ana@ucaldas.edu.co\",\"materia_id\":1}"))
                .andExpect(status().isConflict()).andReturn();

        assertThat(r.getResponse().getContentAsString()).isEqualTo(error);
    }

    // ---------------------------------------------------------------- actualizar y eliminar

    @Test
    void actualizarReenviaSinElCodigoDelCuerpo() throws Exception {
        php.expect(requestTo(PHP + "/monitores/M-001")).andExpect(method(HttpMethod.PUT))
                .andExpect(content().json("{\"nombre\":\"Ana López\",\"correo\":\"ana@ucaldas.edu.co\",\"materia_id\":2}", true))
                .andRespond(withStatus(HttpStatus.OK).contentType(MediaType.APPLICATION_JSON).body(MONITOR));

        mvc.perform(put("/monitores/m-001").contentType(JSON)
                        .content("{\"codigo\":\"OTRO\",\"nombre\":\"Ana López\",\"correo\":\"ana@ucaldas.edu.co\",\"materia_id\":2}"))
                .andExpect(status().isOk());
    }

    @Test
    void actualizarConDatosInvalidosResponde400SinLlamarAPhp() throws Exception {
        mvc.perform(put("/monitores/M-001").contentType(JSON)
                        .content("{\"nombre\":\"Ana López\",\"correo\":\"a@b\",\"materia_id\":2}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error").value("El correo no es válido"));
    }

    @Test
    void eliminarResponde204SinCuerpo() throws Exception {
        php.expect(requestTo(PHP + "/monitores/M-001")).andExpect(method(HttpMethod.DELETE))
                .andRespond(withStatus(HttpStatus.NO_CONTENT));

        MvcResult r = mvc.perform(delete("/monitores/M-001")).andExpect(status().isNoContent()).andReturn();

        assertThat(r.getResponse().getContentAsString()).isEmpty();
        assertThat(r.getResponse().getContentType()).isNull();
    }

    // ---------------------------------------------------------------- errores propios de Java

    @Test
    void phpCaidoResponde502() throws Exception {
        php.expect(requestTo(PHP + "/monitores")).andRespond(withException(new IOException("Connection refused")));

        mvc.perform(get("/monitores"))
                .andExpect(status().isBadGateway())
                .andExpect(jsonPath("$.error").value("Servicio PHP no disponible"));
    }

    @Test
    void errorInesperadoResponde500SinExponerDetalles() throws Exception {
        php.expect(requestTo(PHP + "/monitores")).andRespond(request -> {
            throw new IllegalStateException("detalle interno secreto");
        });

        MvcResult r = mvc.perform(get("/monitores"))
                .andExpect(status().isInternalServerError())
                .andExpect(jsonPath("$.error").value("Error interno del servidor"))
                .andReturn();

        assertThat(r.getResponse().getContentAsString()).doesNotContain("secreto");
    }

    @Test
    void rutaInexistenteResponde404() throws Exception {
        mvc.perform(get("/estudiantes"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error").value("Ruta no encontrada"));
    }

    @Test
    void rutaConBarraFinalResponde404() throws Exception {
        mvc.perform(get("/monitores/"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error").value("Ruta no encontrada"));
    }

    @Test
    void metodoNoSoportadoResponde405() throws Exception {
        mvc.perform(delete("/monitores"))
                .andExpect(status().isMethodNotAllowed())
                .andExpect(jsonPath("$.error").value("Método no permitido"));
    }

    @Test
    void healthSigueRespondiendo() throws Exception {
        mvc.perform(get("/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.service").value("java-controller"))
                .andExpect(jsonPath("$.status").value("ok"));
    }

    // ---------------------------------------------------------------- logs (§11)

    @Test
    void registraUnaLineaDeLogPorPeticion(CapturedOutput output) throws Exception {
        mvc.perform(get("/health"));

        assertThat(output.getOut()).containsPattern("\\[java-controller\\] GET /health -> 200 \\(\\d+ ms\\)");
    }
}
