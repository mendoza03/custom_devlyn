# Biometría

Este documento resume el frente biométrico que vive en este repositorio y cómo se relacionan sus componentes.

## Componentes

- `dahua_interface/`
  Recibe tráfico Dahua, persiste `raw_request`, normaliza eventos, mantiene `device_status`, envía casos no resolubles a cuarentena y expone utilidades operativas como `monitor_live.py` y `attendance_sync_backfill.py`.
- `odoo_biometric/module/hr_biometric_attendance_sync/`
  Proyecta eventos normalizados hacia Odoo en `hr.biometric.event` y `hr.attendance`.
- `odoo_biometric/module/devlyn_dahua_attendance_reporting/`
  Aporta catálogos vivos y el reporte de asistencias por sucursal, incluyendo visor interactivo y exportación XLSX.
- `odoo_biometric/module/odoo_biometric_bridge/`
  Integra el flujo de autenticación biométrica con Odoo mediante bridge OIDC/OAuth, auditoría y políticas de acceso.
- `server_config/auth_gateway/`
  Gateway FastAPI/UI para login biométrico, validación Odoo, telemetría y servicios auxiliares.
- `server_config/lambdas/`
  Triggers de AWS Cognito para `CUSTOM_AUTH`.
- `dashboard/`
  UI operativa para revisar requests, eventos normalizados, cuarentena y estado de dispositivos.
- `server_config/services/`
  Assets de despliegue por servicio: `biometric_ingest`, `attendance_sync`, `dashboard` y `odoo_mcp`.
- `docs/catalogs/`
  Archivos de catálogo usados por el reporte Dahua.
- `docs/vendor/dahua/`
  Manuales de referencia del vendor.

## Flujo operativo

### Ingesta Dahua

`Dahua -> nginx :60005 -> biometric_ingest.py -> spool JSONL -> biometric_router_worker.py -> biometric_ingest.normalized_event`

### Sincronización de asistencias

`normalized_event -> attendance_sync_worker.py -> Odoo hr.biometric.event -> Odoo hr.attendance`

### Reporte por sucursal

`hr.attendance + catálogos Devlyn -> devlyn_dahua_attendance_reporting -> visor interactivo / exportación XLSX`

### Login biométrico

`Navegador -> auth_gateway -> Cognito CUSTOM_AUTH -> Odoo auth_oauth / bridge biométrico`

## Dónde vive cada cosa

- Código Odoo: `odoo_biometric/module/`
- Runtime de ingestión: `dahua_interface/`
- Gateway y assets AWS: `server_config/auth_gateway/`, `server_config/lambdas/`, `server_config/infra/scripts/`
- Monitor operativo: `dashboard/`
- Permisos read-only y consulta por agentes: `odoo_mcp/`

## Qué no se versiona

- `config/servers.json`
- `.env` reales
- bases locales, caches y artefactos temporales

Para despliegue y operación diaria, usa los `.env.example`, los scripts bajo `server_config/` y la documentación específica de cada scope.
