# Reporte de Métricas: Interfaz Dahua

Fecha de corte: **18 de marzo de 2026**  
Hora de snapshot: **2026-03-18 21:06 UTC**

## 1. Contexto y estatus actual

La documentación vigente de la interfaz Dahua ya quedó actualizada al **18 de marzo de 2026** en:

- [README.md](README.md)
- [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md)
- [PROJECT_PENDING.md](PROJECT_PENDING.md)

Actualización posterior al snapshot:

- El `19 de marzo de 2026` quedó validado el estándar `Ruta = /d/<DeviceID>` para eventos de negocio.
- Caso confirmado: `DEVLYN_A303_01` enviando `access_control` y `door_status` por `/d/DEVLYN_A303_01`.
- La documentación normativa de ese cambio quedó en:
  - [DEVICE_MAPPING_STANDARD.md](DEVICE_MAPPING_STANDARD.md)

## 2. Estado operativo validado

Estado comprobado directamente en la EC2 `52.6.240.186`:

- `biometric-ingest`: `active`
- `biometric-router-worker`: `active`
- `nginx`: `active`
- `odoo`: `active`
- `auth-gateway`: `active`

La interfaz Dahua sigue operando con esta topología:

- puerto público `60005` en `nginx`
- servicio interno FastAPI en `127.0.0.1:60006`
- persistencia en PostgreSQL local, base `biometric_ingest`
- Odoo permanece fuera del camino crítico de la ingesta

## 3. Resumen ejecutivo

La interfaz sí está recibiendo y almacenando eventos reales de Dahua. La parte de infraestructura base puede considerarse **funcional**.

Nota de criterio:

- Este snapshot refleja el comportamiento observado antes de aplicar la regla definitiva de negocio para `access_control`.
- A partir del criterio actualizado, `access_control` debe normalizarse aunque exista `no_recent_heartbeat` y aunque el payload no traiga `DeviceID`, pero sí debe traer `UserID`.

El punto débil actual no es la recepción, sino la **resolución de identidad del dispositivo** y el volumen todavía alto de cuarentena:

- la recepción bruta funciona
- la persistencia funciona
- el worker funciona y `processing_error = 0`
- ya existen eventos reales de `AccessControl` y `DoorStatus`
- pero una parte importante de los eventos de negocio sigue quedando en cuarentena por `no_recent_heartbeat`

En este corte, además, **todos los dispositivos están en estado `offline`** dentro de `device_status`, lo cual indica que no han enviado heartbeats recientes al momento del snapshot.

## 4. Ventana temporal de datos

### 4.1 Requests crudos (`raw_request`)

- primer request almacenado: `2026-03-15 00:08:17 UTC`
- último request almacenado: `2026-03-18 18:40:32 UTC`

### 4.2 Eventos normalizados (`normalized_event`)

- primer evento normalizado: `2026-03-12 18:52:55 UTC`
- último evento normalizado: `2026-03-18 18:10:29 UTC`

Observación:

- `normalized_event` contiene algunos eventos de prueba más antiguos que `raw_request`
- esto indica que hay historia de validación previa al corte actual de la ingesta v1

## 5. Métricas base

| Métrica | Valor |
|---|---:|
| Requests crudos (`raw_request`) | `191` |
| Eventos normalizados (`normalized_event`) | `72` |
| Eventos en cuarentena (`event_quarantine`) | `118` |
| Errores de procesamiento (`processing_error`) | `0` |
| Registros en `device_registry` | `3` |
| Registros en `device_status` | `3` |

Lectura operativa:

- `72 / 191 = 37.7%` del tráfico ya terminó normalizado
- `118 / 191 = 61.8%` terminó en cuarentena
- `1 / 191 = 0.5%` quedó crudo sin estar aún ni normalizado ni en cuarentena

## 6. Distribución de tráfico crudo

### 6.1 Por tipo detectado en `raw_request`

| Tipo detectado | Total | Participación |
|---|---:|---:|
| `access_control` | `106` | `55.5%` |
| `door_status` | `68` | `35.6%` |
| `unknown` | `9` | `4.7%` |
| `heartbeat_connect` | `8` | `4.2%` |

### 6.2 Por path HTTP recibido

| Path | Total |
|---|---:|
| `/` | `182` |
| `/cgi-bin/api/autoRegist/connect` | `8` |
| `/custom/unknown` | `1` |

### 6.3 Por fecha

| Fecha | Requests |
|---|---:|
| `2026-03-15` | `5` |
| `2026-03-17` | `103` |
| `2026-03-18` | `83` |

### 6.4 Horas pico de recepción

| Hora UTC | Requests |
|---|---:|
| `2026-03-17 22:00` | `72` |
| `2026-03-17 23:00` | `30` |
| `2026-03-18 01:00` | `18` |
| `2026-03-18 02:00` | `17` |
| `2026-03-18 03:00` | `15` |
| `2026-03-18 18:00` | `12` |

### 6.5 Por IP origen

| IP origen | Requests |
|---|---:|
| `187.236.152.204/32` | `186` |
| `127.0.0.1/32` | `4` |
| `10.20.30.40/32` | `1` |

## 7. Métricas de normalización

### 7.1 Por tipo en `normalized_event`

| Tipo normalizado | Total | Participación |
|---|---:|---:|
| `access_control` | `50` | `69.4%` |
| `door_status` | `12` | `16.7%` |
| `heartbeat_connect` | `8` | `11.1%` |
| `unknown` | `2` | `2.8%` |

### 7.2 Por fecha en `normalized_event`

| Fecha | Tipo | Total |
|---|---|---:|
| `2026-03-12` | `access_control` | `2` |
| `2026-03-12` | `door_status` | `1` |
| `2026-03-15` | `heartbeat_connect` | `1` |
| `2026-03-15` | `unknown` | `1` |
| `2026-03-17` | `access_control` | `31` |
| `2026-03-17` | `door_status` | `11` |
| `2026-03-17` | `heartbeat_connect` | `4` |
| `2026-03-17` | `unknown` | `1` |
| `2026-03-18` | `access_control` | `17` |
| `2026-03-18` | `heartbeat_connect` | `3` |

## 8. Métricas de `AccessControl`

### 8.1 Resultado de acceso

| Dirección | `granted` | Total |
|---|---|---:|
| `entry` | `true` | `38` |
| `entry` | `false` | `12` |

Lectura:

- accesos concedidos: `38` (`76.0%`)
- accesos denegados: `12` (`24.0%`)

### 8.2 Identidad del usuario

| Métrica | Valor |
|---|---:|
| `access_control` normalizados | `50` |
| `user_id_on_device` nulo | `0` |
| `card_name` nulo | `0` |
| `device_id_resolved` nulo | `31` |
| usuarios distintos observados | `11` |
| nombres distintos observados | `11` |

Lectura:

- `31 / 50 = 62.0%` de los `access_control` normalizados siguen sin `device_id_resolved`
- solo `19 / 50 = 38.0%` quedaron con dispositivo resuelto

### 8.3 Usuarios observados

| UserID | Nombre | Eventos | Primer evento UTC | Último evento UTC |
|---|---|---:|---|---|
| `(vacío)` | `(vacío)` | `12` | `2026-03-17 22:13:49+00` | `2026-03-17 23:16:53+00` |
| `19572` | `ROSALBA TORNEZ PARRAL` | `7` | `2026-03-17 22:30:09+00` | `2026-03-18 17:58:02+00` |
| `24367` | `DIEGO ARMANDO JIMENEZ CRUZ` | `6` | `2026-03-17 22:39:24+00` | `2026-03-18 03:24:25+00` |
| `34054` | `LEO FIGUEROA` | `5` | `2026-03-17 22:15:20+00` | `2026-03-18 15:04:37+00` |
| `3852` | `JOSE EDGAR MENDOZA QUIROZ` | `5` | `2026-03-17 22:33:07+00` | `2026-03-18 03:15:18+00` |
| `32638` | `MARIA DEL ROSARIO REYNA CASTAÑ` | `4` | `2026-03-17 22:38:10+00` | `2026-03-18 03:28:19+00` |
| `31545` | `VICTOR ANDRES DE LA CRUZ ISLAS` | `3` | `2026-03-17 22:43:35+00` | `2026-03-18 16:07:50+00` |
| `32832` | `OSCAR EDUARDO HERNANDEZ REYES` | `3` | `2026-03-17 22:34:32+00` | `2026-03-18 02:13:35+00` |
| `98990` | `ALEXIS ARTURO QIROZ MARTINEZ` | `3` | `2026-03-17 22:32:01+00` | `2026-03-18 18:10:29+00` |
| `100` | `UNKNOWN SOURCE` | `1` | `2026-03-12 18:54:35+00` | `2026-03-12 18:54:35+00` |
| `97241` | `TEST USER` | `1` | `2026-03-12 18:52:55+00` | `2026-03-12 18:52:55+00` |

Observación importante:

- los `12` eventos con `UserID/CardName` vacíos corresponden a eventos `granted = false`
- por tanto, no son huecos arbitrarios de parsing: reflejan intentos no concedidos sin identidad útil

## 9. Métricas de `DoorStatus`

| Estado | Total |
|---|---:|
| `Open` | `6` |
| `Close` | `6` |

## 10. Cuarentena

### 10.1 Resumen

| Razón | Tipo | Total |
|---|---|---:|
| `no_recent_heartbeat` | `access_control` | `56` |
| `no_recent_heartbeat` | `door_status` | `55` |
| `no_recent_heartbeat` | `unknown` | `7` |

### 10.2 Por fecha

| Fecha | Tipo | Total |
|---|---|---:|
| `2026-03-17` | `access_control` | `25` |
| `2026-03-17` | `door_status` | `23` |
| `2026-03-17` | `unknown` | `7` |
| `2026-03-18` | `access_control` | `31` |
| `2026-03-18` | `door_status` | `32` |

### 10.3 Ratio de normalización vs cuarentena

| Tipo | Normalizados | Cuarentena | Pendiente | Observación |
|---|---:|---:|---:|---|
| `access_control` | `47.2%` | `52.8%` | `0.0%` | más de la mitad todavía cae a cuarentena |
| `door_status` | `17.6%` | `80.9%` | `1.5%` | resolución todavía muy débil |

## 11. Estado por dispositivo

### 11.1 `device_registry`

| DeviceID | Modelo | Estado | First Seen UTC | Last Seen UTC | Última IP |
|---|---|---|---|---|---|
| `DEVLYN_A303_01` | `DHI-ASI3204E` | `offline` | `2026-03-17 22:02:18 UTC` | `2026-03-17 22:02:18 UTC` | `187.236.152.204/32` |
| `DEVLYN_A317_01` | `DHI-ASI3204E` | `offline` | `2026-03-17 21:57:11 UTC` | `2026-03-18 15:57:25 UTC` | `187.236.152.204/32` |
| `TEST_DEVICE_01` | `DHI-ASI3204E` | `offline` | `2026-03-15 00:08:17 UTC` | `2026-03-15 00:09:09 UTC` | `127.0.0.1/32` |

### 11.2 `device_status`

| DeviceID | Estado | Last Heartbeat UTC | Last Event UTC | Last Event Kind | Heartbeat Interval | Última IP |
|---|---|---|---|---|---:|---|
| `DEVLYN_A303_01` | `offline` | `2026-03-17 22:02:18 UTC` | `2026-03-17 22:02:18 UTC` | `heartbeat_connect` | `null` | `187.236.152.204/32` |
| `DEVLYN_A317_01` | `offline` | `2026-03-18 15:57:25 UTC` | `2026-03-18 15:57:25 UTC` | `heartbeat_connect` | `184` | `187.236.152.204/32` |
| `TEST_DEVICE_01` | `offline` | `2026-03-15 00:08:17 UTC` | `2026-03-15 00:09:09 UTC` | `unknown` | `null` | `127.0.0.1/32` |

### 11.3 Eventos normalizados por dispositivo resuelto

| DeviceID resuelto | Tipo | Total |
|---|---|---:|
| `(null)` | `access_control` | `31` |
| `DEVLYN_A303_01` | `heartbeat_connect` | `1` |
| `DEVLYN_A317_01` | `access_control` | `18` |
| `DEVLYN_A317_01` | `door_status` | `11` |
| `DEVLYN_A317_01` | `heartbeat_connect` | `6` |
| `DEVLYN_A317_01` | `unknown` | `1` |
| `TEST_DEVICE_01` | `access_control` | `1` |
| `TEST_DEVICE_01` | `door_status` | `1` |
| `TEST_DEVICE_01` | `heartbeat_connect` | `1` |
| `TEST_DEVICE_01` | `unknown` | `1` |

Lectura:

- `DEVLYN_A317_01` concentra la mayor parte de la actividad resuelta
- `DEVLYN_A303_01` en este corte solo dejó `heartbeat_connect` normalizado
- el principal problema actual es que `31` eventos `access_control` sí se conservaron, pero sin `device_id_resolved`

## 12. Hallazgos principales

### 12.1 La interfaz Dahua sí está funcionando

Pruebas reales:

- hay recepción sostenida en `60005`
- hay persistencia en `raw_request`
- hay normalización real de `AccessControl`, `DoorStatus` y `heartbeat_connect`
- `processing_error = 0`

### 12.2 La resolución por dispositivo sigue siendo el cuello de botella

La causa observable en este snapshot es consistente con la arquitectura actual:

- ambos dispositivos reales reportan desde la misma IP pública `187.236.152.204/32`
- la correlación actual depende de `source_ip + listener_port + heartbeat reciente`
- cuando no existe un heartbeat reciente suficientemente correlacionable, el worker deriva el evento a cuarentena o lo deja normalizado sin `device_id_resolved`

Esto explica:

- cuarentena alta en `access_control`
- cuarentena muy alta en `door_status`
- `31` eventos de acceso normalizados sin dispositivo resuelto

### 12.3 Todos los dispositivos están `offline` al corte

Esto no niega que haya habido actividad durante el día. Significa que al momento exacto del snapshot no existía heartbeat reciente suficiente para mantenerlos como `online`.

### 12.4 Existe un request crudo pendiente de clasificación final

Se detectó `1` request crudo sin reflejo todavía en `normalized_event` ni en `event_quarantine`:

- `raw_request.id = 87`
- tipo detectado: `door_status`
- recibido: `2026-03-17 23:12:08 UTC`
- IP origen: `187.236.152.204/32`
- path: `/`

No es un volumen problemático, pero conviene revisarlo porque idealmente el gap debe ser `0`.

## 13. Conclusión

La interfaz Dahua está en un estado **operativamente útil** para continuar la fase de estabilización:

- recibe
- guarda
- normaliza
- proyecta estado

Pero todavía **no** está en un punto ideal para integrarse a asistencias Odoo, porque la calidad de resolución por dispositivo aún es insuficiente.

El principal foco inmediato no debe ser “recibir más”, sino:

1. bajar la cuarentena de `access_control`
2. mejorar la atribución de `door_status`
3. cerrar el gap del único request crudo pendiente
4. validar continuidad de heartbeat para que `device_status` sea confiable
