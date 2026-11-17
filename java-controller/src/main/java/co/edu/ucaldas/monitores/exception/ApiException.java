package co.edu.ucaldas.monitores.exception;

/**
 * Error que el controlador Java responde por sí mismo (sin llamar a PHP).
 * El mensaje debe ser uno del catálogo de errores del contrato (§7).
 */
public class ApiException extends RuntimeException {

    private final int status;

    public ApiException(int status, String message) {
        super(message);
        this.status = status;
    }

    public int getStatus() {
        return status;
    }
}
