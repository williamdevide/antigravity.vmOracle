"""
Camada 3 (Execucao): Correcao Deterministica da Rede OCI (VCN, Internet Gateway, Route Table e Security List)
Corrige automaticamente:
1. Criacao de Internet Gateway na VCN ativa da VM (caso ausente).
2. Adicao da rota padrao 0.0.0.0/0 apontando para o Internet Gateway na Route Table da Subnet.
3. Correcao das Ingress Rules na Security List (Portas 22, 80 e 443 com sourcePortRange=None).
"""

import json
from oci_diagnostic import OCIClient

VCN_ID = "ocid1.vcn.oc1.sa-saopaulo-1.amaaaaaaju7cfdyawoslif6bhtmm2ktznpx5apgtgpgzaag7xeyzh34qlk6a"
ROUTE_TABLE_ID = "ocid1.routetable.oc1.sa-saopaulo-1.aaaaaaaaq4dd52wna76uoemzqsnrgqlv3rgyd5377qflq4qcswb54r6o3xda"
SECURITY_LIST_ID = "ocid1.securitylist.oc1.sa-saopaulo-1.aaaaaaaasusiqq2vfbvkynrlcwpr5cxwi7ttlhgttkztv67k35ln2hcoqyra"


def fix_network():
    client = OCIClient()
    iaas = client.iaas_host
    comp_id = client.tenancy

    # 1. Verificar ou criar Internet Gateway na VCN da VM
    igws = client.request("GET", iaas, f"/20160918/internetGateways?compartmentId={comp_id}&vcnId={VCN_ID}")
    if not igws:
        print("[1/3] Criando Internet Gateway na VCN ativa da VM...")
        igw = client.request(
            "POST",
            iaas,
            "/20160918/internetGateways",
            body={
                "compartmentId": comp_id,
                "vcnId": VCN_ID,
                "displayName": "igw-vm-wdk-active",
                "isEnabled": True,
            },
        )
        igw_id = igw["id"]
        print(f"      -> Internet Gateway criado: {igw_id}")
    else:
        igw_id = igws[0]["id"]
        print(f"[1/3] Internet Gateway ja existente: {igw_id}")

    # 2. Atualizar Route Table com rota 0.0.0.0/0 -> Internet Gateway
    print("[2/3] Atualizando Route Table com rota 0.0.0.0/0 para o Internet Gateway...")
    rt = client.request(
        "PUT",
        iaas,
        f"/20160918/routeTables/{ROUTE_TABLE_ID}",
        body={
            "routeRules": [
                {
                    "destination": "0.0.0.0/0",
                    "destinationType": "CIDR_BLOCK",
                    "networkEntityId": igw_id,
                    "description": "Acesso publico a Internet via Internet Gateway",
                }
            ]
        },
    )
    print("      -> Route Table atualizada com sucesso:", len(rt.get("routeRules", [])), "regra(s).")

    # 3. Atualizar Security List (corrigir sourcePortRange em HTTP 80 e HTTPS 443 e garantir SSH 22 e ICMP)
    print("[3/3] Atualizando Security List (Ingress 22, 80, 443 sem restricao de porta de origem)...")
    ingress_rules = [
        {
            "isStateless": False,
            "protocol": "6",
            "source": "0.0.0.0/0",
            "sourceType": "CIDR_BLOCK",
            "description": "SSH Access",
            "tcpOptions": {"destinationPortRange": {"min": 22, "max": 22}},
        },
        {
            "isStateless": False,
            "protocol": "6",
            "source": "0.0.0.0/0",
            "sourceType": "CIDR_BLOCK",
            "description": "HTTP Web Traffic",
            "tcpOptions": {"destinationPortRange": {"min": 80, "max": 80}},
        },
        {
            "isStateless": False,
            "protocol": "6",
            "source": "0.0.0.0/0",
            "sourceType": "CIDR_BLOCK",
            "description": "HTTPS Web Traffic",
            "tcpOptions": {"destinationPortRange": {"min": 443, "max": 443}},
        },
        {
            "isStateless": False,
            "protocol": "1",
            "source": "0.0.0.0/0",
            "sourceType": "CIDR_BLOCK",
            "description": "ICMP Path MTU Discovery & Ping",
            "icmpOptions": {"type": 3, "code": 4},
        },
        {
            "isStateless": False,
            "protocol": "1",
            "source": "0.0.0.0/0",
            "sourceType": "CIDR_BLOCK",
            "description": "ICMP Echo Request (Ping)",
            "icmpOptions": {"type": 8},
        },
    ]
    egress_rules = [
        {
            "destination": "0.0.0.0/0",
            "destinationType": "CIDR_BLOCK",
            "isStateless": False,
            "protocol": "all",
        }
    ]
    sl = client.request(
        "PUT",
        iaas,
        f"/20160918/securityLists/{SECURITY_LIST_ID}",
        body={
            "ingressSecurityRules": ingress_rules,
            "egressSecurityRules": egress_rules,
        },
    )
    print("      -> Security List atualizada com sucesso:", len(sl.get("ingressSecurityRules", [])), "regras de entrada.")


if __name__ == "__main__":
    fix_network()

