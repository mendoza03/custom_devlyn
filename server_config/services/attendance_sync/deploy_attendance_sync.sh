#!/usr/bin/env bash
set -euo pipefail

HOST="${HOST:-52.6.240.186}"
SSH_TARGET="${SSH_TARGET:-root@${HOST}}"
APP_DIR="${APP_DIR:-/opt/biometric-ingest}"
MODULE_DIR="${MODULE_DIR:-/opt/odoo/custom-addons/hr_biometric_attendance_sync}"
ENV_FILE="${ENV_FILE:-/etc/attendance-sync.env}"
LINUX_USER="${LINUX_USER:-biometric}"
LINUX_GROUP="${LINUX_GROUP:-biometric}"
ODOO_DB="${ODOO_DB:-devlyn_com}"
ODOO_LOGIN="${ODOO_LOGIN:-biometric.sync}"
ODOO_TZ="${ODOO_TZ:-America/Mexico_City}"
ODOO_URL="${ODOO_URL:-http://127.0.0.1:8069}"
SERVICE_NAME="${SERVICE_NAME:-attendance-sync-worker}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
SOURCE_DIR="${REPO_ROOT}/dahua_interface"

ODOO_PASSWORD="${ODOO_PASSWORD:-}"
if [[ -z "${ODOO_PASSWORD}" ]]; then
  ODOO_PASSWORD="$(openssl rand -base64 24 | tr -d '\n' | tr '/+' '_-')"
fi

echo "Deploying attendance sync to ${SSH_TARGET}"

tar czf - \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  -C "${SOURCE_DIR}" \
  attendance_sync_worker.py \
  biometric_common.py \
  requirements.txt \
  | ssh -o StrictHostKeyChecking=no "${SSH_TARGET}" "mkdir -p '${APP_DIR}' && tar xzf - -C '${APP_DIR}'"

tar czf - \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  -C "${REPO_ROOT}/odoo_biometric/module" \
  hr_biometric_attendance_sync \
  | ssh -o StrictHostKeyChecking=no "${SSH_TARGET}" "mkdir -p '/opt/odoo/custom-addons' && tar xzf - -C '/opt/odoo/custom-addons'"

scp -o StrictHostKeyChecking=no "${SCRIPT_DIR}/attendance-sync-worker.service" "${SSH_TARGET}:/tmp/attendance-sync-worker.service"

ssh -o StrictHostKeyChecking=no "${SSH_TARGET}" "bash -s" <<EOF
set -euo pipefail

APP_DIR="${APP_DIR}"
MODULE_DIR="${MODULE_DIR}"
ENV_FILE="${ENV_FILE}"
LINUX_USER="${LINUX_USER}"
LINUX_GROUP="${LINUX_GROUP}"
ODOO_DB="${ODOO_DB}"
ODOO_LOGIN="${ODOO_LOGIN}"
ODOO_PASSWORD="${ODOO_PASSWORD}"
ODOO_TZ="${ODOO_TZ}"
ODOO_URL="${ODOO_URL}"
SERVICE_NAME="${SERVICE_NAME}"

mkdir -p "${APP_DIR}" /var/log/biometric-ingest
chown -R "${LINUX_USER}:${LINUX_GROUP}" "${APP_DIR}" /var/log/biometric-ingest
chown -R odoo:odoo "${MODULE_DIR}"

if [[ ! -x "${APP_DIR}/venv/bin/python" ]]; then
  python3 -m venv "${APP_DIR}/venv"
fi
"${APP_DIR}/venv/bin/pip" install --upgrade pip
"${APP_DIR}/venv/bin/pip" install -r "${APP_DIR}/requirements.txt"

biometric_db_url=\$(grep '^BIOMETRIC_DATABASE_URL=' /etc/biometric-ingest.env | cut -d= -f2-)

cat > "${ENV_FILE}" <<ENVVARS
ATTENDANCE_SYNC_BIOMETRIC_DATABASE_URL=\${biometric_db_url}
ATTENDANCE_SYNC_ODOO_URL=${ODOO_URL}
ATTENDANCE_SYNC_ODOO_DB=${ODOO_DB}
ATTENDANCE_SYNC_ODOO_LOGIN=${ODOO_LOGIN}
ATTENDANCE_SYNC_ODOO_PASSWORD=${ODOO_PASSWORD}
ATTENDANCE_SYNC_DEFAULT_TIMEZONE=${ODOO_TZ}
ATTENDANCE_SYNC_SOURCE_MODE_LABEL=biometric_v1
ATTENDANCE_SYNC_INFERENCE_MODE=biometric_v1_raw_toggle
ATTENDANCE_SYNC_POLL_SECONDS=60
ATTENDANCE_SYNC_BATCH_SIZE=100
ATTENDANCE_SYNC_LOG=/var/log/biometric-ingest/attendance-sync.log
ENVVARS
chmod 640 "${ENV_FILE}"
chown root:${LINUX_GROUP} "${ENV_FILE}"

module_state=\$(sudo -u postgres psql -d "${ODOO_DB}" -At -c "SELECT state FROM ir_module_module WHERE name='hr_biometric_attendance_sync' LIMIT 1;")

systemctl stop odoo
if [[ "\${module_state}" == "installed" ]]; then
  sudo -u odoo /usr/bin/odoo --config /etc/odoo/odoo.conf -d "${ODOO_DB}" -u hr_biometric_attendance_sync --stop-after-init
else
  sudo -u odoo /usr/bin/odoo --config /etc/odoo/odoo.conf -d "${ODOO_DB}" -i hr_biometric_attendance_sync --stop-after-init
fi
systemctl start odoo

sudo -u odoo /usr/bin/odoo shell --config /etc/odoo/odoo.conf -d "${ODOO_DB}" <<PY
group_user = env.ref("base.group_user")
group_hr_user = env.ref("hr.group_hr_user")
group_attendance_manager = env.ref("hr_attendance.group_hr_attendance_manager")
login = "${ODOO_LOGIN}"
password = "${ODOO_PASSWORD}"
tz_name = "${ODOO_TZ}"
vals = {
    "name": "Biometric Sync",
    "login": login,
    "tz": tz_name,
    "group_ids": [(6, 0, [group_user.id, group_hr_user.id, group_attendance_manager.id])],
}
user = env["res.users"].with_context(no_reset_password=True).sudo().search([("login", "=", login)], limit=1)
if user:
    user.write(vals)
else:
    user = env["res.users"].with_context(no_reset_password=True).sudo().create(vals)
user.write({"password": password})
env.cr.commit()
PY

install -m 0644 /tmp/attendance-sync-worker.service "/etc/systemd/system/\${SERVICE_NAME}.service"
systemctl daemon-reload
systemctl enable "\${SERVICE_NAME}"
systemctl restart "\${SERVICE_NAME}"

systemctl is-active --quiet odoo
systemctl is-active --quiet "\${SERVICE_NAME}"
systemctl --no-pager --full status "\${SERVICE_NAME}" | sed -n '1,40p'
EOF

echo
echo "Attendance sync deployment complete."
echo "Odoo login stored at ${ENV_FILE} on ${SSH_TARGET}."
