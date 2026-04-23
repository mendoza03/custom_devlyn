#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=${1:-$(cd "$SCRIPT_DIR/../../.." && pwd)}
MODULE_SRC="$PROJECT_ROOT/odoo_biometric/module/odoo_biometric_bridge"
MODULE_DST="/opt/odoo/custom-addons/odoo_biometric_bridge"

mkdir -p /opt/odoo/custom-addons
rsync -av --delete "$MODULE_SRC/" "$MODULE_DST/"
chown -R odoo:odoo /opt/odoo/custom-addons

if ! grep -q "addons_path" /etc/odoo/odoo.conf; then
  cat >> /etc/odoo/odoo.conf <<'CONF'
addons_path = /opt/odoo/custom-addons,/usr/lib/python3/dist-packages/odoo/addons
CONF
else
  sed -i 's|^addons_path *=.*|addons_path = /opt/odoo/custom-addons,/usr/lib/python3/dist-packages/odoo/addons|g' /etc/odoo/odoo.conf
fi

systemctl restart odoo
sleep 3
systemctl --no-pager --full status odoo | sed -n '1,20p'
