#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=${1:-$(cd "$SCRIPT_DIR/../../.." && pwd)}
TARGET_DIR=/opt/auth-gateway
SSL_CONF=/etc/nginx/sites-available/odootest-ssl.conf
BOOTSTRAP_CONF=/etc/nginx/sites-available/odootest-bootstrap.conf
ENABLED_CONF=/etc/nginx/sites-enabled/odootest.conf

apt-get update -qq
apt-get install -y python3-venv python3-pip nginx certbot python3-certbot-nginx rsync

mkdir -p "$TARGET_DIR"
rsync -av --delete "$PROJECT_ROOT/server_config/auth_gateway/app/" "$TARGET_DIR/app/"
cp "$PROJECT_ROOT/server_config/auth_gateway/requirements.txt" "$TARGET_DIR/requirements.txt"
cp "$PROJECT_ROOT/server_config/auth_gateway/.env.example" "$TARGET_DIR/.env"
cp "$PROJECT_ROOT/server_config/auth_gateway/systemd/auth-gateway.service" /etc/systemd/system/auth-gateway.service
cp "$PROJECT_ROOT/server_config/auth_gateway/nginx/odootest.conf" "$SSL_CONF"
cp "$PROJECT_ROOT/server_config/auth_gateway/nginx/odootest-bootstrap.conf" "$BOOTSTRAP_CONF"

if [ -f "$PROJECT_ROOT/server_config/auth_gateway/connection_values.json" ]; then
  cp "$PROJECT_ROOT/server_config/auth_gateway/connection_values.json" "$TARGET_DIR/connection_values.json"
fi

python3 -m venv "$TARGET_DIR/venv"
"$TARGET_DIR/venv/bin/pip" install --upgrade pip
"$TARGET_DIR/venv/bin/pip" install -r "$TARGET_DIR/requirements.txt"

chown -R odoo:odoo "$TARGET_DIR"

if [ -f /etc/letsencrypt/live/auth.odootest.mvpstart.click/fullchain.pem ] && [ -f /etc/letsencrypt/live/erp.odootest.mvpstart.click/fullchain.pem ]; then
  ln -sf "$SSL_CONF" "$ENABLED_CONF"
else
  ln -sf "$BOOTSTRAP_CONF" "$ENABLED_CONF"
fi
rm -f /etc/nginx/sites-enabled/default

systemctl daemon-reload
systemctl enable auth-gateway
systemctl restart auth-gateway
systemctl enable nginx
nginx -t
systemctl restart nginx

systemctl --no-pager --full status auth-gateway | sed -n '1,20p'
