# Devlyn Dahua Attendance Reporting

Addon Odoo dedicado al reporte operativo de asistencias biométricas Dahua por sucursal.

## Objetivo

Resolver el reporte **Asistencias por Sucursal** usando solo biometría de asistencia Dahua y manteniendo separados:

- la autenticación biométrica web
- el worker de sincronización Dahua hacia Odoo
- el reporteo operativo y los catálogos vivos Devlyn

## Alcance funcional

- Catálogos vivos Devlyn dentro de Odoo
- Carga inicial de catálogos desde seeds versionados
- Visor interactivo bajo `Asistencias > Reportes > Asistencias por Sucursal`
- Wizard de exportación XLSX reutilizable desde el visor
- Reporte biométrico basado en `hr.attendance` + `hr.biometric.event`
- Clasificación explícita de casos `SIN_SUCURSAL`

## Fuera de alcance

Este addon **no** cubre nada del flujo biométrico de login/logout:

- reconocimiento facial
- `auth-gateway`
- Cognito
- modelos `biometric.auth.*`
- modelo `biometric.device`
- menús o procesos de autenticación web

## Dependencias

- `hr_attendance`
- `hr_biometric_attendance_sync`
- dependencia Python: `xlsxwriter`

## Estructura

- `models/`
  Catálogos vivos y visor interactivo.
- `wizard/`
  Wizard modal de exportación y recarga manual de catálogos.
- `services/`
  Carga de seeds, utilitarios de derivación y construcción del dataset/exportación.
- `views/`
  Menús, formularios, lista embebida y pantallas de catálogos.
- `data/seed/`
  Seeds normalizados de catálogos.
- `tests/`
  Pruebas unitarias de utilitarios del reporte.

## Modelos principales

### Catálogos

- `devlyn.catalog.region`
- `devlyn.catalog.zone`
- `devlyn.catalog.district`
- `devlyn.catalog.branch`
- `devlyn.catalog.format`
- `devlyn.catalog.status`
- `devlyn.catalog.optical.level`

### Reporte

- `devlyn.attendance.branch.report.viewer`
- `devlyn.attendance.branch.report.line`
- `devlyn.attendance.branch.report.wizard`
- `devlyn.attendance.branch.segment.viewer`
- `devlyn.attendance.branch.segment.line`
- `devlyn.attendance.journey`
- `devlyn.attendance.journey.segment`
- `devlyn.attendance.journey.run`

## Flujo funcional

### 1. Catálogos

Los catálogos fuente se versionan en `data/seed/` y se cargan a tablas Odoo mediante:

- `post_init_hook` al instalar el addon
- acción manual `Recargar catálogos`

La intención es que estas tablas queden vivas en Odoo y más adelante puedan ser actualizadas por un proceso externo de altas, bajas y cambios sin depender del Excel en runtime.

### 2. Visor interactivo

Al entrar al menú:

- se crea un visor transitorio
- el rango por defecto es el mes en curso
- se calculan las líneas del reporte
- se muestran filtros, contadores y tabla navegable

Botones del visor:

- `Actualizar vista`
- `Exportar XLSX`
- `Limpiar filtros`

### 3. Wizard de exportación

El wizard se conserva como flujo oficial de exportación.

No es la pantalla principal del menú, pero sí la pieza que genera el archivo XLSX. Se abre desde el visor heredando los filtros activos del usuario.

## Fuente de datos

La fuente oficial del reporte es:

- `hr.attendance` como base
- `hr.biometric.event` por `biometric_checkin_event_id`
- `hr.biometric.event` por `biometric_checkout_event_id`

El reporte trabaja solo con:

- `hr.attendance.biometric_source = biometric_v1`

No incluye:

- asistencias manuales
- asistencias no biométricas
- eventos de login/logout
- eventos crudos como salida final del reporte

## Regla de sucursal

La sucursal se deriva así:

1. `device_id_resolved` del check-in
2. fallback al `device_id_resolved` del check-out
3. si no hay dispositivo resoluble, clasificar como `SIN_SUCURSAL`

Extracción de centro desde `DeviceID`:

- patrón esperado: `DEVLYN_A753_01`
- centro derivado: `A753`

Ese centro busca contra:

- `devlyn.catalog.branch.center_code`

Si no hay match válido, la fila queda en el bolsón `SIN_SUCURSAL`.

## Layout del reporte

El dataset se consolida a:

- una fila por empleado y fecha local

Columnas actuales:

1. `Fecha`
2. `Id Empleado`
3. `Nombre Completo`
4. `Id Centro`
5. `Sucursal`
6. `Nombre Sucursal`
7. `Nivel Óptica Ventas`
8. `Formato`
9. `Estatus`
10. `Región`
11. `Zona`
12. `Distrito`
13. `Hora Entrada`
14. `Hora Salida`
15. `Tiempo efectivo`

Cuando el usuario activa `Mostrar intermitencias`, el layout agrega al final:

16. `Intermitencias`
17. `Tiempo intermitente`
18. `Estado del día`

El detalle fino vive en un visor separado con una fila por tramo.

## Intermitencias persistidas

La v1 de intermitencias no cambia la semantica del sync biometrico. Se monta
como una proyeccion persistida sobre `hr.attendance`.

Modelos:

- `devlyn.attendance.journey`
  una jornada por `empleado + fecha local`
- `devlyn.attendance.journey.segment`
  un tramo por cada `hr.attendance` biometrico derivado
- `devlyn.attendance.journey.run`
  auditoria de backfill, catch-up y repair

Estados de jornada:

- `open`
- `closed`
- `closed_auto`

Triggers:

- `create`, `write` y `unlink` de `hr.attendance`
- solo para `biometric_source = biometric_v1`
- el backfill raw excepcional desactiva el rebuild por registro con contexto
  `skip_devlyn_journey_rebuild`

## Operacion de rebuild

Servicio Odoo:

- `env["devlyn.attendance.journey.service"].preview_journey(employee_id, local_date)`
- `env["devlyn.attendance.journey.service"].rebuild_journey(employee_id, local_date)`
- `env["devlyn.attendance.journey.service"].rebuild_journeys(...)`
- `env["devlyn.attendance.journey.service"].run_batch(...)`

Wrapper de infraestructura:

- `server_config/infra/scripts/run_devlyn_attendance_journey_batch.sh`

Runbook operativo:

- `docs/reports/RUNBOOK_INTERMITENCIAS_DEPLOY_Y_BACKFILL_2026-04-21.md`

## Archivos clave

- `models/devlyn_catalog_models.py`
- `models/devlyn_attendance_branch_report_viewer.py`
- `wizard/devlyn_attendance_branch_report_wizard.py`
- `services/catalog_loader.py`
- `services/report_export.py`
- `services/report_utils.py`
- `views/devlyn_attendance_branch_report_views.xml`

## Instalación y actualización

Instalación funcional esperada:

```bash
sudo -u odoo /usr/bin/odoo -c /etc/odoo/odoo.conf -d devlyn_com -u devlyn_dahua_attendance_reporting --stop-after-init
```

Después de actualizar:

- validar que el módulo quede `installed`
- validar que los catálogos carguen
- validar que el visor abra y precargue el mes actual
- validar que el wizard exporte respetando los filtros del visor

## Pruebas locales

Pruebas usadas durante el desarrollo:

```bash
python3 -m unittest discover -s odoo_biometric/module/devlyn_dahua_attendance_reporting/tests -p 'test_*.py'
python3 -m py_compile $(find odoo_biometric/module/devlyn_dahua_attendance_reporting -type f -name '*.py')
```

## Referencias

- Catálogos fuente: `docs/catalogs/`
- Diagnóstico funcional y warnings heredados:
  `docs/reports/DIAGNOSTICO_REPORTE_ASISTENCIAS_SUCURSAL_2026-04-21.md`
- Runbook operativo de deploy, backfill y catch-up:
  `docs/reports/RUNBOOK_INTERMITENCIAS_DEPLOY_Y_BACKFILL_2026-04-21.md`
- Handoff tecnico de la iteracion y del deploy ejecutado:
  `docs/reports/HANDOFF_INTERMITENCIAS_2026-04-22.md`
