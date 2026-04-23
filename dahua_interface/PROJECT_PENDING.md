# Pendientes del Proyecto Biometric Ingest

Fecha de referencia: **19 de marzo de 2026 (UTC)**.

## Objetivo de la etapa actual

La etapa actual del proyecto **no** es todavía integración con asistencias Odoo.

La prioridad inmediata es esta:

1. confirmar que los biométricos envían correctamente
2. confirmar que la infraestructura recibe correctamente
3. confirmar que todo lo recibido se almacena correctamente
4. confirmar que la resolución básica de eventos/dispositivos es estable
5. cerrar esta etapa antes de avanzar a la siguiente fase funcional

En otras palabras:

- primero se valida la **confiabilidad de la ingesta**
- después se avanza con **retención, dashboard y sincronización funcional**

## Qué sí debe quedar validado en esta etapa

Antes de mover el proyecto a la siguiente fase, se debe comprobar con dispositivos reales en operación:

### 1. Conectividad y continuidad

- que cada dispositivo mande `heartbeat/connect` de forma consistente
- que no existan cortes frecuentes de reporte
- que el endpoint en `60005` reciba tráfico real de los equipos
- que la infraestructura soporte el patrón de tráfico sin degradar Odoo

### 2. Persistencia

- que todo request recibido quede guardado en `raw_request`
- que los eventos resolubles queden en `normalized_event`
- que los eventos no resolubles queden en `event_quarantine`
- que `processing_error` permanezca en `0` o en un nivel controlado
- que el spool no acumule backlog indefinido

### 3. Calidad de datos

- que `AccessControl` llegue con campos consistentes
- que `DoorStatus` llegue cuando aplique
- que el `UserID` observado sea estable para una misma persona
- que `Type` llegue correctamente como `Entry` / `Exit`
- que `Status` llegue correctamente para concedido/denegado
- que los `epoch timestamps` del equipo correspondan con hora real esperada
- que no existan variaciones inesperadas de payload por firmware o dispositivo

### 4. Resolución de dispositivo

- que `DeviceID` llegue correctamente en `heartbeat_connect` ✔️ validado
- que el estándar `Ruta = /d/<DeviceID>` funcione en la práctica para eventos de negocio ✔️ validado el 19/03/2026
- que la correlación `source_ip + listener_port + heartbeat reciente` quede solo como mecanismo legado/transitorio
- que no aparezcan ambigüedades por múltiples equipos detrás de la misma salida de red
- que `access_control` se normalice aunque no haya heartbeat vigente y aunque no traiga `DeviceID`, siempre que sí traiga `UserID` ✔️ actualizado 18/03/2026
- que solo vayan a cuarentena: `access_control` sin `UserID`, heartbeats sin `DeviceID`, `door_status` no atribuibles, y eventos `unknown`

### 4.1 Política de operación mixta

Durante la transición, coexistirán dos grupos:

- dispositivos ya migrados a `Ruta = /d/<DeviceID>`
- dispositivos aún no migrados que siguen enviando por `/`

En esta etapa debe quedar validado que:

- los dispositivos migrados se resuelven por `request_path_device_hint`
- los dispositivos no migrados siguen entrando sin pérdida de datos
- la operación mixta no rompe la normalización ni el dashboard

Documento de referencia:

- [DEVICE_MAPPING_STANDARD.md](DEVICE_MAPPING_STANDARD.md)

### 5. Criterio operativo de fase 1

Esta fase debe considerarse aceptable cuando:

- los biométricos reporten de forma continua
- el almacenamiento sea confiable
- la normalización sea consistente
- la cuarentena sea entendible y controlada
- el equipo tenga confianza en que la infraestructura ya es estable

## Qué queda explícitamente pendiente

## 1. Política de retención y archivado

Este es el pendiente técnico principal de infraestructura.

Hoy no existe todavía:

- job de archivado automático
- política `90d hot + 1y archive` ejecutándose
- export a JSONL comprimido como proceso operativo
- carga a S3
- purge automático de datos viejos
- procedimiento operativo de restore desde histórico

Estado actual:

- la base ya está lista para recibir
- el worker ya existe
- el particionado mensual ya existe
- pero la retención aún no está cerrada como capacidad operativa

## 2. Observabilidad operativa más fuerte

Pendiente de una fase posterior:

- métricas de ingesta por minuto
- métricas por dispositivo
- alertas automáticas por `stale` / `offline`
- alertas por crecimiento anormal de `event_quarantine`
- alertas por bursts o payloads no esperados
- dashboards de salud fuera del log plano

## 3. Dashboard de dispositivos en Odoo

Ya existe la base técnica en `device_status`, pero todavía no se debe avanzar hasta cerrar la validación de ingesta real.

Pendiente para fase siguiente:

- definir modelo Odoo para hardware físico
- no reutilizar `biometric.device` actual
- sincronizar o exponer `device_status` hacia Odoo
- vista de dispositivos `online / stale / offline`
- vista de último heartbeat y último evento
- filtros por sede, puerta, dispositivo y estado

## 4. Integración con asistencias Odoo

Este tema sigue fuera de alcance en la etapa actual.

Pendiente para fase posterior:

- definir mapping entre `UserID` del dispositivo y empleado Odoo
- definir reglas `Entry/Exit -> check_in/check_out`
- definir tratamiento de denegados, duplicados y secuencias incompletas
- definir reconciliación de eventos tardíos o fuera de orden
- decidir si Odoo consumirá desde `normalized_event` o desde `outbox_sync`

## 5. Seguridad adicional

La infraestructura ya está endurecida en lo básico, pero aún quedan mejoras que no conviene ejecutar antes de validar bien la ingesta real:

- política de allowlist por sitios si más adelante se vuelve viable
- revisión de límites de `nginx` según tráfico real
- estrategia contra escáneres y ruido de Internet
- revisión de cuarentena por cambios de IP pública
- definición de respuesta ante tráfico malicioso persistente

## 6. Migración gradual de equipos al estándar de ruta

Esto ya no es un experimento, sino una tarea operativa vigente.

Pendiente en campo:

- revisar dispositivo por dispositivo el `DeviceID` canónico
- configurar `Carga automática` con `Ruta = /d/<DeviceID>`
- confirmar con evento real que el equipo ya no llega solo por `/`
- marcar qué equipos ya quedaron migrados y cuáles siguen en modo legado

Mientras esta migración no esté completa:

- seguiremos viendo mezcla de eventos por `/` y por `/d/<DeviceID>`
- la calidad de mapeo seguirá siendo desigual entre equipos

## Decisión de proyecto recomendada

La recomendación para el proyecto es esta:

### Etapa actual: estabilización de ingesta

En esta etapa solo debemos:

- observar tráfico real
- validar almacenamiento
- validar normalización
- validar cuarentena
- entender el comportamiento real de los biométricos

### No avanzar todavía con:

- retención final
- dashboard en Odoo
- integración con asistencias
- automatizaciones de negocio

### Gate de salida de la etapa actual

Moverse a la siguiente fase únicamente cuando:

- la ingesta esté estable con dispositivos reales
- el equipo esté conforme con la persistencia
- ya se haya observado suficiente tráfico real para validar estructura y consistencia

## Siguiente fase, cuando esta etapa cierre bien

Una vez validada correctamente la etapa actual, el orden recomendado es:

1. cerrar política de retención y archivado
2. exponer salud de dispositivos para dashboard
3. definir mapping funcional hacia Odoo
4. integrar asistencias

## Conclusión

Lo pendiente del proyecto no es “hacer que el sistema reciba”, porque eso ya está implementado.

Lo pendiente ahora es:

- validar que la ingesta funciona bien con biométricos reales
- confirmar estabilidad operativa
- y solo después avanzar con la siguiente fase del proyecto

Ese orden debe mantenerse para no mezclar validación de infraestructura con lógica funcional de negocio.
