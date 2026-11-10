"""
Camada 3 (Execucao): Diagnostico Deterministico da Infraestrutura Oracle Cloud (OCI)
Inspeciona Instancias, VNICs, IPs Publicos, VCNs, Sub-redes, Internet Gateways,
Route Tables e Security Lists sem depender de pacotes pesados externos.
"""

import base64
import configparser
import email.utils
import hashlib
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, ".oci", "config")


class OCIClient:
    """Cliente leve HTTP Signature v1 para a REST API da Oracle Cloud Infrastructure."""

    def __init__(self, config_path: str = CONFIG_PATH, profile: str = "DEFAULT"):
        cfg = configparser.ConfigParser()
        cfg.read(config_path)
        d = cfg[profile]
        self.user = d["user"].strip()
        self.fingerprint = d["fingerprint"].strip()
        self.tenancy = d["tenancy"].strip()
        self.region = d["region"].strip()
        self.key_file = d["key_file"].strip()
        with open(self.key_file, "rb") as f:
            self.priv_key = serialization.load_pem_private_key(f.read(), password=None)
        self.key_id = f"{self.tenancy}/{self.user}/{self.fingerprint}"
        self.iaas_host = f"iaas.{self.region}.oraclecloud.com"
        self.identity_host = f"identity.{self.region}.oraclecloud.com"

    def request(self, method: str, host: str, path: str, body: dict | None = None):
        method_lower = method.lower()
        date_str = email.utils.formatdate(usegmt=True)
        headers = {
            "Date": date_str,
            "Host": host,
        }
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
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {e.code} em {method} {path}: {err_body}") from e


def run_diagnostics():
    client = OCIClient()
    comp_id = client.tenancy
    iaas = client.iaas_host

    # 1. Listar compartimentos ativos
    compartments = [comp_id]
    try:
        sub_comps = client.request(
            "GET",
            client.identity_host,
            f"/20160918/compartments?compartmentId={comp_id}&compartmentIdInSubtree=true",
        )
        for c in sub_comps:
            if c.get("lifecycleState") == "ACTIVE":
                compartments.append(c["id"])
    except Exception as e:
        print("Aviso ao listar sub-compartimentos:", e)

    report = {"instances": [], "vcns": []}

    for cid in compartments:
        instances = client.request("GET", iaas, f"/20160918/instances?compartmentId={cid}")
        for inst in instances:
            if inst.get("lifecycleState") == "TERMINATED":
                continue
            inst_id = inst["id"]
            # Buscar VNIC attachments
            vnic_atts = client.request(
                "GET", iaas, f"/20160918/vnicAttachments?compartmentId={cid}&instanceId={inst_id}"
            )
            vnics = []
            for va in vnic_atts:
                if va.get("lifecycleState") == "ATTACHED":
                    vnic = client.request("GET", iaas, f"/20160918/vnics/{va['vnicId']}")
                    vnics.append({
                        "vnicId": vnic["id"],
                        "publicIp": vnic.get("publicIp"),
                        "privateIp": vnic.get("privateIp"),
                        "subnetId": vnic.get("subnetId"),
                        "nsgIds": vnic.get("nsgIds", []),
                    })
            # Buscar imagem (SO)
            img_name = "Desconhecido"
            if inst.get("imageId"):
                try:
                    img = client.request("GET", iaas, f"/20160918/images/{inst['imageId']}")
                    img_name = f"{img.get('operatingSystem')} {img.get('operatingSystemVersion')} ({img.get('displayName')})"
                except Exception:
                    pass

            report["instances"].append({
                "id": inst_id,
                "displayName": inst.get("displayName"),
                "shape": inst.get("shape"),
                "shapeConfig": inst.get("shapeConfig"),
                "lifecycleState": inst.get("lifecycleState"),
                "availabilityDomain": inst.get("availabilityDomain"),
                "compartmentId": cid,
                "image": img_name,
                "metadata_ssh_keys": inst.get("metadata", {}).get("ssh_authorized_keys", ""),
                "vnics": vnics,
            })

        vcns = client.request("GET", iaas, f"/20160918/vcns?compartmentId={cid}")
        for v in vcns:
            vcn_id = v["id"]
            igws = client.request("GET", iaas, f"/20160918/internetGateways?compartmentId={cid}&vcnId={vcn_id}")
            rts = client.request("GET", iaas, f"/20160918/routeTables?compartmentId={cid}&vcnId={vcn_id}")
            sls = client.request("GET", iaas, f"/20160918/securityLists?compartmentId={cid}&vcnId={vcn_id}")
            subnets = client.request("GET", iaas, f"/20160918/subnets?compartmentId={cid}&vcnId={vcn_id}")
            nsgs = client.request("GET", iaas, f"/20160918/networkSecurityGroups?compartmentId={cid}&vcnId={vcn_id}")
            nsg_details = []
            for n in nsgs:
                rules = client.request("GET", iaas, f"/20160918/networkSecurityGroups/{n['id']}/securityRules")
                nsg_details.append({"id": n["id"], "displayName": n["displayName"], "rules": rules})

            report["vcns"].append({
                "id": vcn_id,
                "compartmentId": cid,
                "displayName": v.get("displayName"),
                "cidrBlocks": v.get("cidrBlocks"),
                "internetGateways": [
                    {"id": g["id"], "displayName": g["displayName"], "isEnabled": g["isEnabled"]}
                    for g in igws
                ],
                "routeTables": [
                    {"id": r["id"], "displayName": r["displayName"], "routeRules": r["routeRules"]}
                    for r in rts
                ],
                "securityLists": [
                    {
                        "id": s["id"],
                        "displayName": s["displayName"],
                        "ingressSecurityRules": s["ingressSecurityRules"],
                        "egressSecurityRules": s["egressSecurityRules"],
                    }
                    for s in sls
                ],
                "subnets": [
                    {
                        "id": sub["id"],
                        "displayName": sub["displayName"],
                        "cidrBlock": sub["cidrBlock"],
                        "prohibitPublicIpOnVnic": sub.get("prohibitPublicIpOnVnic"),
                        "routeTableId": sub.get("routeTableId"),
                        "securityListIds": sub.get("securityListIds"),
                    }
                    for sub in subnets
                ],
                "nsgs": nsg_details,
            })

    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    run_diagnostics()

