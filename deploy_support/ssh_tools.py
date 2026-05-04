from __future__ import annotations
"""Capa delgada de transporte SSH.

Soporta dos modos:
1. `paramiko` cuando el usuario define password en `tenant_deploy.py`
2. `ssh/scp` del sistema cuando el acceso se resuelve con llaves
"""

from collections.abc import Callable
import subprocess
import time
from dataclasses import dataclass
import os
from pathlib import Path
import sys


@dataclass
class SSHResult:
    """Resultado normalizado de un comando remoto."""
    returncode: int
    stdout: str
    stderr: str


class SSHClient:
    """Cliente SSH reusable para toda la corrida de despliegue."""

    def __init__(self, host: str, port: int, user: str, password: str | None = None) -> None:
        self.host = host
        self.port = port
        self.user = user
        self.password = password.strip() if password and password.strip() else None
        self._paramiko_client = None

    @property
    def remote(self) -> str:
        """Usuario y host en formato apto para SSH nativo."""
        return f"{self.user}@{self.host}"

    def _use_paramiko(self) -> bool:
        """Decide si la sesion ira por password o por binarios del sistema."""
        return self.password is not None

    def _get_paramiko_client(self):
        """Inicializa y cachea una sola sesion Paramiko por corrida."""
        if self._paramiko_client is not None:
            return self._paramiko_client
        try:
            import paramiko
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Password-based SSH requires `paramiko`. Install it with `python3 -m pip install paramiko`."
            ) from exc

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=self.host,
            port=self.port,
            username=self.user,
            password=self.password,
            timeout=20,
            auth_timeout=20,
            banner_timeout=20,
            look_for_keys=False,
            allow_agent=False,
        )
        self._paramiko_client = client
        return client

    def _ssh_prefix(self) -> list[str]:
        """Base comun para invocaciones `ssh` no interactivas."""
        return [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=accept-new",
            "-p",
            str(self.port),
            self.remote,
        ]

    def run(
        self,
        command: str,
        *,
        input_text: str | None = None,
        check: bool = True,
    ) -> SSHResult:
        """Ejecuta un comando remoto y devuelve stdout/stderr completos."""
        if self._use_paramiko():
            client = self._get_paramiko_client()
            stdin, stdout, stderr = client.exec_command(command)
            if input_text:
                stdin.write(input_text)
                stdin.flush()
            stdin.channel.shutdown_write()
            out = stdout.read().decode("utf-8", "replace")
            err = stderr.read().decode("utf-8", "replace")
            result = SSHResult(
                returncode=stdout.channel.recv_exit_status(),
                stdout=out,
                stderr=err,
            )
            if check and result.returncode != 0:
                raise RuntimeError(
                    f"SSH command failed ({result.returncode}): {command}\n"
                    f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
                )
            return result

        process = subprocess.run(
            [*self._ssh_prefix(), command],
            text=True,
            input=input_text,
            capture_output=True,
        )
        result = SSHResult(
            returncode=process.returncode,
            stdout=process.stdout,
            stderr=process.stderr,
        )
        if check and result.returncode != 0:
            raise RuntimeError(
                f"SSH command failed ({result.returncode}): {command}\n"
                f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
            )
        return result

    def upload(self, local_path: Path, remote_path: str) -> None:
        """Sube un archivo local al servidor remoto."""
        if self._use_paramiko():
            client = self._get_paramiko_client()
            sftp = client.open_sftp()
            try:
                sftp.put(str(local_path), remote_path)
            finally:
                sftp.close()
            return

        process = subprocess.run(
            [
                "scp",
                "-P",
                str(self.port),
                "-o",
                "BatchMode=yes",
                "-o",
                "StrictHostKeyChecking=accept-new",
                str(local_path),
                f"{self.remote}:{remote_path}",
            ],
            text=True,
            capture_output=True,
        )
        if process.returncode != 0:
            raise RuntimeError(
                f"SCP upload failed ({process.returncode}) to {remote_path}\n"
                f"STDOUT:\n{process.stdout}\nSTDERR:\n{process.stderr}"
            )

    def stream(
        self,
        command: str,
        log_path: Path,
        *,
        line_mapper: Callable[[str], str | None] | None = None,
    ) -> int:
        """Ejecuta un comando remoto de larga duracion mostrando salida en vivo.

        `line_mapper` permite transformar o suprimir lineas en consola sin tocar
        el contenido que queda persistido en el log local.
        """
        if self._use_paramiko():
            client = self._get_paramiko_client()
            transport = client.get_transport()
            if transport is None:
                raise RuntimeError("SSH transport is not available")
            channel = transport.open_session()
            channel.set_combine_stderr(True)
            channel.exec_command(command)
            with log_path.open("a", encoding="utf-8") as log_file:
                pending = ""
                while True:
                    if channel.recv_ready():
                        chunk = channel.recv(4096).decode("utf-8", "replace")
                        log_file.write(chunk)
                        pending = _write_console_chunk(chunk, pending, line_mapper=line_mapper)
                    if channel.exit_status_ready() and not channel.recv_ready():
                        break
                    time.sleep(0.1)
                while channel.recv_ready():
                    chunk = channel.recv(4096).decode("utf-8", "replace")
                    log_file.write(chunk)
                    pending = _write_console_chunk(chunk, pending, line_mapper=line_mapper)
                if pending:
                    rendered = _render_console_line(pending, line_mapper=line_mapper)
                    if rendered is not None:
                        _print_console(rendered)
                return channel.recv_exit_status()

        with log_path.open("a", encoding="utf-8") as log_file:
            process = subprocess.Popen(
                [*self._ssh_prefix(), command],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            assert process.stdout is not None
            for line in process.stdout:
                log_file.write(line)
                rendered = _render_console_line(line, line_mapper=line_mapper)
                if rendered is not None:
                    _print_console(rendered)
            return process.wait()

    def close(self) -> None:
        """Cierra la sesion Paramiko si existia."""
        if self._paramiko_client is not None:
            self._paramiko_client.close()
            self._paramiko_client = None


ANSI_RESET = "\033[0m"
ANSI_COLORS = {
    "yellow": "\033[33m",
    "red": "\033[31m",
    "green": "\033[32m",
    "blue": "\033[34m",
    "cyan": "\033[36m",
    "bold": "\033[1m",
}


def _use_color() -> bool:
    """Activa colores ANSI cuando stdout soporta TTY y NO_COLOR no lo bloquea."""
    return sys.stdout.isatty() and not os.environ.get("NO_COLOR")


def _paint(text: str, *styles: str) -> str:
    """Aplica estilos ANSI a una linea de consola."""
    if not _use_color() or not styles:
        return text
    prefix = "".join(ANSI_COLORS[style] for style in styles)
    return f"{prefix}{text}{ANSI_RESET}"


def _colorize_line(line: str) -> str:
    """Da color a la salida remota segun su severidad o tipo."""
    upper = line.upper()
    if " ERROR " in upper or upper.startswith("ERROR "):
        return _paint(line, "red", "bold")
    if " WARNING " in upper or upper.startswith("WARNING "):
        return _paint(line, "yellow", "bold")
    if line.startswith("$ "):
        return _paint(line, "cyan", "bold")
    if "Deployment completed successfully" in line or '"status": "ok"' in line:
        return _paint(line, "green", "bold")
    if "HTTP validation retry" in line:
        return _paint(line, "yellow")
    return line


def _print_console(text: str) -> None:
    """Escribe en stdout sin romper el flujo del stream."""
    sys.stdout.write(text)
    sys.stdout.flush()


def _render_console_line(
    line: str,
    *,
    line_mapper: Callable[[str], str | None] | None = None,
) -> str | None:
    """Decide como se debe renderizar una linea remota en consola."""
    if line_mapper is not None:
        return line_mapper(line)
    return _colorize_line(line)


def _write_console_chunk(
    chunk: str,
    pending: str,
    *,
    line_mapper: Callable[[str], str | None] | None = None,
) -> str:
    """Convierte chunks SSH en lineas de consola conservando trozos incompletos."""
    pending += chunk
    while True:
        newline_index = pending.find("\n")
        if newline_index == -1:
            return pending
        line = pending[: newline_index + 1]
        pending = pending[newline_index + 1 :]
        rendered = _render_console_line(line, line_mapper=line_mapper)
        if rendered is not None:
            _print_console(rendered)
