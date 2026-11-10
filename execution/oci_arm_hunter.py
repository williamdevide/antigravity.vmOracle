"""
Camada 3 (Execucao): Robo Cacador Deterministico de Instancia ARM (VM.Standard.A1.Flex)
Inspeciona automaticamente os Service Limits reais da conta via OCI Limits API e procura
vaga continuamente na regiao sa-saopaulo-1 para criar:
- Shape: VM.Standard.A1.Flex (Ampere A1 ARM)
- OCPUs: Maximo permitido na conta (2 OCPUs detectados em standard-a1-core-count)
- RAM: Maximo permitido na conta (12 GB detectados em standard-a1-memory-count)
- Boot Volume: 150 GB (200 GB limite total - 50 GB usados pela VM x86)
Compativel com Windows (local) e Linux (servico systemd 24/7 na VM x86).
"""

import argparse
import base64
import configparser
import datetime
import email.utils
import hashlib
import json
import os
import random
import time
import urllib.error
import urllib.parse
import urllib.request
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OCI_DIR = os.path.join(BASE_DIR, ".oci")
CONFIG_PATH = os.path.join(OCI_DIR, "config")
SSH_PUB_PATH = os.path.join(OCI_DIR, "ssh-key-2026-10-29.key.pub")
STATUS_FILE = os.path.join(BASE_DIR, "execution", "arm_hunter_status.json")
LOG_FILE = os.path.join(BASE_DIR, "execution", "arm_hunter.log")

# Parametros base da VM ARM (ajustados dinamicamente conforme limites da conta)
TARGET_DISPLAY_NAME = "vm-wdk-arm-ampere"
TARGET_SHAPE = "VM.Standard.A1.Flex"
DEFAULT_OCPUS = 2.0
DEFAULT_MEMORY_GB = 12.0
DEFAULT_BOOT_VOLUME_GB = 150
ACTIVE_SUBNET_ID = "ocid1.subnet.oc1.sa-saopaulo-1.aaaaaaaadyfff3qcokjs6jh7lp2d3evb3qtkzr54viwnb3dgcj2slq5uhz7q"


class CrossPlatformOCIClient:
    """Cliente OCI REST multiplataforma (Windows e Linux)."""

    def __init__(self, config_path: str = CONFIG_PATH, profile: str = "DEFAULT"):
        cfg = configparser.ConfigParser()
        cfg.read(config_path)
        d = cfg[profile]
        self.user = d["user"].strip()
        self.fingerprint = d["fingerprint"].strip()
        self.tenancy = d["tenancy"].strip()
        self.region = d["region"].strip()

        raw_key_file = d["key_file"].strip()
        local_fallback = os.path.join(OCI_DIR, "oci_api_key.pem")
        if os.path.exists(raw_key_file):
            self.key_file = raw_key_file
        elif os.path.exists(local_fallback):
            self.key_file = local_fallback
        else:
            raise FileNotFoundError(f"Chave privada OCI nao encontrada em {raw_key_file} nem em {local_fallback}")

        with open(self.key_file, "rb") as f:
            self.priv_key = serialization.load_pem_private_key(f.read(), password=None)

        self.key_id = f"{self.tenancy}/{self.user}/{self.fingerprint}"
        self.iaas_host = f"iaas.{self.region}.oraclecloud.com"
        self.identity_host = f"identity.{self.region}.oraclecloud.com"
        self.limits_host = f"limits.{self.region}.oci.oraclecloud.com"

    def request(self, method: str, host: str, path: str, body: dict | None = None):
        method_lower = method.lower()
        date_str = email.utils.formatdate(usegmt=True)
        headers = {"Date": date_str, "Host": host}
        signing_headers = ["(request-target)", "date", "host"]
        signing_lines = [
            f"(request-target): {method_lower} {path}",
            f"date: {date_str}",
            f"host: {host}",
        ]

        data_bytes = None
        if body is not None:
            data_bytes = json.dumps(body).encode("utf-8")
            sha256_b64 = base64.b64encode(hashlib.sha256(data_bytes).digest()).decode("ascii")
            content_len = str(len(data_bytes))
            headers["Content-Type"] = "application/json"
            headers["Content-Length"] = content_len
            headers["x-content-sha256"] = sha256_b64
            signing_headers.extend(["x-content-sha256", "content-type", "content-length"])
            signing_lines.extend([
                f"x-content-sha256: {sha256_b64}",
                "content-type: application/json",
                f"content-length: {content_len}",
            ])

        signing_str = "\n".join(signing_lines)
        signature = base64.b64encode(
            self.priv_key.sign(signing_str.encode("utf-8"), padding.PKCS1v15(), hashes.SHA256())
        ).decode("ascii")

        headers["Authorization"] = (
            f'Signature version="1",'
            f'keyId="{self.key_id}",'
            f'algorithm="rsa-sha256",'
            f'headers="{" ".join(signing_headers)}",'
            f'signature="{signature}"'
        )

        url = f"https://{host}{path}"
        req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method.upper())
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                raw = resp.read().decode("utf-8")
                return resp.status, (json.loads(raw) if raw else {})
        except urllib.error.HTTPError as e:
            err_raw = e.read().decode("utf-8", errors="replace")
            try:
                err_json = json.loads(err_raw)
            except Exception:
                err_json = {"message": err_raw, "code": str(e.code)}
            return e.code, err_json


def detect_account_arm_limits(client: CrossPlatformOCIClient, ad_name: str):
    """Consulta a API de Limits da OCI para determinar o maximo real de OCPU, RAM e Disco da conta."""
    ocpus = DEFAULT_OCPUS
    memory_gb = DEFAULT_MEMORY_GB
    boot_gb = DEFAULT_BOOT_VOLUME_GB

    try:
        c1, v1 = client.request(
            "GET",
            client.limits_host,
            f"/20190729/limitValues?compartmentId={client.tenancy}&serviceName=compute&name=standard-a1-core-count",
        )
        if c1 == 200 and isinstance(v1, list) and v1:
            val = float(v1[0].get("value", DEFAULT_OCPUS))
            if val > 0:
                ocpus = min(4.0, val)

        c2, v2 = client.request(
            "GET",
            client.limits_host,
            f"/20190729/limitValues?compartmentId={client.tenancy}&serviceName=compute&name=standard-a1-memory-count",
        )
        if c2 == 200 and isinstance(v2, list) and v2:
            val = float(v2[0].get("value", DEFAULT_MEMORY_GB))
            if val > 0:
                memory_gb = min(24.0, val)

        # Calcular espaco livre de Boot Volume dentro dos 200 GB Always Free
        c3, bvs = client.request(
            "GET",
            client.iaas_host,
            f"/20160918/bootVolumes?availabilityDomain={urllib.parse.quote(ad_name)}&compartmentId={client.tenancy}",
        )
        if c3 == 200 and isinstance(bvs, list):
            used_gb = sum(
                int(b.get("sizeInGBs", 0))
                for b in bvs
                if b.get("lifecycleState") not in ("TERMINATED", "TERMINATING")
            )
            avail_gb = max(50, 200 - used_gb)
            boot_gb = min(150, avail_gb)
    except Exception:
        pass

    return ocpus, memory_gb, boot_gb


def write_log_and_status(status_data: dict, log_line: str):
    """Persiste o estado atual em JSON e adiciona linha ao historico de log."""
    now_iso = datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(timespec="seconds")
    status_data["updatedAt"] = now_iso

    history = []
    if os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE, "r", encoding="utf-8") as f:
                old = json.load(f)
                history = old.get("recentLogs", [])
        except Exception:
            history = []

    entry = f"[{now_iso}] {log_line}"
    history.insert(0, entry)
    status_data["recentLogs"] = history[:40]

    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(status_data, f, indent=2, ensure_ascii=False)

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry + "\n")

    print(entry, flush=True)


def run_hunter(once: bool = False):
    client = CrossPlatformOCIClient()
    comp_id = client.tenancy
    iaas = client.iaas_host

    with open(SSH_PUB_PATH, "r", encoding="utf-8") as f:
        ssh_pub_key = f.read().strip()

    # 1. Descobrir Availability Domain
    _, ads = client.request("GET", client.identity_host, f"/20160918/availabilityDomains?compartmentId={comp_id}")
    ad_name = next((a["name"] for a in ads if "-AD-1" in a["name"]), ads[0]["name"])

    # 2. Detectar limites reais da conta (2 OCPU / 12 GB RAM / 150 GB Boot Volume)
    target_ocpus, target_memory_gb, target_boot_gb = detect_account_arm_limits(client, ad_name)

    # 3. Descobrir imagem Ubuntu ARM (aarch64) compativel com VM.Standard.A1.Flex
    query = urllib.parse.urlencode({
        "compartmentId": comp_id,
        "shape": TARGET_SHAPE,
        "operatingSystem": "Canonical Ubuntu",
        "sortBy": "TIMECREATED",
        "sortOrder": "DESC",
    })
    _, images = client.request("GET", iaas, f"/20160918/images?{query}")
    target_img = next(
        (img for img in images if "24.04" in img.get("displayName", "") and "aarch64" in img.get("displayName", "")),
        images[0] if images else None,
    )
    if not target_img:
        raise RuntimeError("Nenhuma imagem Canonical Ubuntu ARM (aarch64) encontrada na regiao.")

    image_id = target_img["id"]
    image_name = target_img["displayName"]

    attempts = 0
    if os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE, "r", encoding="utf-8") as f:
                attempts = int(json.load(f).get("attempts", 0))
        except Exception:
            attempts = 0

    while True:
        # Verificar se a VM ARM ja existe na conta
        status_code, instances = client.request("GET", iaas, f"/20160918/instances?compartmentId={comp_id}")
        if status_code == 200 and isinstance(instances, list):
            existing_arm = next(
                (
                    i for i in instances
                    if i.get("shape") == TARGET_SHAPE
                    and i.get("lifecycleState") not in ("TERMINATED", "TERMINATING")
                ),
                None,
            )
            if existing_arm:
                state_info = {
                    "state": "CAPTURED",
                    "attempts": attempts,
                    "targetShape": TARGET_SHAPE,
                    "ocpus": target_ocpus,
                    "memoryInGBs": target_memory_gb,
                    "bootVolumeSizeInGBs": target_boot_gb,
                    "accountLimitNote": f"Teto real da conta na OCI: {int(target_ocpus)} OCPU / {int(target_memory_gb)} GB RAM / {target_boot_gb} GB livres",
                    "availabilityDomain": ad_name,
                    "imageName": image_name,
                    "capturedInstanceId": existing_arm["id"],
                    "capturedDisplayName": existing_arm.get("displayName"),
                    "capturedLifecycleState": existing_arm.get("lifecycleState"),
                    "lastHttpStatus": 200,
                    "lastMessage": f"Instancia ARM ja provisionada ({existing_arm.get('lifecycleState')})!",
                }
                write_log_and_status(
                    state_info,
                    f"SUCESSO! Instancia ARM localizada na conta: {existing_arm['displayName']} ({existing_arm['id']})",
                )
                return state_info

        attempts += 1
        launch_payload = {
            "compartmentId": comp_id,
            "availabilityDomain": ad_name,
            "shape": TARGET_SHAPE,
            "displayName": TARGET_DISPLAY_NAME,
            "shapeConfig": {
                "ocpus": target_ocpus,
                "memoryInGBs": target_memory_gb,
            },
            "sourceDetails": {
                "sourceType": "image",
                "imageId": image_id,
                "bootVolumeSizeInGBs": target_boot_gb,
            },
            "createVnicDetails": {
                "subnetId": ACTIVE_SUBNET_ID,
                "assignPublicIp": True,
            },
            "metadata": {
                "ssh_authorized_keys": ssh_pub_key,
            },
        }

        http_code, resp = client.request("POST", iaas, "/20160918/instances", body=launch_payload)
        msg = resp.get("message", "") if isinstance(resp, dict) else str(resp)
        err_code = resp.get("code", "") if isinstance(resp, dict) else ""

        if http_code in (200, 201):
            inst_id = resp.get("id", "desconhecido")
            state_info = {
                "state": "CAPTURED",
                "attempts": attempts,
                "targetShape": TARGET_SHAPE,
                "ocpus": target_ocpus,
                "memoryInGBs": target_memory_gb,
                "bootVolumeSizeInGBs": target_boot_gb,
                "accountLimitNote": f"Teto real da conta na OCI: {int(target_ocpus)} OCPU / {int(target_memory_gb)} GB RAM / {target_boot_gb} GB livres",
                "availabilityDomain": ad_name,
                "imageName": image_name,
                "capturedInstanceId": inst_id,
                "lastHttpStatus": http_code,
                "lastMessage": "VM ARM criada com sucesso!",
            }
            write_log_and_status(state_info, f"Tentativa #{attempts}: [SUCESSO] VM ARM criada! ID: {inst_id}")
            return state_info

        if "Out of host capacity" in msg or err_code == "InternalError" or http_code == 500:
            short_msg = (
                f"Sem capacidade fisica de servidores ARM em Sao Paulo (Out of host capacity) "
                f"para {int(target_ocpus)} OCPU / {int(target_memory_gb)} GB RAM / {target_boot_gb} GB."
            )
            wait_secs = random.randint(65, 95)
        elif http_code == 429 or "TooManyRequests" in err_code:
            short_msg = "Rate limit da API Oracle (429 TooManyRequests) — ampliando intervalo de espera."
            wait_secs = random.randint(120, 180)
        else:
            short_msg = f"HTTP {http_code} ({err_code}): {msg[:160]}"
            wait_secs = random.randint(75, 110)

        state_info = {
            "state": "HUNTING" if not once else "IDLE_AFTER_SINGLE_CHECK",
            "attempts": attempts,
            "targetShape": TARGET_SHAPE,
            "ocpus": target_ocpus,
            "memoryInGBs": target_memory_gb,
            "bootVolumeSizeInGBs": target_boot_gb,
            "accountLimitNote": f"Teto real da conta na OCI: {int(target_ocpus)} OCPU / {int(target_memory_gb)} GB RAM / {target_boot_gb} GB livres",
            "availabilityDomain": ad_name,
            "imageName": image_name,
            "capturedInstanceId": None,
            "lastHttpStatus": http_code,
            "lastErrorCode": err_code,
            "lastMessage": short_msg,
            "nextRetrySeconds": wait_secs if not once else 0,
        }
        write_log_and_status(state_info, f"Tentativa #{attempts}: {short_msg}")

        if once:
            return state_info

        time.sleep(wait_secs)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Robo Cacador de VM ARM na Oracle Cloud")
    parser.add_argument("--once", action="store_true", help="Executa apenas 1 tentativa e encerra")
    args = parser.parse_args()
    run_hunter(once=args.once)
