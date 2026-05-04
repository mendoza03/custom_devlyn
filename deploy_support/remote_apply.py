from __future__ import annotations
"""Runner remoto que ejecuta el despliegue real.

Secuencia completa:
1. Crear backup remoto.
2. Extraer el contexto Docker subido desde la maquina local.
3. Construir una imagen derivada de la imagen actual del tenant.
4. Validar el runtime Python aislado antes de tocar la DB.
5. Ejecutar upgrade/install de modulos si corresponde.
6. Cambiar `.env*` al nuevo tag de imagen.
7. Levantar Odoo y validar HTTP + estado de modulos.
8. Si algo falla tras el backup, disparar rollback automatico.
"""

import argparse
import json
import shutil
import subprocess
import sys
import time
import traceback
import urllib.error
import urllib.request
from pathlib import Path


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Permite observar codigos 303/302 como respuesta valida sin seguir redirects."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        return None


class RemoteDeployer:
    """Motor remoto de despliegue y rollback."""

    def __init__(self, manifest_path: Path) -> None:
        """Carga el manifiesto generado por `tenant_deploy.py` y fija el contexto."""
        self.manifest_path = manifest_path
        self.manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.stack_dir = Path(self.manifest["stack_dir"])
        self.archive_dir = Path(self.manifest["archive_dir"])
        self.work_dir = Path(self.manifest["work_dir"])
        self.backup_dir = Path(self.manifest["backup_dir"])
        self.context_tarball = Path(self.manifest["context_tarball"])
        self.env_files = self.manifest["env_files"]
        self.previous_image = self.manifest["previous_image"]
        self.new_image_tag = self.manifest["new_image_tag"]
        self.business_db = self.manifest["business_db"]
        self.web_volume_name = self.manifest["web_volume_name"]
        self.http_expected_codes = {int(item) for item in self.manifest["http_expected_codes"]}
        self.module_plan = self.manifest["module_plan"]
        self.required_python_imports = list(self.manifest.get("required_python_imports", []))
        self.run_log_path = self.archive_dir / "run.log"
        self.rollback_needed = False
        self.db_touched = False
        self.env_swapped = False
        self.rollback_log_path = self.archive_dir / "rollback.log"
        self.manifest["python_runtime_strategy"] = self.manifest.get("python_runtime_strategy", "venv")

    def log(self, message: str) -> None:
        """Escribe una linea tanto en stdout como en `run.log`."""
        line = message.rstrip()
        print(line, flush=True)
        with self.run_log_path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def run(
        self,
        cmd: list[str],
        *,
        log_name: str | None = None,
        cwd: Path | None = None,
        stdin_path: Path | None = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        """Ejecuta un comando local del servidor y duplica su salida a logs.

        Este wrapper es el punto central de auditoria del runner remoto.
        """
        target_log = self.archive_dir / log_name if log_name else None
        display = " ".join(cmd)
        self.log(f"$ {display}")
        if target_log:
            with target_log.open("a", encoding="utf-8") as handle:
                handle.write(f"$ {display}\n")
        stdin_handle = stdin_path.open("rb") if stdin_path else None
        try:
            process = subprocess.Popen(
                cmd,
                cwd=str(cwd) if cwd else None,
                stdin=stdin_handle,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            combined: list[str] = []
            assert process.stdout is not None
            for line in process.stdout:
                combined.append(line)
                sys.stdout.write(line)
                with self.run_log_path.open("a", encoding="utf-8") as handle:
                    handle.write(line)
                if target_log:
                    with target_log.open("a", encoding="utf-8") as handle:
                        handle.write(line)
            returncode = process.wait()
        finally:
            if stdin_handle:
                stdin_handle.close()

        result = subprocess.CompletedProcess(
            args=cmd,
            returncode=returncode,
            stdout="".join(combined),
            stderr="",
        )
        if check and returncode != 0:
            raise RuntimeError(f"Command failed ({returncode}): {display}")
        return result

    def load_env(self, path: Path) -> dict[str, str]:
        """Lee un `.env` del stack sin evaluar shell."""
        env: dict[str, str] = {}
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = raw_line.split("=", 1)
            env[key.strip()] = value.strip()
        return env

    def replace_image_reference(self, path: Path, image: str) -> None:
        """Reescribe `ODOO_IMAGE=` dentro de un archivo `.env`."""
        lines = path.read_text(encoding="utf-8").splitlines()
        output: list[str] = []
        replaced = False
        for line in lines:
            if line.startswith("ODOO_IMAGE="):
                output.append(f"ODOO_IMAGE={image}")
                replaced = True
            else:
                output.append(line)
        if not replaced:
            output.append(f"ODOO_IMAGE={image}")
        path.write_text("\n".join(output) + "\n", encoding="utf-8")

    def query_module_states(self, env: dict[str, str], modules: list[str]) -> dict[str, str]:
        """Consulta el estado final de los modulos tras el despliegue."""
        if not modules:
            return {}
        escaped = ", ".join("'" + module.replace("'", "''") + "'" for module in modules)
        sql = (
            "SELECT name, state "
            "FROM ir_module_module "
            f"WHERE name IN ({escaped}) "
            "ORDER BY name"
        )
        result = self.run(
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
                self.business_db,
                "-At",
                "-F",
                "|",
                "-c",
                sql,
            ],
            cwd=self.stack_dir,
            log_name="upgrade.log",
        )
        states = {module: "absent" for module in modules}
        for line in result.stdout.splitlines():
            if not line.strip():
                continue
            name, state = line.split("|", 1)
            states[name] = state
        return states

    def backup(self) -> None:
        """Genera el punto de rollback antes de tocar imagen, DB o filestore.

        Incluye:
        - `.env`, `.env.final`, `.env.dry-run`
        - `docker-compose.yml`
        - dump de la base
        - globals.sql
        - backup del volumen web
        """
        self.log(f"Creating backup in {self.backup_dir}")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        env = self.load_env(self.stack_dir / ".env")

        # Paso 1: asegurar que la DB este arriba para poder exportarla.
        self.run(["docker", "compose", "up", "-d", "db"], cwd=self.stack_dir)
        for env_file in self.env_files:
            source = self.stack_dir / env_file
            if source.exists():
                shutil.copy2(source, self.backup_dir / env_file)
        shutil.copy2(self.stack_dir / "docker-compose.yml", self.backup_dir / "docker-compose.yml")

        # Paso 2: exportar la base de negocio en formato custom de pg_dump.
        dump_path = self.backup_dir / f"{self.manifest['tenant']}.dump"
        dump_result = subprocess.run(
            [
                "docker",
                "compose",
                "exec",
                "-T",
                "-e",
                f"PGPASSWORD={env['POSTGRES_PASSWORD']}",
                "db",
                "pg_dump",
                "-U",
                env["POSTGRES_USER"],
                "-d",
                self.business_db,
                "-Fc",
                "--no-owner",
                "--no-privileges",
            ],
            cwd=str(self.stack_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if dump_result.returncode != 0:
            raise RuntimeError(
                f"pg_dump failed ({dump_result.returncode}): {dump_result.stderr.decode('utf-8', 'replace')}"
            )
        dump_path.write_bytes(dump_result.stdout)

        # Paso 3: exportar roles/privilegios globales del clustser PostgreSQL.
        globals_result = subprocess.run(
            [
                "docker",
                "compose",
                "exec",
                "-T",
                "-e",
                f"PGPASSWORD={env['POSTGRES_PASSWORD']}",
                "db",
                "pg_dumpall",
                "-g",
                "-U",
                env["POSTGRES_USER"],
            ],
            cwd=str(self.stack_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if globals_result.returncode != 0:
            raise RuntimeError(
                f"pg_dumpall failed ({globals_result.returncode}): {globals_result.stderr.decode('utf-8', 'replace')}"
            )
        (self.backup_dir / "globals.sql").write_bytes(globals_result.stdout)

        # Paso 4: empaquetar el volumen web para recuperar filestore y adjuntos.
        self.run(
            [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{self.web_volume_name}:/src:ro",
                "-v",
                f"{self.backup_dir}:/backup",
                "postgres:16",
                "bash",
                "-lc",
                "cd /src && tar --warning=no-file-changed --exclude='./sessions' -czf /backup/web.tar.gz .",
            ],
        )
        self.rollback_needed = True

    def extract_context(self) -> None:
        """Descomprime el contexto Docker enviado desde la maquina local."""
        context_parent = self.work_dir / "context"
        if context_parent.exists():
            shutil.rmtree(context_parent)
        context_parent.mkdir(parents=True, exist_ok=True)
        self.run(
            ["tar", "-xzf", str(self.context_tarball), "-C", str(self.work_dir)],
        )

    def build_image(self) -> None:
        """Construye la nueva imagen del tenant y captura sus RepoDigests si existen."""
        self.run(
            ["docker", "build", "-t", self.new_image_tag, str(self.work_dir / "context")],
            log_name="build.log",
        )
        digest_result = self.run(
            [
                "docker",
                "image",
                "inspect",
                self.new_image_tag,
                "--format",
                "{{json .RepoDigests}}",
            ],
            log_name="build.log",
        )
        try:
            digests = json.loads(digest_result.stdout.strip())
        except json.JSONDecodeError:
            digests = []
        self.manifest["new_image_repo_digests"] = digests

    def validate_runtime(self) -> None:
        """Valida que la imagen nueva arranque con el runtime Python esperado.

        Esta validacion ocurre antes de ejecutar `-u` o `-i`, asi que un fallo aqui
        no debe tocar la base. El objetivo es detectar de inmediato problemas como:
        - `venv` mal construido
        - dependencias Python no instaladas
        - wrapper `odoo` no funcional
        """
        validation = {
            "status": "running",
            "python_runtime_strategy": self.manifest.get("python_runtime_strategy", "venv"),
            "required_python_imports": self.required_python_imports,
        }
        try:
            python_version = self.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "--entrypoint",
                    "/bin/sh",
                    self.new_image_tag,
                    "-lc",
                    "python3 --version",
                ],
                log_name="runtime_validation.log",
            ).stdout.strip()

            if self.required_python_imports:
                import_code = (
                    "import importlib, json, sys\n"
                    "mods = json.loads(sys.argv[1])\n"
                    "failed = []\n"
                    "for name in mods:\n"
                    "    try:\n"
                    "        importlib.import_module(name)\n"
                    "        print(f'import ok: {name}')\n"
                    "    except Exception as exc:\n"
                    "        failed.append(f'{name}: {exc}')\n"
                    "if failed:\n"
                    "    print('import failures:')\n"
                    "    for item in failed:\n"
                    "        print(item)\n"
                    "    raise SystemExit(1)\n"
                )
                self.run(
                    [
                        "docker",
                        "run",
                        "--rm",
                        "--entrypoint",
                        "/opt/odoo-venv/bin/python",
                        self.new_image_tag,
                        "-c",
                        import_code,
                        json.dumps(self.required_python_imports),
                    ],
                    log_name="runtime_validation.log",
                )

            odoo_version = self.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "--entrypoint",
                    "/bin/sh",
                    self.new_image_tag,
                    "-lc",
                    "odoo --version",
                ],
                log_name="runtime_validation.log",
            ).stdout.strip()

            validation.update(
                {
                    "status": "ok",
                    "python_version": python_version,
                    "odoo_version": odoo_version,
                    "validated_imports": self.required_python_imports,
                }
            )
            self.manifest["python_runtime_validation"] = validation
        except Exception as exc:
            validation.update(
                {
                    "status": "error",
                    "error": str(exc),
                }
            )
            self.manifest["python_runtime_validation"] = validation
            raise RuntimeError(f"Python runtime validation failed: {exc}") from exc

    def run_module_plan(self) -> None:
        """Ejecuta `-u` y/o `-i` con la nueva imagen antes del corte final.

        La DB queda marcada como tocada a partir del momento en que se corre este paso.
        Eso hace que el rollback incluya restauracion de base y volumen web.
        """
        upgrade_modules = self.module_plan.get("upgrade", [])
        install_modules = self.module_plan.get("install", [])
        if not upgrade_modules and not install_modules:
            self.log("No module upgrade/install action required")
            return

        temp_env = self.work_dir / "apply.env"
        shutil.copy2(self.stack_dir / ".env", temp_env)
        self.replace_image_reference(temp_env, self.new_image_tag)

        command = [
            "docker",
            "compose",
            "--env-file",
            str(temp_env),
            "run",
            "--rm",
            "--no-deps",
            "-T",
            "odoo",
            "odoo",
            "-d",
            self.business_db,
            "--stop-after-init",
            "-c",
            "/etc/odoo/odoo.conf",
        ]
        if upgrade_modules:
            command.extend(["-u", ",".join(upgrade_modules)])
        if install_modules:
            command.extend(["-i", ",".join(install_modules)])

        self.run(["docker", "compose", "stop", "odoo"], cwd=self.stack_dir, log_name="upgrade.log")
        self.db_touched = True
        self.run(command, cwd=self.stack_dir, log_name="upgrade.log")

    def swap_env_files(self) -> None:
        """Apunta los `.env*` del tenant a la nueva imagen construida localmente."""
        for env_file in self.env_files:
            path = self.stack_dir / env_file
            if path.exists():
                self.replace_image_reference(path, self.new_image_tag)
        self.env_swapped = True

    def bring_up_odoo(self) -> None:
        """Levanta el servicio Odoo ya apuntando a la nueva imagen."""
        self.run(["docker", "compose", "up", "-d", "odoo"], cwd=self.stack_dir)

    def validate_http(self) -> None:
        """Comprueba que el tenant responda por HTTP con los codigos esperados.

        Odoo puede aceptar la conexion TCP y aun reiniciarse o recalentar workers
        durante varios segundos despues de `docker compose up -d odoo`. Por eso
        no basta un unico intento: se reintenta hasta que todas las URLs
        respondan con un codigo esperado o se agote la ventana de espera.
        """
        opener = urllib.request.build_opener(NoRedirectHandler())
        port = self.manifest["odoo_port"]
        urls = [
            f"http://127.0.0.1:{port}/",
            f"http://127.0.0.1:{port}/web/login",
        ]
        timeout_seconds = 120
        retry_seconds = 5
        deadline = time.monotonic() + timeout_seconds
        attempt = 0
        last_statuses: dict[str, int] = {}
        last_errors: dict[str, str] = {}

        while True:
            attempt += 1
            statuses: dict[str, int] = {}
            errors: dict[str, str] = {}
            all_ok = True

            for url in urls:
                try:
                    with opener.open(url, timeout=20) as response:
                        status = response.getcode()
                    statuses[url] = status
                    if status not in self.http_expected_codes:
                        all_ok = False
                except urllib.error.HTTPError as exc:
                    statuses[url] = exc.code
                    if exc.code not in self.http_expected_codes:
                        all_ok = False
                except Exception as exc:  # pragma: no cover - depende del runtime remoto
                    errors[url] = f"{type(exc).__name__}: {exc}"
                    all_ok = False

            last_statuses = statuses
            last_errors = errors
            if all_ok and not errors:
                self.manifest["http_validation"] = statuses
                return

            if time.monotonic() >= deadline:
                break

            self.log(
                "HTTP validation retry "
                f"(attempt {attempt}, sleeping {retry_seconds}s): "
                f"statuses={statuses or '{}'} errors={errors or '{}'}"
            )
            time.sleep(retry_seconds)

        raise RuntimeError(
            "HTTP validation failed after retries. "
            f"Statuses={last_statuses or '{}'} Errors={last_errors or '{}'} "
            f"Expected codes={sorted(self.http_expected_codes)}"
        )

    def validate_modules(self) -> None:
        """Confirma que los modulos que debian quedar instalados realmente lo quedaron."""
        expected = sorted(
            set(self.module_plan.get("upgrade", [])) | set(self.module_plan.get("install", []))
        )
        if not expected:
            return
        env = self.load_env(self.stack_dir / ".env")
        states = self.query_module_states(env, expected)
        invalid = {name: state for name, state in states.items() if state != "installed"}
        if invalid:
            raise RuntimeError(f"Module validation failed: {invalid}")
        self.manifest["post_apply_module_states"] = states

    def inspect_service(self, service: str) -> dict[str, object]:
        """Inspecciona el contenedor actual de un servicio del stack.

        Esto complementa la validacion HTTP con un estado tecnico del contenedor:
        - running/stopped
        - health de Docker si existe
        - imagen realmente usada
        """
        container_id = self.run(
            ["docker", "compose", "ps", "-q", service],
            cwd=self.stack_dir,
            log_name="health.log",
        ).stdout.strip()
        if not container_id:
            raise RuntimeError(f"Unable to resolve container id for service '{service}'")

        inspect_result = self.run(
            ["docker", "inspect", container_id],
            cwd=self.stack_dir,
            log_name="health.log",
        )
        payload = json.loads(inspect_result.stdout)
        if not payload:
            raise RuntimeError(f"docker inspect returned no data for service '{service}'")
        data = payload[0]
        state = data.get("State", {})
        health = state.get("Health") or {}
        return {
            "service": service,
            "container_id": container_id,
            "container_name": str(data.get("Name", "")).lstrip("/"),
            "image": data.get("Config", {}).get("Image", ""),
            "running": bool(state.get("Running")),
            "status": state.get("Status", "unknown"),
            "health": health.get("Status") or "n/a",
            "started_at": state.get("StartedAt", ""),
            "restart_count": int(data.get("RestartCount", 0)),
            "exit_code": int(state.get("ExitCode", 0)),
        }

    def validate_tenant_health(self) -> None:
        """Construye y valida un reporte final de salud del tenant ya desplegado."""
        self.log("Validating tenant health")
        services = {
            "odoo": self.inspect_service("odoo"),
            "db": self.inspect_service("db"),
        }
        http_validation = dict(self.manifest.get("http_validation", {}))
        module_states = dict(self.manifest.get("post_apply_module_states", {}))
        issues: list[str] = []

        for service_name, report in services.items():
            if not report["running"]:
                issues.append(f"{service_name} is not running")
            health = str(report.get("health") or "n/a")
            if health not in {"n/a", "healthy", "starting"}:
                issues.append(f"{service_name} health is {health}")

        if not http_validation:
            issues.append("http validation data is missing")

        health_report = {
            "status": "ok" if not issues else "error",
            "services": services,
            "http_validation": http_validation,
            "module_states": module_states,
            "issues": issues,
        }
        self.manifest["tenant_health"] = health_report

        if issues:
            self.log("Tenant health issues: " + "; ".join(issues))
            raise RuntimeError("Tenant health validation failed: " + "; ".join(issues))

        http_bits = [f"{url}={status}" for url, status in sorted(http_validation.items())]
        self.log(
            "Tenant health OK: "
            f"odoo={services['odoo']['status']}/{services['odoo']['health']} "
            f"db={services['db']['status']}/{services['db']['health']} "
            f"http={', '.join(http_bits) or '-'}"
        )

    def restore_env_files(self) -> None:
        """Restaura los `.env*` originales desde el backup."""
        for env_file in self.env_files:
            backup_file = self.backup_dir / env_file
            if backup_file.exists():
                shutil.copy2(backup_file, self.stack_dir / env_file)

    def restore_database_and_web(self) -> None:
        """Reconstruye el estado original de DB + filestore usando el backup."""
        env = self.load_env(self.stack_dir / ".env")
        dump_path = self.backup_dir / f"{self.manifest['tenant']}.dump"
        globals_path = self.backup_dir / "globals.sql"

        self.run(["docker", "compose", "up", "-d", "db"], cwd=self.stack_dir, log_name="rollback.log")
        self.run(["docker", "compose", "stop", "odoo"], cwd=self.stack_dir, log_name="rollback.log", check=False)

        # Paso 1: restaurar globals, recrear DB y cargar el dump original.
        self.run(
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
                "postgres",
            ],
            cwd=self.stack_dir,
            stdin_path=globals_path,
            log_name="rollback.log",
            check=False,
        )
        self.run(
            [
                "docker",
                "compose",
                "exec",
                "-T",
                "-e",
                f"PGPASSWORD={env['POSTGRES_PASSWORD']}",
                "db",
                "dropdb",
                "-U",
                env["POSTGRES_USER"],
                "--if-exists",
                self.business_db,
            ],
            cwd=self.stack_dir,
            log_name="rollback.log",
            check=False,
        )
        self.run(
            [
                "docker",
                "compose",
                "exec",
                "-T",
                "-e",
                f"PGPASSWORD={env['POSTGRES_PASSWORD']}",
                "db",
                "createdb",
                "-U",
                env["POSTGRES_USER"],
                self.business_db,
            ],
            cwd=self.stack_dir,
            log_name="rollback.log",
        )
        self.run(
            [
                "docker",
                "compose",
                "exec",
                "-T",
                "-e",
                f"PGPASSWORD={env['POSTGRES_PASSWORD']}",
                "db",
                "pg_restore",
                "-U",
                env["POSTGRES_USER"],
                "-d",
                self.business_db,
                "--clean",
                "--if-exists",
                "--no-owner",
                "--no-privileges",
            ],
            cwd=self.stack_dir,
            stdin_path=dump_path,
            log_name="rollback.log",
        )
        self.run(
            [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{self.web_volume_name}:/dst",
                "-v",
                f"{self.backup_dir}:/backup",
                "postgres:16",
                "bash",
                "-lc",
                "rm -rf /dst/* /dst/.[!.]* /dst/..?* 2>/dev/null || true; "
                "cd /dst && tar -xzf /backup/web.tar.gz",
            ],
            log_name="rollback.log",
        )

    def rollback(self, reason: str) -> None:
        """Rollback automatico disparado por cualquier error despues del backup."""
        self.log(f"Starting rollback: {reason}")
        with self.rollback_log_path.open("a", encoding="utf-8") as handle:
            handle.write(reason + "\n")
        try:
            self.restore_env_files()
            if self.db_touched:
                self.restore_database_and_web()
            self.run(["docker", "compose", "up", "-d", "odoo"], cwd=self.stack_dir, log_name="rollback.log")
            self.log("Rollback completed")
        except Exception as exc:  # noqa: BLE001
            self.log(f"Rollback failed: {exc}")
            self.log(traceback.format_exc())

    def write_manifest(self) -> None:
        """Actualiza en disco el manifiesto remoto con resultados finales."""
        self.manifest_path.write_text(
            json.dumps(self.manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def execute(self) -> None:
        """Ejecuta la secuencia completa del despliegue remoto en orden fijo."""
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.run_log_path.write_text("", encoding="utf-8")

        # Flujo principal: backup -> build -> validacion runtime -> upgrade -> cutover -> validacion.
        self.backup()
        self.extract_context()
        self.build_image()
        self.validate_runtime()
        self.run_module_plan()
        self.swap_env_files()
        self.bring_up_odoo()
        self.validate_http()
        self.validate_modules()
        self.validate_tenant_health()
        self.manifest["status"] = "ok"
        self.write_manifest()


def main() -> int:
    """CLI minima del runner remoto: recibe solo la ruta del manifiesto JSON."""
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest_path")
    args = parser.parse_args()

    deployer = RemoteDeployer(Path(args.manifest_path))
    try:
        deployer.execute()
        result = {
            "status": "ok",
            "archive_dir": str(deployer.archive_dir),
            "backup_dir": str(deployer.backup_dir),
            "new_image_tag": deployer.new_image_tag,
            "repo_digests": deployer.manifest.get("new_image_repo_digests", []),
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001
        # Si hubo backup, el runner intenta volver al estado previo automaticamente.
        deployer.log(f"Deployment failed: {exc}")
        deployer.log(traceback.format_exc())
        deployer.manifest["status"] = "error"
        deployer.manifest["error"] = str(exc)
        if deployer.rollback_needed:
            deployer.manifest["rollback_attempted"] = True
            deployer.rollback(str(exc))
        try:
            deployer.write_manifest()
        except Exception as write_exc:  # noqa: BLE001
            deployer.log(f"Unable to persist remote manifest after failure: {write_exc}")
        result = {
            "status": "error",
            "archive_dir": str(deployer.archive_dir),
            "backup_dir": str(deployer.backup_dir),
            "error": str(exc),
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
