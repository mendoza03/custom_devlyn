# Tenant Deploy Operator Runbook

## Propósito

Este documento describe el flujo técnico de `tenant_deploy.py` y el fallback manual si el operador necesita intervenir sin depender del script.

La salida en consola puede simplificarse desde el propio código con `COMPACT_OUTPUT = True` en `tenant_deploy.py`. Ese modo no cambia el deploy ni los logs persistidos; solo reduce el ruido visible para el usuario final.

## Flujo automatizado

1. Preparación local del source bundle
2. Probe remoto no destructivo
3. Cálculo del plan de módulos
4. Creación de backup remoto
5. Build remoto de imagen derivada desde la `ODOO_IMAGE` activa
6. Creación de `/opt/odoo-venv` y carga de dependencias Python dentro de ese `venv`
7. Validación del runtime Python antes de tocar la DB
8. `docker compose run` con la imagen nueva para `-u` y opcional `-i`
9. Swap de `.env`, `.env.final`, `.env.dry-run`
10. `docker compose up -d odoo`
11. Validación HTTP y validación de estados de módulos
12. Validación de salud final del tenant: `odoo`, `db` y endpoints HTTP
13. Rollback automático si hay error después del backup

## Rutas operativas

- Stacks: `/home/ubuntu/ccima-prod/stacks/<tenant>`
- Backups: `/home/ubuntu/ccima-prod/backups/<tenant>-deploy-<run_id>`
- Logs remotos: `/home/ubuntu/ccima-prod/archive/deployments/<tenant>/<run_id>`
- Logs locales de mantenimiento: `maintenance_logs/<run_id>`

## Artefactos remotos esperados

- `run.log`
- `build.log`
- `runtime_validation.log`
- `upgrade.log`
- `rollback.log` si aplica
- `source_manifest.json`
- `run_manifest.json`
- `source_context.tar.gz`
- `remote_apply.py`

## Modo de consola

`tenant_deploy.py` ya maneja dos formas de presentar el stream remoto:

- `COMPACT_OUTPUT = True`: muestra solo hitos y errores
- `COMPACT_OUTPUT = False`: deja pasar el stream remoto completo

Incluso en modo compacto, el detalle completo sigue quedando en:

- `deploy_logs/<run_id>/remote_apply_stream.log`
- `/home/ubuntu/ccima-prod/archive/deployments/<tenant>/<run_id>/run.log`

Al final del deploy, el resumen local ahora imprime además:

- `Salud tenant`
- `HTTP final`
- `Odoo contenedor`
- `DB contenedor`

## Procedimiento manual de emergencia

### 1. Entrar al stack

```bash
cd /home/ubuntu/ccima-prod/stacks/<tenant>
```

### 2. Hacer backup

```bash
mkdir -p /home/ubuntu/ccima-prod/backups/<tenant>-manual-<fecha>
cp .env .env.final .env.dry-run docker-compose.yml /home/ubuntu/ccima-prod/backups/<tenant>-manual-<fecha>/
docker compose up -d db
docker compose exec -T -e PGPASSWORD="$POSTGRES_PASSWORD" db pg_dump -U "$POSTGRES_USER" -d "$BUSINESS_DB" -Fc --no-owner --no-privileges > /home/ubuntu/ccima-prod/backups/<tenant>-manual-<fecha>/<tenant>.dump
docker compose exec -T -e PGPASSWORD="$POSTGRES_PASSWORD" db pg_dumpall -g -U "$POSTGRES_USER" > /home/ubuntu/ccima-prod/backups/<tenant>-manual-<fecha>/globals.sql
docker run --rm -v "${WEB_VOLUME_NAME}:/src:ro" -v "/home/ubuntu/ccima-prod/backups/<tenant>-manual-<fecha>:/backup" postgres:16 bash -lc "cd /src && tar --warning=no-file-changed --exclude='./sessions' -czf /backup/web.tar.gz ."
```

### 3. Build de imagen nueva

El contexto debe contener:

- `Dockerfile`
- `addons/<addon>/`
- `build_requirements.txt`

El `Dockerfile` generado por el script ahora:

- crea `/opt/odoo-venv`
- instala dependencias Python dentro de ese `venv`
- expone un wrapper `odoo` para que Odoo vea esas librerías sin mezclar paquetes con el Python del sistema

```bash
docker build -t devaie/odoo_ccima:<tenant>-manual-<fecha> <ruta_contexto>
```

### 4. Validar el runtime antes del upgrade

```bash
docker run --rm --entrypoint /bin/sh devaie/odoo_ccima:<tenant>-manual-<fecha> -lc 'python3 --version'
docker run --rm --entrypoint /opt/odoo-venv/bin/python devaie/odoo_ccima:<tenant>-manual-<fecha> -c "import numerize, numpy_financial"
docker run --rm --entrypoint /bin/sh devaie/odoo_ccima:<tenant>-manual-<fecha> -lc 'odoo --version'
```

### 5. Ejecutar upgrade/install con la imagen nueva

Genera una copia temporal de `.env` con `ODOO_IMAGE` apuntando al tag nuevo.

```bash
docker compose --env-file /tmp/<tenant>.env run --rm --no-deps -T odoo odoo -d "$BUSINESS_DB" --stop-after-init -c /etc/odoo/odoo.conf -u <modulo1,modulo2>
```

Si hace falta instalar módulos ya presentes en DB como `uninstalled`:

```bash
docker compose --env-file /tmp/<tenant>.env run --rm --no-deps -T odoo odoo -d "$BUSINESS_DB" --stop-after-init -c /etc/odoo/odoo.conf -i <modulo1,modulo2>
```

### 6. Aplicar nueva imagen al tenant

Actualiza:

- `.env`
- `.env.final`
- `.env.dry-run`

Luego:

```bash
docker compose up -d odoo
```

### 7. Validar

```bash
docker compose ps
curl -I http://127.0.0.1:<puerto>/
curl -I http://127.0.0.1:<puerto>/web/login
docker compose exec -T -e PGPASSWORD="$POSTGRES_PASSWORD" db psql -U "$POSTGRES_USER" -d "$BUSINESS_DB" -At -F '|' -c "select name,state from ir_module_module where name in ('<modulo>');"
```

Si el flujo es por script, esta validación ya queda consolidada en `run_manifest.json` bajo `http_validation`, `post_apply_module_states` y `tenant_health`.

## Rollback manual

### 1. Restaurar `.env*`

```bash
cp /home/ubuntu/ccima-prod/backups/<tenant>-manual-<fecha>/.env .
cp /home/ubuntu/ccima-prod/backups/<tenant>-manual-<fecha>/.env.final .
cp /home/ubuntu/ccima-prod/backups/<tenant>-manual-<fecha>/.env.dry-run .
```

### 2. Restaurar base

```bash
docker compose stop odoo
cat /home/ubuntu/ccima-prod/backups/<tenant>-manual-<fecha>/globals.sql | docker compose exec -T -e PGPASSWORD="$POSTGRES_PASSWORD" db psql -U "$POSTGRES_USER" -d postgres || true
docker compose exec -T -e PGPASSWORD="$POSTGRES_PASSWORD" db dropdb -U "$POSTGRES_USER" --if-exists "$BUSINESS_DB"
docker compose exec -T -e PGPASSWORD="$POSTGRES_PASSWORD" db createdb -U "$POSTGRES_USER" "$BUSINESS_DB"
cat /home/ubuntu/ccima-prod/backups/<tenant>-manual-<fecha>/<tenant>.dump | docker compose exec -T -e PGPASSWORD="$POSTGRES_PASSWORD" db pg_restore -U "$POSTGRES_USER" -d "$BUSINESS_DB" --clean --if-exists --no-owner --no-privileges
docker run --rm -v "${WEB_VOLUME_NAME}:/dst" -v "/home/ubuntu/ccima-prod/backups/<tenant>-manual-<fecha>:/backup" postgres:16 bash -lc 'rm -rf /dst/* /dst/.[!.]* /dst/..?* 2>/dev/null || true; cd /dst && tar -xzf /backup/web.tar.gz'
docker compose up -d odoo
```

## Riesgos conocidos

- Si el addon depende de otro custom no actualizado y hay incompatibilidad, el build pasará pero el upgrade puede fallar.
- Si el build falla o si la validación de `venv` falla, el rollback automático debe dejar el tenant corriendo con la imagen previa. En ese escenario la base no debería quedar tocada.
- `absent` no se instala automáticamente en esta versión.
- El build sobrescribe el addon seleccionado en `/mnt/addons-sam`, pero no resuelve limpieza de módulos no seleccionados.

## Mantenimiento y retención

El mantenimiento quedó separado de `tenant_deploy.py` en `tenant_maintenance.py`.

Objetivo:

- conservar solo cierta cantidad de backups por tenant
- conservar solo cierta cantidad de archivos remotos por tenant
- conservar solo cierta cantidad de imágenes de deploy por tenant
- limpiar logs y temporales locales viejos

Comandos:

```bash
python3 tenant_maintenance.py --dry-run
python3 tenant_maintenance.py --apply
```

Comportamiento esperado:

- nunca borra la imagen activa declarada en `.env`
- no toca el stack del tenant ni reinicia contenedores
- deja reporte local en `maintenance_logs/<run_id>/maintenance_report.json`

Guía detallada:

- `MANTENIMIENTO.md`
