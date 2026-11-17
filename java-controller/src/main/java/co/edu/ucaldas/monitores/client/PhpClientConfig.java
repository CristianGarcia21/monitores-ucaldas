package co.edu.ucaldas.monitores.client;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.client.RestClient;

/** RestClient hacia PHP con la URL de PHP_SERVICE_URL y los timeouts del contrato (§11). */
@Configuration
public class PhpClientConfig {

    static final int CONNECT_TIMEOUT_MS = 3_000;
    static final int READ_TIMEOUT_MS = 10_000;

    @Bean
    public RestClient phpRestClient(@Value("${php.service.url}") String phpServiceUrl) {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(CONNECT_TIMEOUT_MS);
        factory.setReadTimeout(READ_TIMEOUT_MS);
        return RestClient.builder().baseUrl(phpServiceUrl).requestFactory(factory).build();
    }
}
