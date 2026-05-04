#!/usr/bin/env python3
"""Orquestador local para desplegar addons a un tenant de Odoo.

Flujo general:
1. Leer la configuracion fija del bloque superior.
2. Validar herramientas locales y parametros minimos.
3. Preparar un bundle local con los addons a desplegar.
4. Ejecutar un preflight remoto sin mutar nada.
5. Calcular el plan de upgrade/install de modulos.
6. Si es `--apply`, subir artefactos al servidor y lanzar el runner remoto.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import shlex
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from deploy_support.source_bundle import build_context_from_source, prepare_source_bundle
from deploy_support.ssh_tools import SSHClient


# --- Configuracion editable por el usuario ---
# Ejemplo real:
# - servidor: 138.186.200.38:5003
# - usuario: ubuntu
# - tenant: habitta
# - fuente: GitHub, rama/remoto origin/addons-ccima
# - addon: hide_any_menu_user_wise
SSH_HOST = "138.186.200.38"
SSH_PORT = 5003
SSH_USER = "ubuntu"
# Si dejas password, el script usa paramiko.
# Si lo dejas vacio, el script intentara usar ssh/scp con llaves del sistema.
# Ejemplo root: SSH_USER = "root" y SSH_PASSWORD = "<clave_root_real>"
SSH_PASSWORD = "ubuntu"

# Tenant destino. El script solo trabaja un tenant por ejecucion.
# Ejemplos: "habitta", "navetec", "energy"
TARGET_TENANT = "habitta"

# Fuente del codigo:
# - "github": usa el repo clonado y exporta exactamente el ref indicado en GIT_REF
# - "local": usa lo que tienes en tu working tree local
SOURCE_MODE = "local"

# Ref git a desplegar cuando SOURCE_MODE = "github"
# Ejemplos: "origin/addons-ccima", "main", "27a00ade"
GIT_REF = "origin/addons-ccima"

# Ruta local cuando SOURCE_MODE = "local"
# Ejemplos:
# - "." para todo el repo actual
# - "hide_any_menu_user_wise" para un solo addon
# - "custom_addons" para una carpeta que contiene varios addons
LOCAL_SOURCE_PATH = "."

# Lista de addons a desplegar.
# - [] significa "todos los addons detectados en la fuente seleccionada"
# - ["ccima_crm_reassign"] despliega solo ese addon
# - ["ccima_crm_reassign", "hide_any_menu_user_wise"] despliega solo esos dos
ADDON_NAMES: list[str] = [
    "apiccima"
]

# True instala modulos que existan en la DB como uninstalled/to install.
# False solo actualiza los que ya estan instalados.
INSTALL_MISSING = True

# True corre -u para modulos ya instalados.
# False solo sube codigo y no fuerza upgrade de los modulos instalados.
UPGRADE_SELECTED = True

# Espacio libre minimo requerido en el servidor antes de empezar.
# Ajustalo si el tenant o los backups son grandes.
MIN_FREE_GB = 20

# HTTP esperado despues del despliegue.
# En este servidor varios tenants responden 200 o 303 segun su configuracion.
HTTP_EXPECTED_CODES = [200, 303]

# Presentacion en consola durante `--apply`:
# - True: muestra solo hitos importantes y errores, ideal para demos o cliente
# - False: muestra todo el stream remoto completo
COMPACT_OUTPUT = True


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
    """Limita la CLI a dos modos: simulacion o aplicacion real."""
    parser = argparse.ArgumentParser(
        description="Deploy selected addons to one CCIMA tenant at a time.",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Validate and show the plan only")
    mode.add_argument("--apply", action="store_true", help="Execute backup, build and deployment")
    return parser.parse_args()


def utc_run_id() -> str:
    """Genera un identificador UTC estable para logs, backups y rutas remotas."""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def ensure_local_tools() -> None:
    """Verifica dependencias locales antes de tocar el servidor.

    Si se usa password, la sesion SSH/SCP se resuelve con paramiko.
    Si no se usa password, el script asume que el usuario ya tiene llaves
    configuradas y por eso exige `ssh` y `scp`.
    """
    base_tools = ["python3", "git", "tar"]
    if not (SSH_PASSWORD and SSH_PASSWORD.strip()):
        base_tools.extend(["ssh", "scp"])
    missing = [command for command in base_tools if shutil.which(command) is None]
    if missing:
        raise RuntimeError(f"Missing local tools: {', '.join(missing)}")
    if SSH_PASSWORD and SSH_PASSWORD.strip():
        try:
            import paramiko  # noqa: F401
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "SSH_PASSWORD is set, so `paramiko` is required locally. "
                "Install it with `python3 -m pip install paramiko`."
            ) from exc


def validate_config() -> dict[str, object]:
    """Normaliza la configuracion global en un diccionario listo para usar."""
    if SOURCE_MODE not in {"github", "local"}:
        raise RuntimeError("SOURCE_MODE must be 'github' or 'local'")
    if not TARGET_TENANT.strip():
        raise RuntimeError("TARGET_TENANT must not be empty")
    if not isinstance(ADDON_NAMES, list):
        raise RuntimeError("ADDON_NAMES must be a list of addon names")
    if not HTTP_EXPECTED_CODES:
        raise RuntimeError("HTTP_EXPECTED_CODES must not be empty")
    return {
        "ssh_host": SSH_HOST,
        "ssh_port": SSH_PORT,
        "ssh_user": SSH_USER,
        "ssh_password": SSH_PASSWORD.strip(),
        "target_tenant": TARGET_TENANT,
        "source_mode": SOURCE_MODE,
        "git_ref": GIT_REF,
        "local_source_path": LOCAL_SOURCE_PATH,
        "addon_names": [item for item in ADDON_NAMES if item.strip()],
        "install_missing": INSTALL_MISSING,
        "upgrade_selected": UPGRADE_SELECTED,
        "min_free_gb": int(MIN_FREE_GB),
        "http_expected_codes": [int(item) for item in HTTP_EXPECTED_CODES],
        "compact_output": bool(COMPACT_OUTPUT),
    }


def setup_logging(log_dir: Path) -> logging.Logger:
    """Crea logging dual: consola + archivo local por corrida."""
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("tenant_deploy")
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


def write_json(path: Path, payload: dict) -> None:
    """Serializa manifestos y reportes locales de forma consistente."""
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def join_or_dash(items: list[str]) -> str:
    """Convierte listas cortas en texto amigable para consola."""
    return ", ".join(items) if items else "-"


def use_color() -> bool:
    """Activa ANSI solo cuando la consola lo soporta y NO_COLOR no lo deshabilita."""
    return sys.stdout.isatty() and not os.environ.get("NO_COLOR")


def paint(text: str, *styles: str) -> str:
    """Aplica estilos ANSI de forma segura."""
    if not use_color() or not styles:
        return text
    prefix = "".join(ANSI_COLORS[style] for style in styles)
    return f"{prefix}{text}{ANSI_RESET}"


class ColorFormatter(logging.Formatter):
    """Colorea el nivel del log para que la consola sea mas legible."""

    LEVEL_STYLES = {
        logging.INFO: ("cyan",),
        logging.WARNING: ("yellow", "bold"),
        logging.ERROR: ("red", "bold"),
        logging.CRITICAL: ("red", "bold"),
    }

    def format(self, record: logging.LogRecord) -> str:
        rendered = super().format(record)
        styles = self.LEVEL_STYLES.get(record.levelno)
        if not styles:
            return rendered
        return paint(rendered, *styles)


class CompactRemoteReporter:
    """Resume el stream remoto en hitos cortos y suprime el ruido repetitivo.

    El log completo sigue quedando en `remote_apply_stream.log`. Esto solo reduce
    la salida de consola para que el usuario vea progreso entendible.
    """

    def __init__(self) -> None:
        self._seen_stage_keys: set[str] = set()
        self._http_retry_reported = False

    def _emit_once(self, key: str, message: str, *styles: str) -> str | None:
        if key in self._seen_stage_keys:
            return None
        self._seen_stage_keys.add(key)
        return paint(message + "\n", *styles)

    def render_line(self, line: str) -> str | None:
        stripped = line.strip()
        if not stripped:
            return None

        upper = stripped.upper()
        if (
            "DEPLOYMENT FAILED:" in upper
            or upper.startswith("ERROR ")
            or " ERROR " in upper
            or upper.startswith("CRITICAL ")
            or " CRITICAL " in upper
            or "PARSEERROR:" in upper
            or stripped.startswith("Traceback")
        ):
            return paint(line if line.endswith("\n") else line + "\n", "red", "bold")

        if stripped.startswith("Starting rollback:"):
            return self._emit_once("rollback-start", "Rollback: restaurando estado previo", "yellow", "bold")
        if stripped == "Rollback completed":
            return self._emit_once("rollback-end", "Rollback completado", "green", "bold")
        if stripped.startswith("Creating backup in "):
            return self._emit_once("backup-start", "Backup: creando punto de rollback", "cyan", "bold")
        if stripped.startswith("HTTP validation retry"):
            if self._http_retry_reported:
                return None
            self._http_retry_reported = True
            return paint("Validacion HTTP: esperando respuesta del tenant\n", "yellow")
        if stripped == "Validating tenant health":
            return self._emit_once("tenant-health-start", "Health check: validando tenant actualizado", "green")
        if stripped.startswith("Tenant health OK:"):
            return self._emit_once(
                "tenant-health-ok",
                "Health check: tenant responde y contenedores OK",
                "green",
                "bold",
            )
        if stripped.startswith("Tenant health issues:"):
            return paint("Health check: se detectaron problemas en el tenant\n", "red", "bold")
        if '"status": "ok"' in stripped:
            return self._emit_once("remote-ok", "Deploy remoto completado", "green", "bold")
        if '"status": "error"' in stripped:
            return self._emit_once("remote-error", "Deploy remoto reporto error", "red", "bold")

        stage_rules: list[tuple[str, bool, str, tuple[str, ...]]] = [
            (
                "backup-db",
                stripped.startswith("$ docker compose up -d db"),
                "Backup: preparando contenedor DB",
                ("cyan",),
            ),
            (
                "backup-web",
                "/backup/web.tar.gz" in stripped and stripped.startswith("$ docker run --rm"),
                "Backup: empaquetando volumen web",
                ("cyan",),
            ),
            (
                "extract-context",
                stripped.startswith("$ tar -xzf ") and "source_context.tar.gz" in stripped,
                "Preparacion: extrayendo contexto remoto",
                ("cyan",),
            ),
            (
                "build-image",
                stripped.startswith("$ docker build "),
                "Build: construyendo imagen derivada",
                ("blue", "bold"),
            ),
            (
                "runtime-python",
                stripped.startswith("$ docker run --rm --entrypoint /bin/sh ") and "python3 --version" in stripped,
                "Runtime check: validando Python",
                ("blue",),
            ),
            (
                "runtime-imports",
                stripped.startswith("$ docker run --rm --entrypoint /opt/odoo-venv/bin/python "),
                "Runtime check: validando imports Python",
                ("blue",),
            ),
            (
                "runtime-odoo",
                stripped.startswith("$ docker run --rm --entrypoint /bin/sh ") and "odoo --version" in stripped,
                "Runtime check: validando Odoo",
                ("blue",),
            ),
            (
                "stop-odoo",
                stripped.startswith("$ docker compose stop odoo"),
                "Upgrade: deteniendo Odoo",
                ("blue",),
            ),
            (
                "upgrade-run",
                stripped.startswith("$ docker compose --env-file ") and " run --rm --no-deps -T odoo odoo " in stripped,
                "Upgrade: ejecutando modulos seleccionados",
                ("blue", "bold"),
            ),
            (
                "bring-up-odoo",
                stripped.startswith("$ docker compose up -d odoo"),
                "Cutover: levantando tenant con imagen nueva",
                ("blue", "bold"),
            ),
            (
                "validate-modules",
                stripped.startswith("$ docker compose exec -T ") and "SELECT name, state FROM ir_module_module" in stripped,
                "Validacion final: comprobando modulos",
                ("green",),
            ),
        ]
        for key, matched, message, styles in stage_rules:
            if matched:
                return self._emit_once(key, message, *styles)
        return None


def describe_source(run_manifest: dict[str, object]) -> str:
    """Resume de forma humana si la fuente fue local o GitHub."""
    source_mode = str(run_manifest["source_mode"])
    if source_mode == "github":
        git_ref = run_manifest.get("git_ref") or "-"
        git_commit = run_manifest.get("git_commit") or "-"
        return f"github ({git_ref}, commit {git_commit})"
    return f"local ({run_manifest['source_root']})"


def count_findings(log_path: Path) -> dict[str, int]:
    """Cuenta warnings y errores visibles en el stream remoto."""
    counts = {"warnings": 0, "errors": 0}
    if not log_path.exists():
        return counts
    warning_patterns = (
        re.compile(r"(^|\s)WARNING(\s|:)", re.IGNORECASE),
        re.compile(r"^#\d+\s+WARNING:", re.IGNORECASE),
    )
    error_patterns = (
        re.compile(r"(^|\s)ERROR(\s|:)", re.IGNORECASE),
        re.compile(r"^#\d+\s+ERROR:", re.IGNORECASE),
        re.compile(r"^error:", re.IGNORECASE),
    )
    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if any(pattern.search(stripped) for pattern in warning_patterns):
            counts["warnings"] += 1
        if any(pattern.search(stripped) for pattern in error_patterns):
            counts["errors"] += 1
    return counts


def summarize_http_validation(http_validation: object) -> str:
    """Resume la validacion HTTP final con rutas cortas."""
    if not isinstance(http_validation, dict) or not http_validation:
        return "-"
    bits: list[str] = []
    for url, status in sorted(http_validation.items()):
        path = urlsplit(str(url)).path or "/"
        bits.append(f"{path}={status}")
    return " | ".join(bits)


def summarize_service_health(service_report: object) -> str:
    """Resume el estado tecnico de un contenedor del tenant."""
    if not isinstance(service_report, dict) or not service_report:
        return "-"
    running = "running" if service_report.get("running") else "stopped"
    health = service_report.get("health") or "n/a"
    restart_count = service_report.get("restart_count", 0)
    return f"{running} | health={health} | restarts={restart_count}"


def print_user_summary(run_manifest: dict[str, object], *, dry_run: bool) -> None:
    """Imprime un resumen corto pensado para un usuario no tecnico."""
    module_plan = run_manifest["module_plan"]
    assert isinstance(module_plan, dict)
    action_bits = []
    if module_plan["upgrade"]:
        action_bits.append(f"upgrade: {join_or_dash(list(module_plan['upgrade']))}")
    if module_plan["install"]:
        action_bits.append(f"install: {join_or_dash(list(module_plan['install']))}")
    if module_plan["noop"]:
        action_bits.append(f"solo codigo: {join_or_dash(list(module_plan['noop']))}")
    if module_plan["absent"]:
        action_bits.append(f"no existen en DB: {join_or_dash(list(module_plan['absent']))}")
    planned_action = " | ".join(action_bits) if action_bits else "sin cambios de modulo"
    finding_summary = run_manifest.get("log_summary", {})
    warnings = int(finding_summary.get("warnings", 0)) if isinstance(finding_summary, dict) else 0
    errors = int(finding_summary.get("errors", 0)) if isinstance(finding_summary, dict) else 0

    title = paint("DRY RUN OK", "green", "bold") if dry_run else paint("DEPLOY OK", "green", "bold")
    label = lambda text: paint(text, "blue", "bold")
    print()
    print(title)
    print(f"{label('Tenant:')} {run_manifest['tenant']}")
    print(f"{label('Modo fuente:')} {run_manifest['source_mode']}")
    print(f"{label('Origen:')} {describe_source(run_manifest)}")
    print(f"{label('Addons:')} {join_or_dash(list(run_manifest['selected_addons']))}")
    print(f"{label('Imagen actual:')} {run_manifest['previous_image']}")
    print(f"{label('Imagen nueva:')} {run_manifest['new_image_tag']}")
    print(f"{label('Accion planificada:')} {planned_action}")
    print(f"{label('Puerto Odoo:')} {run_manifest['odoo_port']}")
    if not dry_run:
        tenant_health = run_manifest.get("tenant_health", {})
        health_status = "OK"
        health_styles = ("green", "bold")
        health_issues: list[str] = []
        if isinstance(tenant_health, dict):
            if tenant_health.get("status") != "ok":
                health_status = "ERROR"
                health_styles = ("red", "bold")
            raw_issues = tenant_health.get("issues", [])
            if isinstance(raw_issues, list):
                health_issues = [str(item) for item in raw_issues]
        services = tenant_health.get("services", {}) if isinstance(tenant_health, dict) else {}
        print(f"{label('Salud tenant:')} {paint(health_status, *health_styles)}")
        print(f"{label('HTTP final:')} {summarize_http_validation(run_manifest.get('http_validation'))}")
        print(
            f"{label('Odoo contenedor:')} "
            f"{summarize_service_health(services.get('odoo') if isinstance(services, dict) else None)}"
        )
        print(
            f"{label('DB contenedor:')} "
            f"{summarize_service_health(services.get('db') if isinstance(services, dict) else None)}"
        )
        if health_issues:
            print(f"{label('Observaciones salud:')} {join_or_dash(health_issues)}")
        print(f"{label('Warnings detectados:')} {paint(str(warnings), 'yellow', 'bold')}")
        print(f"{label('Errores detectados:')} {paint(str(errors), 'red', 'bold')}")
    print(f"{label('Log local:')} {run_manifest['local_log_dir']}")
    print(f"{label('Archivo remoto:')} {run_manifest['archive_dir']}")
    print(f"{label('Backup remoto:')} {run_manifest['backup_dir']}")
    print(f"{label('Detalle tecnico JSON:')} {Path(str(run_manifest['local_log_dir'])) / 'run_manifest.json'}")


def build_remote_probe_command(tenant: str, min_free_gb: int, modules: list[str]) -> str:
    """Arma el comando remoto que ejecuta el preflight dentro del servidor."""
    command = ["python3", "-", "--tenant", tenant, "--min-free-gb", str(min_free_gb)]
    for module in modules:
        command.extend(["--module", module])
    return shlex.join(command)


def load_script(path: Path) -> str:
    """Lee un helper Python para enviarlo por stdin al servidor."""
    return path.read_text(encoding="utf-8")


def module_plan_from_states(
    module_states: dict[str, str],
    *,
    upgrade_selected: bool,
    install_missing: bool,
) -> dict[str, object]:
    """Traduce el estado actual de modulos en una accion concreta.

    Resultado:
    - `upgrade`: modulos instalados que iran con `-u`
    - `install`: modulos conocidos en DB pero desinstalados, que iran con `-i`
    - `noop`: modulos que solo viajaran dentro de la imagen
    - `absent`: modulos que la DB ni siquiera conoce
    """
    upgrade: list[str] = []
    install: list[str] = []
    noop: list[str] = []
    absent: list[str] = []

    for module in sorted(module_states):
        state = module_states[module]
        if state in {"installed", "to upgrade"}:
            if upgrade_selected:
                upgrade.append(module)
            else:
                noop.append(module)
        elif state in {"uninstalled", "to install"}:
            if install_missing:
                install.append(module)
            else:
                noop.append(module)
        elif state == "absent":
            absent.append(module)
        else:
            noop.append(module)

    return {
        "upgrade": upgrade,
        "install": install,
        "noop": noop,
        "absent": absent,
        "states": module_states,
    }


def make_remote_paths(tenant: str, run_id: str) -> dict[str, str]:
    """Centraliza todas las rutas remotas persistentes de la corrida."""
    archive_dir = f"/home/ubuntu/ccima-prod/archive/deployments/{tenant}/{run_id}"
    return {
        "archive_dir": archive_dir,
        "work_dir": f"{archive_dir}/work",
        "backup_dir": f"/home/ubuntu/ccima-prod/backups/{tenant}-deploy-{run_id}",
        "context_tarball": f"{archive_dir}/source_context.tar.gz",
        "source_manifest": f"{archive_dir}/source_manifest.json",
        "run_manifest": f"{archive_dir}/run_manifest.json",
        "remote_apply": f"{archive_dir}/remote_apply.py",
    }


def make_image_tag(tenant: str, run_id: str) -> str:
    """Genera un tag local e inmutable por tenant y corrida."""
    return f"devaie/odoo_ccima:{tenant}-deploy-{run_id.lower()}"


def fetch_remote_manifest(ssh: SSHClient, remote_path: str) -> dict | None:
    """Intenta recuperar el manifiesto final desde el servidor para guardarlo localmente."""
    try:
        result = ssh.run(f"cat {shlex.quote(remote_path)}", check=False)
    except RuntimeError:
        return None
    if result.returncode != 0 or not result.stdout.strip():
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def main() -> int:
    """Coordina toda la corrida local.

    Paso a paso:
    1. Lee flags y valida herramientas/configuracion.
    2. Prepara el source bundle segun `github` o `local`.
    3. Ejecuta preflight remoto para descubrir imagen base y estado del tenant.
    4. Calcula el plan de modulos y genera el contexto Docker.
    5. En `--dry-run`, solo imprime el plan.
    6. En `--apply`, sube artefactos y ejecuta el despliegue remoto.
    """
    args = parse_args()
    config = validate_config()
    ensure_local_tools()

    # Paso 1: crear rutas locales para esta corrida.
    repo_root = Path(__file__).resolve().parent
    run_id = utc_run_id()
    log_dir = repo_root / "deploy_logs" / run_id
    tmp_dir = repo_root / "deploy_tmp" / run_id
    logger = setup_logging(log_dir)
    logger.info("Starting tenant deploy run %s", run_id)
    compact_reporter = CompactRemoteReporter()

    # Paso 2: construir un bundle local autocontenido con los addons seleccionados.
    prepared_source = prepare_source_bundle(
        repo_root=repo_root,
        source_mode=config["source_mode"],
        git_ref=str(config["git_ref"]),
        local_source_path=str(config["local_source_path"]),
        addon_names=list(config["addon_names"]),
        run_tmp_dir=tmp_dir / "source",
    )
    selected_addons = [manifest.name for manifest in prepared_source.selected_addons]
    logger.info("Selected addons: %s", ", ".join(selected_addons))

    # Paso 3: abrir el canal SSH que se reutilizara para probe, uploads y apply.
    ssh = SSHClient(
        host=str(config["ssh_host"]),
        port=int(config["ssh_port"]),
        user=str(config["ssh_user"]),
        password=str(config["ssh_password"]) or None,
    )
    try:
        # Paso 4: ejecutar un preflight remoto sin crear artefactos persistentes.
        probe_script = load_script(repo_root / "deploy_support" / "remote_probe.py")
        probe_command = build_remote_probe_command(
            str(config["target_tenant"]),
            int(config["min_free_gb"]),
            selected_addons,
        )
        probe_result = ssh.run(probe_command, input_text=probe_script)
        remote_probe = json.loads(probe_result.stdout)
        logger.info(
            "Remote preflight OK for tenant %s using image %s",
            remote_probe["tenant"],
            remote_probe["previous_image"],
        )

        # Paso 5: decidir que modulos se actualizan, se instalan o solo viajan en la imagen.
        module_plan = module_plan_from_states(
            remote_probe["module_states"],
            upgrade_selected=bool(config["upgrade_selected"]),
            install_missing=bool(config["install_missing"]),
        )

        # Paso 6: generar un contexto Docker local basado en la imagen activa del tenant.
        build_context = build_context_from_source(
            prepared_source,
            base_image=remote_probe["previous_image"],
            run_tmp_dir=tmp_dir / "context",
        )

        remote_paths = make_remote_paths(str(config["target_tenant"]), run_id)
        run_manifest = {
            "run_id": run_id,
            "tenant": config["target_tenant"],
            "source_mode": config["source_mode"],
            "git_ref": prepared_source.git_ref,
            "git_commit": prepared_source.git_commit,
            "source_root": prepared_source.root_description,
            "selected_addons": selected_addons,
            "python_runtime_strategy": "venv",
            "required_python_packages": prepared_source.required_python_packages,
            "required_python_imports": prepared_source.required_python_imports,
            "previous_image": remote_probe["previous_image"],
            "new_image_tag": make_image_tag(str(config["target_tenant"]), run_id),
            "stack_dir": remote_probe["stack_dir"],
            "business_db": remote_probe["business_db"],
            "odoo_port": remote_probe["odoo_port"],
            "web_volume_name": remote_probe["web_volume_name"],
            "env_files": [".env", ".env.final", ".env.dry-run"],
            "http_expected_codes": config["http_expected_codes"],
            "module_plan": module_plan,
            "archive_dir": remote_paths["archive_dir"],
            "work_dir": remote_paths["work_dir"],
            "backup_dir": remote_paths["backup_dir"],
            "context_tarball": remote_paths["context_tarball"],
            "source_manifest_remote": remote_paths["source_manifest"],
            "remote_script_path": remote_paths["remote_apply"],
            "preflight": remote_probe,
            "local_log_dir": str(log_dir),
            "local_tmp_dir": str(tmp_dir),
            "mode": "dry-run" if args.dry_run else "apply",
            "ssh_user": config["ssh_user"],
            "ssh_password_configured": bool(config["ssh_password"]),
            "compact_output": bool(config["compact_output"]),
        }

        write_json(log_dir / "source_manifest.json", prepared_source.source_manifest)
        write_json(log_dir / "run_manifest.json", run_manifest)

        logger.info(
            "Module plan: upgrade=%s install=%s noop=%s absent=%s",
            ",".join(module_plan["upgrade"]) or "-",
            ",".join(module_plan["install"]) or "-",
            ",".join(module_plan["noop"]) or "-",
            ",".join(module_plan["absent"]) or "-",
        )
        logger.info("Required Python packages: %s", ", ".join(prepared_source.required_python_packages) or "-")
        logger.info("Required Python imports: %s", ", ".join(prepared_source.required_python_imports) or "-")
        logger.info("Planned remote archive dir: %s", remote_paths["archive_dir"])
        logger.info("Planned remote backup dir: %s", remote_paths["backup_dir"])

        # Paso 7: en dry-run solo se devuelve el plan consolidado y se termina aqui.
        if args.dry_run:
            logger.info("Dry run completed without creating persistent remote artifacts")
            print_user_summary(run_manifest, dry_run=True)
            return 0

        # Paso 8: crear rutas remotas y subir el contexto + manifiestos del despliegue.
        logger.info("Uploading deployment artifacts to %s", remote_paths["archive_dir"])
        mkdir_command = "mkdir -p {archive} {work} {backup}".format(
            archive=shlex.quote(remote_paths["archive_dir"]),
            work=shlex.quote(remote_paths["work_dir"]),
            backup=shlex.quote(remote_paths["backup_dir"]),
        )
        ssh.run(mkdir_command)
        ssh.upload(build_context.tarball_path, remote_paths["context_tarball"])
        ssh.upload(log_dir / "source_manifest.json", remote_paths["source_manifest"])
        ssh.upload(log_dir / "run_manifest.json", remote_paths["run_manifest"])
        ssh.upload(repo_root / "deploy_support" / "remote_apply.py", remote_paths["remote_apply"])

        # Paso 9: arrancar el runner remoto que hace backup, build, upgrade y rollback.
        logger.info("Starting remote apply")
        remote_command = shlex.join(
            [
                "python3",
                remote_paths["remote_apply"],
                remote_paths["run_manifest"],
            ]
        )
        remote_stream_log = log_dir / "remote_apply_stream.log"
        exit_code = ssh.stream(
            remote_command,
            remote_stream_log,
            line_mapper=compact_reporter.render_line if bool(config["compact_output"]) else None,
        )
        log_summary = count_findings(remote_stream_log)

        # Paso 10: si el runner actualizo el manifiesto remoto, lo volvemos a copiar localmente.
        final_manifest = fetch_remote_manifest(ssh, remote_paths["run_manifest"])
        manifest_for_user = dict(run_manifest)
        if final_manifest:
            manifest_for_user.update(final_manifest)
        if exit_code != 0 and log_summary["errors"] == 0:
            log_summary["errors"] = 1
        manifest_for_user["log_summary"] = log_summary
        write_json(log_dir / "run_manifest.json", manifest_for_user)

        logger.info(
            "Remote findings summary: warnings=%s errors=%s",
            log_summary["warnings"],
            log_summary["errors"],
        )

        if exit_code != 0:
            raise RuntimeError(
                "Remote deployment failed. "
                f"Inspect local logs in {log_dir} and remote logs in {remote_paths['archive_dir']}"
            )

        # Paso 11: devolver una salida corta con la ruta remota principal de auditoria.
        logger.info("Deployment completed successfully")
        logger.info("Remote archive dir: %s", remote_paths["archive_dir"])
        print_user_summary(manifest_for_user, dry_run=False)
        return 0
    finally:
        # Cierre explicito para no dejar sesiones abiertas en paramiko.
        ssh.close()


if __name__ == "__main__":
    raise SystemExit(main())
