#!/usr/bin/env python3
"""Mantenimiento de artefactos de despliegue para tenants CCIMA.

Objetivo:
- retener solo cierta cantidad de backups remotos
- retener solo cierta cantidad de archivos remotos de ejecucion
- retener solo cierta cantidad de imagenes Docker de deploy
- limpiar artefactos locales viejos sin tocar la corrida actual
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shlex
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from deploy_support.ssh_tools import SSHClient


# --- Configuracion editable por el usuario ---
# Usa un tenant especifico para ser conservador.
# Si quieres limpiar todo el servidor, cambia a:
# TARGET_TENANT = "all"
SSH_HOST = "138.186.200.38"
SSH_PORT = 5003
SSH_USER = "ubuntu"
SSH_PASSWORD = "ubuntu"
TARGET_TENANT = "habitta"

# Politicas de retencion remota por tenant.
KEEP_REMOTE_BACKUPS = 3
KEEP_REMOTE_ARCHIVES = 3
KEEP_REMOTE_IMAGES = 3

# Politicas de retencion local.
KEEP_LOCAL_DEPLOY_LOGS = 10
KEEP_LOCAL_DEPLOY_TMP = 3
KEEP_LOCAL_MAINTENANCE_LOGS = 10


ANSI_RESET = "\033[0m"
ANSI_COLORS = {
    "green": "\033[32m",
    "yellow": "\033[33m",
    "red": "\033[31m",
    "blue": "\033[34m",
    "cyan": "\033[36m",
    "bold": "\033[1m",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Clean old deploy artifacts on CCIMA tenants")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Show what would be deleted")
    mode.add_argument("--apply", action="store_true", help="Delete old artifacts now")
    return parser.parse_args()


def utc_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def use_color() -> bool:
    return sys.stdout.isatty() and not os.environ.get("NO_COLOR")


def paint(text: str, *styles: str) -> str:
    if not use_color() or not styles:
        return text
    prefix = "".join(ANSI_COLORS[style] for style in styles)
    return f"{prefix}{text}{ANSI_RESET}"


class ColorFormatter(logging.Formatter):
    LEVEL_STYLES = {
        logging.INFO: ("cyan",),
        logging.WARNING: ("yellow", "bold"),
        logging.ERROR: ("red", "bold"),
        logging.CRITICAL: ("red", "bold"),
    }

    def format(self, record: logging.LogRecord) -> str:
        rendered = super().format(record)
        styles = self.LEVEL_STYLES.get(record.levelno)
        return paint(rendered, *styles) if styles else rendered


def setup_logging(log_dir: Path) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("tenant_maintenance")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    file_handler = logging.FileHandler(log_dir / "run.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(ColorFormatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger


def ensure_local_tools() -> None:
    tools = ["python3"]
    if SSH_PASSWORD and SSH_PASSWORD.strip():
        try:
            import paramiko  # noqa: F401
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "SSH_PASSWORD is set, so `paramiko` is required locally. "
                "Install it with `python3 -m pip install paramiko`."
            ) from exc
    else:
        tools.append("ssh")
    missing = [item for item in tools if shutil.which(item) is None]
    if missing:
        raise RuntimeError(f"Missing local tools: {', '.join(missing)}")


def validate_config() -> dict[str, object]:
    if not TARGET_TENANT.strip():
        raise RuntimeError("TARGET_TENANT must not be empty. Use a tenant name or 'all'.")
    return {
        "ssh_host": SSH_HOST,
        "ssh_port": SSH_PORT,
        "ssh_user": SSH_USER,
        "ssh_password": SSH_PASSWORD.strip(),
        "target_tenant": TARGET_TENANT,
        "keep_remote_backups": int(KEEP_REMOTE_BACKUPS),
        "keep_remote_archives": int(KEEP_REMOTE_ARCHIVES),
        "keep_remote_images": int(KEEP_REMOTE_IMAGES),
        "keep_local_deploy_logs": int(KEEP_LOCAL_DEPLOY_LOGS),
        "keep_local_deploy_tmp": int(KEEP_LOCAL_DEPLOY_TMP),
        "keep_local_maintenance_logs": int(KEEP_LOCAL_MAINTENANCE_LOGS),
    }


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_script(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def build_remote_command(config: dict[str, object], apply: bool) -> str:
    command = [
        "python3",
        "-",
        "--tenant",
        str(config["target_tenant"]),
        "--keep-backups",
        str(config["keep_remote_backups"]),
        "--keep-archives",
        str(config["keep_remote_archives"]),
        "--keep-images",
        str(config["keep_remote_images"]),
    ]
    if apply:
        command.append("--apply")
    return shlex.join(command)


def list_named_dirs(path: Path) -> list[Path]:
    if not path.exists():
        return []
    return sorted([item for item in path.iterdir() if item.is_dir()], key=lambda item: item.name, reverse=True)


def summarize_local_cleanup(
    root: Path,
    keep_count: int,
    *,
    apply: bool,
    protected_names: set[str] | None = None,
) -> dict[str, object]:
    protected_names = protected_names or set()
    items = [item.name for item in list_named_dirs(root)]
    kept: list[str] = []
    planned_delete: list[str] = []
    for item in items:
        if item in protected_names:
            kept.append(item)
        elif len(kept) < keep_count:
            kept.append(item)
        else:
            planned_delete.append(item)

    deleted: list[str] = []
    failed: list[dict[str, str]] = []
    if apply:
        for item in planned_delete:
            target = root / item
            try:
                shutil.rmtree(target)
                deleted.append(item)
            except Exception as exc:  # pragma: no cover - depende del FS local
                failed.append({"path": str(target), "error": f"{type(exc).__name__}: {exc}"})
    return {
        "root": str(root),
        "found": len(items),
        "keep_limit": keep_count,
        "kept": kept,
        "planned_delete": planned_delete,
        "deleted": deleted,
        "failed": failed,
    }


def print_user_summary(payload: dict[str, object]) -> None:
    dry_run = payload["mode"] == "dry-run"
    title = paint("MAINTENANCE DRY RUN OK", "green", "bold") if dry_run else paint("MAINTENANCE APPLY OK", "green", "bold")
    label = lambda text: paint(text, "blue", "bold")
    totals = payload["totals"]
    remote = payload["remote"]
    local = payload["local"]
    print()
    print(title)
    print(f"{label('Tenant objetivo:')} {payload['tenant_selector']}")
    print(
        f"{label('Politica remota:')} "
        f"backups={payload['policies']['keep_backups']}, "
        f"archivos={payload['policies']['keep_archives']}, "
        f"imagenes={payload['policies']['keep_images']}"
    )
    print(
        f"{label('Politica local:')} "
        f"deploy_logs={payload['policies']['keep_local_deploy_logs']}, "
        f"deploy_tmp={payload['policies']['keep_local_deploy_tmp']}, "
        f"maintenance_logs={payload['policies']['keep_local_maintenance_logs']}"
    )
    print(f"{label('Tenants evaluados:')} {totals['tenants']}")
    print(
        f"{label('Remoto a borrar:')} "
        f"backups={remote['totals']['backups_planned_delete']}, "
        f"archivos={remote['totals']['archives_planned_delete']}, "
        f"imagenes={remote['totals']['images_planned_delete']}"
    )
    print(
        f"{label('Local a borrar:')} "
        f"deploy_logs={len(local['deploy_logs']['planned_delete'])}, "
        f"deploy_tmp={len(local['deploy_tmp']['planned_delete'])}, "
        f"maintenance_logs={len(local['maintenance_logs']['planned_delete'])}"
    )
    if not dry_run:
        print(
            f"{label('Remoto borrado:')} "
            f"backups={remote['totals']['backups_deleted']}, "
            f"archivos={remote['totals']['archives_deleted']}, "
            f"imagenes={remote['totals']['images_deleted']}"
        )
        print(
            f"{label('Local borrado:')} "
            f"deploy_logs={len(local['deploy_logs']['deleted'])}, "
            f"deploy_tmp={len(local['deploy_tmp']['deleted'])}, "
            f"maintenance_logs={len(local['maintenance_logs']['deleted'])}"
        )
    failure_count = int(remote["totals"]["failures"]) + len(local["deploy_logs"]["failed"]) + len(local["deploy_tmp"]["failed"]) + len(local["maintenance_logs"]["failed"])
    print(f"{label('Fallos detectados:')} {paint(str(failure_count), 'red', 'bold') if failure_count else paint('0', 'green', 'bold')}")
    print(f"{label('Log local:')} {payload['local_log_dir']}")
    print(f"{label('Detalle tecnico JSON:')} {Path(str(payload['local_log_dir'])) / 'maintenance_report.json'}")


def main() -> int:
    args = parse_args()
    config = validate_config()
    ensure_local_tools()

    repo_root = Path(__file__).resolve().parent
    run_id = utc_run_id()
    log_dir = repo_root / "maintenance_logs" / run_id
    logger = setup_logging(log_dir)
    logger.info("Starting maintenance run %s", run_id)

    ssh = SSHClient(
        host=str(config["ssh_host"]),
        port=int(config["ssh_port"]),
        user=str(config["ssh_user"]),
        password=str(config["ssh_password"]) or None,
    )
    try:
        remote_script = load_script(repo_root / "deploy_support" / "remote_maintenance.py")
        remote_result = ssh.run(build_remote_command(config, args.apply), input_text=remote_script)
        remote_payload = json.loads(remote_result.stdout)
        logger.info(
            "Remote maintenance evaluated %s tenant(s), planned delete: backups=%s archives=%s images=%s",
            remote_payload["totals"]["tenants"],
            remote_payload["totals"]["backups_planned_delete"],
            remote_payload["totals"]["archives_planned_delete"],
            remote_payload["totals"]["images_planned_delete"],
        )
    finally:
        ssh.close()

    local_payload = {
        "deploy_logs": summarize_local_cleanup(
            repo_root / "deploy_logs",
            int(config["keep_local_deploy_logs"]),
            apply=args.apply,
        ),
        "deploy_tmp": summarize_local_cleanup(
            repo_root / "deploy_tmp",
            int(config["keep_local_deploy_tmp"]),
            apply=args.apply,
        ),
        "maintenance_logs": summarize_local_cleanup(
            repo_root / "maintenance_logs",
            int(config["keep_local_maintenance_logs"]),
            apply=args.apply,
            protected_names={run_id},
        ),
    }
    logger.info(
        "Local maintenance planned delete: deploy_logs=%s deploy_tmp=%s maintenance_logs=%s",
        len(local_payload["deploy_logs"]["planned_delete"]),
        len(local_payload["deploy_tmp"]["planned_delete"]),
        len(local_payload["maintenance_logs"]["planned_delete"]),
    )

    report = {
        "run_id": run_id,
        "mode": "apply" if args.apply else "dry-run",
        "tenant_selector": config["target_tenant"],
        "policies": {
            "keep_backups": config["keep_remote_backups"],
            "keep_archives": config["keep_remote_archives"],
            "keep_images": config["keep_remote_images"],
            "keep_local_deploy_logs": config["keep_local_deploy_logs"],
            "keep_local_deploy_tmp": config["keep_local_deploy_tmp"],
            "keep_local_maintenance_logs": config["keep_local_maintenance_logs"],
        },
        "remote": remote_payload,
        "local": local_payload,
        "local_log_dir": str(log_dir),
        "totals": {
            "tenants": remote_payload["totals"]["tenants"],
            "remote_failures": remote_payload["totals"]["failures"],
            "local_failures": len(local_payload["deploy_logs"]["failed"]) + len(local_payload["deploy_tmp"]["failed"]) + len(local_payload["maintenance_logs"]["failed"]),
        },
    }
    write_json(log_dir / "maintenance_report.json", report)
    print_user_summary(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
