FROM nginx:1.27-alpine
# Dirección del controlador Java. En un solo equipo es el nombre del servicio en Docker; en el
# despliegue distribuido se puede cambiar sin reconstruir la imagen (ver despliegue/README.md)
ENV JAVA_SERVICE_URL=http://java-controller:8081
# La imagen oficial convierte las plantillas de /etc/nginx/templates en archivos de conf.d al arrancar
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY index.html styles.css api.js app.js /usr/share/nginx/html/
EXPOSE 80
