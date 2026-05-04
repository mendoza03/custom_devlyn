# Tenant Maintenance Guide

## Qué hace

`tenant_maintenance.py` limpia artefactos viejos que deja el proceso de despliegue:

- backups remotos
- archivos remotos de ejecución
- imágenes Docker de deploy
- logs locales de deploy
- temporales locales de deploy
- logs locales de mantenimiento

No toca la imagen activa del tenant.

## Requisitos

- Estar en la raíz del clon `odoo-ccima/`
- Tener `python3`
- Tener acceso SSH al servidor
- Haber editado el bloque `CONFIG` de `tenant_maintenance.py`

## Valores que debes revisar

- `SSH_HOST`
- `SSH_PORT`
- `SSH_USER`
- `SSH_PASSWORD`
- `TARGET_TENANT`
- `KEEP_REMOTE_BACKUPS`
- `KEEP_REMOTE_ARCHIVES`
- `KEEP_REMOTE_IMAGES`
- `KEEP_LOCAL_DEPLOY_LOGS`
- `KEEP_LOCAL_DEPLOY_TMP`
- `KEEP_LOCAL_MAINTENANCE_LOGS`

Uso conservador:

- `TARGET_TENANT = "habitta"`

Uso global:

- `TARGET_TENANT = "all"`

## Flujo recomendado

### 1. Simular limpieza

```bash
python3 tenant_maintenance.py --dry-run
```

Esto no borra nada. Solo muestra:

- cuántos backups viejos detectó
- cuántos archivos remotos viejos detectó
- cuántas imágenes viejas detectó
- cuántos logs y temporales locales detectó

### 2. Ejecutar limpieza real

```bash
python3 tenant_maintenance.py --apply
```

Esto sí borra lo que exceda la retención configurada.

## Qué conserva siempre

- la imagen activa definida en `.env`
- las últimas N corridas según tu política de retención
- el log de mantenimiento actual

## Dónde queda el reporte

- `maintenance_logs/<run_id>/maintenance_report.json`
- `maintenance_logs/<run_id>/run.log`

## Política sugerida

- `KEEP_REMOTE_BACKUPS = 3`
- `KEEP_REMOTE_ARCHIVES = 3`
- `KEEP_REMOTE_IMAGES = 3`
- `KEEP_LOCAL_DEPLOY_LOGS = 10`
- `KEEP_LOCAL_DEPLOY_TMP = 3`
- `KEEP_LOCAL_MAINTENANCE_LOGS = 10`

## Recomendación operativa

Haz primero:

```bash
python3 tenant_maintenance.py --dry-run
```

Revisa el resumen y luego corre:

```bash
python3 tenant_maintenance.py --apply
```
