# Server Config

Este scope concentra infraestructura, despliegue y automatización asociados al frente biométrico y al MCP server.

## Contenido

- `auth_gateway/`
  Servicio FastAPI/UI, plantillas, assets web, configuración `nginx` y unidad `systemd`.
- `services/`
  Assets por servicio: `systemd`, `nginx`, `.env.example` y scripts de despliegue.
- `infra/scripts/`
  Scripts operativos para despliegue de addons, configuración OAuth, Route53, fail2ban, Cognito y backfill.
- `lambdas/`
  Triggers Cognito para `CUSTOM_AUTH`.
- `bootstrap/`
  User-data base y user-data biométrico.

## Regla

- El runtime funcional vive en `dahua_interface/`, `dashboard/`, `odoo_biometric/` y `odoo_mcp/`.
- Los assets de servidor viven aquí.
- Los secretos reales no se versionan; usa `.env.example` y configuración local.
