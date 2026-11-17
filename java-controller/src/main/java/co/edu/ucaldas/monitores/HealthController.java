package co.edu.ucaldas.monitores;

import java.util.Map;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Esqueleto inicial: solo expone /health.
 * Implementar MonitorController con los endpoints de docs/api-contract.md (sección Java).
 */
@RestController
public class HealthController {

    @GetMapping("/health")
    public Map<String, String> health() {
        return Map.of("service", "java-controller", "status", "ok");
    }
}
