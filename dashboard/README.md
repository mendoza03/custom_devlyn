# Dashboard Prototype

Prototipo local para inspeccionar la ingesta Dahua en tablas paginadas, conectado por defecto a la base real vía túnel SSH.

## Objetivo

Permitir análisis rápido de:

- requests crudos
- `access_control` normalizados con `UserID`
- eventos en cuarentena
- eventos técnicos de dispositivo (`door_status`, `heartbeat_connect`, `unknown`)

El frontend muestra las fechas en **GMT-6 (México)**.

## Modos de operación

### 1. Live por túnel SSH

Modo por defecto. Abre un túnel SSH a la EC2 y consulta PostgreSQL en vivo.

Variables:

- `DAHUA_DASHBOARD_SOURCE=ssh_tunnel`
- `DAHUA_DASHBOARD_SSH_TARGET=root@52.6.240.186`
- `DAHUA_DASHBOARD_REMOTE_ENV_PATH=/etc/biometric-ingest.env`
- `DAHUA_DASHBOARD_REMOTE_DB_HOST=127.0.0.1`
- `DAHUA_DASHBOARD_REMOTE_DB_PORT=5432`

### 2. PostgreSQL directo

Útil si ya tienes acceso local a la base.

Variables:

- `DAHUA_DASHBOARD_SOURCE=postgres`
- `DAHUA_DASHBOARD_DATABASE_URL=postgresql://...`

### 3. Snapshot local

Solo como fallback para desarrollo sin acceso al servidor.

Variables:

- `DAHUA_DASHBOARD_SOURCE=snapshot`
- `DAHUA_DASHBOARD_SNAPSHOT_PATH=dashboard/sample_data/biometric_snapshot_2026-03-18.json`

## Dependencias

Instala el driver PostgreSQL y el servidor ASGI:

```bash
python3 -m pip install --user --break-system-packages -r dashboard/requirements.txt
```

## Assets de despliegue

Los archivos operativos del dashboard ya no viven dentro del runtime de la app. Quedaron centralizados en:

- [deploy_dashboard.sh](../server_config/services/dashboard/deploy_dashboard.sh)
- [dahua-dashboard.service](../server_config/services/dashboard/dahua-dashboard.service)
- [dahua-dashboard.env.example](../server_config/services/dashboard/dahua-dashboard.env.example)
- [dahua-monitor-http.conf](../server_config/services/dashboard/dahua-monitor-http.conf)
- [dahua-monitor-https.conf](../server_config/services/dashboard/dahua-monitor-https.conf)

Despliegue remoto:

```bash
chmod +x server_config/services/dashboard/deploy_dashboard.sh
./server_config/services/dashboard/deploy_dashboard.sh
```

## Ejecución local

Forma recomendada:

```bash
./dashboard/run_local.sh
```

También puedes hacerlo manualmente.

Desde la raíz del repo:

```bash
python3 -m uvicorn dashboard.app:app --reload --port 8090
```

Si ya estás parado dentro de `dashboard/`:

```bash
python3 -m uvicorn app:app --reload --port 8090
```

Abrir:

```text
http://127.0.0.1:8090
```

También responde en:

```text
http://127.0.0.1:8090/monitor.html
```

## Pestañas disponibles

- `Normalizados`
- `Cuarentena`
- `Crudos`
- `Devices`

Cada pestaña tiene:

- paginación
- búsqueda
- filtros por tipo/razón/outcome según la vista
- detalle JSON en diálogo modal mediante `Ver detalle`
