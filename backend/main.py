"""
Backend FastAPI — A.C.O. v3.0 (Antigravity Cloud Orchestrator — Coolify Edition)
Protegido com Autenticacao Zero-Trust via Google Sign-In (exclusivo williamdevide@gmail.com):
- Telemetria de Disco e Memoria RAM por projeto + plataforma A.C.O. Core
- Auto-Deploy Hibrido: Webhook HMAC do GitHub + Background Git Commit Watcher (a cada 60s)
- Historico completo de Deploys por projeto + Logs de Runtime (journalctl)
- Gestao de Variaveis de Ambiente (.env) por projeto + Controles Start/Stop/Restart
- Provisionamento 1-Clique de Bancos de Dados (SQLite, PostgreSQL, MySQL/MariaDB, Redis)
"""

import asyncio
import base64
from contextlib import asynccontextmanager
import hashlib
import hmac
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXECUTION_DIR = os.path.join(BASE_DIR, "execution")
if EXECUTION_DIR not in sys.path:
    sys.path.insert(0, EXECUTION_DIR)

import database_manager as db_mgr  # noqa: E402
import deploy_project as deployer  # noqa: E402
import oci_arm_hunter as arm_hunter  # noqa: E402

_VERIFIED_TOKEN_CACHE: dict[str, dict[str, Any]] = {}
_LAST_WATCHER_CHECK: dict[str, Any] = {"lastRunAt": None, "triggered": []}


def load_env_file() -> dict[str, str]:
    """Le variaveis do arquivo .env na raiz do projeto, removendo aspas externas."""
    env_path = os.path.join(BASE_DIR, ".env")
    values: dict[str, str] = {}
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                v_clean = v.strip().rstrip(",").strip().strip('"').strip("'")
                values[k.strip()] = v_clean
    return values


async def autodeploy_watcher_loop():
    """Loop assincrono em background que verifica novos commits no GitHub a cada 60 segundos."""
    await asyncio.sleep(10)
    while True:
        try:
            env_vars = load_env_file()
            token = env_vars.get("GITHUB_TOKEN", "").strip()
            triggered = await asyncio.to_thread(deployer.check_and_autodeploy_all, token)
            _LAST_WATCHER_CHECK["lastRunAt"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
            if triggered:
                _LAST_WATCHER_CHECK["triggered"] = (triggered + _LAST_WATCHER_CHECK.get("triggered", []))[:20]
        except Exception as e:
            print(f"[AutoDeploy Watcher] Aviso: {e}", flush=True)
        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    watcher_task = asyncio.create_task(autodeploy_watcher_loop())
    yield
    watcher_task.cancel()


def decode_jwt_payload(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Formato de token JWT invalido.")
    payload_b64 = parts[1]
    pad = "=" * ((4 - len(payload_b64) % 4) % 4)
    raw = base64.urlsafe_b64decode(payload_b64 + pad).decode("utf-8")
    return json.loads(raw)


def verify_admin_user(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    """
    Dependency Zero-Trust:
    Valida token JWT do Firebase/Google e exige email_verified == True e email == williamdevide@gmail.com.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Não autenticado. Faça login com sua conta Google autorizada.",
        )

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Token de autenticação vazio.")

    env_vars = load_env_file()
    firebase_api_key = env_vars.get("FIREBASE_API_KEY", "")
    firebase_project_id = env_vars.get("FIREBASE_PROJECT_ID", "antigravityvmoracle")
    allowed_email = env_vars.get("ALLOWED_ADMIN_EMAIL", "williamdevide@gmail.com").strip().lower()

    now = time.time()
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

    cached = _VERIFIED_TOKEN_CACHE.get(token_hash)
    if cached and cached.get("expires_at", 0) > now:
        return cached["user"]

    try:
        claims = decode_jwt_payload(token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token JWT inválido: {e}") from e

    aud = claims.get("aud", "")
    iss = claims.get("iss", "")
    exp = float(claims.get("exp", 0))

    if exp <= now:
        raise HTTPException(status_code=401, detail="Sessão expirada. Faça login novamente com o Google.")

    if firebase_project_id and (
        aud != firebase_project_id or iss != f"https://securetoken.google.com/{firebase_project_id}"
    ):
        raise HTTPException(
            status_code=401,
            detail="Token emitido para um projeto Firebase diferente do autorizado.",
        )

    lookup_url = f"https://identitytoolkit.googleapis.com/v1/accounts:lookup?key={firebase_api_key}"
    req_body = json.dumps({"idToken": token}).encode("utf-8")
    req = urllib.request.Request(
        lookup_url,
        data=req_body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            lookup_data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise HTTPException(
            status_code=401,
            detail=f"Token rejeitado pelo Google Identity Toolkit (HTTP {e.code}).",
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Erro ao validar token junto ao Google: {e}",
        ) from e

    users = lookup_data.get("users", [])
    if not users:
        raise HTTPException(status_code=401, detail="Nenhum usuário encontrado para o token informado.")

    google_user = users[0]
    email = (google_user.get("email") or "").strip().lower()
    email_verified = bool(google_user.get("emailVerified", False))

    if not email_verified:
        raise HTTPException(status_code=403, detail="O e-mail da conta Google não está verificado.")

    if email != allowed_email:
        raise HTTPException(
            status_code=403,
            detail=f"ACESSO NEGADO: A conta '{email}' não possui permissão para administrar esta VM. Exclusivo para {allowed_email}.",
        )

    user_info = {
        "uid": google_user.get("localId"),
        "email": email,
        "displayName": google_user.get("displayName") or "William Devide",
        "photoUrl": google_user.get("photoUrl") or "",
        "emailVerified": email_verified,
    }

    _VERIFIED_TOKEN_CACHE[token_hash] = {
        "user": user_info,
        "expires_at": min(exp, now + 300),
    }
    return user_info


app = FastAPI(
    title="A.C.O. v3.0 — Antigravity Cloud Orchestrator (Coolify Edition)",
    description="PaaS Self-Hosted com Auto-Deploy GitHub, Bancos de Dados 1-Clique e Telemetria por Projeto.",
    version="3.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class DeployRequest(BaseModel):
    name: str | None = Field(default=None, description="Nome amigavel do projeto")
    slug: str = Field(default="", description="Subdominio desejado (ex: meu-site)")
    customDomain: str = Field(default="", description="Dominio customizado opcional")
    gitUrl: str = Field(default="", description="URL do repositorio GitHub")
    repoUrl: str = Field(default="", description="Alias para URL do repositorio GitHub")
    projectType: str = Field(default="auto", description="auto, fullstack, react-vite, static, node, python, php")
    branch: str = Field(default="main", description="Branch Git")
    startCommand: str = Field(default="", description="Comando customizado de inicializacao (opcional)")
    envVarsText: str | None = Field(default=None, description="Conteudo .env opcional")
    autoDeploy: bool = Field(default=True, description="Ativar deteccao automatica de commits no GitHub")
    trigger: str = Field(default="manual", description="Origem do deploy")
    gitToken: str = Field(default="", description="Token pessoal opcional para repositorios privados de alunos")
    cronSchedule: str = Field(default="", description="Expressao cron opcional (ex: */5 * * * *)")
    cronCommand: str = Field(default="", description="Comando opcional a ser executado no cron")


class ProjectCronRequest(BaseModel):
    schedule: str = Field(default="* * * * *", description="Expressao crontab (ex: */5 * * * *)")
    command: str = Field(..., description="Comando shell/php a ser executado")
    enabled: bool = Field(default=True, description="Ativar ou desativar o agendamento no sistema")


class ProjectSettingsRequest(BaseModel):
    envVarsText: str | None = None
    autoDeploy: bool | None = None
    branch: str | None = None
    startCommand: str | None = None
    redeploy: bool = False


class ServiceControlRequest(BaseModel):
    action: str = Field(..., description="start, stop ou restart")


class ArmActionRequest(BaseModel):
    action: str = Field(..., description="trigger_once, start, stop ou restart")


class RenameSlugRequest(BaseModel):
    newSlug: str = Field(..., description="Novo subdominio HTTPS desejado para o projeto")
    customDomain: str = Field(default="", description="Dominio customizado opcional")


class CreateDatabaseRequest(BaseModel):
    name: str = Field(..., description="Identificador do banco de dados")
    engine: str = Field(default="sqlite", description="sqlite, postgresql, mysql ou redis")


def get_linux_memory_info() -> dict[str, Any]:
    mem_info: dict[str, int] = {}
    if os.path.exists("/proc/meminfo"):
        with open("/proc/meminfo", "r", encoding="utf-8") as f:
            for line in f:
                parts = line.split(":")
                if len(parts) == 2:
                    key = parts[0].strip()
                    val_kb = int(parts[1].strip().split()[0])
                    mem_info[key] = val_kb // 1024

        ram_total = mem_info.get("MemTotal", 951)
        ram_avail = mem_info.get("MemAvailable", 550)
        ram_used = max(0, ram_total - ram_avail)

        swap_total = mem_info.get("SwapTotal", 0)
        swap_free = mem_info.get("SwapFree", 0)
        swap_used = max(0, swap_total - swap_free)
    else:
        ram_total, ram_used, ram_avail = 951, 360, 591
        swap_total, swap_used, swap_free = 4096, 0, 4096

    return {
        "ramTotalMB": ram_total,
        "ramUsedMB": ram_used,
        "ramAvailableMB": ram_avail,
        "ramPercent": round((ram_used / ram_total) * 100, 1) if ram_total else 0,
        "swapTotalMB": swap_total,
        "swapUsedMB": swap_used,
        "swapFreeMB": swap_free,
        "swapPercent": round((swap_used / swap_total) * 100, 1) if swap_total else 0,
    }


def get_service_status(service_name: str) -> str:
    if platform.system() != "Linux":
        return "local-dev"
    try:
        res = subprocess.run(
            ["systemctl", "is-active", service_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
        )
        return res.stdout.strip() or "inactive"
    except Exception:
        return "unknown"


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": "aco-orchestrator-v3",
        "security": "google-zero-trust-enforced",
    }


@app.get("/api/auth/me")
def get_authenticated_admin(admin: dict[str, Any] = Depends(verify_admin_user)):
    return {"authenticated": True, "admin": admin}


@app.get("/api/system-status")
def system_status(_admin: dict[str, Any] = Depends(verify_admin_user)):
    """Retorna metricas globais da VM + telemetria dedicada da plataforma A.C.O. Core."""
    env_vars = load_env_file()
    vm_ip = env_vars.get("OCI_VM_IP", "147.15.2.73")
    mem = get_linux_memory_info()

    total_b, used_b, free_b = shutil.disk_usage("/")
    disk = {
        "totalGB": round(total_b / (1024**3), 1),
        "usedGB": round(used_b / (1024**3), 1),
        "freeGB": round(free_b / (1024**3), 1),
        "percent": round((used_b / total_b) * 100, 1) if total_b else 0,
    }

    uptime_str = "Ativo"
    if os.path.exists("/proc/uptime"):
        try:
            with open("/proc/uptime", "r", encoding="utf-8") as f:
                secs = int(float(f.read().split()[0]))
                hours = secs // 3600
                mins = (secs % 3600) // 60
                uptime_str = f"{hours}h {mins}m"
        except Exception:
            pass

    load_avg = [0.0, 0.0, 0.0]
    if hasattr(os, "getloadavg"):
        try:
            load_avg = [round(x, 2) for x in os.getloadavg()]
        except Exception:
            pass

    aco_telemetry = deployer.get_aco_platform_telemetry()

    return {
        "vmName": env_vars.get("OCI_VM_NAME", "vm-wdk-amd-x86"),
        "publicIp": vm_ip,
        "dashboardDomain": f"https://{vm_ip}.sslip.io",
        "wildcardPattern": f"https://<projeto>.{vm_ip}.sslip.io",
        "os": "Canonical Ubuntu 26.04 LTS (x86_64)",
        "shape": "VM.Standard.E2.1.Micro (AMD EPYC)",
        "region": "sa-saopaulo-1 (São Paulo, Brasil)",
        "uptime": uptime_str,
        "loadAvg": load_avg,
        "memory": mem,
        "disk": disk,
        "acoPlatform": aco_telemetry,
        "autoDeployWatcher": _LAST_WATCHER_CHECK,
        "services": {
            "caddyProxy": get_service_status("caddy"),
            "armHunterDaemon": get_service_status("oci-arm-hunter"),
        },
    }


@app.get("/api/arm-hunter")
def get_arm_hunter_status(_admin: dict[str, Any] = Depends(verify_admin_user)):
    daemon_state = get_service_status("oci-arm-hunter")
    status_file = arm_hunter.STATUS_FILE
    data: dict[str, Any] = {
        "state": "IDLE",
        "attempts": 0,
        "targetShape": "VM.Standard.A1.Flex",
        "ocpus": 2.0,
        "memoryInGBs": 12.0,
        "bootVolumeSizeInGBs": 150,
        "accountLimitNote": "Teto real da conta na OCI: 2 OCPU / 12 GB RAM / 150 GB livres",
        "lastMessage": "Aguardando primeira execucao...",
        "recentLogs": [],
    }
    if os.path.exists(status_file):
        try:
            with open(status_file, "r", encoding="utf-8") as f:
                data.update(json.load(f))
        except Exception:
            pass

    data["systemdServiceStatus"] = daemon_state
    return data


@app.post("/api/arm-hunter/action")
def control_arm_hunter(req: ArmActionRequest, _admin: dict[str, Any] = Depends(verify_admin_user)):
    act = req.action.strip().lower()
    if act == "trigger_once":
        try:
            result = arm_hunter.run_hunter(once=True)
            return {"ok": True, "action": act, "status": result}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    if act in ("start", "stop", "restart"):
        if platform.system() == "Linux":
            subprocess.run(["sudo", "systemctl", act, "oci-arm-hunter"], check=False)
        return {"ok": True, "action": act, "systemdServiceStatus": get_service_status("oci-arm-hunter")}

    raise HTTPException(status_code=400, detail=f"Acao desconhecida: {act}")


@app.get("/api/overview")
def get_complete_overview(_admin: dict[str, Any] = Depends(verify_admin_user)):
    """Endpoint unificado estilo Coolify: retorna VM, Plataforma A.C.O., Projetos, Bancos e Caçador ARM."""
    sys_data = system_status(_admin)
    hunter_data = get_arm_hunter_status(_admin)
    projs = deployer.load_projects()
    dbs = db_mgr.load_databases()
    vm_ip = sys_data["publicIp"]
    mem = sys_data["memory"]
    disk = sys_data["disk"]

    return {
        "status": "success",
        "baseDomain": f"{vm_ip}.sslip.io",
        "vm": {
            "hostname": sys_data["vmName"],
            "ip": vm_ip,
            "os": sys_data["os"],
            "shape": sys_data["shape"],
            "uptime": sys_data["uptime"],
            "loadAvg": sys_data["loadAvg"],
            "memory": {
                "used": mem["ramUsedMB"],
                "total": mem["ramTotalMB"],
                "percent": mem["ramPercent"],
                "swapUsed": mem["swapUsedMB"],
                "swapTotal": mem["swapTotalMB"],
            },
            "disk": {
                "used": f"{disk['usedGB']}G",
                "total": f"{disk['totalGB']}G",
                "percent": f"{disk['percent']}%",
            },
        },
        "acoPlatform": sys_data["acoPlatform"],
        "hunter": {
            "service_active": hunter_data.get("systemdServiceStatus", "active"),
            "target_shape": f"{hunter_data.get('targetShape', 'VM.Standard.A1.Flex')} ({hunter_data.get('ocpus', 2)} OCPU / {hunter_data.get('memoryInGBs', 12)}GB RAM / {hunter_data.get('bootVolumeSizeInGBs', 150)}GB)",
            "attempts": hunter_data.get("attempts", 0),
            "last_check": hunter_data.get("lastCheck") or hunter_data.get("lastAttemptAt") or "Ativo 24/7",
            "last_message": hunter_data.get("lastMessage", "Monitorando disponibilidade em São Paulo..."),
            "recent_logs": hunter_data.get("recentLogs", []),
        },
        "projects": projs,
        "databases": dbs,
        "autoDeployWatcher": _LAST_WATCHER_CHECK,
    }


@app.post("/api/hunter/{endpoint}")
def control_hunter_legacy_route(endpoint: str, _admin: dict[str, Any] = Depends(verify_admin_user)):
    mapped = "trigger_once" if endpoint == "trigger-now" else endpoint
    return control_arm_hunter(ArmActionRequest(action=mapped), _admin)


@app.get("/api/github/repos")
def list_github_repos(username: str = "WilliamDevide", _admin: dict[str, Any] = Depends(verify_admin_user)):
    env_vars = load_env_file()
    token = env_vars.get("GITHUB_TOKEN", "").strip()
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "ACO-Coolify-Orchestrator",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
        url = "https://api.github.com/user/repos?sort=updated&per_page=40&affiliation=owner,collaborator"
    else:
        url = f"https://api.github.com/users/{username}/repos?sort=updated&per_page=40"

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw_repos = json.loads(resp.read().decode("utf-8"))
            repos = []
            for r in raw_repos:
                size_kb = int(r.get("size", 0) or 0)
                repo_bytes = size_kb * 1024
                repo_human = deployer.format_bytes_human(repo_bytes)
                lang = r.get("language") or "Web"

                if lang in ("TypeScript", "JavaScript", "Vue", "Svelte"):
                    est_bytes = int(repo_bytes * 1.35) + (2 * 1024 * 1024)
                    note = "SPA/Full-Stack: node_modules (~150 MB) é limpo após gerar o build estático"
                elif lang == "Python":
                    est_bytes = repo_bytes + (32 * 1024 * 1024)
                    note = "Python: inclui ambiente virtual (.venv) dedicado"
                else:
                    est_bytes = max(repo_bytes, 64 * 1024)
                    note = "Arquivos estáticos / código direto"

                repos.append({
                    "id": r.get("id"),
                    "name": r.get("name"),
                    "fullName": r.get("full_name"),
                    "htmlUrl": r.get("html_url"),
                    "cloneUrl": r.get("clone_url"),
                    "clone_url": r.get("clone_url"),
                    "private": r.get("private", False),
                    "language": lang,
                    "sizeKB": size_kb,
                    "size_kb": size_kb,
                    "repoSizeFormatted": repo_human,
                    "estimatedDiskBytes": est_bytes,
                    "estimatedDiskMB": round(est_bytes / (1024 * 1024), 2),
                    "estimatedDiskFormatted": f"~{deployer.format_bytes_human(est_bytes)}",
                    "diskNote": note,
                    "description": r.get("description") or "",
                    "defaultBranch": r.get("default_branch", "main"),
                    "default_branch": r.get("default_branch", "main"),
                    "updatedAt": r.get("updated_at"),
                })
            return {"status": "success", "authenticated": True, "repos": repos}
    except Exception as e:
        return {"status": "error", "authenticated": False, "error": str(e), "repos": []}


@app.get("/api/projects")
def get_deployed_projects(_admin: dict[str, Any] = Depends(verify_admin_user)):
    """Lista todos os projetos publicados com consumo real de RAM e Disco + Plataforma A.C.O."""
    projs = deployer.load_projects()
    aco_platform = deployer.get_aco_platform_telemetry()
    total_disk = sum(int(p.get("diskBytes", 0)) for p in projs)
    total_ram = sum(int(p.get("ramBytes", 0)) for p in projs)
    return {
        "status": "success",
        "acoPlatform": aco_platform,
        "projects": projs,
        "totalDiskBytes": total_disk,
        "totalDiskFormatted": deployer.format_bytes_human(total_disk),
        "totalRamBytes": total_ram,
        "totalRamFormatted": deployer.format_bytes_human(total_ram),
    }


@app.post("/api/projects/deploy")
def deploy_new_project(req: DeployRequest, _admin: dict[str, Any] = Depends(verify_admin_user)):
    env_vars = load_env_file()
    token = env_vars.get("GITHUB_TOKEN", "").strip()
    effective_slug = req.slug.strip() or (req.name or "").strip()
    effective_repo = req.gitUrl.strip() or req.repoUrl.strip()
    try:
        record = deployer.deploy_project(
            slug=effective_slug,
            repo_url=effective_repo,
            project_type=req.projectType,
            branch=req.branch or "main",
            start_command=req.startCommand,
            env_vars_text=req.envVarsText,
            auto_deploy=req.autoDeploy,
            trigger=req.trigger or "manual",
            github_token=token,
            name=req.name or effective_slug,
            custom_domain=req.customDomain,
            git_token=req.gitToken,
            cron_schedule=req.cronSchedule,
            cron_command=req.cronCommand,
        )
        return {"status": "success", "ok": True, "project": record, "log": record.get("lastBuildLog", "")}
    except Exception as e:
        return {"status": "error", "ok": False, "message": str(e), "log": str(e)}


@app.get("/api/projects/{slug}/cron")
def get_project_cron_endpoint(slug: str, _admin: dict[str, Any] = Depends(verify_admin_user)):
    try:
        info = deployer.get_project_cron(slug)
        return {"status": "success", "ok": True, "cron": info}
    except Exception as e:
        return {"status": "error", "ok": False, "message": str(e)}


@app.put("/api/projects/{slug}/cron")
def update_project_cron_endpoint(
    slug: str,
    req: ProjectCronRequest,
    _admin: dict[str, Any] = Depends(verify_admin_user),
):
    try:
        updated = deployer.update_project_cron(
            slug=slug,
            schedule=req.schedule,
            command=req.command,
            enabled=req.enabled,
        )
        return {"status": "success", "ok": True, "cron": updated}
    except Exception as e:
        return {"status": "error", "ok": False, "message": str(e)}


@app.post("/api/projects/{slug}/cron/run-now")
def run_project_cron_now_endpoint(slug: str, _admin: dict[str, Any] = Depends(verify_admin_user)):
    try:
        result = deployer.run_project_cron_now(slug)
        return {"status": "success", "ok": True, **result}
    except Exception as e:
        return {"status": "error", "ok": False, "message": str(e)}


@app.put("/api/projects/{slug}/settings")
def update_project_settings_endpoint(
    slug: str,
    req: ProjectSettingsRequest,
    _admin: dict[str, Any] = Depends(verify_admin_user),
):
    env_vars = load_env_file()
    token = env_vars.get("GITHUB_TOKEN", "").strip()
    try:
        updated = deployer.update_project_settings(
            slug=slug,
            env_vars_text=req.envVarsText,
            auto_deploy=req.autoDeploy,
            start_command=req.startCommand,
            redeploy=req.redeploy,
            github_token=token,
        )
        return {"status": "success", "ok": True, "project": updated}
    except Exception as e:
        return {"status": "error", "ok": False, "message": str(e)}


@app.post("/api/projects/{slug}/service")
def control_project_service_endpoint(
    slug: str,
    req: ServiceControlRequest,
    _admin: dict[str, Any] = Depends(verify_admin_user),
):
    try:
        updated = deployer.control_project_service(slug, req.action)
        return {"status": "success", "ok": True, "project": updated}
    except Exception as e:
        return {"status": "error", "ok": False, "message": str(e)}


@app.get("/api/projects/{slug}/logs")
def get_project_logs_endpoint(slug: str, lines: int = 100, _admin: dict[str, Any] = Depends(verify_admin_user)):
    try:
        logs = deployer.get_project_runtime_logs(slug, lines=lines)
        return {"status": "success", "ok": True, "slug": slug, "logs": logs, "runtimeLogs": logs}
    except Exception as e:
        return {"status": "error", "ok": False, "logs": str(e)}


@app.post("/api/projects/check-updates")
def force_check_git_updates(_admin: dict[str, Any] = Depends(verify_admin_user)):
    """Dispara imediatamente a verificacao de novos commits no GitHub em todos os projetos."""
    env_vars = load_env_file()
    token = env_vars.get("GITHUB_TOKEN", "").strip()
    try:
        triggered = deployer.check_and_autodeploy_all(token)
        _LAST_WATCHER_CHECK["lastRunAt"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        results = [{**item, "updated": item.get("status") == "SUCCESS"} for item in triggered]
        return {
            "status": "success",
            "ok": True,
            "triggered": triggered,
            "results": results,
            "checkedAt": _LAST_WATCHER_CHECK["lastRunAt"],
        }
    except Exception as e:
        return {"status": "error", "ok": False, "message": str(e), "results": []}


@app.post("/api/webhooks/github/{slug}")
async def github_webhook_receiver(
    slug: str,
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
    x_github_event: str | None = Header(default=None),
):
    """
    Endpoint publico assinado para receber Webhooks de push diretamente do GitHub.
    Valida a assinatura HMAC-SHA256 com o webhookSecret do projeto antes de iniciar o Auto-Deploy.
    """
    raw_body = await request.body()
    projects = deployer.load_projects()
    target = next((p for p in projects if p.get("slug") == slug), None)
    if not target:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")

    secret = target.get("webhookSecret", "")
    if secret:
        if not x_hub_signature_256 or not x_hub_signature_256.startswith("sha256="):
            raise HTTPException(status_code=401, detail="Assinatura HMAC do Webhook ausente.")
        expected = "sha256=" + hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, x_hub_signature_256):
            raise HTTPException(status_code=403, detail="Assinatura HMAC inválida.")

    if x_github_event == "ping":
        return {"ok": True, "message": "Webhook A.C.O. conectado com sucesso!"}

    if not target.get("autoDeploy", True):
        return {"ok": True, "skipped": "Auto-Deploy desativado para este projeto."}

    env_vars = load_env_file()
    token = env_vars.get("GITHUB_TOKEN", "").strip()

    updated = await asyncio.to_thread(
        deployer.deploy_project,
        slug=slug,
        repo_url=target["repoUrl"],
        project_type=target.get("projectType", "auto"),
        start_command=target.get("startCommand", ""),
        env_vars_text=target.get("envVarsText", ""),
        auto_deploy=True,
        trigger="webhook-github",
        github_token=token,
        name=target.get("name", slug),
        custom_domain=target.get("customDomain", ""),
    )
    return {"ok": True, "deployed": updated["slug"], "commit": updated.get("lastCommitShortHash")}


@app.delete("/api/projects/{slug}")
def delete_deployed_project(slug: str, _admin: dict[str, Any] = Depends(verify_admin_user)):
    try:
        res = deployer.remove_project(slug)
        return {"status": "success", "ok": True, **res}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/api/projects/{slug}/rename")
def rename_deployed_project(
    slug: str,
    req: RenameSlugRequest,
    _admin: dict[str, Any] = Depends(verify_admin_user),
):
    try:
        updated = deployer.rename_project_slug(slug, req.newSlug, req.customDomain)
        return {"status": "success", "ok": True, "project": updated}
    except Exception as e:
        return {"status": "error", "ok": False, "message": str(e)}


# ================= ENDPOINTS DE BANCOS DE DADOS 1-CLIQUE =================


@app.get("/api/databases")
def list_managed_databases(_admin: dict[str, Any] = Depends(verify_admin_user)):
    dbs = db_mgr.load_databases()
    total_disk = sum(int(d.get("diskBytes", 0)) for d in dbs)
    total_ram = sum(int(d.get("ramBytes", 0)) for d in dbs)
    return {
        "status": "success",
        "databases": dbs,
        "totalDiskFormatted": db_mgr.format_bytes_human(total_disk),
        "totalRamFormatted": db_mgr.format_bytes_human(total_ram),
    }


@app.post("/api/databases")
def create_managed_database(req: CreateDatabaseRequest, _admin: dict[str, Any] = Depends(verify_admin_user)):
    try:
        created = db_mgr.create_database(name=req.name, engine=req.engine)
        return {"status": "success", "ok": True, "database": created}
    except Exception as e:
        return {"status": "error", "ok": False, "message": str(e)}


@app.delete("/api/databases/{slug}")
def delete_managed_database(slug: str, _admin: dict[str, Any] = Depends(verify_admin_user)):
    try:
        res = db_mgr.delete_database(slug)
        return {"status": "success", "ok": True, **res}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/api/databases/{db_slug}/inject/{project_slug}")
def inject_database_into_project(
    db_slug: str,
    project_slug: str,
    _admin: dict[str, Any] = Depends(verify_admin_user),
):
    """Injeta automaticamente a DATABASE_URL e credenciais de um banco nas variaveis .env de um projeto."""
    dbs = db_mgr.load_databases()
    target_db = next((d for d in dbs if d.get("slug") == db_slug), None)
    if not target_db:
        return {"status": "error", "ok": False, "message": "Banco de dados não encontrado."}

    projects = deployer.load_projects()
    target_proj = next((p for p in projects if p.get("slug") == project_slug), None)
    if not target_proj:
        return {"status": "error", "ok": False, "message": "Projeto não encontrado."}

    existing_env = target_proj.get("envVarsText", "").strip()
    snippet = target_db.get("envSnippet", "")
    new_env = (existing_env + "\n\n# Banco Injetado pelo A.C.O. (" + db_slug + ")\n" + snippet).strip()

    env_vars = load_env_file()
    token = env_vars.get("GITHUB_TOKEN", "").strip()
    updated = deployer.update_project_settings(
        slug=project_slug,
        env_vars_text=new_env,
        redeploy=False,
        github_token=token,
    )
    return {
        "status": "success",
        "ok": True,
        "message": f"Credenciais de '{target_db['name']}' injetadas no .env de '{target_proj['name']}'!",
        "project": updated,
        "injectedDatabase": db_slug,
    }
