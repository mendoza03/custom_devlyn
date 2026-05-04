from __future__ import annotations
"""Preflight remoto no destructivo.

Este script corre dentro del servidor y responde preguntas clave antes del deploy:
1. Existe el tenant y su stack.
2. Docker/Compose estan operativos.
3. La imagen base actual existe en el host.
4. La base y el volumen web tienen las variables esperadas.
5. Hay espacio libre suficiente.
6. Los modulos seleccionados existen o no dentro de la DB.
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def run(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Wrapper remoto para comandos shell con errores legibles."""
    result = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
    )
    if check and result.returncode != 0:
        raise RuntimeError(
            f"Command failed ({result.returncode}): {' '.join(cmd)}\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return result


def load_env(path: Path) -> dict[str, str]:
    """Lee un `.env` simple de Compose sin evaluar shell."""
    env: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = raw_line.split("=", 1)
        env[key.strip()] = value.strip()
    return env


def shell_check(image: str, shell_command: str) -> tuple[bool, str]:
    """Ejecuta una sonda corta dentro de la imagen activa del tenant."""
    result = run(
        ["docker", "run", "--rm", "--entrypoint", "sh", image, "-lc", shell_command],
        check=False,
    )
    output = (result.stdout + result.stderr).strip()
    return result.returncode == 0, output


def query_module_states(stack_dir: Path, env: dict[str, str], modules: list[str]) -> dict[str, str]:
    """Consulta el estado actual de los modulos seleccionados en PostgreSQL."""
    if not modules:
        return {}

    escaped = ", ".join("'" + module.replace("'", "''") + "'" for module in modules)
    sql = (
        "SELECT name, state "
        "FROM ir_module_module "
        f"WHERE name IN ({escaped}) "
        "ORDER BY name"
    )
    result = run(
        [
            "docker",
            "compose",
            "exec",
            "-T",
            "-e",
            f"PGPASSWORD={env['POSTGRES_PASSWORD']}",
            "db",
            "psql",
            "-U",
            env["POSTGRES_USER"],
            "-d",
            env["BUSINESS_DB"],
            "-At",
            "-F",
            "|",
            "-c",
            sql,
        ],
        cwd=stack_dir,
    )
    states = {module: "absent" for module in modules}
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        name, state = line.split("|", 1)
        states[name] = state
    return states


def main() -> int:
    """Ejecuta el preflight completo y devuelve un JSON de descubrimiento."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant", required=True)
    parser.add_argument("--min-free-gb", type=int, required=True)
    parser.add_argument("--module", action="append", default=[])
    args = parser.parse_args()

    stack_dir = Path("/home/ubuntu/ccima-prod/stacks") / args.tenant
    env_path = stack_dir / ".env"
    compose_path = stack_dir / "docker-compose.yml"

    if not stack_dir.exists():
        raise RuntimeError(f"Stack directory not found: {stack_dir}")
    if not env_path.exists():
        raise RuntimeError(f"Stack env file not found: {env_path}")
    if not compose_path.exists():
        raise RuntimeError(f"Compose file not found: {compose_path}")

    env = load_env(env_path)
    required_env = [
        "ODOO_IMAGE",
        "BUSINESS_DB",
        "ODOO_PORT",
        "WEB_VOLUME_NAME",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
    ]
    missing_env = [key for key in required_env if not env.get(key)]
    if missing_env:
        raise RuntimeError(f"Missing required env keys: {', '.join(missing_env)}")

    # Paso 1: validar que Docker y Compose responden en el servidor.
    run(["docker", "compose", "version"])
    run(["docker", "info"])

    # Paso 2: confirmar que la imagen actual del tenant existe localmente.
    image_inspect = run(["docker", "image", "inspect", env["ODOO_IMAGE"]], check=False)
    if image_inspect.returncode != 0:
        raise RuntimeError(f"Base image not available locally: {env['ODOO_IMAGE']}")

    db_container = run(["docker", "compose", "ps", "-q", "db"], cwd=stack_dir).stdout.strip()
    if not db_container:
        raise RuntimeError("DB service is not running for this tenant")

    # Paso 3: comprobar que la DB este sana antes de pensar en backups o upgrades.
    db_inspect_raw = run(["docker", "inspect", db_container]).stdout
    db_inspect = json.loads(db_inspect_raw)[0]
    db_health = db_inspect["State"].get("Health", {}).get("Status", "unknown")
    if db_health != "healthy":
        raise RuntimeError(f"DB container health is not healthy: {db_health}")

    odoo_container = run(["docker", "compose", "ps", "-q", "odoo"], cwd=stack_dir).stdout.strip()

    free_gb = shutil.disk_usage("/home/ubuntu/ccima-prod").free / (1024 ** 3)
    if free_gb < args.min_free_gb:
        raise RuntimeError(
            f"Insufficient free space: {free_gb:.2f} GB available, "
            f"{args.min_free_gb} GB required"
        )

    addon_dir_ok, addon_dir_output = shell_check(env["ODOO_IMAGE"], "test -d /mnt/addons-sam")
    if not addon_dir_ok:
        raise RuntimeError(
            "/mnt/addons-sam is not available in the active image. "
            f"Output: {addon_dir_output}"
        )

    pip_ok, pip_output = shell_check(env["ODOO_IMAGE"], "python3 -m pip --version")
    if not pip_ok:
        raise RuntimeError(
            "python3 -m pip is not available in the active image. "
            f"Output: {pip_output}"
        )

    # Paso 4: devolver metadata suficiente para que el orquestador local arme el plan.
    module_states = query_module_states(stack_dir, env, sorted(set(args.module)))

    result = {
        "tenant": args.tenant,
        "stack_dir": str(stack_dir),
        "compose_path": str(compose_path),
        "env_path": str(env_path),
        "previous_image": env["ODOO_IMAGE"],
        "business_db": env["BUSINESS_DB"],
        "odoo_port": int(env["ODOO_PORT"]),
        "web_volume_name": env["WEB_VOLUME_NAME"],
        "postgres_user": env["POSTGRES_USER"],
        "db_container_id": db_container,
        "odoo_container_id": odoo_container,
        "db_health": db_health,
        "free_gb": round(free_gb, 2),
        "module_states": module_states,
        "checks": {
            "docker_compose": True,
            "docker_info": True,
            "base_image_present": True,
            "addons_path_present": addon_dir_ok,
            "pip_available": pip_ok,
        },
    }
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
