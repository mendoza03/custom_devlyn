# Handoff Tecnico - Intermitencias y Deploy Controlado

Fecha de cierre de esta iteracion: `2026-04-22`

## Objetivo de este handoff

Dejar contexto util para futuros agentes o developers sobre:

- que se implemento en `devlyn_dahua_attendance_reporting`
- que se desplego en el servidor de pruebas
- que incidente post-deploy aparecio
- que hotfix adicional se aplico
- cual es el estado final en Git y en el ambiente remoto

Este documento no duplica secretos. Si hace falta acceder al servidor o a
credenciales, revisar `config/servers.json` y no copiar esos valores a nuevos
documentos.

## Alcance implementado

Se implemento la capa persistida de **Intermitencias** sobre `hr.attendance`
biometrico, sin cambiar la semantica del sync `raw toggle`.

Cambios principales:

- nuevos modelos:
  `devlyn.attendance.journey`,
  `devlyn.attendance.journey.segment`,
  `devlyn.attendance.journey.run`
- nuevo servicio:
  `devlyn.attendance.journey.service`
- hooks en `hr.attendance` para reconstruccion idempotente por
  `employee_id + local_date`
- enriquecimiento opcional del reporte resumen `Asistencias por Sucursal` con:
  `Intermitencias`, `Tiempo intermitente`, `Estado del dia`
- nuevo visor y exportacion de detalle por tramo:
  `Detalle de Intermitencias`
- wrapper operativo:
  `server_config/infra/scripts/run_devlyn_attendance_journey_batch.sh`
- documentacion tecnica y runbook de deploy/backfill

## Archivos mas relevantes

Addon principal:

- `odoo_biometric/module/devlyn_dahua_attendance_reporting/models/devlyn_attendance_journey.py`
- `odoo_biometric/module/devlyn_dahua_attendance_reporting/models/hr_attendance.py`
- `odoo_biometric/module/devlyn_dahua_attendance_reporting/models/devlyn_attendance_branch_report_viewer.py`
- `odoo_biometric/module/devlyn_dahua_attendance_reporting/models/devlyn_attendance_branch_segment_viewer.py`
- `odoo_biometric/module/devlyn_dahua_attendance_reporting/services/journey_service.py`
- `odoo_biometric/module/devlyn_dahua_attendance_reporting/services/report_export.py`
- `odoo_biometric/module/devlyn_dahua_attendance_reporting/views/devlyn_attendance_branch_report_views.xml`

Soporte operativo:

- `server_config/infra/scripts/run_devlyn_attendance_journey_batch.sh`
- `dahua_interface/attendance_sync_worker.py`
- `dahua_interface/attendance_sync_backfill.py`

Hotfix complementario:

- `custom_devlyn/models/models.py`

## Validacion local realizada antes del deploy

Comandos ejecutados localmente:

```bash
python3 -m py_compile $(find odoo_biometric/module/devlyn_dahua_attendance_reporting -type f -name '*.py')
python3 -m unittest discover -s odoo_biometric/module/devlyn_dahua_attendance_reporting/tests -p 'test_*.py'
bash -n server_config/infra/scripts/run_devlyn_attendance_journey_batch.sh
python3 -m py_compile custom_devlyn/models/models.py
```

Resultado:

- compilacion Python limpia
- `8` pruebas unitarias del addon en verde
- wrapper shell sin errores de sintaxis

## Deploy realizado

Ambiente intervenido:

- host Odoo: `erp.odootest.mvpstart.click`
- host SSH: revisar `config/servers.json`
- base de datos: `devlyn_com`
- servicios involucrados:
  `odoo`,
  `attendance-sync-worker`
- custom addons remoto:
  `/opt/odoo/custom-addons`

Fecha operativa del deploy:

- ventana ejecutada alrededor de `2026-04-22 01:27 UTC`

## Secuencia real aplicada

Se hizo lo siguiente:

1. backup previo del addon y snapshot de base
2. stop de `attendance-sync-worker`
3. deploy de archivos a `/opt/odoo/custom-addons`
4. upgrade manual del addon como usuario `odoo`
5. restart de `odoo`
6. backfill historico
7. restart del worker
8. catch-up final post-deploy
9. validaciones funcionales y de conteo

## Hallazgos operativos importantes durante el deploy

### 1. No usar `install_odoo_module.sh` en este host para este caso

El script existente intento ejecutar Odoo como `root` y fallo por
autenticacion peer de PostgreSQL.

Forma que si funciono:

```bash
sudo -u odoo /usr/bin/odoo \
  --addons-path=/opt/odoo/custom-addons,/usr/lib/python3/dist-packages/odoo/addons \
  -c /etc/odoo/odoo.conf \
  -d devlyn_com \
  -u devlyn_dahua_attendance_reporting \
  --stop-after-init
```

### 2. El wrapper de batch necesitaba preservar variables de entorno

Se corrigio `server_config/infra/scripts/run_devlyn_attendance_journey_batch.sh`
para exportar y preservar:

- `MODE`
- `RUN_TYPE`
- `DATE_FROM`
- `DATE_TO`
- `BATCH_SIZE`
- `EMPLOYEE_IDS`
- `COMMIT_MODE`

Sin ese ajuste, `sudo -u odoo` limpiaba variables y el wrapper no recibia el
modo o el rango esperado.

### 3. Ojo con permisos de `/opt/odoo/custom-addons`

Durante la extraccion se alteraron permisos del directorio y Odoo dejo de ver
addons. El estado correcto restaurado fue:

```bash
chown root:root /opt/odoo/custom-addons
chmod 755 /opt/odoo/custom-addons
```

## Backfill y catch-up ejecutados

Se uso fecha de inicio historica:

- `2026-03-20`

Corridas registradas:

- dry-run backfill:
  `run_id=2`,
  `processed_count=496`,
  `segment_count=636`,
  `intermittence_count=140`,
  `error_count=0`
- apply backfill:
  `run_id=3`,
  `processed_count=496`,
  `segment_count=636`,
  `intermittence_count=140`,
  `error_count=0`
- apply catch-up:
  `run_id=4`,
  rango `2026-04-20` a `2026-04-21`,
  `processed_count=40`,
  `updated_count=40`,
  `segment_count=45`,
  `intermittence_count=5`,
  `error_count=0`

Validacion posterior:

- `journey_count=496`
- `segment_count=636`
- `open_journeys=19`
- `closed_auto_journeys=160`
- `after_close_review_journeys=0`
- `intermittent_journeys=138`
- `catchup_missing_count=0`

## Incidente post-deploy y hotfix aplicado

Despues del deploy, al filtrar empleados en:

- `Asistencias por Sucursal`
- `Detalle de Intermitencias`

aparecio un RPC error sobre `hr.employee.name_search`.

### Causa raiz

`custom_devlyn/models/models.py` tenia un override heredado de `name_search`
con firma antigua:

- usaba `args=...`
- llamaba `super().name_search(..., args=args, ...)`

Eso es incompatible con Odoo `19`, donde `BaseModel.name_search()` espera
`domain=...`.

### Hotfix final aplicado

Se ajusto `custom_devlyn/models/models.py` para:

- usar la firma correcta de Odoo 19
- restaurar el formato visible del empleado como `ID - Nombre`
- recalcular `display_name` con `employee_number`
- mantener busqueda por numero exacto y por nombre

Validacion remota posterior:

- `display_name` de empleado `5812`:
  `5812 - BRAVO GARCIA ALMA LETICIA`
- `name_search('5812')` devuelve `5812 - BRAVO GARCIA ALMA LETICIA`
- `name_search('BRAVO')` devuelve resultados con formato `ID - Nombre`

## Estado final visible para usuarios

Al cierre de esta iteracion:

- el reporte resumen ya puede mostrar intermitencias mediante el checkbox
  `Mostrar intermitencias`
- existe el visor separado `Detalle de Intermitencias`
- el filtro de empleados vuelve a mostrar `ID - Nombre`
- el backend Odoo y el worker quedaron activos tras el deploy

No se detecto pendiente funcional abierto en el flujo principal del reporte.

## Estado final en Git

Rama publicada:

- `addons-devlyn`

Commit relevante publicado a GitHub:

- `7d57c26` `Add persisted intermitencias reporting flow`

Ese commit incluye:

- cambios del addon `devlyn_dahua_attendance_reporting`
- soporte de `dahua_interface`
- wrapper de batch
- hotfix en `custom_devlyn/models/models.py`
- documentacion asociada

## Ruido local que no se incluyo en el commit

Al cerrar esta iteracion quedaban cambios locales no funcionales que no deben
confundirse con el feature:

- `.gitignore`
- `custom_devlyn/models/__pycache__/models.cpython-312.pyc`
- `.vscode/`

Si otro agente entra despues, no debe asumir que esos cambios forman parte del
despliegue ni del commit publicado.

## Puntos de entrada recomendados para futuros agentes

Si el tema es funcional/reportes:

- empezar por
  `odoo_biometric/module/devlyn_dahua_attendance_reporting/README.md`
- luego leer
  `docs/reports/DIAGNOSTICO_REPORTE_ASISTENCIAS_SUCURSAL_2026-04-21.md`
- y este handoff

Si el tema es operacion o reparacion:

- leer primero
  `docs/reports/RUNBOOK_INTERMITENCIAS_DEPLOY_Y_BACKFILL_2026-04-21.md`
- revisar `devlyn.attendance.journey.run`
- usar el wrapper
  `server_config/infra/scripts/run_devlyn_attendance_journey_batch.sh`

Si el problema vuelve a ser filtro de empleados:

- revisar primero `custom_devlyn/models/models.py`
- confirmar `display_name`
- confirmar `name_search`

## Verificaciones rapidas recomendadas

Remoto:

```bash
sudo systemctl is-active odoo
sudo systemctl is-active attendance-sync-worker
```

Shell Odoo:

```python
Employee = env["hr.employee"]
print(Employee.name_search(name="5812", limit=5))

journey_count = env["devlyn.attendance.journey"].search_count([])
segment_count = env["devlyn.attendance.journey.segment"].search_count([])
print({"journey_count": journey_count, "segment_count": segment_count})
```

## Referencias cruzadas

- `docs/reports/DIAGNOSTICO_REPORTE_ASISTENCIAS_SUCURSAL_2026-04-21.md`
- `docs/reports/RUNBOOK_INTERMITENCIAS_DEPLOY_Y_BACKFILL_2026-04-21.md`
- `odoo_biometric/module/devlyn_dahua_attendance_reporting/README.md`
