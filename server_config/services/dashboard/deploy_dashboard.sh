#!/usr/bin/env bash
set -euo pipefail

HOST="${HOST:-52.6.240.186}"
SSH_TARGET="${SSH_TARGET:-root@${HOST}}"
APP_DIR="${APP_DIR:-/opt/dahua-dashboard}"
ENV_FILE="${ENV_FILE:-/etc/dahua-dashboard.env}"
HTTP_CONF="${HTTP_CONF:-/etc/nginx/sites-available/dahua-monitor-http.conf}"
HTTP_ENABLED="${HTTP_ENABLED:-/etc/nginx/sites-enabled/dahua-monitor-http.conf}"
HTTPS_CONF="${HTTPS_CONF:-/etc/nginx/sites-available/dahua-monitor-https.conf}"
HTTPS_ENABLED="${HTTPS_ENABLED:-/etc/nginx/sites-enabled/dahua-monitor-https.conf}"
LINUX_USER="${LINUX_USER:-biometric}"
LINUX_GROUP="${LINUX_GROUP:-biometric}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

echo "Deploying dashboard to ${SSH_TARGET}"

tar czf - \
  --exclude='dashboard/.venv' \
  --exclude='dashboard/__pycache__' \
  --exclude='dashboard/*.pyc' \
  -C "${REPO_ROOT}" \
  dashboard \
  | ssh -o StrictHostKeyChecking=no "${SSH_TARGET}" "mkdir -p '${APP_DIR}' && tar xzf - -C '${APP_DIR}' --strip-components=1"

scp -o StrictHostKeyChecking=no "${SCRIPT_DIR}/dahua-dashboard.service" "${SSH_TARGET}:/tmp/dahua-dashboard.service"
scp -o StrictHostKeyChecking=no "${SCRIPT_DIR}/dahua-monitor-http.conf" "${SSH_TARGET}:/tmp/dahua-monitor-http.conf"
scp -o StrictHostKeyChecking=no "${SCRIPT_DIR}/dahua-monitor-https.conf" "${SSH_TARGET}:/tmp/dahua-monitor-https.conf"

ssh -o StrictHostKeyChecking=no "${SSH_TARGET}" "bash -s" <<'EOF'
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/dahua-dashboard}"
ENV_FILE="${ENV_FILE:-/etc/dahua-dashboard.env}"
HTTP_CONF="${HTTP_CONF:-/etc/nginx/sites-available/dahua-monitor-http.conf}"
HTTP_ENABLED="${HTTP_ENABLED:-/etc/nginx/sites-enabled/dahua-monitor-http.conf}"
HTTPS_CONF="${HTTPS_CONF:-/etc/nginx/sites-available/dahua-monitor-https.conf}"
HTTPS_ENABLED="${HTTPS_ENABLED:-/etc/nginx/sites-enabled/dahua-monitor-https.conf}"
LINUX_USER="${LINUX_USER:-biometric}"
LINUX_GROUP="${LINUX_GROUP:-biometric}"

mkdir -p "${APP_DIR}"
chown -R "${LINUX_USER}:${LINUX_GROUP}" "${APP_DIR}"

python3 -m venv "${APP_DIR}/venv"
"${APP_DIR}/venv/bin/pip" install --upgrade pip
"${APP_DIR}/venv/bin/pip" install -r "${APP_DIR}/requirements.txt"

db_url="$(grep '^BIOMETRIC_DATABASE_URL=' /etc/biometric-ingest.env | tail -n 1 | cut -d= -f2-)"
cat > "${ENV_FILE}" <<ENVVARS
DAHUA_DASHBOARD_SOURCE=postgres
DAHUA_DASHBOARD_DATABASE_URL=${db_url}
ENVVARS
chmod 640 "${ENV_FILE}"
chown root:${LINUX_GROUP} "${ENV_FILE}"

install -m 0644 /tmp/dahua-dashboard.service /etc/systemd/system/dahua-dashboard.service
install -m 0644 /tmp/dahua-monitor-http.conf "${HTTP_CONF}"
ln -sfn "${HTTP_CONF}" "${HTTP_ENABLED}"

systemctl daemon-reload
systemctl enable dahua-dashboard
systemctl restart dahua-dashboard
systemctl is-active --quiet dahua-dashboard

nginx -t
systemctl reload nginx
EOF

echo "Dashboard deployment complete."
