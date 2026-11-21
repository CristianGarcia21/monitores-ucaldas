# Despliegue distribuido en tres equipos

Cómo correr el sistema repartido en tres computadores de la misma red: la capa de presentación en uno,
el intermediario PHP en otro y la capa de lógica y datos en un tercero. Para correrlo todo en un solo
equipo, sigue usando el `docker-compose.yml` de la raíz ([README principal](../README.md)).

El diagrama de despliegue y la justificación de esta distribución están en
[docs/despliegue.md](../docs/despliegue.md).

## Distribución

```
            PC1 · Presentación                  PC2 · Intermediario           PC3 · Lógica y datos
  ┌──────────────────────────────────┐      ┌──────────────────────┐      ┌───────────────────────────┐
  │ nginx (interfaz) ─► Java          │ HTTP │ PHP                  │ HTTP │ Python ─► PostgreSQL       │
  │ :8080              :8081 (local)  │─────►│ :8082                │─────►│ :8083      :5432 (local)   │
  └──────────────────────────────────┘      └──────────────────────┘      └───────────────────────────┘
        ▲ navegadores de la red
```

| Equipo | Capa | Servicios | Archivo | Puerto abierto a la red | Necesita la IP de |
|--------|------|-----------|---------|-------------------------|-------------------|
| **PC1** | Presentación | Interfaz (nginx) y controlador Java | `pc1-presentacion.yml` | 8080 (usuarios) | PC2 |
| **PC2** | Intermediario | Servicio PHP | `pc2-intermediario.yml` | 8082 (lo llama Java) | PC3 |
| **PC3** | Lógica y datos | Servicio Python y PostgreSQL | `pc3-logica.yml` | 8083 (lo llama PHP) | — |

- **Java queda en el PC1** porque es el controlador de la interfaz: recibe sus solicitudes y valida la
  información básica antes de enviarla al intermediario.
- **La base de datos queda en el PC3**, junto a Python, porque solo Python se conecta a ella (A3). Sus
  puertos (5432) y el de Java (8081) solo se publican en `127.0.0.1`: no se ven desde la red.
- El código no cambia: cada servicio ya lee la dirección del siguiente de una variable de entorno
  (`PHP_SERVICE_URL`, `PYTHON_SERVICE_URL`). Solo cambia el valor: la IP del otro equipo en vez del
  nombre del contenedor.

## Requisitos

- Los tres equipos en la **misma red** (el mismo Wi-Fi, un router o el punto de acceso de un celular).
  Algunas redes institucionales aíslan a los equipos entre sí: si no se ven, usen un router o un
  celular como punto de acceso.
- **Docker Desktop** abierto y **el repositorio clonado** en los tres equipos.
- Conocer la IP de cada equipo y que **no cambie** durante la presentación.

## Paso 1: anotar la IP de cada equipo

En cada equipo:

```powershell
ipconfig        # Windows: "Dirección IPv4" del adaptador Wi-Fi o Ethernet (ej. 192.168.1.20)
```

```bash
ip -4 addr      # Linux   ·   en Mac: ipconfig getifaddr en0
```

No uses las IP de adaptadores virtuales (`vEthernet`, `VirtualBox`, `172.x` de WSL).

**No hace falta configurar una IP fija a mano.** La IP que el router asigna sola (DHCP) sirve, con dos
condiciones:

- Se anota **el mismo día**, después de conectarse a la red. Si un equipo se reconecta o cambia de red,
  su IP puede cambiar.
- Solo dos equipos necesitan conocer una IP ajena: el PC1 la del PC2 y el PC2 la del PC3. El PC3 no
  necesita ninguna, y los usuarios solo necesitan la del PC1 para abrir la aplicación.

Si una IP cambia, basta con actualizar `despliegue/.env` en el equipo que la usa y repetir el `up -d`
(paso 4). Para evitarlo, se puede reservar la IP de cada equipo en el router ("reserva DHCP"), si se
tiene acceso a él.

> ¿Por qué no usar el nombre del equipo (`http://PC-JUAN:8082`)? Dentro de los contenedores de Docker
> los nombres de equipo de Windows no siempre se resuelven. La IP funciona siempre.

## Paso 2: abrir el puerto en el firewall

Windows bloquea por defecto las conexiones que llegan desde otros equipos. En **PowerShell como
administrador**, cada equipo abre **solo su puerto**:

```powershell
# PC1
New-NetFirewallRule -DisplayName "Monitores PC1 interfaz" -Direction Inbound -Protocol TCP -LocalPort 8080 -Action Allow
# PC2
New-NetFirewallRule -DisplayName "Monitores PC2 PHP" -Direction Inbound -Protocol TCP -LocalPort 8082 -Action Allow
# PC3
New-NetFirewallRule -DisplayName "Monitores PC3 Python" -Direction Inbound -Protocol TCP -LocalPort 8083 -Action Allow
```

Si Windows marcó la red como **Pública**, cámbiala a **Privada** (Configuración → Red e Internet →
propiedades de la red), o agrega `-Profile Any` al comando. Para quitar la regla al terminar:
`Remove-NetFirewallRule -DisplayName "Monitores PC1 interfaz"`.

> Opcional, más seguro: limitar cada regla al único equipo que debe llamar, con
> `-RemoteAddress <IP del PC1>` en el PC2 y `-RemoteAddress <IP del PC2>` en el PC3.

## Paso 3: configurar `despliegue/.env`

En el **PC1** y el **PC2**, copia el ejemplo y pon las IP reales:

```bash
cp despliegue/.env.example despliegue/.env       # PowerShell: Copy-Item despliegue\.env.example despliegue\.env
```

| Equipo | Variable que debe tener `despliegue/.env` | Ejemplo |
|--------|-------------------------------------------|---------|
| PC1 | `PHP_SERVICE_URL=http://<IP del PC2>:8082` | `http://192.168.1.20:8082` |
| PC2 | `PYTHON_SERVICE_URL=http://<IP del PC3>:8083` | `http://192.168.1.30:8083` |
| PC3 | Ninguna (solo si hay que cambiar un puerto) | — |

- Las URL van **sin** `/` al final.
- Si falta la variable, Docker Compose se detiene con un mensaje que dice cuál es.
- `.env` no se sube al repositorio.

## Paso 4: levantar en orden (PC3 → PC2 → PC1)

Desde la raíz del repositorio de cada equipo:

```bash
# PC3 · lógica y datos
docker compose -f despliegue/pc3-logica.yml up --build -d --wait

# PC2 · intermediario
docker compose -f despliegue/pc2-intermediario.yml up --build -d --wait

# PC1 · presentación
docker compose -f despliegue/pc1-presentacion.yml up --build -d --wait
```

El orden evita errores en las primeras peticiones, pero no es obligatorio. Si un equipo arranca antes que
el siguiente, solo responde 502 hasta que el otro esté arriba.

## Paso 5: verificar

Cada salto se prueba desde el equipo que hace la llamada:

```bash
# En el PC2: ¿llega al Python del PC3?
curl http://<IP del PC3>:8083/health      # {"service":"python-service","status":"ok"}

# En el PC1: ¿llega al PHP del PC2?
curl http://<IP del PC2>:8082/health      # {"service":"php-service","status":"ok"}

# En el PC1: la cadena completa
./scripts/smoke-test.sh                    # PowerShell: .\scripts\smoke-test.ps1
```

- El smoke test debe dar **14 pasos correctos y 1 omitido**. Omite la revisión de los logs de PHP,
  porque PHP no corre en el PC1.
- Para hacer esa revisión a mano, ejecuta en el PC2:
  `docker compose -f despliegue/pc2-intermediario.yml logs php-service`. Un `POST` sin nombre no debe
  aparecer, porque lo rechaza Java.

Por último, desde cualquier equipo de la red, abre **`http://<IP del PC1>:8080`**.

## Operación

| Acción | Comando (en el equipo correspondiente) |
|--------|----------------------------------------|
| Ver el estado | `docker compose -f despliegue/pcN-....yml ps` |
| Ver los logs en vivo | `docker compose -f despliegue/pcN-....yml logs -f <servicio>` |
| Detener | `docker compose -f despliegue/pcN-....yml down` |
| Reiniciar la BD desde cero (PC3) | `docker compose -f despliegue/pc3-logica.yml down -v` y volver a levantar |
| Cambió la IP de otro equipo | Editar `despliegue/.env` y repetir el `up -d` (no hace falta `--build`) |

Cada servicio sigue escribiendo una línea por petición (`[servicio] MÉTODO RUTA -> STATUS (ms)`), así
que con los logs de los tres equipos se sigue una petición de punta a punta.

## Solución de problemas

| Síntoma | Causa probable | Qué revisar |
|---------|----------------|-------------|
| La interfaz muestra `Servicio PHP no disponible` (502) | El PC1 no alcanza al PC2 | `PHP_SERVICE_URL` del PC1, firewall del PC2 (8082), que el PC2 esté arriba: `curl` del paso 5 |
| La interfaz muestra `Servicio de persistencia no disponible` (502) | El PC2 no alcanza al PC3 | `PYTHON_SERVICE_URL` del PC2, firewall del PC3 (8083), que el PC3 esté arriba |
| La interfaz muestra `Base de datos no disponible` (503) | Python no alcanza a PostgreSQL en el PC3 | `docker compose -f despliegue/pc3-logica.yml ps`: `monitores-db` debe estar `healthy` |
| Ningún `curl` entre equipos responde | Red con aislamiento de clientes o perfil Público | Probar con un punto de acceso propio; poner la red como Privada |
| `port is already allocated` | Ese puerto está ocupado en ese equipo | Cambiarlo en `despliegue/.env` (ej. `PHP_PORT=9082`) y actualizar la URL en el equipo que lo llama |

## Probar la distribución en un solo equipo

Para ensayar antes de la presentación, los tres archivos se pueden levantar en el mismo equipo. Cada uno
es un proyecto de Compose distinto, y se comunican por la IP de red del equipo, igual que entre
computadores:

```bash
docker compose down        # detener el despliegue normal: usan los mismos puertos y nombres
# despliegue/.env con la IP propia en las dos URL, por ejemplo:
#   PHP_SERVICE_URL=http://192.168.1.20:8082
#   PYTHON_SERVICE_URL=http://192.168.1.20:8083
docker compose -f despliegue/pc3-logica.yml up --build -d --wait
docker compose -f despliegue/pc2-intermediario.yml up --build -d --wait
docker compose -f despliegue/pc1-presentacion.yml up --build -d --wait
./scripts/smoke-test.sh
```

## Qué hace cada integrante

| Integrante | Equipo | Tarea para el despliegue |
|------------|--------|--------------------------|
| Valentina Galvis | — | Dueña de `despliegue/`. Revisar este PR y coordinar las IP, el orden de arranque y la red el día de la presentación |
| Tania Botina | PC1 | Revisar el cambio de `frontend/` (`nginx.conf.template` y `JAVA_SERVICE_URL`). La interfaz no cambia: sigue llamando a `/api` |
| Cristian Garcia | PC1 | Nada en el código: Java ya lee `PHP_SERVICE_URL`. Levantar el PC1 y aprobar el cambio de contrato (§2) |
| Juan Fernando García | PC2 | Nada en el código: PHP ya lee `PYTHON_SERVICE_URL` y escucha en `0.0.0.0`. Levantar el PC2 y abrir el 8082 |
| Juan Diego Henao Quintero | PC3 | Nada en el código: Python ya lee `DB_HOST` y escucha en `0.0.0.0`. Levantar el PC3 y abrir el 8083 |
| Jose Daniel Restrepo Orozco | — | Agregar el diagrama de despliegue (`docs/despliegue.md`) al documento final |
