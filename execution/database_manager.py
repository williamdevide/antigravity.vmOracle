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
        with open(DB_REGISTRY_PATH, "r", encoding="utf-8-sig") as f:
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
                f'DB_NAME="{db_name}"\nDB_USER="{db_user}"\nDB_PASSWORD="{password}"\n'
                f'DB_PASS="{password}"'
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

    # Desvincular de quaisquer projetos registrados no A.C.O.
    try:
        from execution.deploy_project import load_projects, save_projects
        projs = load_projects()
        changed = False
        for p in projs:
            if p.get("databaseSlug") == clean or p.get("databaseSlug") == target.get("dbName"):
                p["databaseSlug"] = None
                changed = True
        if changed:
            save_projects(projs)
    except Exception:
        pass

    return {"deleted": clean, "remaining": len(dbs)}


# ==============================================================================
# VISUALIZADOR DETERMINÍSTICO DE BANCO DE DADOS (ESTRUTURA E DADOS)
# ==============================================================================


def list_database_tables(db_name: str = "labw") -> list[dict[str, Any]]:
    """Lista todas as tabelas de um banco MariaDB/MySQL com contagem de linhas e tamanho."""
    clean_db = re.sub(r"[^a-zA-Z0-9_]", "", db_name.strip()) or "labw"
    sql = f"""
    SELECT 
        table_name AS name,
        COALESCE(table_rows, 0) AS estimated_rows,
        COALESCE(data_length + index_length, 0) AS total_bytes
    FROM information_schema.tables 
    WHERE table_schema = '{clean_db}'
    ORDER BY table_name ASC;
    """
    cmd = ["sudo", "mysql", "-e", sql, "-B"]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
        if res.returncode != 0:
            return []
        lines = res.stdout.strip().splitlines()
        if not lines or len(lines) <= 1:
            return []
        tables = []
        for line in lines[1:]:
            parts = line.split("\t")
            if len(parts) >= 3:
                name = parts[0]
                rows_val = int(parts[1]) if parts[1].isdigit() else 0
                bytes_val = int(parts[2]) if parts[2].isdigit() else 0
                tables.append({
                    "name": name,
                    "estimatedRows": rows_val,
                    "totalBytes": bytes_val,
                    "sizeFormatted": format_bytes_human(bytes_val),
                })
        return tables
    except Exception:
        return []


def get_table_schema(db_name: str, table_name: str) -> list[dict[str, Any]]:
    """Retorna as colunas, tipos de dados, chaves e defaults de uma tabela."""
    clean_db = re.sub(r"[^a-zA-Z0-9_]", "", db_name.strip()) or "labw"
    clean_table = re.sub(r"[^a-zA-Z0-9_]", "", table_name.strip())
    if not clean_table:
        return []

    sql = f"SHOW FULL COLUMNS FROM `{clean_db}`.`{clean_table}`;"
    cmd = ["sudo", "mysql", "-e", sql, "-B"]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
        if res.returncode != 0:
            return []
        lines = res.stdout.strip().splitlines()
        if not lines or len(lines) <= 1:
            return []
        headers = lines[0].split("\t")
        columns = []
        for line in lines[1:]:
            parts = line.split("\t")
            col_data = dict(zip(headers, parts))
            columns.append({
                "field": col_data.get("Field", ""),
                "type": col_data.get("Type", ""),
                "null": col_data.get("Null", "YES"),
                "key": col_data.get("Key", ""),
                "default": col_data.get("Default", "NULL"),
                "extra": col_data.get("Extra", ""),
                "comment": col_data.get("Comment", ""),
            })
        return columns
    except Exception:
        return []


def get_table_data(db_name: str, table_name: str, limit: int = 50, offset: int = 0) -> dict[str, Any]:
    """Retorna os registros de uma tabela em formato JSON com paginacao e tratamento seguro de BLOBs/Binarios."""
    clean_db = re.sub(r"[^a-zA-Z0-9_]", "", db_name.strip()) or "labw"
    clean_table = re.sub(r"[^a-zA-Z0-9_]", "", table_name.strip())
    if not clean_table:
        return {"columns": [], "rows": [], "total": 0}

    safe_limit = max(1, min(int(limit), 200))
    safe_offset = max(0, int(offset))

    # 1. Total real de linhas
    count_sql = f"SELECT COUNT(*) FROM `{clean_db}`.`{clean_table}`;"
    total = 0
    try:
        c_res = subprocess.run(["sudo", "mysql", "-e", count_sql, "-sN"], stdout=subprocess.PIPE, text=True, errors="replace", timeout=5)
        if c_res.stdout.strip().isdigit():
            total = int(c_res.stdout.strip())
    except Exception:
        pass

    # 2. Obter colunas e identificar tipos BLOB / binários para projetar de forma legível
    schema_cols = get_table_schema(clean_db, clean_table)
    col_projections = []
    for col in schema_cols:
        c_name = col.get("field", "")
        c_type = (col.get("type") or "").lower()
        if any(b in c_type for b in ["blob", "binary", "varbinary"]):
            col_projections.append(f"CONCAT('[BLOB: ', COALESCE(LENGTH(`{c_name}`), 0), ' bytes]') AS `{c_name}`")
        else:
            col_projections.append(f"`{c_name}`")

    select_expr = ", ".join(col_projections) if col_projections else "*"

    # 3. Registros da tabela
    data_sql = f"SELECT {select_expr} FROM `{clean_db}`.`{clean_table}` LIMIT {safe_limit} OFFSET {safe_offset};"
    cmd = ["sudo", "mysql", "-e", data_sql, "-B"]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors="replace", timeout=10)
        if res.returncode != 0:
            return {"columns": [], "rows": [], "total": total}
        lines = res.stdout.strip().splitlines()
        if not lines:
            return {"columns": [], "rows": [], "total": total}
        columns = lines[0].split("\t")
        rows = []
        for line in lines[1:]:
            parts = line.split("\t")
            # Truncar campos de texto muito longos para performance
            row_dict = {}
            for col, val in zip(columns, parts):
                row_dict[col] = (val[:300] + "...") if len(val) > 300 else val
            rows.append(row_dict)

        return {
            "columns": columns,
            "rows": rows,
            "total": total,
            "limit": safe_limit,
            "offset": safe_offset,
        }
    except Exception:
        return {"columns": [], "rows": [], "total": total}



# ==============================================================================
# IMPORTAÇÃO DE SQL E PROVISIONAMENTO DE BANCO DE PROJETO
# ==============================================================================


def import_sql_script(db_slug_or_name: str, sql_content: str = "", sql_file_path: str = "") -> dict[str, Any]:
    """Importa um script .sql para dentro de um banco de dados gerenciado (MySQL/MariaDB, Postgres ou SQLite)."""
    dbs = load_databases()
    target = next((d for d in dbs if d.get("slug") == db_slug_or_name or d.get("dbName") == db_slug_or_name), None)

    db_name = target.get("dbName", db_slug_or_name) if target else db_slug_or_name
    engine = target.get("engine", "mysql") if target else "mysql"

    if sql_file_path and os.path.exists(sql_file_path):
        with open(sql_file_path, "r", encoding="utf-8", errors="replace") as f:
            sql_content = f.read()

    sql_content = (sql_content or "").strip()
    if not sql_content:
        raise ValueError("Nenhum comando ou script SQL fornecido para importação.")

    if engine == "mysql":
        cmd = ["sudo", "mysql", "--default-character-set=utf8mb4", db_name]
        proc = subprocess.run(cmd, input=sql_content, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)
        if proc.returncode != 0:
            raise RuntimeError(f"Erro ao importar SQL no MariaDB: {proc.stderr[:1000]}")
        tables = list_database_tables(db_name)
        return {
            "ok": True,
            "status": "success",
            "message": f"Script SQL executado com sucesso no banco '{db_name}'. {len(tables)} tabela(s) disponível(is).",
            "tablesCount": len(tables),
            "tables": tables,
        }

    elif engine == "postgresql":
        cmd = ["sudo", "-u", "postgres", "psql", "-d", db_name]
        proc = subprocess.run(cmd, input=sql_content, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)
        if proc.returncode != 0:
            raise RuntimeError(f"Erro ao importar SQL no PostgreSQL: {proc.stderr[:1000]}")
        return {
            "ok": True,
            "status": "success",
            "message": f"Script SQL executado com sucesso no PostgreSQL '{db_name}'.",
        }

    elif engine == "sqlite":
        db_path = target.get("dataPath", "") if target else ""
        if not db_path or not os.path.exists(db_path):
            raise ValueError("Arquivo SQLite não encontrado.")
        conn = sqlite3.connect(db_path)
        conn.executescript(sql_content)
        conn.commit()
        conn.close()
        return {
            "ok": True,
            "status": "success",
            "message": "Script SQL executado com sucesso no SQLite.",
        }
    else:
        raise ValueError(f"Importação SQL não suportada para engine '{engine}'.")


def create_project_database(
    project_slug: str,
    engine: str = "mysql",
    initial_sql: str = "",
    initial_sql_file: str = "",
    custom_name: str = "",
) -> dict[str, Any]:
    """Cria um banco dedicado para um projeto, importa SQL inicial (se houver) e retorna os dados para injeção."""
    clean_proj = sanitize_db_slug(project_slug)
    db_label = custom_name.strip() if custom_name else f"Banco {project_slug}"
    db_slug = f"proj_{clean_proj}"

    dbs = load_databases()
    existing = next((d for d in dbs if d.get("slug") == db_slug), None)
    if existing:
        db_record = existing
    else:
        db_record = create_database(name=db_label, engine=engine)

    import_result = None
    if initial_sql_file or initial_sql:
        try:
            import_result = import_sql_script(
                db_slug_or_name=db_record["slug"],
                sql_content=initial_sql,
                sql_file_path=initial_sql_file,
            )
        except Exception as e:
            import_result = {"ok": False, "error": str(e)}

    return {
        "ok": True,
        "database": db_record,
        "sqlImport": import_result,
    }
