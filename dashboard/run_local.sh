#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PORT="${PORT:-8090}"

python3 -m pip install --user --break-system-packages -r "${SCRIPT_DIR}/requirements.txt" >/dev/null

export DAHUA_DASHBOARD_SOURCE="${DAHUA_DASHBOARD_SOURCE:-ssh_tunnel}"
export DAHUA_DASHBOARD_SSH_TARGET="${DAHUA_DASHBOARD_SSH_TARGET:-root@52.6.240.186}"
export DAHUA_DASHBOARD_REMOTE_ENV_PATH="${DAHUA_DASHBOARD_REMOTE_ENV_PATH:-/etc/biometric-ingest.env}"
export DAHUA_DASHBOARD_REMOTE_DB_HOST="${DAHUA_DASHBOARD_REMOTE_DB_HOST:-127.0.0.1}"
export DAHUA_DASHBOARD_REMOTE_DB_PORT="${DAHUA_DASHBOARD_REMOTE_DB_PORT:-5432}"

cd "${REPO_ROOT}"
exec python3 -m uvicorn dashboard.app:app --reload --port "${PORT}"
