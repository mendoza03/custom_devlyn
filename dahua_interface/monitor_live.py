#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shlex
import signal
import subprocess
import sys
from typing import Any


DEFAULT_HOST = "52.6.240.186"
DEFAULT_USER = "root"
DEFAULT_LOG_PATH = "/var/log/dahua_events.log"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Monitorea en vivo los requests capturados por el listener Dahua."
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help="Host remoto del listener.")
    parser.add_argument("--user", default=DEFAULT_USER, help="Usuario SSH.")
    parser.add_argument(
        "--log-path",
        default=DEFAULT_LOG_PATH,
        help="Ruta del log a seguir en el servidor remoto.",
    )
    parser.add_argument(
        "--history",
        type=int,
        default=5,
        help="Cantidad de eventos previos a mostrar antes de seguir en vivo.",
    )
    parser.add_argument(
        "--body-limit",
        type=int,
        default=1000,
        help="Cantidad maxima de caracteres a imprimir del body.",
    )
    parser.add_argument(
        "--ip",
        help="Filtra por IP origen exacta.",
    )
    parser.add_argument(
        "--path",
        help="Filtra por path exacto.",
    )
    parser.add_argument(
        "--show-headers",
        action="store_true",
        help="Imprime todos los headers del request.",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Imprime la linea completa del log sin procesar.",
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="Lee el archivo local en vez de conectarse por SSH.",
    )
    parser.add_argument(
        "--identity-file",
        help="Archivo de llave SSH opcional.",
    )
    return parser.parse_args()


def build_command(args: argparse.Namespace) -> list[str]:
    history_cmd = f"""
python3 - <<'PY'
from pathlib import Path
import sys

log_path = Path({args.log_path!r})
history = {max(args.history, 0)}
marker = "Request dump: "

try:
    lines = log_path.read_text(encoding="utf-8", errors="ignore").splitlines()
except FileNotFoundError:
    lines = []

events = [line for line in lines if marker in line]
for line in events[-history:]:
    print(line)
PY
""".strip()
    tail_cmd = f"tail -n 0 -F {shlex.quote(args.log_path)}"
    shell_cmd = f"{history_cmd}\n{tail_cmd}"
    if args.local:
        return ["bash", "-lc", shell_cmd]

    command = ["ssh"]
    if args.identity_file:
        command.extend(["-i", args.identity_file])
    command.extend(
        [
            "-o",
            "StrictHostKeyChecking=no",
            f"{args.user}@{args.host}",
            f"bash -lc {shlex.quote(shell_cmd)}",
        ]
    )
    return command


def shorten(text: str, limit: int) -> str:
    if limit <= 0 or len(text) <= limit:
        return text
    return f"{text[:limit]}... [truncated {len(text) - limit} chars]"


def selected_headers(headers: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "host",
        "content-type",
        "content-length",
        "user-agent",
        "authorization",
        "referer",
    )
    return {key: headers[key] for key in keys if key in headers}


def event_matches_filters(event: dict[str, Any], args: argparse.Namespace) -> bool:
    if args.ip and event.get("source_ip") != args.ip:
        return False
    if args.path and event.get("path") != args.path:
        return False
    return True


def print_event(event: dict[str, Any], args: argparse.Namespace) -> None:
    body_raw = event.get("body_raw")
    body = body_raw if body_raw else event.get("body")
    headers = event.get("headers") or {}
    compact_headers = headers if args.show_headers else selected_headers(headers)

    print("=" * 88)
    print(
        f"{event.get('timestamp_utc', 'unknown')} | "
        f"{event.get('source_ip', 'unknown')} | "
        f"{event.get('method', 'UNKNOWN')} {event.get('path', '/')}"
    )
    if event.get("query"):
        print(f"Query: {event['query']}")
    if compact_headers:
        print("Headers:")
        print(json.dumps(compact_headers, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print("Headers: <none>")

    if body in (None, ""):
        print("Body: <empty>")
    elif isinstance(body, str):
        print("Body:")
        print(shorten(body, args.body_limit))
    else:
        print("Body:")
        print(shorten(json.dumps(body, ensure_ascii=False, indent=2), args.body_limit))
    sys.stdout.flush()


def process_line(line: str, args: argparse.Namespace) -> None:
    if args.raw:
        print(line.rstrip())
        sys.stdout.flush()
        return

    marker = "Request dump: "
    if marker not in line:
        return

    payload_text = line.split(marker, 1)[1].strip()
    try:
        event = json.loads(payload_text)
    except json.JSONDecodeError:
        print(line.rstrip())
        sys.stdout.flush()
        return

    if event_matches_filters(event, args):
        print_event(event, args)


def terminate_process(process: subprocess.Popen[str] | None) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        process.kill()


def main() -> int:
    args = parse_args()
    command = build_command(args)

    print("Monitoring Dahua listener")
    if args.local:
        print(f"Mode: local log file {args.log_path}")
    else:
        print(f"Mode: ssh {args.user}@{args.host}")
        if args.identity_file:
            print(f"Identity: {args.identity_file}")
        print(f"Remote log: {args.log_path}")
    print(f"History: {args.history}")
    if args.ip:
        print(f"IP filter: {args.ip}")
    if args.path:
        print(f"Path filter: {args.path}")
    print("Press Ctrl+C to stop.")
    sys.stdout.flush()

    process: subprocess.Popen[str] | None = None

    def handle_signal(_signum: int, _frame: Any) -> None:
        terminate_process(process)
        raise SystemExit(130)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
    except FileNotFoundError as exc:
        print(f"Failed to start monitor: {exc}", file=sys.stderr)
        return 1

    assert process.stdout is not None

    try:
        for line in process.stdout:
            process_line(line, args)
    except KeyboardInterrupt:
        terminate_process(process)
        return 130

    return process.wait()


if __name__ == "__main__":
    raise SystemExit(main())
