# Estándar de Mapeo de Dispositivo Dahua

Fecha de referencia: **19 de marzo de 2026 (UTC)**.

## Objetivo

Definir el mecanismo oficial para asociar eventos de negocio Dahua (`access_control`, `door_status` y eventos futuros) con un `DeviceID` canónico dentro de `biometric_ingest`.

Este estándar se establece después de validar en producción que la ruta configurada en `Carga automática` sí puede transportar un identificador estable de dispositivo.

## Hallazgo validado

El `19 de marzo de 2026` se validó en la EC2 `52.6.240.186` que el equipo `DEVLYN_A303_01` envió eventos de negocio por una ruta configurada manualmente en `Carga automática`:

- `POST /d/DEVLYN_A303_01` con `Code=AccessControl`
- `POST /d/DEVLYN_A303_01` con `Code=DoorStatus`

Esos eventos quedaron normalizados con:

- `device_id_resolved = DEVLYN_A303_01`
- `identity_resolution = request_path_device_hint`

Esto confirma que la ruta personalizada es un mecanismo válido y superior a la inferencia por IP para mapear dispositivos.

## Problema que resuelve

Antes de esta validación, los eventos de negocio llegaban mayoritariamente por `/` y presentaban estas limitaciones:

- `access_control` no incluye `DeviceID` en el payload observado
- `door_status` no incluye `DeviceID`
- múltiples dispositivos pueden compartir la misma IP pública por NAT
- la correlación por `source_ip + heartbeat reciente` es útil, pero no determinística

Con la ruta dedicada por dispositivo, los eventos de negocio ya no dependen de la IP para su asociación principal.

## Configuración estándar para dispositivos nuevos

### 1. Registro Automático CGI

Debe permanecer habilitado para heartbeats y autoregistro:

- función: `Registro Automático CGI`
- host: `52.6.240.186`
- puerto: `60005`
- protocolo: `HTTP`
- `ID Dispositivo`: usar el `DeviceID` canónico

Ejemplo:

- `DeviceID = DEVLYN_A303_01`

Este flujo sigue generando:

- `POST /cgi-bin/api/autoRegist/connect`

y se usa para:

- registrar vida del dispositivo
- actualizar `device_registry`
- actualizar `device_status`

### 2. Carga automática

Este es el estándar nuevo para eventos de negocio.

Parámetros:

- host: `52.6.240.186`
- puerto: `60005`
- protocolo: `HTTP`
- `HTTPS`: apagado
- `Ruta`: `/d/<DeviceID>`

Ejemplo:

- `/d/DEVLYN_A303_01`

## Regla canónica de naming

Se adopta como identificador oficial el `DeviceID` completo.

Formato recomendado:

- `DEVLYN_<SUCURSAL>_<NUMERO>`

Ejemplos:

- `DEVLYN_A303_01`
- `DEVLYN_A317_01`

La ruta debe repetir exactamente ese mismo valor:

- `DeviceID = DEVLYN_A303_01`
- `Ruta = /d/DEVLYN_A303_01`

No usar solo sucursal en la ruta cuando pueda haber más de un biométrico por tienda.

## Regla oficial de resolución de dispositivo

A partir de este estándar, el orden de resolución queda así:

### 1. Heartbeat/autoregistro

Para `heartbeat_connect`, la identidad oficial del dispositivo sigue siendo:

- `DeviceID` dentro del payload

Resultado esperado:

- `identity_resolution = heartbeat_payload`

### 2. Eventos de negocio con ruta dedicada

Para `access_control`, `door_status` y eventos futuros que lleguen por:

- `/d/<DeviceID>`

la identidad principal será:

- `<DeviceID>` extraído de la ruta

Resultado esperado:

- `identity_resolution = request_path_device_hint`

### 3. Modo legado temporal

Si el evento de negocio sigue llegando por `/`, el sistema continúa operando en modo transitorio:

- se intenta correlación por `source_ip + listener_port + heartbeat reciente`
- si la correlación no es suficientemente confiable, aplica la política actual de normalización/cuarentena

Esto permite coexistencia entre:

- dispositivos ya migrados al estándar `/d/<DeviceID>`
- dispositivos aún no migrados que siguen reportando por `/`

## Política de transición

El proyecto entra en un periodo de operación mixta.

### Dispositivos ya migrados

Deben quedar con:

- `Registro Automático CGI` activo
- `ID Dispositivo` correcto
- `Carga automática` activa
- `Ruta = /d/<DeviceID>`

Ventaja:

- `access_control` y `door_status` quedan asociados al dispositivo sin depender de IP o heartbeat reciente

### Dispositivos no migrados todavía

Pueden seguir enviando por `/` mientras se completa el ajuste en campo.

Tratamiento:

- `heartbeat_connect` sigue útil para detectar vida
- `access_control` con `UserID` se sigue normalizando aunque no haya `DeviceID`
- `door_status` sin resolución confiable puede seguir yendo a cuarentena
- la atribución de dispositivo seguirá siendo más débil que en los equipos ya migrados

## Evidencia concreta de la validación

Validación positiva observada el `19 de marzo de 2026`:

- `2026-03-19 22:50:39 UTC` `POST /d/DEVLYN_A303_01` `access_control`
- `2026-03-19 22:50:42 UTC` `POST /d/DEVLYN_A303_01` `door_status`
- `2026-03-19 22:50:42 UTC` `POST /d/DEVLYN_A303_01` `access_control`
- `2026-03-19 22:50:45 UTC` `POST /d/DEVLYN_A303_01` `door_status`

Normalización asociada:

- `device_id_resolved = DEVLYN_A303_01`
- `identity_resolution = request_path_device_hint`

Evento útil observado:

- `user_id_on_device = 97241`
- `card_name = RAUL IVAN RODRIGUEZ`
- `granted = true`
- `direction = entry`

## Hallazgos que siguen vigentes

- `Type` sigue llegando como `Entry` en los eventos útiles observados
- no se ha validado todavía un `Type = Exit`
- el botón `Prueba` del Dahua no es evidencia suficiente por sí mismo
- la validación confiable sigue siendo generar un evento real en el equipo

## Recomendación operativa

Para seguir mapeando registros nuevos, el estándar recomendado es:

1. configurar `DeviceID` canónico en `Registro Automático CGI`
2. configurar la misma identidad en `Carga automática` como `/d/<DeviceID>`
3. validar con evento real
4. revisar en dashboard o base que el evento quede con `identity_resolution = request_path_device_hint`

## Criterio de éxito por dispositivo

Un equipo se considera correctamente migrado cuando se cumplen ambos puntos:

- se recibe `heartbeat_connect` con `DeviceID` esperado
- se recibe al menos un evento de negocio por `/d/<DeviceID>`

## Conclusión

La ruta personalizada por dispositivo queda adoptada como mecanismo oficial de asociación de `DeviceID` para eventos de negocio.

La infraestructura seguirá soportando temporalmente dispositivos no migrados, pero la calidad del mapeo será mejor y más estable en los equipos que adopten el estándar `/d/<DeviceID>`.
