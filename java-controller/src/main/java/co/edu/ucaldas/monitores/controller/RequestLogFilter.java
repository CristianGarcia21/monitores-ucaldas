package co.edu.ucaldas.monitores.controller;

import java.io.IOException;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

/** Una línea por petición: [java-controller] MÉTODO RUTA -> STATUS (ms)  (contrato §11, T2). */
@Component
public class RequestLogFilter extends OncePerRequestFilter {

    private static final Logger log = LoggerFactory.getLogger(RequestLogFilter.class);

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        long inicio = System.currentTimeMillis();
        try {
            chain.doFilter(request, response);
        } finally {
            log.info("[java-controller] {} {} -> {} ({} ms)", request.getMethod(), request.getRequestURI(),
                    response.getStatus(), System.currentTimeMillis() - inicio);
        }
    }
}
