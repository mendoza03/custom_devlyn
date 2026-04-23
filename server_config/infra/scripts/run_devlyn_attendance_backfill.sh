#!/usr/bin/env bash
set -euo pipefail

MODE=${MODE:-${1:-dry-run}}
ID_FROM=${ID_FROM:-482}
ID_TO=${ID_TO:-1770}
TARGET_SSH=${TARGET_SSH:-root@52.6.240.186}
ODOO_DB=${ODOO_DB:-devlyn_com}
BIOMETRIC_DB=${BIOMETRIC_DB:-biometric_ingest}
CURSOR_NAME=${CURSOR_NAME:-main}
BATCH_SIZE=${BATCH_SIZE:-100}
TIMESTAMP=${TIMESTAMP:-$(date -u +%Y%m%dT%H%M%SZ)}
REMOTE_BASE_DIR=${REMOTE_BASE_DIR:-/tmp/attendance-backfill-${TIMESTAMP}}
REMOTE_REPORT_DIR=${REMOTE_REPORT_DIR:-/var/backups/attendance-backfill/${TIMESTAMP}-${MODE}}
SSH_OPTS=(-o StrictHostKeyChecking=no)

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ROOT_DIR=$(cd "${SCRIPT_DIR}/../../.." && pwd)

restart_worker() {
  if [[ "${MODE}" == "apply" ]]; then
    ssh "${SSH_OPTS[@]}" "${TARGET_SSH}" "sudo systemctl start attendance-sync-worker >/dev/null 2>&1 || true"
  fi
}

trap restart_worker EXIT

if [[ "${MODE}" != "dry-run" && "${MODE}" != "apply" ]]; then
  echo "MODE must be dry-run or apply" >&2
  exit 1
fi

echo "[1/4] Uploading backfill utility to ${TARGET_SSH}"
tar czf - -C "${ROOT_DIR}/dahua_interface" \
  attendance_sync_backfill.py \
  attendance_sync_worker.py \
  biometric_common.py \
  | ssh "${SSH_OPTS[@]}" "${TARGET_SSH}" "mkdir -p '${REMOTE_BASE_DIR}' && tar xzf - -C '${REMOTE_BASE_DIR}'"

echo "[2/4] Preparing remote report directory ${REMOTE_REPORT_DIR}"
ssh "${SSH_OPTS[@]}" "${TARGET_SSH}" "mkdir -p '${REMOTE_REPORT_DIR}'"

if [[ "${MODE}" == "apply" ]]; then
  echo "[3/4] Taking backup and stopping attendance-sync-worker"
  ssh "${SSH_OPTS[@]}" "${TARGET_SSH}" "sudo bash -lc '
    set -euo pipefail
    systemctl stop attendance-sync-worker
    sudo -u postgres pg_dump -Fc -d ${ODOO_DB} > \"${REMOTE_REPORT_DIR}/devlyn_com.pre_backfill.dump\"
    sudo -u postgres psql -d ${ODOO_DB} -P pager=off --pset footer=off <<\"SQL\" > \"${REMOTE_REPORT_DIR}/baseline_counts.txt\"
select 'hr_attendance' as table_name, count(*) from hr_attendance
union all
select 'hr_biometric_event' as table_name, count(*) from hr_biometric_event
union all
select 'hr_biometric_sync_run' as table_name, count(*) from hr_biometric_sync_run
union all
select 'hr_biometric_sync_cursor' as table_name, count(*) from hr_biometric_sync_cursor;
SQL
  '"
fi

echo "[4/4] Running ${MODE}"
ssh "${SSH_OPTS[@]}" "${TARGET_SSH}" "sudo bash -lc '
  set -euo pipefail
  set -a
  source /etc/attendance-sync.env
  set +a
  export PYTHONPATH=\"${REMOTE_BASE_DIR}:\${PYTHONPATH:-}\"
  /opt/biometric-ingest/venv/bin/python \"${REMOTE_BASE_DIR}/attendance_sync_backfill.py\" \
    --mode \"${MODE}\" \
    --id-from \"${ID_FROM}\" \
    --id-to \"${ID_TO}\" \
    --odoo-db \"${ODOO_DB}\" \
    --biometric-db \"${BIOMETRIC_DB}\" \
    --cursor-name \"${CURSOR_NAME}\" \
    --batch-size \"${BATCH_SIZE}\" \
    --report-dir \"${REMOTE_REPORT_DIR}\"
'"

if [[ "${MODE}" == "apply" ]]; then
  echo "[5/5] Restarting attendance-sync-worker"
  ssh "${SSH_OPTS[@]}" "${TARGET_SSH}" "sudo systemctl start attendance-sync-worker && sudo systemctl is-active attendance-sync-worker"
fi

trap - EXIT

echo "Report directory: ${REMOTE_REPORT_DIR}"
