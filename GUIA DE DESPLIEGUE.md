# Tenant Deploy Client Guide

## Qué hace este script

`tenant_deploy.py` sube uno o varios addons hacia un solo tenant del servidor `138.186.200.38`, construyendo una imagen local nueva en el servidor, dejando backup previo, logs y rollback automático si el proceso falla después de tocar base o filestore.

No usa GitHub Actions.

Desde esta version, la imagen derivada crea un `venv` en `/opt/odoo-venv`. Las dependencias Python de los addons ya no se instalan sobre el Python del sistema, con lo que se evita el fallo de PEP 668 al construir la imagen.

## Requisitos mínimos

- Estar parado en la raíz del clon `odoo-ccima/`
- Tener `python3`, `git`, `ssh`, `scp` y `tar`
- Tener acceso por terminal al servidor
- Haber editado el bloque `CONFIG` al inicio de `tenant_deploy.py`

## Qué valores debes cambiar

Edita estos valores en `tenant_deploy.py`:

- `SSH_USER`
- `SSH_PASSWORD`
- `TARGET_TENANT`
- `SOURCE_MODE`
- `GIT_REF`
- `LOCAL_SOURCE_PATH`
- `ADDON_NAMES`
- `INSTALL_MISSING`
- `UPGRADE_SELECTED`
- `COMPACT_OUTPUT`

El archivo ahora viene con un ejemplo real de despliegue hacia `habitta` con todos los addons del repo:

- `SSH_HOST = "138.186.200.38"`
- `SSH_PORT = 5003`
- `SSH_USER = "ubuntu"`
- `SSH_PASSWORD = "replace_root_or_server_password"`
- `TARGET_TENANT = "habitta"`
- `SOURCE_MODE = "github"`
- `GIT_REF = "origin/addons-ccima"`
- `ADDON_NAMES = []`

Debes reemplazar al menos `SSH_PASSWORD` antes de ejecutar.

Si tu servidor permite login directo por `root`, puedes usar:

- `SSH_USER = "root"`
- `SSH_PASSWORD = "<clave_root_real>"`

Defaults recomendados:

- `SOURCE_MODE = "github"` cuando quieres desplegar exactamente un commit o branch
- `SOURCE_MODE = "local"` cuando quieres subir lo que todavía no has hecho commit
- `UPGRADE_SELECTED = True`
- `INSTALL_MISSING = False`
- `COMPACT_OUTPUT = True` para que la consola muestre solo etapas y errores

## Modo compacto

El script ya no necesita un flag tipo `--compact`.

Se controla desde el bloque de configuración:

```python
COMPACT_OUTPUT = True
```

Comportamiento:

- `True`: la consola muestra solo hitos importantes como backup, build, runtime check, upgrade, validación y resumen final
- `False`: la consola muestra el stream remoto completo, útil para diagnóstico fino

Importante:

- aunque `COMPACT_OUTPUT = True`, el log detallado completo sigue quedando en `deploy_logs/<run_id>/remote_apply_stream.log`
- el resumen final ahora incluye una validación de salud del tenant:
  - `Salud tenant`
  - `HTTP final`
  - estado del contenedor `odoo`
  - estado del contenedor `db`

## Flujo recomendado

### Opción 1: validar sin tocar nada

```bash
python3 tenant_deploy.py --dry-run
```

Esto valida:

- acceso SSH
- acceso Docker
- tenant existente
- imagen base activa
- espacio libre
- addons detectados
- estado actual de módulos en la base
- plan de upgrade/install

No deja artefactos persistentes en el servidor.

## Opción 2: ejecutar de verdad

```bash
python3 tenant_deploy.py --apply
```

Esto sí hace:

- backup previo
- build de imagen nueva en el servidor
- validación técnica del runtime antes de tocar la base:
  - `python3 --version`
  - imports Python requeridos por los addons
  - `odoo --version`
- upgrade o install de módulos si aplica
- actualización de `.env`, `.env.final`, `.env.dry-run`
- restart del tenant
- validación HTTP
- validación final de salud del tenant actualizado:
  - contenedor `odoo` en ejecución
  - contenedor `db` en ejecución
  - health de Docker si existe
  - rutas HTTP del tenant respondiendo
- rollback automático si falla

Si el build o la validación del runtime fallan antes del upgrade de módulos, el script igual vuelve al estado anterior del tenant y no toca la base de datos.

Si el script termina bien, el resumen en pantalla ya no solo dice `DEPLOY OK`: también muestra si el tenant quedó sano a nivel de HTTP y contenedores.

## Dónde quedan los logs

Local:

- `deploy_logs/<run_id>/`
- `maintenance_logs/<run_id>/` para limpieza y retención

Servidor:

- `/home/ubuntu/ccima-prod/archive/deployments/<tenant>/<run_id>/`

## Cómo elegir fuente

### Despliegue desde GitHub

Usa:

- `SOURCE_MODE = "github"`
- `GIT_REF = "origin/addons-ccima"` o un commit/tag específico

El script ignora cambios locales sin commit.

### Despliegue desde tu carpeta local

Usa:

- `SOURCE_MODE = "local"`
- `LOCAL_SOURCE_PATH = "mi_addon"` para un solo addon
- `LOCAL_SOURCE_PATH = "."` o `LOCAL_SOURCE_PATH = "carpeta_addons"` para varios addons

Si `ADDON_NAMES = []`, el script toma todos los addons detectados en esa ruta.

## Qué no hace

- No despliega varios tenants al mismo tiempo
- No publica imágenes al registry
- No garantiza validación funcional del negocio
- No instala módulos nuevos que estén `absent` en la base actual

## Qué revisar si falla

- `deploy_logs/<run_id>/run.log`
- `deploy_logs/<run_id>/remote_apply_stream.log`
- `/home/ubuntu/ccima-prod/archive/deployments/<tenant>/<run_id>/run.log`
- `/home/ubuntu/ccima-prod/archive/deployments/<tenant>/<run_id>/runtime_validation.log`
- `/home/ubuntu/ccima-prod/archive/deployments/<tenant>/<run_id>/rollback.log`

## Limpieza de artefactos viejos

Existe un script separado para mantenimiento:

```bash
python3 tenant_maintenance.py --dry-run
python3 tenant_maintenance.py --apply
```

Ese flujo limpia:

- backups remotos viejos
- archivos remotos viejos
- imágenes Docker viejas de deploy
- logs y temporales locales viejos

Guía completa:

- `MANTENIMIENTO.md`
