#!/usr/bin/env bash
set -euo pipefail

MODE=${MODE:-${1:-dry-run}}
RUN_TYPE=${RUN_TYPE:-${2:-backfill}}
DATE_FROM=${DATE_FROM:-2026-03-20}
DATE_TO=${DATE_TO:-$(date +%F)}
BATCH_SIZE=${BATCH_SIZE:-500}
EMPLOYEE_IDS=${EMPLOYEE_IDS:-}
COMMIT_MODE=${COMMIT_MODE:-auto}
ODOO_BIN=${ODOO_BIN:-/usr/bin/odoo}
ODOO_CONFIG=${ODOO_CONFIG:-/etc/odoo/odoo.conf}
ODOO_DB=${ODOO_DB:-devlyn_com}
ODOO_USER=${ODOO_USER:-odoo}
OUTPUT_JSON=${OUTPUT_JSON:-}

case "${MODE}" in
  dry-run|dry_run)
    MODE=dry_run
    ;;
  apply)
    ;;
  *)
    echo "MODE must be dry-run, dry_run or apply" >&2
    exit 1
    ;;
esac

case "${RUN_TYPE}" in
  backfill|catchup|repair)
    ;;
  *)
    echo "RUN_TYPE must be backfill, catchup or repair" >&2
    exit 1
    ;;
esac

case "${COMMIT_MODE}" in
  auto|true|false)
    ;;
  *)
    echo "COMMIT_MODE must be auto, true or false" >&2
    exit 1
    ;;
esac

RESULT_LINE=$(
  export MODE RUN_TYPE DATE_FROM DATE_TO BATCH_SIZE EMPLOYEE_IDS COMMIT_MODE
  sudo --preserve-env=MODE,RUN_TYPE,DATE_FROM,DATE_TO,BATCH_SIZE,EMPLOYEE_IDS,COMMIT_MODE -u "${ODOO_USER}" "${ODOO_BIN}" shell -c "${ODOO_CONFIG}" -d "${ODOO_DB}" <<'PY' | grep '^__DEVLYN_JOURNEY_BATCH__=' | tail -n 1 || true
import json
import os

employee_ids_raw = os.getenv("EMPLOYEE_IDS", "").strip()
employee_ids = [int(piece.strip()) for piece in employee_ids_raw.split(",") if piece.strip()]

commit_mode = os.getenv("COMMIT_MODE", "auto").strip().lower()
if commit_mode == "auto":
    commit = None
elif commit_mode == "true":
    commit = True
else:
    commit = False

service = env["devlyn.attendance.journey.service"]
result = service.run_batch(
    run_type=os.environ["RUN_TYPE"],
    mode=os.environ["MODE"],
    date_from=os.environ["DATE_FROM"],
    date_to=os.environ["DATE_TO"],
    employee_ids=employee_ids,
    batch_size=int(os.environ["BATCH_SIZE"]),
    commit=commit,
)
print("__DEVLYN_JOURNEY_BATCH__=" + json.dumps(result, sort_keys=True))
PY
)

if [[ -z "${RESULT_LINE}" ]]; then
  echo "No result returned by Odoo shell batch execution." >&2
  exit 1
fi

RESULT_JSON=${RESULT_LINE#__DEVLYN_JOURNEY_BATCH__=}

if [[ -n "${OUTPUT_JSON}" ]]; then
  mkdir -p "$(dirname "${OUTPUT_JSON}")"
  printf '%s\n' "${RESULT_JSON}" > "${OUTPUT_JSON}"
fi

printf '%s\n' "${RESULT_JSON}"
