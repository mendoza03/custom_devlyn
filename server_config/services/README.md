# Service Assets

Assets de despliegue centralizados por servicio.

## Estructura

- `biometric_ingest/`
  Unidades `systemd`, `nginx`, `.env.example` y script de despliegue del listener/worker Dahua.

- `attendance_sync/`
  Unidad `systemd` y script de despliegue del worker de sincronización hacia Odoo.

- `dashboard/`
  Unidades `systemd`, configuración `nginx`, `.env.example` y script de despliegue del dashboard.

- `odoo_mcp/`
  Unidad `systemd`, drop-in de ciclo de vida con Odoo, configuración `nginx`, `.env.example` y script de despliegue del MCP server.

## Regla

El runtime Python permanece en su scope funcional (`dahua_interface/`, `dashboard/` u `odoo_mcp/`). Todo asset operativo de servidor va aquí.
