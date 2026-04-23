# Runbook de Deploy y Backfill - Intermitencias

Fecha de version: `2026-04-21`

## Objetivo

Operar el rollout de intermitencias persistidas del modulo
`devlyn_dahua_attendance_reporting` sin alterar el contrato del sync biometrico
actual y dejando trazabilidad completa de:

- backfill historico
- catch-up final post deploy
- reparaciones puntuales
- fallback de raw backfill solo si existe gap real de pipeline

## Componentes involucrados

- addon Odoo:
  `odoo_biometric/module/devlyn_dahua_attendance_reporting`
- servicio Odoo:
  `devlyn.attendance.journey.service`
- modelos persistidos:
  `devlyn.attendance.journey`,
  `devlyn.attendance.journey.segment`,
  `devlyn.attendance.journey.run`
- worker:
  `attendance-sync-worker`
- fallback excepcional:
  `dahua_interface/attendance_sync_backfill.py`
- wrapper operativo:
  `server_config/infra/scripts/run_devlyn_attendance_journey_batch.sh`

## Metodos disponibles desde Odoo shell

Snippet base:

```bash
sudo -u odoo /usr/bin/odoo shell -c /etc/odoo/odoo.conf -d devlyn_com
```

Dentro del shell:

```python
service = env["devlyn.attendance.journey.service"]

service.preview_journey(employee_id=24367, local_date="2026-03-26")

service.rebuild_journey(employee_id=24367, local_date="2026-03-26")

service.rebuild_journeys(
    date_from="2026-03-20",
    date_to="2026-04-21",
    batch_size=500,
    run_type="backfill",
    mode="dry_run",
)
```

## Wrapper de batch

Wrapper listo para shell del host Odoo:

```bash
MODE=dry-run \
RUN_TYPE=backfill \
DATE_FROM=2026-03-20 \
DATE_TO=2026-04-21 \
BATCH_SIZE=500 \
OUTPUT_JSON=/var/tmp/devlyn_journey_backfill_dry_run.json \
server_config/infra/scripts/run_devlyn_attendance_journey_batch.sh
```

Variables soportadas:

- `MODE`: `dry-run`, `dry_run`, `apply`
- `RUN_TYPE`: `backfill`, `catchup`, `repair`
- `DATE_FROM`
- `DATE_TO`
- `BATCH_SIZE`
- `EMPLOYEE_IDS`: lista separada por comas
- `COMMIT_MODE`: `auto`, `true`, `false`
- `ODOO_BIN`
- `ODOO_CONFIG`
- `ODOO_DB`
- `ODOO_USER`
- `OUTPUT_JSON`

## Prechecks antes del deploy

Validar addon y worker:

```bash
systemctl is-active odoo
systemctl is-active attendance-sync-worker
```

Capturar hora real de mantenimiento en UTC:

```bash
date -u +"%Y-%m-%dT%H:%M:%SZ"
```

Tomar snapshot del cursor y conteos base:

```bash
sudo -u odoo /usr/bin/odoo shell -c /etc/odoo/odoo.conf -d devlyn_com <<'PY'
import json

cursor = env["hr.biometric.sync.cursor"].search([("name", "=", "main")], limit=1)
summary = {
    "cursor": {
        "id": cursor.id,
        "last_normalized_event_id": cursor.last_normalized_event_id,
        "last_event_occurred_at_utc": str(cursor.last_event_occurred_at_utc or ""),
        "last_success_at": str(cursor.last_success_at or ""),
    },
    "counts": {
        "hr_attendance": env["hr.attendance"].search_count([("biometric_source", "=", "biometric_v1")]),
        "journey": env["devlyn.attendance.journey"].search_count([]),
        "segment": env["devlyn.attendance.journey.segment"].search_count([]),
        "journey_run": env["devlyn.attendance.journey.run"].search_count([]),
    },
}
print(json.dumps(summary, indent=2, sort_keys=True))
PY
```

## Secuencia normal de deploy

### 1. Detener el worker

```bash
systemctl stop attendance-sync-worker
systemctl is-active attendance-sync-worker || true
```

### 2. Deploy y upgrade del addon

```bash
MODULE=devlyn_dahua_attendance_reporting \
MODULE_OPERATION=upgrade \
DB_NAME=devlyn_com \
server_config/infra/scripts/install_odoo_module.sh
```

### 3. Backfill dry-run

```bash
MODE=dry-run \
RUN_TYPE=backfill \
DATE_FROM=2026-03-20 \
DATE_TO=$(date +%F) \
OUTPUT_JSON=/var/tmp/devlyn_journey_backfill_dry_run.json \
server_config/infra/scripts/run_devlyn_attendance_journey_batch.sh
```

Validar el JSON de salida:

- `key_count`
- `segment_count`
- `intermittence_count`
- `error_count = 0`

### 4. Backfill apply

```bash
MODE=apply \
RUN_TYPE=backfill \
DATE_FROM=2026-03-20 \
DATE_TO=$(date +%F) \
OUTPUT_JSON=/var/tmp/devlyn_journey_backfill_apply.json \
server_config/infra/scripts/run_devlyn_attendance_journey_batch.sh
```

### 5. Reiniciar el worker

```bash
systemctl start attendance-sync-worker
systemctl is-active attendance-sync-worker
```

### 6. Esperar drenado del backlog normal

Revisar logs y cursor hasta que el worker vuelva a ritmo estable:

```bash
journalctl -u attendance-sync-worker -n 100 --no-pager
```

### 7. Catch-up final post deploy

Regla:

- `DATE_FROM` = `maintenance_start_local_date - 1 dia`
- `DATE_TO` = fecha local actual

Ejemplo:

```bash
MODE=apply \
RUN_TYPE=catchup \
DATE_FROM=2026-04-20 \
DATE_TO=2026-04-21 \
OUTPUT_JSON=/var/tmp/devlyn_journey_catchup_apply.json \
server_config/infra/scripts/run_devlyn_attendance_journey_batch.sh
```

## Validaciones post deploy

Verificar que no queden jornadas faltantes para el rango del catch-up:

```bash
sudo -u odoo /usr/bin/odoo shell -c /etc/odoo/odoo.conf -d devlyn_com <<'PY'
from collections import Counter

service = env["devlyn.attendance.journey.service"]
keys = service._collect_range_keys("2026-04-20", "2026-04-21")
journeys = env["devlyn.attendance.journey"].search([
    ("local_date", ">=", "2026-04-20"),
    ("local_date", "<=", "2026-04-21"),
])
journey_keys = {(journey.employee_id.id, journey.local_date) for journey in journeys}
missing = sorted(keys - journey_keys)
states = Counter(journeys.mapped("day_state"))

print({
    "expected_keys": len(keys),
    "journey_rows": len(journeys),
    "missing_count": len(missing),
    "states": dict(states),
})
if missing:
    print({"missing_sample": missing[:20]})
PY
```

Verificar corridas persistidas:

```bash
sudo -u odoo /usr/bin/odoo shell -c /etc/odoo/odoo.conf -d devlyn_com <<'PY'
runs = env["devlyn.attendance.journey.run"].search([], limit=10, order="id desc")
for run in runs:
    print({
        "id": run.id,
        "run_type": run.run_type,
        "mode": run.mode,
        "status": run.status,
        "date_from": str(run.date_from),
        "date_to": str(run.date_to),
        "key_count": run.key_count,
        "processed_count": run.processed_count,
        "segment_count": run.segment_count,
        "intermittence_count": run.intermittence_count,
        "error_count": run.error_count,
    })
PY
```

## Reparacion puntual

Rebuild por rango especifico:

```bash
MODE=apply \
RUN_TYPE=repair \
DATE_FROM=2026-04-10 \
DATE_TO=2026-04-10 \
EMPLOYEE_IDS=24367,40739 \
server_config/infra/scripts/run_devlyn_attendance_journey_batch.sh
```

## Fallback de raw backfill

Solo activar si existe evidencia real de hueco en:

- `normalized_event`
- `hr.biometric.event`
- `hr.attendance`

No usar como camino feliz del rollout de intermitencias.

Secuencia:

1. Correr `dahua_interface/attendance_sync_backfill.py` en `dry-run`.
2. Validar consistencia de conteos y rango faltante.
3. Ejecutar `apply`.
4. Rerun de `catchup` de jornadas sobre el rango local afectado.

Wrapper existente:

```bash
MODE=dry-run server_config/infra/scripts/run_devlyn_attendance_backfill.sh
MODE=apply server_config/infra/scripts/run_devlyn_attendance_backfill.sh
```

Nota:

- el raw backfill ya escribe `hr.attendance` con contexto
  `skip_devlyn_journey_rebuild=True`
- por eso no dispara rebuild por registro y deja el rebuild analitico para el
  batch posterior

## Criterios de rollback

Rollback operativo si ocurre cualquiera de estos puntos:

- upgrade del addon falla
- `error_count > 0` en backfill apply o catch-up
- el worker no vuelve a estado estable
- quedan llaves faltantes relevantes tras catch-up
- la validacion funcional del reporte actual rompe layout o conteos esperados

Acciones:

1. detener `attendance-sync-worker`
2. restaurar backup previo del deploy si aplica
3. revertir addon a version anterior
4. reiniciar Odoo
5. reiniciar `attendance-sync-worker`

## Criterios de aceptacion operativa

- el reporte `Asistencias por Sucursal` sigue igual por defecto
- `show_intermitencias=False` no cambia layout ni export actual
- `show_intermitencias=True` agrega las tres columnas nuevas al final
- el detalle separado muestra una fila por tramo
- el backfill historico es rerunnable sin duplicados
- el catch-up final deja alineado el rango afectado por mantenimiento
