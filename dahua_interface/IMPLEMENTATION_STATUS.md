# Estado de Implementación: Biometric Ingest v1

Fecha de referencia: **19 de marzo de 2026 (UTC)**.

## Resumen ejecutivo

Se implementó una infraestructura de ingesta biométrica **independiente de Odoo** en la misma EC2 `52.6.240.186`, reutilizando el PostgreSQL local pero en una base de datos separada: `biometric_ingest`.

La solución ya recibe eventos HTTP en el puerto público `60005`, los almacena primero en un spool durable local, luego los procesa con un worker y los persiste en PostgreSQL en capas separadas:

- request crudo
- evento normalizado
- estado de dispositivo
- cuarentena para eventos no resolubles
- outbox reservado para integración futura con Odoo

Odoo quedó **fuera del camino crítico** de la ingesta.

## Attendance Sync V1

Al 20 de marzo de 2026 también quedó implementada la primera fase de integración con asistencias Odoo:

- modulo Odoo: `hr_biometric_attendance_sync`
- servicio continuo: `attendance-sync-worker`
- fuente: `biometric_ingest.normalized_event`
- destino: `hr.biometric.event` y `hr.attendance`

La lógica activa en esta fase es provisional:

- solo procesa `access_control`
- requiere `UserID`
- busca empleado por `employee_number`
- aplica debounce de `90` segundos
- alterna `check_in` / `check_out`
- deja staging aun cuando el evento no cree asistencia
- mantiene autocierre al cambiar de día y deja listo el cierre nocturno configurado

Esta capa ya está desplegada en la EC2 y funcionando contra la base `devlyn_com` sin usar SQL directo sobre las tablas de Odoo.

Validacion formal del alcance Odoo:

- [ODOO_MODULE_VALIDATION_2026-03-20.md](ODOO_MODULE_VALIDATION_2026-03-20.md)

## Lo que se implementó

### 1. Edge HTTP público en `60005`

Se sustituyó el listener directo en `0.0.0.0:60005` por un edge `nginx` dedicado:

- escucha en `0.0.0.0:60005`
- proxya internamente a `127.0.0.1:60006`
- solo acepta `POST` para tráfico público
- responde `405` a métodos no permitidos como `GET`
- aplica límites básicos:
  - `client_max_body_size`
  - timeouts cortos
  - `limit_req`
  - `limit_conn`
- deja logs dedicados de edge en:
  - `/var/log/nginx/biometric_ingest_access.log`
  - `/var/log/nginx/biometric_ingest_error.log`

Archivo de configuración en repo:

- [biometric-ingest-60005.conf](../server_config/services/biometric_ingest/biometric-ingest-60005.conf)

### 2. Servicio de ingesta interno

Se creó un nuevo servicio FastAPI para la captura real:

- nombre lógico: `biometric-ingest`
- bind interno: `127.0.0.1:60006`
- recibe cualquier path
- clasifica eventos detectados
- genera `ingest_id`
- escribe primero a spool JSONL con `fsync`
- luego responde `200 OK`

Este servicio conserva el log operativo en:

- `/var/log/dahua_events.log`

pero ese log ya no es el almacenamiento primario, sino una salida de soporte operativo y debugging.

Archivo principal:

- [biometric_ingest.py](biometric_ingest.py)

### 3. Worker/router de eventos

Se creó un worker separado para sacar el procesamiento del request en línea:

- nombre lógico: `biometric-router-worker`
- consume el spool local
- persiste requests crudos en PostgreSQL
- normaliza eventos conocidos
- resuelve identidad de dispositivo por heartbeat reciente
- actualiza `device_registry` y `device_status`
- envía a `event_quarantine` lo no resoluble
- deja reservado `outbox_sync` para integración futura

Archivo principal:

- [biometric_router_worker.py](biometric_router_worker.py)

### 4. Base de datos dedicada

Se creó una base nueva en PostgreSQL local:

- base: `biometric_ingest`
- usuario app: `biometric_app`
- usuario readonly: `biometric_readonly`

Se mantuvo PostgreSQL solo en `127.0.0.1:5432`.

Se implementó esquema con particionado mensual para:

- `raw_request`
- `normalized_event`

Tablas implementadas:

- `raw_request`
- `normalized_event`
- `raw_request_registry`
- `normalized_event_registry`
- `device_registry`
- `device_status`
- `event_quarantine`
- `processing_error`
- `outbox_sync`

Archivo de esquema:

- [biometric_schema.sql](biometric_schema.sql)

Lógica DB:

- [biometric_db.py](biometric_db.py)

### 5. Despliegue automatizado

Se dejó un script de despliegue para reinstalar o replicar la infraestructura:

- crea usuario Linux `biometric`
- instala virtualenv y dependencias
- crea/actualiza roles y base PostgreSQL
- instala unidades `systemd`
- publica el edge en `nginx`
- deshabilita el listener anterior
- verifica `__health` interno y público

Archivo:

- [deploy_biometric_ingest.sh](../server_config/services/biometric_ingest/deploy_biometric_ingest.sh)

## Comportamiento implementado

### Eventos aceptados y probados

Se validó persistencia para:

- `POST /cgi-bin/api/autoRegist/connect`
- `POST /` con `Code=AccessControl`
- `POST /` con `Code=DoorStatus`
- payloads desconocidos

### Normalización actual

Tipos implementados:

- `heartbeat_connect`
- `access_control`
- `door_status`
- `unknown`

Mapeos activos:

- `Type: Entry` -> `entry`
- `Type: Exit` -> `exit`
- `Status: 1` -> `granted = true`
- `Status: 0` -> `granted = false`
- `RealUTC -> UTC -> CreateTime -> received_at_utc`

### Resolución de identidad

La identidad del dispositivo se resuelve así:

- heartbeat: usa `DeviceID`
- eventos de negocio con ruta `/d/<DeviceID>`: extrae `DeviceID` desde la ruta
- eventos de negocio sin ruta dedicada: correlación por `source_ip + listener_port + heartbeat reciente`
- ventana actual: `600` segundos

Orden de prioridad actual:

1. `heartbeat_payload`
2. `request_path_device_hint`
3. correlación por heartbeat reciente

### Política de cuarentena (actualizada 18/03/2026)

Los eventos `access_control` son registros válidos de auditoría biométrica y se normalizan **aunque no se resuelva el `device_id`** y **aunque el payload no incluya `DeviceID`**, siempre que el payload sí traiga `UserID`.

Solo van a cuarentena:

- `access_control` sin `UserID`
- `heartbeat_connect` sin `DeviceID`
- `door_status` sin resolución confiable de dispositivo
- eventos `unknown` sin datos interpretables

Esto aplica tanto para eventos nuevos como para reprocesamiento de cuarentena existente mediante `BiometricDatabase.reprocess_quarantine()`.

### Estado de dispositivos

El worker ya actualiza proyección viva en `device_status`:

- `last_seen_at`
- `last_heartbeat_at`
- `last_event_at`
- `last_event_kind`
- `status`
- `heartbeat_interval_seconds`
- `stale_since`
- `offline_since`
- `last_source_ip`

Esto deja lista la base para un dashboard futuro en Odoo.

## Estado operativo actual

Servicios activos:

- `biometric-ingest`
- `biometric-router-worker`
- `nginx`
- `odoo`
- `auth-gateway`

Servicio anterior:

- `dahua-listener`: **deshabilitado**

Puertos efectivos:

- público: `60005` por `nginx`
- interno: `60006` por `uvicorn`
- PostgreSQL: `127.0.0.1:5432`

Log operativo:

- `/var/log/dahua_events.log`

Logs nuevos:

- `/var/log/biometric-ingest/ingest.log`
- `/var/log/biometric-ingest/worker.log`

Spool:

- `/var/lib/biometric-ingest/spool`

Estado del worker:

- procesa spool y deja el offset en `/var/lib/biometric-ingest/state/router_state.json`

## Lo que se validó

Validaciones realizadas:

- `POST` al endpoint público devuelve `200`
- `GET /` público devuelve `405`
- los eventos de prueba sí se almacenan en `raw_request`
- los eventos `access_control` sí pasan a `normalized_event` aunque no haya heartbeat vigente ni `DeviceID`, siempre que traigan `UserID`
- `door_status` no atribuible y `unknown` sí pasan a `event_quarantine`
- `processing_error` quedó en `0` tras corregir los fallos iniciales de despliegue
- Odoo y `auth-gateway` siguieron activos tras el cambio
- el monitor operativo sigue funcionando:
  - [monitor_live.py](monitor_live.py)

### Validación con dispositivos reales (17/03/2026)

Se conectaron los primeros dispositivos biométricos reales:

| Dispositivo | Modelo | IP Origen | Primera conexión |
|---|---|---|---|
| `DEVLYN_A317_01` | DHI-ASI3204E | 187.236.152.204 | 17-Mar 21:57 UTC |
| `DEVLYN_A303_01` | DHI-ASI3204E | 187.236.152.204 | 17-Mar 22:02 UTC |

Usuarios observados con acceso concedido en `Door1`:

- LEO FIGUEROA (34054)
- ROSALBA TORNEZ PARRAL (19572)

### Validación del estándar de ruta por dispositivo (19/03/2026)

Se validó en producción el uso de `Carga automática` con ruta dedicada por dispositivo.

Caso validado:

- `DeviceID`: `DEVLYN_A303_01`
- `Ruta configurada`: `/d/DEVLYN_A303_01`

Eventos recibidos y resueltos correctamente:

- `POST /d/DEVLYN_A303_01` con `Code=AccessControl`
- `POST /d/DEVLYN_A303_01` con `Code=DoorStatus`

Resultado en normalización:

- `device_id_resolved = DEVLYN_A303_01`
- `identity_resolution = request_path_device_hint`

Esto deja formalmente validado que:

- la ruta personalizada sí llega al listener
- la ruta personalizada sí permite asociar eventos de negocio a un dispositivo específico
- esta estrategia es superior a depender solo de IP pública cuando existen NAT compartidos

Documento normativo asociado:

- [DEVICE_MAPPING_STANDARD.md](DEVICE_MAPPING_STANDARD.md)
- ALEXIS ARTURO QUIROZ MARTINEZ (98990)
- JOSE EDGAR MENDOZA QUIROZ (3852)
- OSCAR EDUARDO HERNANDEZ REYES (32832)
- MARIA DEL ROSARIO REYNA CASTAÑEDA (32638)
- DIEGO ARMANDO JIMENEZ CRUZ (24367)
- VICTOR ANDRES DE LA CRUZ ISLAS (31545)

Resultados:

- heartbeats recibidos y procesados correctamente
- eventos `access_control` y `door_status` normalizados
- resolución de identidad por heartbeat funcional
- eventos `access_control` con `UserID` que llegaron sin heartbeat vigente también normalizados correctamente
- `processing_error` en `0`

## Pendiente principal: retención y archivado

Sí: la **política de retención** todavía no está implementada como flujo operativo completo.

Qué sí existe hoy:

- particionado mensual en PostgreSQL para `raw_request` y `normalized_event`
- directorio preparado para archivo local:
  - `/var/lib/biometric-ingest/archive`
- worker de ingesta/normalización

Qué **no** existe todavía:

- job de archivado a JSONL comprimido
- rotación automática por antigüedad
- subida a S3
- purge de datos hot pasados los `90 días`
- política formal de recuperación desde archivo histórico

Conclusión:

- el **worker sí existe y sí procesa eventos**
- lo que **no** está definido/implementado aún es la **retención/archivo de largo plazo**

## Observaciones importantes

- `device_status` y `device_registry` ya sirven como base para dashboard de dispositivos vivos/no reportando.
- La integración con asistencias Odoo todavía **no** está conectada y sigue fuera de alcance.
- El modelo Odoo `biometric.device` no se reutilizó, porque hoy representa fingerprints de navegador y no hardware físico.
- El endpoint sigue siendo **HTTP** por limitación del dispositivo.
- Los dispositivos Dahua envían heartbeat con intervalo largo (~10 min); los eventos `access_control` con `UserID` no dependen del heartbeat para normalizarse.

## Changelog

### 17 de marzo de 2026

- Se conectaron los primeros dispositivos reales (`DEVLYN_A317_01`, `DEVLYN_A303_01`) desde sucursal Devlyn.
- Se aplicó un criterio intermedio: `access_control` con `UserID` pasó a normalizarse sin requerir resolución de `device_id`.
- Se agregó método `BiometricDatabase.reprocess_quarantine()` para reprocesar eventos de cuarentena que califiquen.
- Se reprocesaron 12 eventos válidos de cuarentena a `normalized_event`.
- 8 usuarios biométricos observados con lecturas exitosas en `Door1`.

### 18 de marzo de 2026

- Se ajustó la política de normalización: `access_control` ya no depende de `heartbeat` reciente ni de `DeviceID` para registrarse en `normalized_event`, pero sí requiere `UserID`.
- Se actualizó `BiometricDatabase.reprocess_quarantine()` para mover a normalización solo los `access_control` con `UserID` que hubieran quedado en cuarentena con el criterio anterior.

## Archivos principales del entregable

- [README.md](README.md)
- [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md)
- [PROJECT_PENDING.md](PROJECT_PENDING.md)
- [biometric_ingest.py](biometric_ingest.py)
- [biometric_router_worker.py](biometric_router_worker.py)
- [biometric_db.py](biometric_db.py)
- [biometric_schema.sql](biometric_schema.sql)
- [deploy_biometric_ingest.sh](../server_config/services/biometric_ingest/deploy_biometric_ingest.sh)
