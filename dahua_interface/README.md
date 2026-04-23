# Biometric Ingest v1

Infraestructura de ingesta biométrica independiente de Odoo para la EC2 `52.6.240.186`.

Documento de estado y handoff:

- [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md)
- [PROJECT_PENDING.md](PROJECT_PENDING.md)
- [METRICS_REPORT_2026-03-18.md](METRICS_REPORT_2026-03-18.md)
- [DEVICE_MAPPING_STANDARD.md](DEVICE_MAPPING_STANDARD.md)
- [ATTENDANCE_SYNC_PHASES.md](ATTENDANCE_SYNC_PHASES.md)
- [ATTENDANCE_SYNC_PHASE1_SPEC.md](ATTENDANCE_SYNC_PHASE1_SPEC.md)
- [ATTENDANCE_SYNC_OPEN_DECISIONS.md](ATTENDANCE_SYNC_OPEN_DECISIONS.md)
- [ODOO_MODULE_VALIDATION_2026-03-20.md](ODOO_MODULE_VALIDATION_2026-03-20.md)

## Componentes

- `biometric_ingest.py`
  - API FastAPI interna en `127.0.0.1:60006`
  - recibe requests desde `nginx`
  - escribe primero a spool JSONL con `fsync`
  - deja soporte operativo en `/var/log/dahua_events.log`

- `biometric_router_worker.py`
  - consume el spool
  - inserta `raw_request`
  - normaliza `heartbeat_connect`, `access_control`, `door_status`
  - `access_control` se normaliza aunque no se resuelva `device_id` y aunque el payload no incluya `DeviceID`, siempre que sí traiga `UserID`
  - actualiza `device_registry` y `device_status`
  - manda a `event_quarantine` `access_control` sin `UserID`, heartbeats sin `DeviceID`, `door_status` sin resolución confiable, y `unknown`
  - no implementa todavía el archivado/retención de largo plazo

- `biometric_schema.sql`
  - esquema PostgreSQL para `biometric_ingest`

## Assets de despliegue

- [biometric-ingest-60005.conf](../server_config/services/biometric_ingest/biometric-ingest-60005.conf)
  - edge `nginx` público en `:60005`
  - rate limiting y logging dedicado

- [biometric-ingest.service](../server_config/services/biometric_ingest/biometric-ingest.service)
- [biometric-router-worker.service](../server_config/services/biometric_ingest/biometric-router-worker.service)
- [biometric-ingest.env.example](../server_config/services/biometric_ingest/biometric-ingest.env.example)
- [deploy_biometric_ingest.sh](../server_config/services/biometric_ingest/deploy_biometric_ingest.sh)
- [attendance-sync-worker.service](../server_config/services/attendance_sync/attendance-sync-worker.service)
- [deploy_attendance_sync.sh](../server_config/services/attendance_sync/deploy_attendance_sync.sh)

## Despliegue

```bash
chmod +x server_config/services/biometric_ingest/deploy_biometric_ingest.sh
./server_config/services/biometric_ingest/deploy_biometric_ingest.sh
```

## Servicios

```bash
systemctl status biometric-ingest
systemctl status biometric-router-worker
systemctl status nginx
```

## Validación

```bash
curl -X POST http://52.6.240.186:60005/ \
  -H "Content-Type: application/json" \
  -d '{"Code":"DoorStatus","Data":{"Status":"Open","RealUTC":1773341575}}'

python3 dahua_interface/monitor_live.py --history 20
```

## Estándar vigente de mapeo

El mecanismo preferido para asociar eventos de negocio a un dispositivo específico ya no es la IP, sino la ruta dedicada configurada en `Carga automática`.

Estándar actual:

- `Registro Automático CGI`
  - sigue activo
  - entrega `heartbeat_connect` con `DeviceID`
- `Carga automática`
  - debe usar `Ruta = /d/<DeviceID>`

Ejemplo:

- `DeviceID = DEVLYN_A303_01`
- `Ruta = /d/DEVLYN_A303_01`

Este estándar ya fue validado con tráfico real el `19 de marzo de 2026`.

Detalle operativo:

- [DEVICE_MAPPING_STANDARD.md](DEVICE_MAPPING_STANDARD.md)

## Consultas útiles

```sql
SELECT event_kind, count(*)
FROM normalized_event
GROUP BY 1
ORDER BY 2 DESC;

SELECT device_id, status, last_heartbeat_at, last_event_at, last_source_ip
FROM device_status
ORDER BY last_seen_at DESC;

SELECT reason, count(*)
FROM event_quarantine
GROUP BY 1
ORDER BY 2 DESC;
```

## Pendiente actual

- La retención `90d hot + 1y archive` todavía no está implementada como job de archivado/purge.
- Hoy sí existe ingestión, spool, normalización, cuarentena y proyección de estado.

## Attendance Sync V1

La integracion provisional con `hr_attendance` queda implementada con:

- worker continuo: `attendance_sync_worker.py`
- servicio `systemd`: [attendance-sync-worker.service](../server_config/services/attendance_sync/attendance-sync-worker.service)
- despliegue: [deploy_attendance_sync.sh](../server_config/services/attendance_sync/deploy_attendance_sync.sh)
- modulo Odoo: `hr_biometric_attendance_sync`

Este flujo no usa `to_attendance_device` como motor principal.

Estado actual de despliegue:

- modulo `hr_biometric_attendance_sync` instalado en `devlyn_com`
- usuario tecnico Odoo: `biometric.sync`
- servicio `attendance-sync-worker` activo en la EC2
- staging funcional en `hr.biometric.event`
- destino funcional activo en `hr.attendance`
- los polls sin eventos no crean corridas vacias en `hr.biometric.sync.run`

## Backfill histórico

Para recuperar huecos históricos acotados sin hacer rewind del worker vivo se agregó:

- [attendance_sync_backfill.py](attendance_sync_backfill.py)
- [run_devlyn_attendance_backfill.sh](../server_config/infra/scripts/run_devlyn_attendance_backfill.sh)

Caso ya resuelto:

- rango `normalized_event_id 482–1770`
- hueco local `2026-03-24` a `2026-04-06`
- backfill aplicado el `2026-04-09`

Estado esperado después del apply:

- `attendance-sync-worker` vuelve a `active`
- `hr.attendance` deja de tener el hueco histórico
- el reporte `Asistencias por Sucursal` muestra fechas continuas en ese tramo
