# Devlyn Odoo Attendance MCP

MCP server read-only para Devlyn, orientado a operación Odoo y asistencias Dahua.

V2 de ergonomía para LLM:

- tools de conteo para estimar volumen antes de paginar
- tools de detalle para recuperar un registro puntual por id
- descripciones prescriptivas con paginación, defaults y costo relativo
- resources adicionales para envelope, filtros y guía de exploración
- enums expuestos en `inputSchema` para filtros críticos

V3 de control de volumen:

- las tools de búsqueda/listado ahora usan por defecto `detail_level=summary`
- el servidor recorta respuestas grandes por diseño y marca `truncated=true` cuando hay más datos por explorar
- el patrón recomendado pasa a ser `count_* -> search_*(summary) -> get_*_by_id -> search_*(standard|full)`
- `include_fields` permite pedir campos extra sin abandonar un modo compacto
- `truncate_text` permite acotar cadenas largas y evitar payloads excesivos

## Alcance

- Odoo read-only por XML-RPC
- PostgreSQL read-only sobre `biometric_ingest`
- MCP Streamable HTTP en `https://mcp.odootest.mvpstart.click/mcp`
- Autenticación por `X-API-Key`
- Compatibilidad adicional con `Authorization: Bearer <token>`

Fuera de alcance:

- login facial
- `auth-gateway`
- `biometric.auth.*`
- `biometric.device`
- `biometric.policy`
- cualquier operación de escritura

## Estructura

- `app.py`
  App Starlette con middleware de auth, `healthz`/`readyz`/`version` y endpoint MCP exacto en `/mcp`.
- `server.py`
  Registro de tools/resources MCP y runtime.
- `backends/`
  Adaptadores read-only para Odoo XML-RPC y PostgreSQL `biometric_ingest`.
- `branch_report.py`
  Reimplementación del reporte Devlyn de asistencias por sucursal sin transients Odoo.
- `odoo_addon/odoo_mcp_readonly_access/`
  Addon mínimo para permisos de lectura del usuario técnico `mcp.readonly`.
- `../server_config/services/odoo_mcp/`
  Service `systemd`, vhosts `nginx`, `.env.example` y script de despliegue.

## Variables de entorno

Ver [`../server_config/services/odoo_mcp/odoo-mcp.env.example`](../server_config/services/odoo_mcp/odoo-mcp.env.example).

Variables clave:

- `ODOO_MCP_PUBLIC_BASE_URL`
- `ODOO_MCP_API_KEY`
- `ODOO_MCP_ODOO_URL`
- `ODOO_MCP_ODOO_DB`
- `ODOO_MCP_ODOO_LOGIN`
- `ODOO_MCP_ODOO_API_KEY`
- `ODOO_MCP_BIOMETRIC_PG_DSN`

## Ejecución local

```bash
python3 -m pip install --break-system-packages -r odoo_mcp/requirements.txt
export ODOO_MCP_PUBLIC_BASE_URL=https://mcp.odootest.mvpstart.click
export ODOO_MCP_API_KEY=replace_me
export ODOO_MCP_ODOO_URL=http://127.0.0.1:8069
export ODOO_MCP_ODOO_DB=devlyn_com
export ODOO_MCP_ODOO_LOGIN=mcp.readonly
export ODOO_MCP_ODOO_API_KEY=replace_me
export ODOO_MCP_BIOMETRIC_PG_DSN='postgresql://mcp_readonly:replace_me@127.0.0.1:5432/biometric_ingest'
uvicorn odoo_mcp.app:create_app --factory --host 127.0.0.1 --port 8071
```

## Despliegue EC2

Archivos operativos:

- [`../server_config/services/odoo_mcp/odoo-mcp.service`](../server_config/services/odoo_mcp/odoo-mcp.service)
- [`../server_config/services/odoo_mcp/odoo-service-mcp-wants.conf`](../server_config/services/odoo_mcp/odoo-service-mcp-wants.conf)
- [`../server_config/services/odoo_mcp/odoo-mcp-http.conf`](../server_config/services/odoo_mcp/odoo-mcp-http.conf)
- [`../server_config/services/odoo_mcp/odoo-mcp-https.conf`](../server_config/services/odoo_mcp/odoo-mcp-https.conf)
- [`../server_config/services/odoo_mcp/odoo-mcp.env.example`](../server_config/services/odoo_mcp/odoo-mcp.env.example)
- [`../server_config/services/odoo_mcp/deploy_odoo_mcp.sh`](../server_config/services/odoo_mcp/deploy_odoo_mcp.sh)

DNS:

- [`../server_config/infra/scripts/configure_route53.sh`](../server_config/infra/scripts/configure_route53.sh) ahora también hace `UPSERT` de `mcp.odootest.mvpstart.click`.

### Ciclo de vida systemd

`odoo-mcp.service` depende de `odoo.service` y se detiene cuando Odoo se detiene. Para evitar que el MCP quede abajo despues de mantenimientos de Odoo, el despliegue instala el drop-in `/etc/systemd/system/odoo.service.d/10-odoo-mcp.conf` desde [`../server_config/services/odoo_mcp/odoo-service-mcp-wants.conf`](../server_config/services/odoo_mcp/odoo-service-mcp-wants.conf).

El contrato esperado es:

- `systemctl stop odoo` detiene tambien `odoo-mcp`.
- `systemctl start odoo` arranca tambien `odoo-mcp`.
- `systemctl restart odoo` reinicia el ciclo completo y deja `odoo-mcp` activo despues de Odoo.

Verificacion rapida despues de mantenimiento:

```bash
sudo systemctl is-active odoo odoo-mcp
sudo ss -ltnp | grep ':8071'
curl -i https://mcp.odootest.mvpstart.click/healthz
```

## Tools MCP

- `describe_server_capabilities`
- `count_employees`
- `search_employees`
- `get_employee_by_id`
- `count_attendance_records`
- `search_attendance_records`
- `get_attendance_record_by_id`
- `get_employee_attendance_summary`
- `count_hr_biometric_events`
- `search_hr_biometric_events`
- `get_hr_biometric_event_by_id`
- `get_devlyn_catalogs`
- `get_branch_attendance_report`
- `search_dahua_raw_requests`
- `count_dahua_normalized_events`
- `search_dahua_normalized_events`
- `get_dahua_normalized_event_by_id`
- `search_dahua_quarantine_events`
- `get_dahua_device_status`
- `search_projects`
- `search_tasks`
- `get_task_by_id`
- `count_helpdesk_tickets`
- `get_helpdesk_catalogs`
- `describe_helpdesk_ticket_schema`
- `search_helpdesk_tickets`
- `get_helpdesk_ticket_by_id`
- `search_users`
- `search_contacts`

Patrón recomendado:

- `count_*` para medir cardinalidad por filtro
- `search_*` para explorar páginas con `limit`, `cursor` y `detail_level=summary`
- `get_*_by_id` para ampliar un registro puntual
- `get_devlyn_catalogs` antes de `get_branch_attendance_report`
- para tareas de proyecto, usa `search_projects` para ubicar el proyecto y luego `search_tasks(project_ids=[...])`
- `search_projects` tolera variantes simples con y sin acento, por ejemplo `Biométricos` y `biometricos`

## Contrato de volumen

- `count_*`
  Respuesta mínima. No devuelve filas en `items`.
- `search_*` y tools de listado
  Default: `detail_level=summary`.
- `search_tasks`
  El default ya devuelve `assignees`, `project_name` y `stage_name`; no hace falta pedir `full` para saber responsables y etapa.
  Además agrega `pending_count`, `stage_breakdown`, `assignee_breakdown` y `top_pending_tasks` en `summary`.
- `detail_level`
  Valores: `summary`, `standard`, `full`.
- `include_fields`
  Lista opcional de campos top-level extra para enriquecer una respuesta compacta.
- `truncate_text`
  Límite opcional de caracteres por string. Usa `null` o valores `<= 0` para desactivar truncado.
- `truncated`
  Indica que la respuesta fue compactada o que aún hay más datos relevantes por explorar.
- `summary.total_count`
  Cardinalidad total para búsquedas paginadas.
- `summary.matched_count`
  Cardinalidad total para counts.
- `next_cursor`
  Cursor opaco para continuar la exploración.
- tool errors
  Cuando una tool falla, `isError=true` expone un payload estructurado con `error_code`, `message`, `retryable`, `suggested_arguments` y `details`.

Notas de migración:

- antes, varias tools devolvían páginas relativamente amplias por defecto
- ahora, el default está optimizado para agentes y conversaciones largas
- para aproximar el comportamiento anterior, usa `detail_level=standard` o `detail_level=full` junto con `limit`

## Recursos MCP

- `odoo-mcp://server/overview`
- `odoo-mcp://server/tool-catalog`
- `odoo-mcp://server/usage-guide`
- `odoo-mcp://server/response-envelope`
- `odoo-mcp://server/filter-reference`
- `odoo-mcp://schemas/{domain_name}`

## Snippets de conexión

### OpenAI Codex

```toml
[mcp_servers.devlyn_odoo]
url = "https://mcp.odootest.mvpstart.click/mcp"
http_headers = { "X-API-Key" = "REPLACE_WITH_TOKEN" }
```

### Claude Code / Claude Desktop

```json
{
  "mcpServers": {
    "devlyn-odoo": {
      "url": "https://mcp.odootest.mvpstart.click/mcp",
      "headers": {
        "X-API-Key": "REPLACE_WITH_TOKEN"
      }
    }
  }
}
```

### Gemini-compatible MCP client

Si el cliente soporta header custom:

```json
{
  "url": "https://mcp.odootest.mvpstart.click/mcp",
  "headers": {
    "X-API-Key": "REPLACE_WITH_TOKEN"
  }
}
```

Si solo soporta bearer:

```http
Authorization: Bearer REPLACE_WITH_TOKEN
```

## Validación manual

Health:

```bash
curl -i https://mcp.odootest.mvpstart.click/healthz
```

Tools list:

```bash
curl -i https://mcp.odootest.mvpstart.click/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H 'MCP-Protocol-Version: 2025-06-18' \
  -H 'X-API-Key: REPLACE_WITH_TOKEN' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

Smoke con cliente MCP oficial:

```bash
python3 - <<'PY'
import asyncio
import httpx
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client

TOKEN = "REPLACE_WITH_TOKEN"
URL = "https://mcp.odootest.mvpstart.click/mcp"

async def main():
    async with httpx.AsyncClient(headers={"X-API-Key": TOKEN}) as client:
        async with streamable_http_client(URL, http_client=client) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                print("tools", len(tools.tools))
                resources = await session.list_resources()
                print("resources", len(resources.resources))
                result = await session.call_tool("describe_server_capabilities")
                print(result.content[0].text)

asyncio.run(main())
PY
```
