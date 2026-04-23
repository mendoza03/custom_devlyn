#!/usr/bin/env bash
set -euo pipefail

DB_NAME=${DB_NAME:-devlyn_com}
MODULE=${MODULE:-odoo_biometric_bridge}
MODULE_OPERATION=${MODULE_OPERATION:-auto}

run_odoo_module() {
  local operation="$1"
  /usr/bin/odoo -c /etc/odoo/odoo.conf -d "$DB_NAME" "$operation" "$MODULE" --stop-after-init
}

case "$MODULE_OPERATION" in
  install)
    run_odoo_module -i
    ;;
  upgrade)
    run_odoo_module -u
    ;;
  auto)
    if ! run_odoo_module -u; then
      echo "Upgrade failed, attempting install..."
      run_odoo_module -i
    fi
    ;;
  *)
    echo "Unsupported MODULE_OPERATION: $MODULE_OPERATION" >&2
    exit 1
    ;;
esac

systemctl restart odoo
systemctl --no-pager --full status odoo | sed -n '1,25p'
