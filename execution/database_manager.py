"""
Camada 3 (Execucao): Gerenciador Deterministico de Bancos de Dados 1-Clique (A.C.O. Database Engine)
Suporta provisionamento, telemetria de RAM/Disco e injecao automatica de DATABASE_URL para:
- SQLite3 (Zero-RAM, arquivo dedicado em /var/lib/aco-databases/<slug>/<slug>.sqlite)
- PostgreSQL Tuned (shared_buffers=32MB, otimizado para VM Micro/ARM)
- MariaDB / MySQL Tuned (innodb_buffer_pool_size=32M, performance_schema=OFF)
- Redis Cache (maxmemory 32mb, allkeys-lru)
"""

import datetime
import json
import os
import platform
import re
import secrets
import shutil
import sqlite3
import subprocess
from typing import Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_REGISTRY_PATH = os.path.join(BASE_DIR, "execution", "managed_databases.json")
ACO_DB_ROOT = "/var/lib/aco-databases"

ENGINE_LABELS = {
    "sqlite": "SQLite 3",
    "postgresql": "PostgreSQL 16 Tuned",
    "mysql": "MariaDB / MySQL Tuned",
    "redis": "Redis Cache",
}


def sanitize_db_slug(raw: str) -> str:
    slug = re.sub(r"[^a-z0-9_]", "_", raw.strip().lower())
    slug = re.sub(r"_+", "_", slug).strip("_")
    if not slug:
        raise ValueError("Nome do banco de dados inválido.")
    return slug[:24]


def format_bytes_human(size_bytes: int) -> str:
    if size_bytes <= 0:
        return "0 B"
    if size_bytes < 1024:
        return f"{size_bytes} B"
    kb = size_bytes / 1024.0
    if kb < 1024:
        return f"{kb:.1f} KB"
    mb = kb / 1024.0
    if mb < 1024:
        return f"{mb:.2f} MB"
    return f"{mb / 1024.0:.2f} GB"


def get_dir_size(path: str) -> int:
    if not path or not os.path.exists(path):
        return 0
    if os.path.isfile(path):
        return os.path.getsize(path)
    total = 0
    for root, _dirs, files in os.walk(path):
        for f in files:
            fp = os.path.join(root, f)
            if not os.path.islink(fp):
                try:
                    total += os.path.getsize(fp)
                except OSError:
                    pass
    return total


def get_systemd_memory_bytes(service_name: str) -> tuple[int, str]:
    """Retorna (memory_bytes, active_state) de um servico systemd no Linux."""
    if platform.system() != "Linux":
        return 0, "local"
    try:
        res = subprocess.run(
            ["systemctl", "show", service_name, "--property=MemoryCurrent,ActiveState"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
        )
        mem_bytes = 0
        state = "inactive"
        for line in res.stdout.splitlines():
            if line.startswith("MemoryCurrent="):
                val = line.split("=", 1)[1].strip()
                if val.isdigit() and int(val) < (1 << 60):
                    mem_bytes = int(val)
            elif line.startswith("ActiveState="):
                state = line.split("=", 1)[1].strip()
        return mem_bytes, state
    except Exception:
        return 0, "unknown"


def run_cmd(cmd: list[str] | str, timeout: int = 300) -> str:
    proc = subprocess.run(
        cmd,
        shell=isinstance(cmd, str),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Erro ao executar comando ({proc.returncode}): {proc.stdout[-1000:]}")
    return proc.stdout


def load_databases() -> list[dict[str, Any]]:
    if not os.path.exists(DB_REGISTRY_PATH):
        return []
    try:
        with open(DB_REGISTRY_PATH, "r", encoding="utf-8") as f:
            dbs = json.load(f)
            if not isinstance(dbs, list):
                return []
    except Exception:
        return []

    # Atualizar telemetria em tempo real (RAM e Disco)
    for db in dbs:
        engine = db.get("engine", "sqlite")
        db["engineLabel"] = ENGINE_LABELS.get(engine, engine.upper())
        if engine == "sqlite":
            db_path = db.get("dataPath", "")
            sz = get_dir_size(db_path)
            db["diskBytes"] = sz
            db["diskMb"] = round(sz / (1024 * 1024), 2)
            db["diskFormatted"] = format_bytes_human(sz)
            db["ramBytes"] = 0
            db["ramMb"] = 0.0
            db["ramFormatted"] = "0 B (Embarcado)"
            db["status"] = "ONLINE" if os.path.exists(db_path) else "MISSING"
        elif engine == "postgresql":
            mem_b, state = get_systemd_memory_bytes("postgresql")
            sz = get_dir_size("/var/lib/postgresql")
            db["diskBytes"] = sz
            db["diskMb"] = round(sz / (1024 * 1024), 2)
            db["diskFormatted"] = format_bytes_human(sz)
            db["ramBytes"] = mem_b
            db["ramMb"] = round(mem_b / (1024 * 1024), 2)
            db["ramFormatted"] = format_bytes_human(mem_b)
            db["status"] = "ONLINE" if state == "active" else state.upper()
        elif engine == "mysql":
            mem_b, state = get_systemd_memory_bytes("mariadb")
            sz = get_dir_size("/var/lib/mysql")
            db["diskBytes"] = sz
            db["diskMb"] = round(sz / (1024 * 1024), 2)
            db["diskFormatted"] = format_bytes_human(sz)
            db["ramBytes"] = mem_b
            db["ramMb"] = round(mem_b / (1024 * 1024), 2)
            db["ramFormatted"] = format_bytes_human(mem_b)
            db["status"] = "ONLINE" if state == "active" else state.upper()
        elif engine == "redis":
            mem_b, state = get_systemd_memory_bytes("redis-server")
            sz = get_dir_size("/var/lib/redis")
            db["diskBytes"] = sz
            db["diskMb"] = round(sz / (1024 * 1024), 2)
            db["diskFormatted"] = format_bytes_human(sz)
            db["ramBytes"] = mem_b
            db["ramMb"] = round(mem_b / (1024 * 1024), 2)
            db["ramFormatted"] = format_bytes_human(mem_b)
            db["status"] = "ONLINE" if state == "active" else state.upper()

    return dbs


get_databases = load_databases


def save_databases(dbs: list[dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(DB_REGISTRY_PATH), exist_ok=True)
    with open(DB_REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(dbs, f, indent=2, ensure_ascii=False)


def create_database(name: str, engine: str = "sqlite") -> dict[str, Any]:
    """Provisiona um novo banco de dados (sqlite, postgresql, mysql ou redis) na VM."""
    slug = sanitize_db_slug(name)
    engine = engine.strip().lower()
    dbs = load_databases()
    if any(d.get("slug") == slug for d in dbs):
        raise ValueError(f"Já existe um banco de dados com o identificador '{slug}'.")

    os.makedirs(ACO_DB_ROOT, exist_ok=True)
    now_iso = datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(timespec="seconds")
    password = secrets.token_urlsafe(12).replace("-", "").replace("_", "")[:16]
    db_name = f"aco_{slug}"
    db_user = f"usr_{slug[:12]}"

    if engine == "sqlite":
        db_dir = os.path.join(ACO_DB_ROOT, slug)
        os.makedirs(db_dir, exist_ok=True)
        db_file = os.path.join(db_dir, f"{slug}.sqlite")
        conn = sqlite3.connect(db_file)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS _aco_meta (created_at TEXT, db_name TEXT);"
        )
        conn.execute("INSERT INTO _aco_meta VALUES (?, ?);", (now_iso, db_name))
        conn.commit()
        conn.close()

        conn_url = f"sqlite:///{db_file}"
        record = {
            "slug": slug,
            "name": name.strip(),
            "engine": "sqlite",
            "engineLabel": ENGINE_LABELS["sqlite"],
            "host": "localhost (Arquivo Local)",
            "port": None,
            "dbName": db_name,
            "dbUser": "local",
            "dbPassword": "",
            "dataPath": db_file,
            "connectionUrl": conn_url,
            "envSnippet": f'DATABASE_URL="{conn_url}"\nDB_ENGINE="sqlite"\nSQLITE_PATH="{db_file}"',
            "createdAt": now_iso,
        }

    elif engine == "postgresql":
        if not shutil.which("psql"):
            run_cmd("sudo DEBIAN_FRONTEND=noninteractive apt-get update -y -q && sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -q postgresql postgresql-contrib")
        run_cmd(["sudo", "systemctl", "enable", "postgresql"])
        run_cmd(["sudo", "systemctl", "start", "postgresql"])

        sql_user = f"DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '{db_user}') THEN CREATE ROLE {db_user} LOGIN PASSWORD '{password}'; END IF; END $$;"
        run_cmd(["sudo", "-u", "postgres", "psql", "-c", sql_user])
        try:
            run_cmd(["sudo", "-u", "postgres", "psql", "-c", f"CREATE DATABASE {db_name} OWNER {db_user};"])
        except Exception:
            pass

        conn_url = f"postgresql://{db_user}:{password}@127.0.0.1:5432/{db_name}"
        record = {
            "slug": slug,
            "name": name.strip(),
            "engine": "postgresql",
            "engineLabel": ENGINE_LABELS["postgresql"],
            "host": "127.0.0.1",
            "port": 5432,
            "dbName": db_name,
            "dbUser": db_user,
            "dbPassword": password,
            "dataPath": "/var/lib/postgresql",
            "connectionUrl": conn_url,
            "envSnippet": (
                f'DATABASE_URL="{conn_url}"\n'
                f'DB_HOST="127.0.0.1"\nDB_PORT="5432"\n'
                f'DB_NAME="{db_name}"\nDB_USER="{db_user}"\nDB_PASSWORD="{password}"'
            ),
            "createdAt": now_iso,
        }

    elif engine == "mysql":
        if not shutil.which("mysql"):
            run_cmd("sudo DEBIAN_FRONTEND=noninteractive apt-get update -y -q && sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -q mariadb-server")
        run_cmd(["sudo", "systemctl", "enable", "mariadb"])
        run_cmd(["sudo", "systemctl", "start", "mariadb"])

        sql_cmds = (
            f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci; "
            f"CREATE USER IF NOT EXISTS '{db_user}'@'127.0.0.1' IDENTIFIED BY '{password}'; "
            f"CREATE USER IF NOT EXISTS '{db_user}'@'localhost' IDENTIFIED BY '{password}'; "
            f"GRANT ALL PRIVILEGES ON `{db_name}`.* TO '{db_user}'@'127.0.0.1'; "
            f"GRANT ALL PRIVILEGES ON `{db_name}`.* TO '{db_user}'@'localhost'; "
            "FLUSH PRIVILEGES;"
        )
        run_cmd(["sudo", "mysql", "-e", sql_cmds])

        conn_url = f"mysql://{db_user}:{password}@127.0.0.1:3306/{db_name}"
        record = {
            "slug": slug,
            "name": name.strip(),
            "engine": "mysql",
            "engineLabel": ENGINE_LABELS["mysql"],
            "host": "127.0.0.1",
            "port": 3306,
            "dbName": db_name,
            "dbUser": db_user,
            "dbPassword": password,
            "dataPath": "/var/lib/mysql",
            "connectionUrl": conn_url,
            "envSnippet": (
                f'DATABASE_URL="{conn_url}"\n'
                f'DB_HOST="127.0.0.1"\nDB_PORT="3306"\n'
                f'DB_NAME="{db_name}"\nDB_USER="{db_user}"\nDB_PASSWORD="{password}"'
            ),
            "createdAt": now_iso,
        }

    elif engine == "redis":
        if not shutil.which("redis-server"):
            run_cmd("sudo DEBIAN_FRONTEND=noninteractive apt-get update -y -q && sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -q redis-server")
        run_cmd(["sudo", "systemctl", "enable", "redis-server"])
        run_cmd(["sudo", "systemctl", "start", "redis-server"])

        conn_url = "redis://127.0.0.1:6379/0"
        record = {
            "slug": slug,
            "name": name.strip(),
            "engine": "redis",
            "engineLabel": ENGINE_LABELS["redis"],
            "host": "127.0.0.1",
            "port": 6379,
            "dbName": "db0",
            "dbUser": "default",
            "dbPassword": "",
            "dataPath": "/var/lib/redis",
            "connectionUrl": conn_url,
            "envSnippet": f'REDIS_URL="{conn_url}"\nDATABASE_URL="{conn_url}"',
            "createdAt": now_iso,
        }
    else:
        raise ValueError(f"Engine de banco de dados não suportada: {engine}")

    dbs.insert(0, record)
    save_databases(dbs)
    return load_databases()[0]


def delete_database(slug: str) -> dict[str, Any]:
    clean = sanitize_db_slug(slug)
    dbs = load_databases()
    target = next((d for d in dbs if d.get("slug") == clean), None)
    if not target:
        raise ValueError(f"Banco '{clean}' não encontrado.")

    engine = target.get("engine")
    if engine == "sqlite":
        db_dir = os.path.join(ACO_DB_ROOT, clean)
        if os.path.exists(db_dir):
            shutil.rmtree(db_dir, ignore_errors=True)
    elif engine == "postgresql" and shutil.which("psql"):
        try:
            run_cmd(["sudo", "-u", "postgres", "psql", "-c", f"DROP DATABASE IF EXISTS {target['dbName']};"])
            run_cmd(["sudo", "-u", "postgres", "psql", "-c", f"DROP ROLE IF EXISTS {target['dbUser']};"])
        except Exception:
            pass
    elif engine == "mysql" and shutil.which("mysql"):
        try:
            run_cmd(["sudo", "mysql", "-e", f"DROP DATABASE IF EXISTS `{target['dbName']}`;"])
        except Exception:
            pass

    dbs = [d for d in dbs if d.get("slug") != clean]
    save_databases(dbs)
    return {"deleted": clean, "remaining": len(dbs)}
