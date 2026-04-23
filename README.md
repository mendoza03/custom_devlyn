# odoo-devlyn

Repositorio principal de addons Odoo y componentes complementarios usados en Devlyn.

Además de los addons heredados que viven en la raíz, este repositorio ahora concentra el frente biométrico completo: ingesta Dahua, dashboard operativo, addons Odoo biométricos, gateway/Cognito, assets de despliegue y el MCP server de solo lectura.

## Scopes principales

- `custom_devlyn/`, `helpdesk/`, `helpdesk_custom_datos/`, `helpdesk_web_form/`, `to_base/`, `to_attendance_device/` y demás addons históricos en raíz.
- `odoo_biometric/`
  Addons Odoo para bridge biométrico, sincronización de asistencias y reporte Dahua por sucursal.
- `dahua_interface/`
  Runtime de ingesta Dahua, normalización, cuarentena, estado de dispositivos y backfill acotado.
- `dashboard/`
  Dashboard operativo para inspección de requests crudos, normalizados, cuarentena y devices.
- `server_config/`
  Gateway FastAPI/UI, triggers Cognito, user-data, scripts operativos y assets `systemd/nginx/env.example`.
- `odoo_mcp/`
  MCP server read-only para Odoo y `biometric_ingest`.
- `docs/`
  Catálogos del reporte y manuales vendor Dahua.
- `config/`
  Ejemplo de configuración local del operador.

## Documentación rápida

- [`BIOMETRIA.md`](BIOMETRIA.md)
  Vista general del stack biométrico y de sus componentes.
- [`MCP.md`](MCP.md)
  Resumen del MCP server, su addon read-only y sus assets de despliegue.

## Regla de configuración

- `config/servers.json` es local y no se versiona.
- El archivo de ejemplo que sí vive en git es `config/servers.example.json`.
- Los secretos del gateway y de despliegue deben resolverse por variables de entorno o `.env.example` renderizados localmente.
