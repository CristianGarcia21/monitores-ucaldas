package co.edu.ucaldas.monitores.validation;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;

import co.edu.ucaldas.monitores.exception.ApiException;

/** Reglas de normalización y validación del contrato §6 y mensajes del catálogo §7. */
class MonitorValidatorTest {

    private final ObjectMapper mapper = new ObjectMapper();
    private final MonitorValidator validator = new MonitorValidator(mapper);

    private JsonNode json(String raw) throws Exception {
        return mapper.readTree(raw);
    }

    private static final String VALIDO =
            "{\"codigo\":\"M-001\",\"nombre\":\"Ana López\",\"correo\":\"ana@ucaldas.edu.co\",\"materia_id\":1}";

    private void assertError400(String body, String mensaje) {
        assertThatThrownBy(() -> validator.validarCreacion(json(body)))
                .isInstanceOf(ApiException.class)
                .hasMessage(mensaje)
                .extracting("status").isEqualTo(400);
    }

    // ---------------------------------------------------------------- normalización (§6.1)

    @Test
    void normalizaCodigoNombreYCorreo() throws Exception {
        ObjectNode r = validator.validarCreacion(json(
                "{\"codigo\":\"  m-001 \",\"nombre\":\" Ana   María  López \",\"correo\":\" Ana@UCaldas.edu.CO \",\"materia_id\":1}"));

        assertThat(r.get("codigo").asText()).isEqualTo("M-001");
        assertThat(r.get("nombre").asText()).isEqualTo("Ana María López");
        assertThat(r.get("correo").asText()).isEqualTo("ana@ucaldas.edu.co");
        assertThat(r.get("materia_id").asInt()).isEqualTo(1);
    }

    @Test
    void descartaCamposQueNoEstanEnElContrato() throws Exception {
        ObjectNode r = validator.validarCreacion(json(
                "{\"codigo\":\"M-001\",\"nombre\":\"Ana López\",\"correo\":\"ana@ucaldas.edu.co\",\"materia_id\":1,"
                        + "\"materia_nombre\":\"X\",\"hack\":true}"));

        assertThat(r.properties()).extracting(e -> e.getKey())
                .containsExactly("codigo", "nombre", "correo", "materia_id");
    }

    @Test
    void normalizarCodigoDeRutaQuitaEspaciosYPasaAMayusculas() {
        assertThat(validator.normalizarCodigo(" m-001 ")).isEqualTo("M-001");
    }

    // ---------------------------------------------------------------- E01 JSON inválido

    @ParameterizedTest
    @ValueSource(strings = {"[]", "\"texto\"", "5", "null"})
    void bodyQueNoEsObjetoEsJsonInvalido(String body) {
        assertError400(body, "JSON inválido");
    }

    @Test
    void bodyAusenteEsJsonInvalido() {
        assertThatThrownBy(() -> validator.validarCreacion(null))
                .isInstanceOf(ApiException.class).hasMessage("JSON inválido");
    }

    // ---------------------------------------------------------------- código (E02, E03)

    @ParameterizedTest
    @ValueSource(strings = {
            "{\"nombre\":\"Ana López\",\"correo\":\"ana@ucaldas.edu.co\",\"materia_id\":1}",
            "{\"codigo\":null,\"nombre\":\"Ana López\",\"correo\":\"ana@ucaldas.edu.co\",\"materia_id\":1}",
            "{\"codigo\":\"   \",\"nombre\":\"Ana López\",\"correo\":\"ana@ucaldas.edu.co\",\"materia_id\":1}"})
    void codigoVacioEsObligatorio(String body) {
        assertError400(body, "El código es obligatorio");
    }

    @ParameterizedTest
    @ValueSource(strings = {"M 001", "MÑ-1", "M_001", "ABCDEFGHIJKLMNOPQRSTU"})
    void codigoConFormatoInvalido(String codigo) {
        assertError400("{\"codigo\":\"" + codigo + "\",\"nombre\":\"Ana López\",\"correo\":\"ana@ucaldas.edu.co\",\"materia_id\":1}",
                "El código solo puede tener letras, números y guiones (máximo 20 caracteres)");
    }

    @Test
    void codigoDeVeinteCaracteresEsValido() throws Exception {
        ObjectNode r = validator.validarCreacion(json(
                "{\"codigo\":\"ABCDEFGHIJKLMNOPQRST\",\"nombre\":\"Ana López\",\"correo\":\"ana@ucaldas.edu.co\",\"materia_id\":1}"));
        assertThat(r.get("codigo").asText()).hasSize(20);
    }

    // ---------------------------------------------------------------- nombre (E04, E05)

    @Test
    void nombreVacioEsObligatorio() {
        assertError400("{\"codigo\":\"M-001\",\"nombre\":\"  \",\"correo\":\"ana@ucaldas.edu.co\",\"materia_id\":1}",
                "El nombre es obligatorio");
    }

    @Test
    void nombreDeDosCaracteresEsMuyCorto() {
        assertError400("{\"codigo\":\"M-001\",\"nombre\":\"Al\",\"correo\":\"ana@ucaldas.edu.co\",\"materia_id\":1}",
                "El nombre debe tener entre 3 y 150 caracteres");
    }

    @Test
    void nombreDe151CaracteresEsMuyLargo() {
        assertError400("{\"codigo\":\"M-001\",\"nombre\":\"" + "a".repeat(151) + "\",\"correo\":\"ana@ucaldas.edu.co\",\"materia_id\":1}",
                "El nombre debe tener entre 3 y 150 caracteres");
    }

    // ---------------------------------------------------------------- correo (E06, E07, E08)

    @Test
    void correoVacioEsObligatorio() {
        assertError400("{\"codigo\":\"M-001\",\"nombre\":\"Ana López\",\"materia_id\":1}", "El correo es obligatorio");
    }

    @ParameterizedTest
    @ValueSource(strings = {"a@b", "ana.ucaldas.edu.co", "ana@@ucaldas.co", "ana @ucaldas.co"})
    void correoConFormatoInvalido(String correo) {
        assertError400("{\"codigo\":\"M-001\",\"nombre\":\"Ana López\",\"correo\":\"" + correo + "\",\"materia_id\":1}",
                "El correo no es válido");
    }

    @Test
    void correoDe151CaracteresEsMuyLargo() {
        String correo = "a".repeat(140) + "@ucaldas.co"; // 151 caracteres
        assertError400("{\"codigo\":\"M-001\",\"nombre\":\"Ana López\",\"correo\":\"" + correo + "\",\"materia_id\":1}",
                "El correo debe tener máximo 150 caracteres");
    }

    // ---------------------------------------------------------------- materia (E09)

    @ParameterizedTest
    @ValueSource(strings = {"", ",\"materia_id\":null", ",\"materia_id\":\"1\"", ",\"materia_id\":1.5",
            ",\"materia_id\":0", ",\"materia_id\":-3", ",\"materia_id\":true"})
    void materiaAusenteOInvalidaEsObligatoria(String materia) {
        assertError400("{\"codigo\":\"M-001\",\"nombre\":\"Ana López\",\"correo\":\"ana@ucaldas.edu.co\"" + materia + "}",
                "La materia es obligatoria");
    }

    // ---------------------------------------------------------------- orden (§6.3)

    @Test
    void conVariosErroresRespondeElPrimeroSegunElOrdenDelContrato() {
        assertError400("{\"codigo\":\"M-001\",\"nombre\":\"\",\"correo\":\"malo\"}", "El nombre es obligatorio");
    }

    // ---------------------------------------------------------------- actualización

    @Test
    void actualizacionNoExigeCodigoYLoDescartaSiViene() throws Exception {
        ObjectNode r = validator.validarActualizacion(json(
                "{\"codigo\":\"OTRO\",\"nombre\":\"Ana López\",\"correo\":\"ANA@ucaldas.edu.co\",\"materia_id\":2}"));

        assertThat(r.properties()).extracting(e -> e.getKey()).containsExactly("nombre", "correo", "materia_id");
        assertThat(r.get("correo").asText()).isEqualTo("ana@ucaldas.edu.co");
    }

    @Test
    void actualizacionExigeLosTresCamposEditables() {
        assertThatThrownBy(() -> validator.validarActualizacion(json("{\"nombre\":\"Ana López\",\"correo\":\"ana@ucaldas.edu.co\"}")))
                .isInstanceOf(ApiException.class).hasMessage("La materia es obligatoria");
    }

    @Test
    void cuerpoValidoNoLanzaError() throws Exception {
        assertThat(validator.validarCreacion(json(VALIDO))).isNotNull();
    }
}
