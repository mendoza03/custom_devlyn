#!/usr/bin/env bash
set -euo pipefail

HOST="${HOST:-52.6.240.186}"
SSH_TARGET="${SSH_TARGET:-root@${HOST}}"
APP_DIR="${APP_DIR:-/opt/biometric-ingest}"
ENV_FILE="${ENV_FILE:-/etc/biometric-ingest.env}"
NGINX_CONF="${NGINX_CONF:-/etc/nginx/conf.d/biometric-ingest-60005.conf}"
LINUX_USER="${LINUX_USER:-biometric}"
LINUX_GROUP="${LINUX_GROUP:-biometric}"
DB_NAME="${DB_NAME:-biometric_ingest}"
DB_APP_USER="${DB_APP_USER:-biometric_app}"
DB_READONLY_USER="${DB_READONLY_USER:-biometric_readonly}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
SOURCE_DIR="${REPO_ROOT}/dahua_interface"

APP_PASSWORD="${APP_PASSWORD:-}"
READONLY_PASSWORD="${READONLY_PASSWORD:-}"

if [[ -z "${APP_PASSWORD}" ]]; then
  APP_PASSWORD="$(openssl rand -base64 24 | tr -d '\n' | tr '/+' '_-')"
fi

if [[ -z "${READONLY_PASSWORD}" ]]; then
  READONLY_PASSWORD="$(openssl rand -base64 24 | tr -d '\n' | tr '/+' '_-')"
fi

echo "Deploying biometric ingest to ${SSH_TARGET}"

tar czf - \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  -C "${SOURCE_DIR}" \
  biometric_common.py \
  biometric_db.py \
  biometric_ingest.py \
  biometric_router_worker.py \
  biometric_schema.sql \
  requirements.txt \
  monitor_live.py \
  | ssh -o StrictHostKeyChecking=no "${SSH_TARGET}" "mkdir -p '${APP_DIR}' && tar xzf - -C '${APP_DIR}'"

scp -o StrictHostKeyChecking=no "${SCRIPT_DIR}/biometric-ingest.service" "${SSH_TARGET}:/tmp/biometric-ingest.service"
scp -o StrictHostKeyChecking=no "${SCRIPT_DIR}/biometric-router-worker.service" "${SSH_TARGET}:/tmp/biometric-router-worker.service"
scp -o StrictHostKeyChecking=no "${SCRIPT_DIR}/biometric-ingest-60005.conf" "${SSH_TARGET}:/tmp/biometric-ingest-60005.conf"

ssh -o StrictHostKeyChecking=no "${SSH_TARGET}" "bash -s" <<EOF
set -euo pipefail

if ! id -u "${LINUX_USER}" >/dev/null 2>&1; then
  getent group "${LINUX_GROUP}" >/dev/null 2>&1 || groupadd --system "${LINUX_GROUP}"
  useradd --system --home "${APP_DIR}" --gid "${LINUX_GROUP}" --shell /usr/sbin/nologin "${LINUX_USER}"
fi

mkdir -p "${APP_DIR}" /var/lib/biometric-ingest/spool /var/lib/biometric-ingest/state /var/lib/biometric-ingest/archive /var/log/biometric-ingest
touch /var/log/dahua_events.log
chown -R "${LINUX_USER}:${LINUX_GROUP}" "${APP_DIR}" /var/lib/biometric-ingest /var/log/biometric-ingest /var/log/dahua_events.log
chmod 750 /var/lib/biometric-ingest /var/lib/biometric-ingest/spool /var/lib/biometric-ingest/state /var/lib/biometric-ingest/archive /var/log/biometric-ingest

python3 -m venv "${APP_DIR}/venv"
"${APP_DIR}/venv/bin/pip" install --upgrade pip
"${APP_DIR}/venv/bin/pip" install -r "${APP_DIR}/requirements.txt"

if [[ -f "${ENV_FILE}" ]]; then
  current_url=\$(grep '^BIOMETRIC_DATABASE_URL=' "${ENV_FILE}" | sed 's/^BIOMETRIC_DATABASE_URL=//')
else
  current_url=""
fi

if [[ -n "\${current_url}" ]]; then
  db_url="\${current_url}"
  APP_PASSWORD="\${current_url#*://}"
  APP_PASSWORD="\${APP_PASSWORD#*:}"
  APP_PASSWORD="\${APP_PASSWORD%@*}"
else
  db_url="postgresql://${DB_APP_USER}:${APP_PASSWORD}@127.0.0.1:5432/${DB_NAME}"
fi

cat > "${ENV_FILE}" <<ENVVARS
BIOMETRIC_PUBLIC_PORT=60005
BIOMETRIC_INTERNAL_PORT=60006
BIOMETRIC_SPOOL_DIR=/var/lib/biometric-ingest/spool
BIOMETRIC_STATE_DIR=/var/lib/biometric-ingest/state
BIOMETRIC_ARCHIVE_DIR=/var/lib/biometric-ingest/archive
BIOMETRIC_REQUEST_LOG=/var/log/dahua_events.log
BIOMETRIC_INGEST_LOG=/var/log/biometric-ingest/ingest.log
BIOMETRIC_WORKER_LOG=/var/log/biometric-ingest/worker.log
BIOMETRIC_DATABASE_URL=\${db_url}
BIOMETRIC_HEARTBEAT_WINDOW_SECONDS=600
BIOMETRIC_STALE_AFTER_SECONDS=120
BIOMETRIC_OFFLINE_AFTER_SECONDS=300
BIOMETRIC_WORKER_POLL_SECONDS=2
BIOMETRIC_MAX_BODY_BYTES=131072
BIOMETRIC_HEARTBEAT_EXPECTED_INTERVAL_SECONDS=30
ENVVARS
chmod 640 "${ENV_FILE}"
chown root:${LINUX_GROUP} "${ENV_FILE}"

sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='${DB_APP_USER}'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE ROLE ${DB_APP_USER} LOGIN PASSWORD '${APP_PASSWORD}';"
sudo -u postgres psql -c "ALTER ROLE ${DB_APP_USER} WITH PASSWORD '\${APP_PASSWORD}';"

sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='${DB_READONLY_USER}'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE ROLE ${DB_READONLY_USER} LOGIN PASSWORD '${READONLY_PASSWORD}';"
sudo -u postgres psql -c "ALTER ROLE ${DB_READONLY_USER} WITH PASSWORD '${READONLY_PASSWORD}';"

sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1 || sudo -u postgres createdb -O "${DB_APP_USER}" "${DB_NAME}"
sudo -u postgres psql -d "${DB_NAME}" -c "GRANT CONNECT ON DATABASE ${DB_NAME} TO ${DB_READONLY_USER};"

install -m 0644 /tmp/biometric-ingest.service /etc/systemd/system/biometric-ingest.service
install -m 0644 /tmp/biometric-router-worker.service /etc/systemd/system/biometric-router-worker.service
install -m 0644 /tmp/biometric-ingest-60005.conf "${NGINX_CONF}"

systemctl daemon-reload
systemctl enable biometric-ingest biometric-router-worker
systemctl restart biometric-ingest
systemctl restart biometric-router-worker

for _ in {1..20}; do
  if curl -fsS http://127.0.0.1:60006/__health >/dev/null 2>/dev/null; then
    break
  fi
  sleep 1
done
curl -fsS http://127.0.0.1:60006/__health >/dev/null
nginx -t

if systemctl is-active --quiet dahua-listener; then
  systemctl stop dahua-listener
  systemctl disable dahua-listener || true
fi

systemctl reload nginx

for _ in {1..20}; do
  if curl -fsS http://127.0.0.1:60005/__health >/dev/null 2>/dev/null; then
    break
  fi
  sleep 1
done

sudo -u postgres psql -d "${DB_NAME}" -c "GRANT USAGE ON SCHEMA public TO ${DB_READONLY_USER};"
sudo -u postgres psql -d "${DB_NAME}" -c "GRANT SELECT ON ALL TABLES IN SCHEMA public TO ${DB_READONLY_USER};"
sudo -u postgres psql -d "${DB_NAME}" -c "ALTER DEFAULT PRIVILEGES FOR ROLE ${DB_APP_USER} IN SCHEMA public GRANT SELECT ON TABLES TO ${DB_READONLY_USER};"

systemctl --no-pager --full status biometric-ingest | sed -n '1,40p'
echo '---'
systemctl --no-pager --full status biometric-router-worker | sed -n '1,40p'
echo '---'
ss -tulpn | grep -E '60005|60006'
echo '---'
curl -fsS http://127.0.0.1:60005/__health
EOF

echo
echo "Deployment complete."
echo "Application database URL stored at ${ENV_FILE} on ${SSH_TARGET}."
