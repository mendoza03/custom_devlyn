#!/usr/bin/env bash
set -euo pipefail

EMAIL=${1:-admin@odootest.mvpstart.click}
SSL_CONF=/etc/nginx/sites-available/odootest-ssl.conf
ENABLED_CONF=/etc/nginx/sites-enabled/odootest.conf

mkdir -p /var/www/html

certbot certonly --webroot --non-interactive --agree-tos -m "$EMAIL" \
  -w /var/www/html -d auth.odootest.mvpstart.click
certbot certonly --webroot --non-interactive --agree-tos -m "$EMAIL" \
  -w /var/www/html -d erp.odootest.mvpstart.click

ln -sf "$SSL_CONF" "$ENABLED_CONF"
nginx -t
systemctl reload nginx
