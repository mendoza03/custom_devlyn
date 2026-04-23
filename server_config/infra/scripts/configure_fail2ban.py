#!/usr/bin/env python3
import json
import os
import paramiko
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = Path(os.getenv("SERVERS_JSON", REPO_ROOT / "config" / "servers.json"))
SERVER_KEY = os.getenv("SERVER_KEY", "devlyn_prod")

# Configuración de fail2ban para SSH
FAIL2BAN_CONFIG = """[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600
findtime = 600
"""

commands = [
    "apt-get update -qq",
    "apt-get install -y fail2ban",
    "systemctl enable fail2ban",
    f"echo '{FAIL2BAN_CONFIG}' > /etc/fail2ban/jail.local",
    "systemctl restart fail2ban",
    "systemctl status fail2ban --no-pager",
    "fail2ban-client status",
    "fail2ban-client status sshd"
]


def load_server_config() -> tuple[str, str, str]:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"No se encontro {CONFIG_PATH}. Crea config/servers.json a partir de config/servers.example.json."
        )

    payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    servers = payload.get("servers", payload)
    server = servers.get(SERVER_KEY)
    if not server:
        raise KeyError(f"No existe la entrada '{SERVER_KEY}' en {CONFIG_PATH}.")

    host = server.get("host", "").strip()
    user = server.get("user", "root").strip()
    password = (server.get("password") or os.getenv("SSH_PASSWORD", "")).strip()

    if not host:
        raise ValueError(f"La entrada '{SERVER_KEY}' no tiene host configurado.")
    if not password:
        raise ValueError(
            f"La entrada '{SERVER_KEY}' no tiene password. Completa config/servers.json o exporta SSH_PASSWORD."
        )

    return host, user, password

def run_remote_commands():
    host, user, password = load_server_config()
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print(f"Conectando a {host} como {user}...")
    client.connect(
        host,
        username=user,
        password=password,
        timeout=30,
        allow_agent=False,
        look_for_keys=False
    )
    print("Conexión establecida!\n")
    
    for cmd in commands:
        print(f">>> Ejecutando: {cmd[:60]}...")
        stdin, stdout, stderr = client.exec_command(cmd, timeout=120)
        
        output = stdout.read().decode()
        error = stderr.read().decode()
        
        if output:
            print(output)
        if error and "WARNING" not in error:
            print(f"[stderr]: {error}")
        print("-" * 50)
    
    client.close()
    print("\n✅ Configuración de fail2ban completada!")

if __name__ == "__main__":
    run_remote_commands()
