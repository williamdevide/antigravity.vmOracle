"""
Camada 3 (Execucao): Motor PaaS A.C.O. v3.0 (Coolify Edition)
Gerencia o ciclo de vida completo de aplicacoes na VM Linux da Oracle Cloud:
- Suporte a Full-Stack Monorepo (/frontend + /backend), React/Vite (SPA), Static, Node.js e Python
- Telemetria real de Memoria RAM (systemd cgroups MemoryCurrent) e Disco por projeto + Plataforma A.C.O.
- Gestao de Variaveis de Ambiente (.env) por projeto com injecao em build (VITE_*) e runtime (systemd)
- Historico completo de Deploys (deploymentsHistory) com hash do commit, autor, duracao, trigger e log
- Auto-Deploy Hibrido: Webhook do GitHub + Verificador automatico de novos commits (git ls-remote)
"""

import datetime
import json
import os
import platform
import re
import secrets
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from typing import Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECTS_DB_PATH = os.path.join(BASE_DIR, "execution", "deployed_projects.json")
PROJECTS_ROOT = "/var/www/projects"
CADDY_SITES_DIR = "/etc/caddy/sites.d"
VM_IP = os.environ.get("OCI_VM_IP", "147.15.2.73")

# Previne qualquer erro de dubious ownership no Git para o sistema todo
try:
    subprocess.run(["git", "config", "--global", "--add", "safe.directory", "*"], check=False)
except Exception:
    pass


def sanitize_slug(raw_slug: str) -> str:
    """Converte o nome do subdominio para formato DNS seguro."""
    slug = re.sub(r"[^a-z0-9-]", "-", raw_slug.strip().lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    if not slug or slug in ("painel", "api", "admin", "default", "aco"):
        raise ValueError(f"Subdominio '{raw_slug}' invalido ou reservado pelo sistema.")
    return slug[:32]


def get_directory_size_bytes(path: str) -> int:
    """Calcula o tamanho real ocupado em disco (em bytes) por um diretorio."""
    if not path or not os.path.exists(path):
        return 0
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


def format_bytes_human(size_bytes: int) -> str:
    """Formata bytes em string legivel (B, KB, MB ou GB)."""
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
    gb = mb / 1024.0
    return f"{gb:.2f} GB"


def get_systemd_service_telemetry(service_name: str) -> dict[str, Any]:
    """Consulta MemoryCurrent, ActiveState e MainPID de um servico systemd no Linux."""
    if platform.system() != "Linux":
        return {"activeState": "active", "memoryBytes": 0, "memoryFormatted": "0 B", "pid": 0}
    try:
        res = subprocess.run(
            ["systemctl", "show", service_name, "--property=MemoryCurrent,ActiveState,SubState,MainPID"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
        )
        mem_bytes = 0
        active_state = "inactive"
        sub_state = "dead"
        pid = 0
        for line in res.stdout.splitlines():
            if line.startswith("MemoryCurrent="):
                val = line.split("=", 1)[1].strip()
                if val.isdigit() and int(val) < (1 << 60):
                    mem_bytes = int(val)
            elif line.startswith("ActiveState="):
                active_state = line.split("=", 1)[1].strip()
            elif line.startswith("SubState="):
                sub_state = line.split("=", 1)[1].strip()
            elif line.startswith("MainPID="):
                val = line.split("=", 1)[1].strip()
                if val.isdigit():
                    pid = int(val)
        return {
            "activeState": active_state,
            "subState": sub_state,
            "memoryBytes": mem_bytes,
            "memoryMB": round(mem_bytes / (1024 * 1024), 2),
            "memoryFormatted": format_bytes_human(mem_bytes),
            "pid": pid,
        }
    except Exception:
        return {"activeState": "unknown", "memoryBytes": 0, "memoryFormatted": "0 B", "pid": 0}


def get_aco_platform_telemetry() -> dict[str, Any]:
    """
    Mede o consumo real de Disco e Memoria RAM da propria plataforma
    A.C.O. (Antigravity Cloud Orchestrator):
    - Backend FastAPI (antigravity-dashboard.service)
    - Robo Cacador ARM 24/7 (oci-arm-hunter.service)
    - Reverse Proxy HTTPS (caddy.service)
    - Diretorio /opt/antigravity-oracle
    """
    dash_tel = get_systemd_service_telemetry("antigravity-dashboard")
    arm_tel = get_systemd_service_telemetry("oci-arm-hunter")
    caddy_tel = get_systemd_service_telemetry("caddy")

    total_ram = dash_tel["memoryBytes"] + arm_tel["memoryBytes"] + caddy_tel["memoryBytes"]
    aco_dir = "/opt/antigravity-oracle" if os.path.exists("/opt/antigravity-oracle") else BASE_DIR
    disk_bytes = get_directory_size_bytes(aco_dir)

    deploy_time_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    try:
        # Prioriza a data do último commit Git ou do build do frontend
        cmd_git = ["git", "-C", aco_dir, "log", "-1", "--format=%cd", "--date=format:%d/%m/%Y %H:%M"]
        res = subprocess.run(cmd_git, capture_output=True, text=True, timeout=3)
        if res.returncode == 0 and res.stdout.strip():
            deploy_time_str = res.stdout.strip()
        else:
            dist_index = os.path.join(aco_dir, "frontend", "dist", "index.html")
            if os.path.exists(dist_index):
                deploy_time_str = datetime.datetime.fromtimestamp(os.path.getmtime(dist_index)).strftime("%d/%m/%Y %H:%M")
    except Exception:
        pass

    return {
        "name": "A.C.O. Core Platform (Antigravity Cloud Orchestrator)",
        "slug": "aco-core",
        "version": "v3.6.0",
        "deployDate": deploy_time_str,
        "url": f"https://{VM_IP}.sslip.io",
        "status": "ONLINE" if dash_tel["activeState"] == "active" else dash_tel["activeState"].upper(),
        "diskBytes": disk_bytes,
        "diskMB": round(disk_bytes / (1024 * 1024), 2),
        "diskFormatted": format_bytes_human(disk_bytes),
        "ramBytes": total_ram,
        "ramMB": round(total_ram / (1024 * 1024), 2),
        "ramFormatted": format_bytes_human(total_ram),
        "totalRamFormatted": format_bytes_human(total_ram),
        "components": [
            {
                "name": "FastAPI Orchestrator (antigravity-dashboard)",
                "service": "antigravity-dashboard.service",
                "status": dash_tel["activeState"],
                "ramFormatted": dash_tel["memoryFormatted"],
                "ramBytes": dash_tel["memoryBytes"],
            },
            {
                "name": "Robô Caçador ARM 24/7 (oci-arm-hunter)",
                "service": "oci-arm-hunter.service",
                "status": arm_tel["activeState"],
                "ramFormatted": arm_tel["memoryFormatted"],
                "ramBytes": arm_tel["memoryBytes"],
            },
            {
                "name": "Caddy Reverse Proxy HTTPS (caddy)",
                "service": "caddy.service",
                "status": caddy_tel["activeState"],
                "ramFormatted": caddy_tel["memoryFormatted"],
                "ramBytes": caddy_tel["memoryBytes"],
            },
        ],
    }


def reconcile_unindexed_projects(existing_projects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Auto-Discovery & Auto-Recuperacao (Self-Annealing):
    Escaneia /etc/caddy/sites.d/*.caddy e /var/www/projects/*/ para identificar
    projetos que já estejam rodando na VM (como o Sistema Manu) mas que por ventura
    nao estejam cadastrados no deployed_projects.json.
    """
    known_slugs = {p.get("slug") for p in existing_projects if p.get("slug")}
    found_slugs: set[str] = set()

    # 1. Escanear arquivos .caddy
    if os.path.isdir(CADDY_SITES_DIR):
        try:
            for f in os.listdir(CADDY_SITES_DIR):
                if f.endswith(".caddy") and not f.endswith(".disabled"):
                    s = f[:-6]
                    if s and s not in known_slugs:
                        found_slugs.add(s)
        except Exception:
            pass

    # 2. Escanear diretorios em /var/www/projects
    if os.path.isdir(PROJECTS_ROOT):
        try:
            for d in os.listdir(PROJECTS_ROOT):
                full_p = os.path.join(PROJECTS_ROOT, d)
                if os.path.isdir(full_p) and d not in known_slugs:
                    found_slugs.add(d)
        except Exception:
            pass

    changed = False
    for slug in sorted(found_slugs):
        proj_dir = os.path.join(PROJECTS_ROOT, slug)
        caddy_file = os.path.join(CADDY_SITES_DIR, f"{slug}.caddy")
        domain = f"{slug}.{VM_IP}.sslip.io"
        port = None
        ptype = "static"

        if os.path.exists(caddy_file):
            try:
                with open(caddy_file, "r", encoding="utf-8") as cf:
                    content = cf.read()
                lines = content.strip().splitlines()
                if lines and not lines[0].startswith("#") and "{" in lines[0]:
                    domain = lines[0].split("{")[0].strip()
                if "php_fastcgi" in content:
                    ptype = "php"
                m_port = re.search(r"reverse_proxy\s+(?:127\.0\.0\.1|localhost):(\d+)", content)
                if m_port:
                    port = int(m_port.group(1))
            except Exception:
                pass

        if os.path.isdir(proj_dir):
            if os.path.isdir(os.path.join(proj_dir, "frontend")) and (
                os.path.isdir(os.path.join(proj_dir, "backend")) or os.path.isdir(os.path.join(proj_dir, "server"))
            ):
                ptype = "fullstack"
            elif (
                os.path.exists(os.path.join(proj_dir, "index.php"))
                or os.path.exists(os.path.join(proj_dir, "composer.json"))
                or os.path.exists(os.path.join(proj_dir, "public", "index.php"))
            ):
                ptype = "php"

        repo_url = ""
        git_dir = os.path.join(proj_dir, ".git")
        if os.path.isdir(git_dir):
            try:
                res = subprocess.run(
                    ["git", "config", "--get", "remote.origin.url"],
                    cwd=proj_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=5,
                )
                repo_url = res.stdout.strip()
            except Exception:
                pass

        if not repo_url:
            if slug == "manu":
                repo_url = "https://github.com/williamdevide/antigravity.Manu.git"
            else:
                repo_url = f"https://github.com/WilliamDevide/{slug}.git"

        commit_meta = get_git_commit_metadata(proj_dir) if os.path.isdir(proj_dir) else {"shortHash": "local", "message": "Ativo na VM", "author": "Administrador"}
        friendly_name = "Sistema Manu" if slug == "manu" else slug.replace("-", " ").title()
        now_iso = datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(timespec="seconds")

        rec = {
            "name": friendly_name,
            "slug": slug,
            "customDomain": "",
            "gitUrl": repo_url,
            "repoUrl": repo_url,
            "projectType": ptype,
            "branch": "main",
            "startCommand": "",
            "domain": domain,
            "url": f"https://{domain}",
            "port": port,
            "workDir": proj_dir,
            "autoDeploy": True,
            "status": "running",
            "lastCommitShortHash": commit_meta.get("shortHash", "ativo"),
            "lastCommitHash": commit_meta.get("shortHash", "ativo"),
            "lastCommitMessage": commit_meta.get("message", "Projeto recuperado e ativo na VM"),
            "lastCommitAuthor": commit_meta.get("author", "WilliamDevide"),
            "envVarsText": "",
            "diskBytes": get_directory_size_bytes(proj_dir),
            "updatedAt": now_iso,
            "lastBuildLog": f"[+] Projeto '{friendly_name}' sincronizado e integrado ao painel A.C.O. via reconciliação automática.",
            "deploymentsHistory": [
                {
                    "id": f"dep-rec-{slug}",
                    "commitHash": commit_meta.get("shortHash", "ativo"),
                    "commitMessage": commit_meta.get("message", "Projeto ativo na VM"),
                    "commitAuthor": commit_meta.get("author", "A.C.O. Auto-Discovery"),
                    "trigger": "reconciliation",
                    "status": "SUCCESS",
                    "timestamp": now_iso,
                    "durationSeconds": 1.0,
                    "log": f"[+] Projeto '{friendly_name}' ({domain}) auto-detectado no servidor e reconciliado com sucesso.",
                }
            ],
        }
        existing_projects.append(rec)
        changed = True

    if changed:
        try:
            save_projects(existing_projects)
        except Exception as e:
            print(f"[Aviso Reconcile] Nao foi possivel salvar projetos reconciliados: {e}", flush=True)

    return existing_projects


def load_projects() -> list[dict[str, Any]]:
    """Carrega a lista de projetos publicados e atualiza telemetria de Disco e RAM em tempo real."""
    data = []
    if os.path.exists(PROJECTS_DB_PATH):
        try:
            with open(PROJECTS_DB_PATH, "r", encoding="utf-8-sig") as f:
                loaded = json.load(f)
                if isinstance(loaded, list):
                    data = loaded
        except Exception:
            data = []

    # Reconcilia projetos que estejam no Caddy ou em /var/www/projects mas nao no JSON
    try:
        data = reconcile_unindexed_projects(data)
    except Exception as e:
        print(f"[Aviso load_projects] Falha ao reconciliar projetos: {e}", flush=True)

    for p in data:
        slug = p.get("slug", "")
        p.setdefault("name", slug.replace("-", " ").title() if slug else "Projeto")
        p.setdefault("gitUrl", p.get("repoUrl", ""))
        p.setdefault("repoUrl", p.get("gitUrl", ""))
        p.setdefault("customDomain", "")

        proj_dir = os.path.join(PROJECTS_ROOT, slug) if slug else p.get("workDir", "")
        if proj_dir and os.path.exists(proj_dir):
            sz_bytes = get_directory_size_bytes(proj_dir)
            p["diskBytes"] = sz_bytes
            p["diskMB"] = round(sz_bytes / (1024 * 1024), 2)
            p["diskMb"] = p["diskMB"]
            p["diskFormatted"] = format_bytes_human(sz_bytes)
        else:
            p.setdefault("diskBytes", 4096)
            p.setdefault("diskMB", 0.01)
            p["diskMb"] = p.get("diskMB", 0.01)
            p.setdefault("diskFormatted", "4.0 KB")

        ptype = p.get("projectType", "static")
        if ptype in ("node", "python", "fullstack") or p.get("port"):
            tel = get_systemd_service_telemetry(f"app-{slug}")
            p["ramBytes"] = tel["memoryBytes"]
            p["ramMB"] = tel.get("memoryMB", 0.0)
            p["ramMb"] = p["ramMB"]
            p["ramFormatted"] = tel["memoryFormatted"]
            p["serviceState"] = tel["activeState"]
            p["status"] = "running" if tel["activeState"] == "active" else "stopped"
        else:
            p["ramBytes"] = 0
            p["ramMB"] = 0.0
            p["ramMb"] = 0.0
            p["ramFormatted"] = "0 B (Estático Caddy)"
            p["serviceState"] = "static"
            p["status"] = "running"

        p.setdefault("autoDeploy", True)
        p.setdefault("branch", "main")
        p.setdefault("envVarsText", "")
        p["envVars"] = parse_env_text(p.get("envVarsText", ""))
        p["lastCommitHash"] = p.get("lastCommitShortHash") or p.get("lastCommitHash") or "local"
        p.setdefault("lastCommitMessage", "Deploy inicial ativo")

        hist = p.get("deploymentsHistory") or []
        if not hist and p.get("lastBuildLog"):
            hist = [
                {
                    "id": f"dep-init-{slug}",
                    "commitHash": p["lastCommitHash"],
                    "commitMessage": p["lastCommitMessage"],
                    "commitAuthor": p.get("lastCommitAuthor", "Administrador"),
                    "trigger": "initial",
                    "status": "success",
                    "timestamp": p.get("updatedAt", "Recente"),
                    "durationSec": 1.2,
                    "durationSeconds": 1.2,
                    "log": p.get("lastBuildLog", ""),
                }
            ]
        for h in hist:
            h["status"] = "success" if str(h.get("status", "")).lower() in ("success", "online") else "failed"
            h.setdefault("durationSec", h.get("durationSeconds", 1.0))
        p["deploymentsHistory"] = hist

    return data


get_deployed_projects = load_projects


def safe_write_file(file_path: str, content: str, mode: str = "666") -> None:
    """Escreve um arquivo de forma segura, com fallback para sudo caso haja PermissionError."""
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        try:
            subprocess.run(["chmod", mode, file_path], check=False)
        except Exception:
            pass
    except PermissionError:
        p = subprocess.run(
            ["sudo", "tee", file_path],
            input=content,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )
        if p.returncode != 0:
            raise RuntimeError(f"Falha ao escrever {file_path} via sudo: {p.stderr}")
        subprocess.run(["sudo", "chmod", mode, file_path], check=False)


def save_projects(projects: list[dict[str, Any]]) -> None:
    """Salva a lista de projetos publicados no banco JSON com resiliencia a permissoes."""
    os.makedirs(os.path.dirname(PROJECTS_DB_PATH), exist_ok=True)
    payload = json.dumps(projects, indent=2, ensure_ascii=False)
    safe_write_file(PROJECTS_DB_PATH, payload, mode="666")


def allocate_port(projects: list[dict[str, Any]], existing_slug: str | None = None) -> int:
    """Aloca uma porta TCP livre entre 4100 e 4199 para backends Node.js, Python ou Full-Stack."""
    for p in projects:
        if p.get("slug") == existing_slug and p.get("port"):
            return int(p["port"])
    used_ports = {int(p["port"]) for p in projects if p.get("port")}
    for port in range(4100, 4200):
        if port not in used_ports:
            return port
    raise RuntimeError("Todas as portas do pool (4100-4199) estao ocupadas.")


def run_cmd(cmd: list[str] | str, cwd: str | None = None, env: dict | None = None, timeout: int = 300) -> str:
    """Executa um comando de sistema e retorna stdout+stderr combinados."""
    merged_env = os.environ.copy()
    merged_env["GIT_CONFIG_PARAMETERS"] = "'safe.directory=*'"
    if env:
        merged_env.update(env)

    effective_cmd = cmd
    if isinstance(cmd, list) and cmd and cmd[0] == "git" and "-c" not in cmd:
        effective_cmd = ["git", "-c", "safe.directory=*"] + cmd[1:]
    elif isinstance(cmd, str) and cmd.strip().startswith("git ") and "safe.directory" not in cmd:
        effective_cmd = "git -c safe.directory=* " + cmd.strip()[4:]

    proc = subprocess.run(
        effective_cmd,
        cwd=cwd,
        env=merged_env,
        shell=isinstance(effective_cmd, str),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Comando falhou (exit {proc.returncode}):\n{proc.stdout[-1800:]}")
    return proc.stdout


def parse_env_text(env_text: str) -> dict[str, str]:
    """Converte um texto .env (KEY=VALUE) em dicionario Python."""
    result: dict[str, str] = {}
    if not env_text:
        return result
    for line in env_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k:
            result[k] = v
    return result



def write_project_env_files(target_dir: str, env_text: str) -> str:
    """
    Escreve o arquivo .aco.env (para EnvironmentFile do systemd) e .env
    na raiz do projeto e tambem em /frontend e /backend caso existam.
    """
    env_dict = parse_env_text(env_text)
    clean_lines = [f'{k}="{v}"' for k, v in env_dict.items()]
    systemd_lines = [f"{k}={v}" for k, v in env_dict.items()]

    aco_env_path = os.path.join(target_dir, ".aco.env")
    safe_write_file(aco_env_path, "\n".join(systemd_lines) + ("\n" if systemd_lines else ""))

    if clean_lines:
        dot_env_content = "\n".join(clean_lines) + "\n"
        safe_write_file(os.path.join(target_dir, ".env"), dot_env_content)
        for sub in ("frontend", "backend", "server", "client"):
            sub_dir = os.path.join(target_dir, sub)
            if os.path.isdir(sub_dir):
                safe_write_file(os.path.join(sub_dir, ".env"), dot_env_content)

    return aco_env_path


def get_project_env(slug: str) -> dict[str, Any]:
    """Retorna o conteudo real do arquivo .env gravado no disco do projeto."""
    clean_slug = sanitize_slug(slug)
    projects = load_projects()
    target = next((p for p in projects if p.get("slug") == clean_slug), None)

    target_dir = os.path.join(PROJECTS_ROOT, clean_slug)
    env_file = os.path.join(target_dir, ".env")
    aco_env = os.path.join(target_dir, ".aco.env")

    content = ""
    file_found = None

    for cand in (env_file, aco_env):
        if os.path.exists(cand):
            try:
                with open(cand, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    file_found = cand
                    break
            except Exception:
                pass

    if not content and target:
        content = target.get("envVarsText", "")

    return {
        "slug": clean_slug,
        "envText": content,
        "filePath": file_found or env_file,
        "exists": file_found is not None,
    }


def build_authenticated_git_url(repo_url: str, github_token: str = "", custom_token: str = "") -> str:
    clean = repo_url.strip()
    if not clean.startswith("http"):
        clean = f"https://github.com/{clean.lstrip('/')}"
    if not clean.endswith(".git") and "github.com/" in clean:
        clean = clean.rstrip("/") + ".git"
    if "@" in clean:
        return clean
    effective_token = custom_token.strip() or github_token.strip()
    if effective_token and "github.com/" in clean:
        return clean.replace("https://github.com/", f"https://{effective_token}@github.com/")
    return clean


def find_php_fpm_socket() -> str:
    """Detecta automaticamente o socket UNIX ativo do PHP-FPM no Ubuntu."""
    common_sockets = [
        "/run/php/php8.3-fpm.sock",
        "/run/php/php8.2-fpm.sock",
        "/run/php/php8.1-fpm.sock",
        "/run/php/php8.0-fpm.sock",
        "/run/php/php-fpm.sock",
    ]
    for s in common_sockets:
        if os.path.exists(s):
            return s
    if os.path.isdir("/run/php"):
        try:
            for f in os.listdir("/run/php"):
                if f.endswith(".sock") and "fpm" in f:
                    return os.path.join("/run/php", f)
        except Exception:
            pass
    return "/run/php/php8.3-fpm.sock"


ACO_CRON_DIR = "/etc/cron.d"
ACO_CRON_LOG_DIR = "/var/log/aco-cron"


def get_project_cron(slug: str) -> dict[str, Any]:
    """Consulta a configuracao de agendamento Cron e o log recente de execucao."""
    clean_slug = sanitize_slug(slug)
    cron_candidates = [
        os.path.join(ACO_CRON_DIR, f"aco-{clean_slug}"),
        os.path.join(ACO_CRON_DIR, f"aco-project-{clean_slug}"),
    ]
    log_file = os.path.join(ACO_CRON_LOG_DIR, f"{clean_slug}.log")

    enabled = False
    schedule = "0 * * * *"
    command = ""
    cron_file_found = None

    for cron_file in cron_candidates:
        if os.path.exists(cron_file):
            cron_file_found = cron_file
            try:
                with open(cron_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#") or line.startswith("PATH="):
                            continue
                        parts = line.split(maxsplit=6)
                        if len(parts) >= 7:
                            schedule = " ".join(parts[:5])
                            raw_cmd = parts[6]
                            if " >> " in raw_cmd:
                                raw_cmd = raw_cmd.split(" >> ")[0]
                            if " > " in raw_cmd:
                                raw_cmd = raw_cmd.split(" > ")[0]
                            if " && " in raw_cmd:
                                raw_cmd = raw_cmd.split(" && ", 1)[1]
                            command = raw_cmd.strip()
                            enabled = True
                            break
            except Exception:
                pass
            if enabled:
                break

    # Fallback para dados persistidos no catalogo de projetos
    if not command:
        projects = load_projects()
        target = next((p for p in projects if p.get("slug") == clean_slug), None)
        if target:
            if target.get("cronSchedule"):
                schedule = target["cronSchedule"]
                enabled = True
            if target.get("cronCommand"):
                command = target["cronCommand"]
                enabled = True

    recent_logs = ""
    if os.path.exists(log_file):
        try:
            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                recent_logs = "".join(lines[-100:])
        except Exception as e:
            recent_logs = f"Erro ao ler log do cron: {e}"
    else:
        recent_logs = "Ainda não há registros de execução para este evento Cron."

    return {
        "slug": clean_slug,
        "enabled": enabled,
        "schedule": schedule,
        "command": command,
        "cronFilePath": cron_file_found or os.path.join(ACO_CRON_DIR, f"aco-{clean_slug}"),
        "logFilePath": log_file,
        "recentLogs": recent_logs,
    }


def get_project_file_tree(slug: str, relative_path: str = "") -> dict[str, Any]:
    """Retorna a arvore de arquivos e diretorios de um projeto publicado para navegacao visual."""
    clean_slug = sanitize_slug(slug)
    project_root = os.path.join(PROJECTS_ROOT, clean_slug)

    if not os.path.isdir(project_root):
        raise ValueError(f"Diretorio do projeto '{clean_slug}' nao encontrado.")

    # Impedir path traversal (../)
    safe_relative = relative_path.strip().lstrip("/\\")
    target_dir = os.path.abspath(os.path.join(project_root, safe_relative))

    if not target_dir.startswith(os.path.abspath(project_root)):
        raise ValueError("Acesso negado fora do diretorio raiz do projeto.")

    if not os.path.exists(target_dir):
        raise ValueError(f"Caminho '{safe_relative}' nao encontrado.")

    items = []
    try:
        with os.scandir(target_dir) as entries:
            for entry in entries:
                if entry.name == ".git":
                    continue
                is_dir = entry.is_dir(follow_symlinks=False)
                entry_stat = entry.stat(follow_symlinks=False)
                size_bytes = entry_stat.st_size if not is_dir else 0
                rel = os.path.relpath(entry.path, project_root).replace("\\", "/")
                ext = os.path.splitext(entry.name)[1].lower().lstrip(".")

                items.append({
                    "name": entry.name,
                    "relativePath": rel,
                    "isDirectory": is_dir,
                    "type": "directory" if is_dir else "file",
                    "extension": ext,
                    "sizeBytes": size_bytes,
                    "sizeFormatted": format_bytes_human(size_bytes) if not is_dir else "--",
                    "modifiedAt": datetime.datetime.fromtimestamp(entry_stat.st_mtime).strftime("%d/%m/%Y %H:%M:%S"),
                })
    except Exception as e:
        raise RuntimeError(f"Erro ao ler diretorio do projeto: {e}") from e

    # Ordenar: diretorios primeiro, depois arquivos alfabeticamente
    items.sort(key=lambda x: (not x["isDirectory"], x["name"].lower()))

    current_rel = os.path.relpath(target_dir, project_root).replace("\\", "/")
    if current_rel == ".":
        current_rel = ""

    return {
        "slug": clean_slug,
        "currentPath": current_rel,
        "items": items,
        "totalItems": len(items),
    }


def get_project_file_content(slug: str, relative_file_path: str) -> dict[str, Any]:
    """Retorna o conteudo de texto de um arquivo de projeto (max 512 KB)."""
    clean_slug = sanitize_slug(slug)
    project_root = os.path.join(PROJECTS_ROOT, clean_slug)

    safe_relative = relative_file_path.strip().lstrip("/\\")
    file_path = os.path.abspath(os.path.join(project_root, safe_relative))

    if not file_path.startswith(os.path.abspath(project_root)):
        raise ValueError("Acesso negado fora do diretorio do projeto.")

    if not os.path.isfile(file_path):
        raise ValueError(f"Arquivo '{safe_relative}' nao encontrado.")

    size = os.path.getsize(file_path)
    if size > 1024 * 512:
        return {
            "slug": clean_slug,
            "relativePath": safe_relative,
            "sizeBytes": size,
            "sizeFormatted": format_bytes_human(size),
            "content": f"[Aviso: Arquivo grande ({format_bytes_human(size)}). Visualizacao limitada.]",
            "isTruncated": True,
        }

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return {
            "slug": clean_slug,
            "relativePath": safe_relative,
            "sizeBytes": size,
            "sizeFormatted": format_bytes_human(size),
            "content": content,
            "isTruncated": False,
        }
    except Exception as e:
        raise RuntimeError(f"Erro ao ler arquivo: {e}") from e


def update_project_cron(slug: str, schedule: str, command: str, enabled: bool) -> dict[str, Any]:
    """Atualiza ou remove o arquivo /etc/cron.d/aco-<slug> para agendamentos automaticos."""
    clean_slug = sanitize_slug(slug)
    projects = load_projects()
    proj = next((p for p in projects if p.get("slug") == clean_slug), None)
    work_dir = proj.get("workDir", os.path.join(PROJECTS_ROOT, clean_slug)) if proj else os.path.join(PROJECTS_ROOT, clean_slug)

    cron_file = os.path.join(ACO_CRON_DIR, f"aco-{clean_slug}")
    log_file = os.path.join(ACO_CRON_LOG_DIR, f"{clean_slug}.log")

    if not enabled or not command.strip():
        if os.path.exists(cron_file):
            try:
                os.remove(cron_file)
            except Exception:
                run_cmd(["sudo", "rm", "-f", cron_file])
        return get_project_cron(clean_slug)

    clean_sched = schedule.strip() or "* * * * *"
    clean_cmd = command.strip()

    os.makedirs(ACO_CRON_LOG_DIR, exist_ok=True)
    cron_content = (
        "PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin\n"
        f"# A.C.O. Scheduled Task - Projeto: {clean_slug}\n"
        f"{clean_sched} ubuntu cd {work_dir} && {clean_cmd} >> {log_file} 2>&1\n"
    )

    temp_path = f"/tmp/aco-cron-{clean_slug}"
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(cron_content)
        run_cmd(["sudo", "mv", temp_path, cron_file])
        run_cmd(["sudo", "chmod", "644", cron_file])
    except Exception as e:
        if platform.system() != "Linux":
            pass
        else:
            raise RuntimeError(f"Falha ao salvar agendamento Cron: {e}") from e

    return get_project_cron(clean_slug)


def run_project_cron_now(slug: str) -> dict[str, Any]:
    """Executa o comando Cron do projeto manualmente em tempo real para testes."""
    clean_slug = sanitize_slug(slug)
    cron_info = get_project_cron(clean_slug)
    cmd = cron_info.get("command", "").strip()
    if not cmd:
        raise ValueError("Nenhum comando Cron configurado para este projeto.")

    projects = load_projects()
    proj = next((p for p in projects if p.get("slug") == clean_slug), None)
    work_dir = proj.get("workDir", os.path.join(PROJECTS_ROOT, clean_slug)) if proj else os.path.join(PROJECTS_ROOT, clean_slug)
    log_file = os.path.join(ACO_CRON_LOG_DIR, f"{clean_slug}.log")

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = f"\n[{now_str}] --- Execução Manual Disparada via Painel A.C.O. ---\n"
    try:
        out = run_cmd(f"cd {work_dir} && {cmd}", timeout=120)
        full_out = header + out + "\n[SUCESSO] Código de saída: 0\n"
    except Exception as e:
        full_out = header + str(e) + "\n[ERRO] Falha na execução manual.\n"

    try:
        os.makedirs(ACO_CRON_LOG_DIR, exist_ok=True)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(full_out)
    except Exception:
        pass

    return {
        "status": "success",
        "output": full_out,
        "cron": get_project_cron(clean_slug),
    }


def extract_github_owner_repo(repo_url: str) -> tuple[str, str] | None:
    """Extrai (owner, repo) de uma URL do GitHub."""
    m = re.search(r"github\.com[:/]([^/]+)/([^/.]+)(?:\.git)?$", repo_url.strip())
    if m:
        return m.group(1), m.group(2)
    return None


def ensure_github_webhook(repo_url: str, slug: str, webhook_secret: str, github_token: str) -> str:
    """
    Registra automaticamente um Webhook no repositorio do GitHub para acionar
    POST https://147.15.2.73.sslip.io/api/webhooks/github/<slug> a cada git push.
    """
    if not github_token:
        return "Sem GITHUB_TOKEN para registrar webhook."
    parsed = extract_github_owner_repo(repo_url)
    if not parsed:
        return "URL nao pertence ao GitHub."
    owner, repo = parsed
    hook_url = f"https://{VM_IP}.sslip.io/api/webhooks/github/{slug}"

    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "ACO-Coolify-Orchestrator",
        "Content-Type": "application/json",
    }

    try:
        req = urllib.request.Request(f"https://api.github.com/repos/{owner}/{repo}/hooks", headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            hooks = json.loads(resp.read().decode("utf-8"))
            for h in hooks:
                if h.get("config", {}).get("url") == hook_url:
                    return f"Webhook GitHub ativo (ID {h.get('id')})"

        payload = {
            "name": "web",
            "active": True,
            "events": ["push"],
            "config": {
                "url": hook_url,
                "content_type": "json",
                "secret": webhook_secret,
                "insecure_ssl": "0",
            },
        }
        post_req = urllib.request.Request(
            f"https://api.github.com/repos/{owner}/{repo}/hooks",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(post_req, timeout=10) as resp:
            created = json.loads(resp.read().decode("utf-8"))
            return f"Webhook GitHub registrado com sucesso (ID {created.get('id')})"
    except Exception as e:
        return f"Polling Git 60s ativo (Webhook opcional: {str(e)[:80]})"


def detect_project_type(target_dir: str, requested_type: str = "auto") -> str:
    """Detecta automaticamente fullstack (/frontend + /backend), react-vite, node, python ou static."""
    if requested_type and requested_type != "auto":
        return requested_type

    fe_dir = os.path.join(target_dir, "frontend")
    be_dir = os.path.join(target_dir, "backend")
    srv_dir = os.path.join(target_dir, "server")

    has_fe = os.path.isdir(fe_dir) and os.path.exists(os.path.join(fe_dir, "package.json"))
    has_be = (
        os.path.isdir(be_dir)
        and (
            os.path.exists(os.path.join(be_dir, "requirements.txt"))
            or os.path.exists(os.path.join(be_dir, "main.py"))
            or os.path.exists(os.path.join(be_dir, "app.py"))
            or os.path.exists(os.path.join(be_dir, "package.json"))
        )
    ) or (os.path.isdir(srv_dir) and os.path.exists(os.path.join(srv_dir, "package.json")))

    if has_fe and has_be:
        return "fullstack"

    work_dir = find_effective_project_root(target_dir)
    pkg_json_path = os.path.join(work_dir, "package.json")
    if os.path.exists(pkg_json_path):
        try:
            with open(pkg_json_path, "r", encoding="utf-8") as f:
                pkg = json.load(f)
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            scripts = pkg.get("scripts", {})
            if "vite" in deps or "react-scripts" in deps or ("build" in scripts and "start" not in scripts):
                return "react-vite"
            if "start" in scripts or "express" in deps or "fastify" in deps:
                return "node"
            if "build" in scripts:
                return "react-vite"
        except Exception:
            pass

    if (
        os.path.exists(os.path.join(work_dir, "requirements.txt"))
        or os.path.exists(os.path.join(work_dir, "main.py"))
        or os.path.exists(os.path.join(work_dir, "app.py"))
    ):
        return "python"

    if (
        os.path.exists(os.path.join(work_dir, "index.php"))
        or os.path.exists(os.path.join(work_dir, "composer.json"))
        or os.path.exists(os.path.join(work_dir, "artisan"))
        or os.path.exists(os.path.join(work_dir, "public", "index.php"))
    ):
        return "php"

    return "static"


def find_effective_project_root(base_dir: str) -> str:
    """Encontra o diretorio efetivo quando nao for fullstack."""
    if (
        os.path.exists(os.path.join(base_dir, "package.json"))
        or os.path.exists(os.path.join(base_dir, "requirements.txt"))
        or os.path.exists(os.path.join(base_dir, "index.html"))
        or os.path.exists(os.path.join(base_dir, "index.php"))
        or os.path.exists(os.path.join(base_dir, "composer.json"))
    ):
        return base_dir

    for sub in ("public", "src", "frontend", "client", "web", "backend", "api", "server"):
        candidate = os.path.join(base_dir, sub)
        if os.path.isdir(candidate) and (
            os.path.exists(os.path.join(candidate, "package.json"))
            or os.path.exists(os.path.join(candidate, "index.html"))
            or os.path.exists(os.path.join(candidate, "index.php"))
            or os.path.exists(os.path.join(candidate, "requirements.txt"))
        ):
            return candidate
    return base_dir


def get_git_commit_metadata(repo_dir: str) -> dict[str, str]:
    """Retorna hash curto, hash completo, mensagem e autor do ultimo commit local."""
    if not os.path.exists(os.path.join(repo_dir, ".git")):
        return {
            "shortHash": "local",
            "fullHash": "local",
            "message": "Deploy estático / local",
            "author": "Administrador",
        }
    try:
        full_hash = run_cmd(["git", "rev-parse", "HEAD"], cwd=repo_dir).strip()
        short_hash = full_hash[:7]
        msg = run_cmd(["git", "log", "-1", "--pretty=%s"], cwd=repo_dir).strip()
        author = run_cmd(["git", "log", "-1", "--pretty=%an"], cwd=repo_dir).strip()
        return {
            "shortHash": short_hash,
            "fullHash": full_hash,
            "message": msg or "Atualização de código",
            "author": author or "GitHub",
        }
    except Exception:
        return {"shortHash": "head", "fullHash": "head", "message": "Commit recente", "author": "GitHub"}


def check_remote_commit_hash(repo_url: str, github_token: str = "") -> str | None:
    """Consulta no GitHub o hash do HEAD remoto em 2s via git ls-remote."""
    if not repo_url or "antigravity/demo-showcase" in repo_url:
        return None
    auth_url = build_authenticated_git_url(repo_url, github_token)
    try:
        out = run_cmd(["git", "ls-remote", auth_url, "HEAD"], timeout=15)
        first_line = out.strip().splitlines()[0] if out.strip() else ""
        if first_line:
            return first_line.split()[0].strip()
    except Exception:
        return None
    return None


def _setup_backend_systemd_service(
    service_name: str,
    clean_slug: str,
    backend_dir: str,
    port: int,
    aco_env_path: str,
    start_command: str,
    logs: list[str],
) -> None:
    """Configura e inicia servico systemd para backend Node.js ou Python."""
    is_python = (
        os.path.exists(os.path.join(backend_dir, "requirements.txt"))
        or os.path.exists(os.path.join(backend_dir, "main.py"))
        or os.path.exists(os.path.join(backend_dir, "app.py"))
    )

    if is_python:
        venv_dir = os.path.join(backend_dir, ".venv")
        logs.append(f"[*] Preparando ambiente Python (.venv) em {backend_dir} (Porta {port})...")
        run_cmd(["python3", "-m", "venv", venv_dir], cwd=backend_dir)
        pip_bin = os.path.join(venv_dir, "bin", "pip")
        run_cmd([pip_bin, "install", "--upgrade", "pip", "uvicorn", "gunicorn", "fastapi", "flask"], cwd=backend_dir)
        req_file = os.path.join(backend_dir, "requirements.txt")
        if os.path.exists(req_file):
            run_cmd([pip_bin, "install", "-r", req_file], cwd=backend_dir, timeout=420)

        if start_command.strip():
            cmd_exec = f"{venv_dir}/bin/{start_command.strip()}"
        elif os.path.exists(os.path.join(backend_dir, "main.py")):
            cmd_exec = f"{venv_dir}/bin/uvicorn main:app --host 127.0.0.1 --port {port}"
        elif os.path.exists(os.path.join(backend_dir, "app.py")):
            cmd_exec = f"{venv_dir}/bin/uvicorn app:app --host 127.0.0.1 --port {port}"
        else:
            cmd_exec = f"{venv_dir}/bin/python3 -m http.server {port}"
    else:
        logs.append(f"[*] Instalando dependencias Node.js do backend em {backend_dir} (Porta {port})...")
        run_cmd(["npm", "install", "--omit=dev", "--no-audit", "--no-fund"], cwd=backend_dir, timeout=360)
        cmd_exec = start_command.strip() or "/usr/bin/npm start"
        if not cmd_exec.startswith("/"):
            cmd_exec = f"/usr/bin/env {cmd_exec}"

    unit_content = f"""[Unit]
Description=A.C.O. Managed Service ({clean_slug})
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory={backend_dir}
EnvironmentFile=-{aco_env_path}
Environment=PORT={port}
Environment=NODE_ENV=production
ExecStart={cmd_exec}
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""
    subprocess.run(
        ["sudo", "tee", f"/etc/systemd/system/{service_name}.service"],
        input=unit_content,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=True,
    )
    run_cmd(["sudo", "systemctl", "daemon-reload"])
    run_cmd(["sudo", "systemctl", "enable", service_name])
    run_cmd(["sudo", "systemctl", "restart", service_name])


def deploy_project(
    slug: str,
    repo_url: str,
    project_type: str = "auto",
    branch: str = "main",
    start_command: str = "",
    env_vars_text: str | None = None,
    auto_deploy: bool | None = None,
    trigger: str = "manual",
    github_token: str = "",
    name: str | None = None,
    custom_domain: str = "",
    git_token: str = "",
    cron_schedule: str = "",
    cron_command: str = "",
    create_database: bool = False,
    database_engine: str = "mysql",
    initial_sql: str = "",
    initial_sql_file: str = "",
) -> dict[str, Any]:
    """
    Executa o ciclo completo de Deploy de um projeto (Frontend, Backend, Full-Stack ou PHP),
    grava no Historico de Deploys do projeto e atualiza telemetria de Disco e RAM.
    """
    start_ts = time.time()
    now_iso = datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(timespec="seconds")
    clean_slug = sanitize_slug(slug)
    projects = load_projects()
    existing = next((p for p in projects if p.get("slug") == clean_slug), None)

    effective_name = (name or "").strip() or (existing.get("name") if existing else "") or clean_slug
    effective_custom_domain = (custom_domain or "").strip().lower() or (existing.get("customDomain", "") if existing else "")
    effective_env_text = env_vars_text if env_vars_text is not None else (existing.get("envVarsText", "") if existing else "")
    effective_auto_deploy = auto_deploy if auto_deploy is not None else (existing.get("autoDeploy", True) if existing else True)
    effective_start_cmd = start_command.strip() or (existing.get("startCommand", "") if existing else "")
    webhook_secret = (existing.get("webhookSecret") if existing else None) or secrets.token_hex(16)
    history = list(existing.get("deploymentsHistory", [])) if existing else []

    target_dir = os.path.join(PROJECTS_ROOT, clean_slug)
    os.makedirs(PROJECTS_ROOT, exist_ok=True)
    os.makedirs(CADDY_SITES_DIR, exist_ok=True)

    logs = [f"=== A.C.O. Deploy Engine v3.0 • Inicio: {now_iso} | Disparo: {trigger.upper()} ==="]
    auth_url = build_authenticated_git_url(repo_url, github_token, git_token)

    try:
        # Garantir permissoes adequadas para o usuario de execucao (ubuntu) e servidor web (www-data)
        if os.path.exists(target_dir):
            try:
                run_cmd(["sudo", "chown", "-R", "ubuntu:www-data", target_dir])
                run_cmd(["sudo", "chmod", "-R", "u+rwX,g+rwX", target_dir])
            except Exception:
                pass

        # 1. Clone ou Git Pull
        if os.path.exists(os.path.join(target_dir, ".git")):
            logs.append(f"[*] Sincronizando alteracoes do GitHub em {target_dir}...")
            try:
                run_cmd(["git", "remote", "set-url", "origin", auth_url], cwd=target_dir)
                run_cmd(["git", "fetch", "--all"], cwd=target_dir)
                out = run_cmd(["git", "reset", "--hard", "origin/HEAD"], cwd=target_dir)
                logs.append(out.strip())
            except Exception as e:
                logs.append(f"[!] Aviso no sync com token ({e}). Tentando fallback anonimo publico...")
                run_cmd(["git", "remote", "set-url", "origin", repo_url.strip()], cwd=target_dir)
                run_cmd(["git", "fetch", "--all"], cwd=target_dir)
                out = run_cmd(["git", "reset", "--hard", "origin/HEAD"], cwd=target_dir)
                logs.append(out.strip())
        elif "antigravity/demo-showcase" not in repo_url:
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir)
            logs.append(f"[*] Clonando repositorio {repo_url} em {target_dir}...")
            try:
                out = run_cmd(["git", "clone", "--depth", "1", auth_url, target_dir])
                logs.append(out.strip())
            except Exception as e:
                logs.append(f"[!] Falha no clone autenticado ({e}). Tentando clone publico anonimo...")
                out = run_cmd(["git", "clone", "--depth", "1", repo_url.strip(), target_dir])
                logs.append(out.strip())

        commit_meta = get_git_commit_metadata(target_dir)
        logs.append(
            f"[+] Commit ativo: {commit_meta['shortHash']} — \"{commit_meta['message']}\" ({commit_meta['author']})"
        )

        # 1.5. Provisionamento Automático de Banco de Dados 1-Clique (se solicitado)
        bound_db_slug = existing.get("databaseSlug") if existing else None
        if create_database:
            try:
                import database_manager as db_mgr
                logs.append(f"[*] Provisionando banco de dados 1-Clique ({database_engine.upper()}) para o projeto...")
                sql_file_to_run = ""
                if initial_sql_file:
                    candidate = os.path.join(target_dir, initial_sql_file.lstrip("/\\"))
                    if os.path.exists(candidate):
                        sql_file_to_run = candidate
                        logs.append(f"[*] Encontrado script SQL no repositório: {initial_sql_file}")
                elif not initial_sql:
                    for candidate_name in ("schema.sql", "database.sql", "banco.sql", "dump.sql", "init.sql", "install.sql"):
                        candidate = os.path.join(target_dir, candidate_name)
                        if os.path.exists(candidate):
                            sql_file_to_run = candidate
                            logs.append(f"[*] Auto-detectado script SQL no repositório: {candidate_name}")
                            break

                db_res = db_mgr.create_project_database(
                    project_slug=clean_slug,
                    engine=database_engine,
                    initial_sql=initial_sql,
                    initial_sql_file=sql_file_to_run,
                    custom_name=f"Banco {effective_name}",
                )
                created_db = db_res["database"]
                bound_db_slug = created_db["slug"]
                logs.append(f"[+] Banco de dados provisionado: {created_db['dbName']} ({created_db['engineLabel']})")

                db_snippet = created_db.get("envSnippet", "")
                if db_snippet:
                    if effective_env_text:
                        effective_env_text = effective_env_text.strip() + "\n\n# Banco 1-Clique A.C.O.\n" + db_snippet
                    else:
                        effective_env_text = "# Banco 1-Clique A.C.O.\n" + db_snippet
                    logs.append("[+] DATABASE_URL e credenciais injetadas no .env")

                if db_res.get("sqlImport") and db_res["sqlImport"].get("ok"):
                    logs.append(f"[+] {db_res['sqlImport']['message']}")
                elif db_res.get("sqlImport") and not db_res["sqlImport"].get("ok"):
                    logs.append(f"[!] Aviso no SQL: {db_res['sqlImport'].get('error')}")
            except Exception as e:
                logs.append(f"[!] Erro no provisionamento do banco 1-clique: {e}")

        # 2. Escrever Variaveis de Ambiente (.env / .aco.env)
        aco_env_path = write_project_env_files(target_dir, effective_env_text)
        env_dict = parse_env_text(effective_env_text)
        if env_dict:
            logs.append(f"[+] {len(env_dict)} variavel(is) de ambiente injetada(s) no projeto.")

        resolved_type = detect_project_type(target_dir, project_type)
        work_dir = target_dir if resolved_type == "fullstack" else find_effective_project_root(target_dir)
        logs.append(f"[+] Arquitetura detectada: {resolved_type.upper()} | Raiz: {work_dir}")

        domain = effective_custom_domain or f"{clean_slug}.{VM_IP}.sslip.io"
        public_url = f"https://{domain}"
        port = None
        service_name = f"app-{clean_slug}"

        # 3. Build por Arquitetura
        if resolved_type == "static":
            static_root = work_dir
            for sub in ("public", "dist", "build", "docs"):
                if not os.path.exists(os.path.join(static_root, "index.html")) and os.path.exists(
                    os.path.join(work_dir, sub, "index.html")
                ):
                    static_root = os.path.join(work_dir, sub)
                    break

            caddy_conf = f"""{domain} {{
    root * {static_root}
    encode gzip
    file_server
}}
"""

        elif resolved_type == "react-vite":
            logs.append("[*] Instalando pacotes NPM do Frontend (com Swap protegida)...")
            build_env = {"NODE_OPTIONS": "--max-old-space-size=1024", "CI": "false", **env_dict}
            run_cmd(["npm", "install", "--no-audit", "--no-fund"], cwd=work_dir, env=build_env, timeout=420)
            logs.append("[*] Compilando bundle de producao (npm run build)...")
            run_cmd(["npm", "run", "build"], cwd=work_dir, env=build_env, timeout=420)

            dist_dir = os.path.join(work_dir, "dist")
            if not os.path.isdir(dist_dir):
                dist_dir = os.path.join(work_dir, "build")
            if not os.path.isdir(dist_dir):
                dist_dir = work_dir

            nm_path = os.path.join(work_dir, "node_modules")
            if os.path.isdir(nm_path):
                nm_bytes = get_directory_size_bytes(nm_path)
                shutil.rmtree(nm_path, ignore_errors=True)
                logs.append(
                    f"[+] Otimizacao de Disco: node_modules ({format_bytes_human(nm_bytes)}) removida apos gerar dist/!"
                )

            caddy_conf = f"""{domain} {{
    root * {dist_dir}
    encode gzip
    try_files {{path}} /index.html
    file_server
}}
"""

        elif resolved_type == "fullstack":
            fe_dir = os.path.join(target_dir, "frontend")
            be_dir = (
                os.path.join(target_dir, "backend")
                if os.path.isdir(os.path.join(target_dir, "backend"))
                else os.path.join(target_dir, "server")
            )
            logs.append("[*] [Full-Stack 1/2] Compilando camada /frontend...")
            build_env = {"NODE_OPTIONS": "--max-old-space-size=1024", "CI": "false", **env_dict}
            run_cmd(["npm", "install", "--no-audit", "--no-fund"], cwd=fe_dir, env=build_env, timeout=420)
            run_cmd(["npm", "run", "build"], cwd=fe_dir, env=build_env, timeout=420)

            fe_dist = os.path.join(fe_dir, "dist")
            if not os.path.isdir(fe_dist):
                fe_dist = os.path.join(fe_dir, "build")

            nm_path = os.path.join(fe_dir, "node_modules")
            if os.path.isdir(nm_path):
                nm_bytes = get_directory_size_bytes(nm_path)
                shutil.rmtree(nm_path, ignore_errors=True)
                logs.append(f"[+] Frontend node_modules ({format_bytes_human(nm_bytes)}) limpa com sucesso.")

            port = allocate_port(projects, clean_slug)
            logs.append(f"[*] [Full-Stack 2/2] Configurando camada /backend na porta {port}...")
            _setup_backend_systemd_service(
                service_name=service_name,
                clean_slug=clean_slug,
                backend_dir=be_dir,
                port=port,
                aco_env_path=aco_env_path,
                start_command=effective_start_cmd,
                logs=logs,
            )

            caddy_conf = f"""{domain} {{
    encode gzip

    handle /api/* {{
        reverse_proxy 127.0.0.1:{port}
    }}

    handle {{
        root * {fe_dist}
        try_files {{path}} /index.html
        file_server
    }}
}}
"""

        elif resolved_type == "php":
            # 1. Composer install se existir composer.json
            composer_json = os.path.join(work_dir, "composer.json")
            if os.path.exists(composer_json):
                logs.append("[*] Executando composer install para dependencias PHP...")
                try:
                    out = run_cmd(["composer", "install", "--no-interaction", "--prefer-dist", "--optimize-autoloader", "--no-dev"], cwd=work_dir, timeout=300)
                    logs.append(out.strip()[-500:])
                except Exception as e:
                    logs.append(f"[!] Aviso no composer install: {e}")

            # 2. Determinar pasta raiz do site (public/ se existir, senao raiz)
            public_dir = os.path.join(work_dir, "public")
            if os.path.isdir(public_dir) and (os.path.exists(os.path.join(public_dir, "index.php")) or os.path.exists(os.path.join(public_dir, "index.html"))):
                php_root = public_dir
            else:
                php_root = work_dir

            # 3. Detectar socket UNIX do PHP-FPM
            php_sock = find_php_fpm_socket()
            logs.append(f"[+] PHP-FPM vinculado via socket: {php_sock} (DocumentRoot: {php_root})")

            caddy_conf = f"""{domain} {{
    encode gzip
    root * {php_root}
    php_fastcgi unix/{php_sock}
    file_server
}}
"""

        elif resolved_type in ("node", "python"):
            port = allocate_port(projects, clean_slug)
            _setup_backend_systemd_service(
                service_name=service_name,
                clean_slug=clean_slug,
                backend_dir=work_dir,
                port=port,
                aco_env_path=aco_env_path,
                start_command=effective_start_cmd,
                logs=logs,
            )
            caddy_conf = f"""{domain} {{
    encode gzip
    reverse_proxy 127.0.0.1:{port}
}}
"""
        else:
            raise ValueError(f"Tipo de projeto nao suportado: {resolved_type}")

        # 4. Configurar Caddy e recarregar
        caddy_file = os.path.join(CADDY_SITES_DIR, f"{clean_slug}.caddy")
        with open(caddy_file, "w", encoding="utf-8") as f:
            f.write(caddy_conf)

        run_cmd(["sudo", "chmod", "-R", "755", target_dir])
        run_cmd(["sudo", "systemctl", "reload", "caddy"])

        # 4.1. Configurar tarefas Cron (se informado na requisicao ou se existir .cron no repositorio)
        effective_cron_cmd = cron_command.strip()
        effective_cron_sched = cron_schedule.strip() or "* * * * *"
        if not effective_cron_cmd:
            repo_cron = os.path.join(target_dir, ".cron")
            if not os.path.exists(repo_cron):
                repo_cron = os.path.join(target_dir, "crontab")
            if os.path.exists(repo_cron):
                try:
                    with open(repo_cron, "r", encoding="utf-8") as cf:
                        for line in cf:
                            line = line.strip()
                            if line and not line.startswith("#"):
                                parts = line.split(maxsplit=5)
                                if len(parts) >= 6:
                                    effective_cron_sched = " ".join(parts[:5])
                                    effective_cron_cmd = parts[5]
                                else:
                                    effective_cron_cmd = line
                                break
                except Exception:
                    pass

        if effective_cron_cmd:
            update_project_cron(clean_slug, effective_cron_sched, effective_cron_cmd, enabled=True)
            logs.append(f"[+] Tarefa Cron ativada: [{effective_cron_sched}] {effective_cron_cmd}")

        # 5. Configurar Webhook no GitHub se autoDeploy estiver ativo
        webhook_status = "Desativado"
        if effective_auto_deploy:
            webhook_status = ensure_github_webhook(repo_url, clean_slug, webhook_secret, github_token)
            logs.append(f"[+] Auto-Deploy: {webhook_status}")

        duration_s = round(time.time() - start_ts, 1)
        final_bytes = get_directory_size_bytes(target_dir)
        final_human = format_bytes_human(final_bytes)
        logs.append(f"[+] Espaco ocupado em disco: {final_human} | Tempo de deploy: {duration_s}s")
        logs.append(f"[SUCESSO] Aplicacao online em {public_url}")

        # Garantir permissao compartilhada final para PHP/Caddy (www-data) e A.C.O. (ubuntu)
        try:
            run_cmd(["sudo", "chown", "-R", "ubuntu:www-data", target_dir])
            run_cmd(["sudo", "chmod", "-R", "u+rwX,g+rwX", target_dir])
        except Exception:
            pass

        deploy_entry = {
            "id": f"dep-{int(time.time())}",
            "commitHash": commit_meta["shortHash"],
            "commitMessage": commit_meta["message"],
            "commitAuthor": commit_meta["author"],
            "trigger": trigger,
            "status": "SUCCESS",
            "timestamp": now_iso,
            "durationSeconds": duration_s,
            "log": "\n".join(logs)[-4000:],
        }
        history.insert(0, deploy_entry)

        record = {
            "name": effective_name,
            "slug": clean_slug,
            "customDomain": effective_custom_domain,
            "gitUrl": repo_url.strip(),
            "repoUrl": repo_url.strip(),
            "projectType": resolved_type,
            "branch": branch,
            "startCommand": effective_start_cmd,
            "domain": domain,
            "url": public_url,
            "port": port,
            "workDir": work_dir,
            "autoDeploy": effective_auto_deploy,
            "webhookSecret": webhook_secret,
            "webhookStatus": webhook_status,
            "lastCommitShortHash": commit_meta["shortHash"],
            "lastCommitHash": commit_meta["shortHash"],
            "lastCommitFullHash": commit_meta["fullHash"],
            "lastCommitMessage": commit_meta["message"],
            "lastCommitAuthor": commit_meta["author"],
            "envVarsText": effective_env_text,
            "databaseSlug": bound_db_slug,
            "diskBytes": final_bytes,
            "diskMB": round(final_bytes / (1024 * 1024), 2),
            "diskFormatted": final_human,
            "updatedAt": now_iso,
            "status": "running",
            "lastBuildLog": "\n".join(logs)[-4000:],
            "deploymentsHistory": history[:20],
        }

        projects = [p for p in projects if p.get("slug") != clean_slug]
        projects.insert(0, record)
        save_projects(projects)
        return load_projects()[0]

    except Exception as e:
        duration_s = round(time.time() - start_ts, 1)
        logs.append(f"[ERRO FATAL] {e}")
        if existing:
            fail_entry = {
                "id": f"dep-{int(time.time())}",
                "commitHash": existing.get("lastCommitShortHash", "erro"),
                "commitMessage": f"Falha no deploy ({trigger})",
                "commitAuthor": "Sistema",
                "trigger": trigger,
                "status": "FAILED",
                "timestamp": now_iso,
                "durationSeconds": duration_s,
                "log": "\n".join(logs)[-4000:],
            }
            history.insert(0, fail_entry)
            existing["deploymentsHistory"] = history[:20]
            existing["lastBuildLog"] = "\n".join(logs)[-4000:]
            save_projects(projects)
        raise


def update_project_settings(
    slug: str,
    env_vars_text: str | None = None,
    auto_deploy: bool | None = None,
    start_command: str | None = None,
    redeploy: bool = False,
    github_token: str = "",
    database_slug: str | None = None,
) -> dict[str, Any]:
    """Atualiza variaveis .env, configuracao de Auto-Deploy ou comando de inicializacao de um projeto."""
    clean_slug = sanitize_slug(slug)
    projects = load_projects()
    target = next((p for p in projects if p.get("slug") == clean_slug), None)
    if not target:
        raise ValueError(f"Projeto '{clean_slug}' não encontrado.")

    if env_vars_text is not None:
        target["envVarsText"] = env_vars_text
        target_dir = os.path.join(PROJECTS_ROOT, clean_slug)
        if os.path.exists(target_dir):
            write_project_env_files(target_dir, env_vars_text)

    if auto_deploy is not None:
        target["autoDeploy"] = bool(auto_deploy)

    if start_command is not None:
        target["startCommand"] = start_command.strip()

    if database_slug is not None:
        target["databaseSlug"] = database_slug.strip()

    save_projects(projects)

    if redeploy:
        return deploy_project(
            slug=clean_slug,
            repo_url=target["repoUrl"],
            project_type=target.get("projectType", "auto"),
            start_command=target.get("startCommand", ""),
            env_vars_text=target.get("envVarsText", ""),
            auto_deploy=target.get("autoDeploy", True),
            trigger="env-update",
            github_token=github_token,
        )

    # Se for servico backend, reiniciar systemd para recarregar o .aco.env imediatamente
    if target.get("port") and platform.system() == "Linux":
        try:
            run_cmd(["sudo", "systemctl", "restart", f"app-{clean_slug}"])
        except Exception:
            pass

    return next((p for p in load_projects() if p.get("slug") == clean_slug), target)


def control_project_service(slug: str, action: str) -> dict[str, Any]:
    """Executa start, stop ou restart no servico de um projeto (systemd ou caddy)."""
    clean_slug = sanitize_slug(slug)
    act = action.strip().lower()
    if act not in ("start", "stop", "restart"):
        raise ValueError(f"Ação inválida: {act}")

    projects = load_projects()
    target = next((p for p in projects if p.get("slug") == clean_slug), None)
    if not target:
        raise ValueError(f"Projeto '{clean_slug}' não encontrado.")

    if target.get("port") and platform.system() == "Linux":
        run_cmd(["sudo", "systemctl", act, f"app-{clean_slug}"])
    elif platform.system() == "Linux":
        # Para projetos estaticos servidos pelo Caddy
        if act == "restart":
            run_cmd(["sudo", "systemctl", "reload", "caddy"])
        elif act == "stop":
            # Renomeia temporariamente o arquivo .caddy para desativar rota
            caddy_file = os.path.join(CADDY_SITES_DIR, f"{clean_slug}.caddy")
            disabled_file = os.path.join(CADDY_SITES_DIR, f"{clean_slug}.caddy.disabled")
            if os.path.exists(caddy_file):
                os.rename(caddy_file, disabled_file)
                run_cmd(["sudo", "systemctl", "reload", "caddy"])
        elif act == "start":
            caddy_file = os.path.join(CADDY_SITES_DIR, f"{clean_slug}.caddy")
            disabled_file = os.path.join(CADDY_SITES_DIR, f"{clean_slug}.caddy.disabled")
            if os.path.exists(disabled_file):
                os.rename(disabled_file, caddy_file)
                run_cmd(["sudo", "systemctl", "reload", "caddy"])

    return next((p for p in load_projects() if p.get("slug") == clean_slug), target)


def get_project_runtime_logs(slug: str, lines: int = 80) -> str:
    """Retorna os logs de execucao em tempo real (journalctl) para projetos com backend ou log de acesso."""
    clean_slug = sanitize_slug(slug)
    projects = load_projects()
    target = next((p for p in projects if p.get("slug") == clean_slug), None)
    if not target:
        raise ValueError(f"Projeto '{clean_slug}' não encontrado.")

    if target.get("port") and platform.system() == "Linux":
        try:
            out = run_cmd(["journalctl", "-u", f"app-{clean_slug}", "-n", str(lines), "--no-pager"])
            return out or "Sem logs recentes no systemd journal."
        except Exception as e:
            return f"Erro ao ler journalctl: {e}"

    return (
        f"Projeto '{clean_slug}' ({target.get('projectType')}) é servido diretamente como bundle estático de alta performance pelo Caddy Reverse Proxy.\n"
        f"Diretório: /var/www/projects/{clean_slug}\n"
        f"URL Pública: {target.get('url')}\n\n"
        f"--- Último Log de Build ---\n{target.get('lastBuildLog', '')}"
    )


def check_and_autodeploy_all(github_token: str = "") -> list[dict[str, Any]]:
    """
    Verifica todos os projetos com autoDeploy=True; se o commit HEAD no GitHub mudou,
    executa o deploy automaticamente e registra no historico!
    """
    projects = load_projects()
    triggered = []
    for proj in projects:
        if not proj.get("autoDeploy", True):
            continue
        repo_url = proj.get("repoUrl", "")
        if not repo_url or "antigravity/demo-showcase" in repo_url:
            continue

        remote_hash = check_remote_commit_hash(repo_url, github_token)
        local_hash = proj.get("lastCommitFullHash", "")
        if remote_hash and local_hash and remote_hash != local_hash:
            try:
                updated = deploy_project(
                    slug=proj["slug"],
                    repo_url=repo_url,
                    project_type=proj.get("projectType", "auto"),
                    start_command=proj.get("startCommand", ""),
                    env_vars_text=proj.get("envVarsText", ""),
                    auto_deploy=True,
                    trigger="auto-watcher",
                    github_token=github_token,
                )
                triggered.append({"slug": proj["slug"], "newCommit": remote_hash[:7], "status": "SUCCESS", "project": updated})
            except Exception as e:
                triggered.append({"slug": proj["slug"], "newCommit": remote_hash[:7], "status": "FAILED", "error": str(e)})
    return triggered


def remove_project(slug: str) -> dict[str, Any]:
    """Remove um projeto publicado, encerra seu servico systemd e limpa a rota no Caddy com sudo."""
    clean_slug = sanitize_slug(slug)
    projects = load_projects()
    service_name = f"app-{clean_slug}"

    # 1. Parar e remover servico systemd se existir
    try:
        run_cmd(["sudo", "systemctl", "stop", service_name])
        run_cmd(["sudo", "rm", "-f", f"/etc/systemd/system/{service_name}.service"])
        run_cmd(["sudo", "systemctl", "daemon-reload"])
    except Exception:
        pass

    # 2. Remover arquivo de rota Caddy com sudo
    caddy_file = os.path.join(CADDY_SITES_DIR, f"{clean_slug}.caddy")
    try:
        subprocess.run(["sudo", "rm", "-f", caddy_file], check=False)
        subprocess.run(["sudo", "rm", "-f", f"{caddy_file}.disabled"], check=False)
        run_cmd(["sudo", "systemctl", "reload", "caddy"])
    except Exception:
        pass

    # 3. Remover tarefas Cron associadas
    for cf in (
        os.path.join(ACO_CRON_DIR, f"aco-{clean_slug}"),
        os.path.join(ACO_CRON_DIR, f"aco-project-{clean_slug}"),
    ):
        subprocess.run(["sudo", "rm", "-f", cf], check=False)

    # 4. Remover diretorio do projeto com sudo
    target_dir = os.path.join(PROJECTS_ROOT, clean_slug)
    if os.path.exists(target_dir):
        subprocess.run(["sudo", "rm", "-rf", target_dir], check=False)

    # 5. Salvar lista limpa no deployed_projects.json
    projects = [p for p in projects if p.get("slug") != clean_slug]
    save_projects(projects)
    return {"removed": clean_slug, "remaining": len(projects)}


def rename_project_slug(old_slug: str, new_slug: str, custom_domain: str = "") -> dict[str, Any]:
    """Altera instantaneamente o subdominio HTTPS ou dominio customizado de um projeto ja publicado."""
    clean_old = sanitize_slug(old_slug)
    clean_new = sanitize_slug(new_slug)
    clean_custom = (custom_domain or "").strip().lower()

    projects = load_projects()
    target_proj = next((p for p in projects if p.get("slug") == clean_old), None)
    if not target_proj:
        raise ValueError(f"Projeto '{clean_old}' não encontrado.")

    if clean_old != clean_new and any(p.get("slug") == clean_new for p in projects):
        raise ValueError(f"Já existe outro projeto usando o subdomínio '{clean_new}'.")

    old_domain = target_proj.get("domain") or f"{clean_old}.{VM_IP}.sslip.io"
    new_domain = clean_custom or f"{clean_new}.{VM_IP}.sslip.io"
    new_url = f"https://{new_domain}"

    old_caddy_file = os.path.join(CADDY_SITES_DIR, f"{clean_old}.caddy")
    new_caddy_file = os.path.join(CADDY_SITES_DIR, f"{clean_new}.caddy")

    if not os.path.exists(old_caddy_file):
        raise RuntimeError(f"Arquivo de rota Caddy não encontrado para '{clean_old}'.")

    with open(old_caddy_file, "r", encoding="utf-8") as f:
        caddy_content = f.read()

    updated_caddy = caddy_content.replace(old_domain, new_domain, 1)
    with open(new_caddy_file, "w", encoding="utf-8") as f:
        f.write(updated_caddy)

    if old_caddy_file != new_caddy_file and os.path.exists(old_caddy_file):
        os.remove(old_caddy_file)
    run_cmd(["sudo", "systemctl", "reload", "caddy"])

    now_iso = datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(timespec="seconds")
    target_proj["slug"] = clean_new
    target_proj["customDomain"] = clean_custom
    target_proj["domain"] = new_domain
    target_proj["url"] = new_url
    target_proj["updatedAt"] = now_iso
    target_proj["lastBuildLog"] = (
        target_proj.get("lastBuildLog", "")
        + f"\n[{now_iso}] Endereço HTTPS alterado de https://{old_domain} para {new_url}"
    )[-4000:]

    save_projects(projects)
    return target_proj
