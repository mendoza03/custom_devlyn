# MCP

El scope `odoo_mcp/` implementa un MCP server read-only para consultar Odoo y la base `biometric_ingest` desde clientes compatibles con MCP.

## Propósito

- exponer datos operativos sin permisos de escritura
- facilitar exploración incremental para agentes y asistentes
- unificar acceso a empleados, asistencias, eventos biométricos, catálogos Devlyn, proyectos, helpdesk, usuarios, contactos y eventos Dahua

## Estructura

- `odoo_mcp/app.py`
  App HTTP con auth, `healthz`, `readyz`, `version` y mount MCP.
- `odoo_mcp/server.py`
  Registro de tools y resources MCP.
- `odoo_mcp/backends/`
  Adaptadores read-only para Odoo XML-RPC y PostgreSQL.
- `odoo_mcp/branch_report.py`
  Implementación del reporte Devlyn de asistencias por sucursal fuera de Odoo transient.
- `odoo_mcp/odoo_addon/odoo_mcp_readonly_access/`
  Addon que define permisos y reglas de solo lectura para el usuario técnico MCP.
- `server_config/services/odoo_mcp/`
  Unidad `systemd`, vhosts `nginx`, `.env.example` y script de despliegue.

## Fuentes de datos

- Odoo por XML-RPC
- PostgreSQL `biometric_ingest` por conexión read-only

## Patrón recomendado de uso

- `count_*` para estimar volumen antes de explorar
- `search_*` con `detail_level=summary` para paginar
- `get_*_by_id` para abrir un registro puntual
- `get_devlyn_catalogs` antes de `get_branch_attendance_report`

## Seguridad

- autenticación por `X-API-Key`
- compatibilidad adicional con `Authorization: Bearer <token>`
- permisos reforzados por el addon `odoo_mcp_readonly_access`

## Referencias

- [`odoo_mcp/README.md`](odoo_mcp/README.md)
- [`server_config/services/odoo_mcp/odoo-mcp.env.example`](server_config/services/odoo_mcp/odoo-mcp.env.example)
- [`server_config/services/odoo_mcp/deploy_odoo_mcp.sh`](server_config/services/odoo_mcp/deploy_odoo_mcp.sh)
