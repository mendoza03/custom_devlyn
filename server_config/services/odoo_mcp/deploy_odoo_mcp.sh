#!/usr/bin/env bash
set -euo pipefail

HOST="${HOST:-52.6.240.186}"
SSH_TARGET="${SSH_TARGET:-ubuntu@${HOST}}"
APP_DIR="${APP_DIR:-/opt/odoo-mcp}"
ADDON_DIR="${ADDON_DIR:-/opt/odoo/custom-addons/odoo_mcp_readonly_access}"
ENV_FILE="${ENV_FILE:-/etc/odoo-mcp.env}"
HTTP_CONF="${HTTP_CONF:-/etc/nginx/sites-available/odoo-mcp-http.conf}"
HTTP_ENABLED="${HTTP_ENABLED:-/etc/nginx/sites-enabled/odoo-mcp-http.conf}"
HTTPS_CONF="${HTTPS_CONF:-/etc/nginx/sites-available/odoo-mcp-https.conf}"
HTTPS_ENABLED="${HTTPS_ENABLED:-/etc/nginx/sites-enabled/odoo-mcp-https.conf}"
PUBLIC_HOST="${PUBLIC_HOST:-mcp.odootest.mvpstart.click}"
CERTBOT_EMAIL="${CERTBOT_EMAIL:-admin@odootest.mvpstart.click}"
DB_NAME="${DB_NAME:-devlyn_com}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

echo "Deploying Devlyn Odoo MCP to ${SSH_TARGET}"

tar czf - \
  --exclude='odoo_mcp/__pycache__' \
  --exclude='odoo_mcp/**/*.pyc' \
  -C "${REPO_ROOT}" \
  odoo_mcp \
  | ssh -o StrictHostKeyChecking=no "${SSH_TARGET}" "sudo mkdir -p '${APP_DIR}' && sudo tar xzf - -C '${APP_DIR}'"

scp -o StrictHostKeyChecking=no \
  "${SCRIPT_DIR}/odoo-mcp.service" \
  "${SCRIPT_DIR}/odoo-mcp-http.conf" \
  "${SCRIPT_DIR}/odoo-mcp-https.conf" \
  "${SCRIPT_DIR}/odoo-mcp.env.example" \
  "${SSH_TARGET}:/tmp/"

ssh -o StrictHostKeyChecking=no "${SSH_TARGET}" \
  "APP_DIR='${APP_DIR}' ADDON_DIR='${ADDON_DIR}' ENV_FILE='${ENV_FILE}' HTTP_CONF='${HTTP_CONF}' HTTP_ENABLED='${HTTP_ENABLED}' HTTPS_CONF='${HTTPS_CONF}' HTTPS_ENABLED='${HTTPS_ENABLED}' PUBLIC_HOST='${PUBLIC_HOST}' CERTBOT_EMAIL='${CERTBOT_EMAIL}' DB_NAME='${DB_NAME}' bash -s" <<'EOF'
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/odoo-mcp}"
ADDON_DIR="${ADDON_DIR:-/opt/odoo/custom-addons/odoo_mcp_readonly_access}"
SOURCE_DIR="${APP_DIR}/odoo_mcp"
ENV_FILE="${ENV_FILE:-/etc/odoo-mcp.env}"
HTTP_CONF="${HTTP_CONF:-/etc/nginx/sites-available/odoo-mcp-http.conf}"
HTTP_ENABLED="${HTTP_ENABLED:-/etc/nginx/sites-enabled/odoo-mcp-http.conf}"
HTTPS_CONF="${HTTPS_CONF:-/etc/nginx/sites-available/odoo-mcp-https.conf}"
HTTPS_ENABLED="${HTTPS_ENABLED:-/etc/nginx/sites-enabled/odoo-mcp-https.conf}"
PUBLIC_HOST="${PUBLIC_HOST:-mcp.odootest.mvpstart.click}"
CERTBOT_EMAIL="${CERTBOT_EMAIL:-admin@odootest.mvpstart.click}"
DB_NAME="${DB_NAME:-devlyn_com}"

sudo apt-get update -y
sudo apt-get install -y python3-venv python3-pip certbot rsync

sudo mkdir -p "${APP_DIR}" "${ADDON_DIR}" /var/www/html
sudo rsync -a --delete "${SOURCE_DIR}/odoo_addon/odoo_mcp_readonly_access/" "${ADDON_DIR}/"
sudo chown -R odoo:odoo "${APP_DIR}" "${ADDON_DIR}"

sudo python3 -m venv "${APP_DIR}/venv"
sudo "${APP_DIR}/venv/bin/pip" install --upgrade pip
sudo "${APP_DIR}/venv/bin/pip" install -r "${SOURCE_DIR}/requirements.txt"

if [[ ! -f "${ENV_FILE}" ]]; then
  sudo install -m 0640 -o root -g odoo /tmp/odoo-mcp.env.example "${ENV_FILE}"
  echo "Created placeholder ${ENV_FILE}; populate real secrets before restarting the service." >&2
fi

sudo install -m 0644 /tmp/odoo-mcp.service /etc/systemd/system/odoo-mcp.service
sudo install -m 0644 /tmp/odoo-mcp-http.conf "${HTTP_CONF}"
sudo install -m 0644 /tmp/odoo-mcp-https.conf "${HTTPS_CONF}"
sudo ln -sfn "${HTTP_CONF}" "${HTTP_ENABLED}"

sudo nginx -t
sudo systemctl reload nginx

if [[ ! -f "/etc/letsencrypt/live/${PUBLIC_HOST}/fullchain.pem" ]]; then
  sudo certbot certonly --webroot --non-interactive --agree-tos -m "${CERTBOT_EMAIL}" \
    -w /var/www/html -d "${PUBLIC_HOST}"
fi

sudo ln -sfn "${HTTPS_CONF}" "${HTTPS_ENABLED}"
sudo nginx -t
sudo systemctl reload nginx

sudo systemctl daemon-reload
sudo systemctl enable odoo-mcp

module_state="$(
  sudo -u odoo /usr/bin/odoo shell -c /etc/odoo/odoo.conf -d "${DB_NAME}" <<'PY' 2>/dev/null | tail -n 1
mod = env['ir.module.module'].search([('name', '=', 'odoo_mcp_readonly_access')], limit=1)
print(mod.state or 'missing')
PY
)"
if [[ "${module_state}" == "installed" || "${module_state}" == "to upgrade" || "${module_state}" == "to remove" ]]; then
  sudo -u odoo /usr/bin/odoo -c /etc/odoo/odoo.conf -d "${DB_NAME}" -u odoo_mcp_readonly_access --stop-after-init
else
  sudo -u odoo /usr/bin/odoo -c /etc/odoo/odoo.conf -d "${DB_NAME}" -i odoo_mcp_readonly_access --stop-after-init
fi
sudo systemctl restart odoo

if grep -q '^ODOO_MCP_API_KEY=replace-with-generated-global-mcp-token$' "${ENV_FILE}" 2>/dev/null; then
  echo "Skipping odoo-mcp restart because ${ENV_FILE} still contains placeholder secrets." >&2
else
  sudo systemctl restart odoo-mcp
  sudo systemctl is-active --quiet odoo-mcp
fi
EOF

echo "MCP deployment sync complete."
