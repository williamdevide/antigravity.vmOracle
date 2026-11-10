# 📋 SOP 01: Diagnóstico e Correção de Rede OCI & Acesso SSH

## 1. Objetivo ("O Quê" e "Por Quê")
Garantir conectividade determinística entre o ambiente de orquestração local e a instância Linux na Oracle Cloud Infrastructure (OCI), eliminando bloqueios de VCN (ausência de Internet Gateway ou rota `0.0.0.0/0`), erros de filtro em Security Lists (restrição indevida de `sourcePortRange`) e falhas de permissão de chave privada SSH no Windows.

## 2. Entradas Esperadas
- Credenciais da API OCI em `.oci/config` e chave privada RSA em `.oci/oci_api_key.pem`.
- Chave privada SSH da instância em `.oci/ssh-key-2026-10-29.key` (espelhada com ACL restrita em `C:\Users\William\.ssh\oracle_vm_x86.key`).
- IP Público da instância (`147.15.2.73`) e usuário padrão (`ubuntu`).

## 3. Ferramentas Determinísticas (Camada 3 — `/execution`)
- `execution/oci_diagnostic.py`: Inspeciona todas as instâncias, VNICs, VCNs, Sub-redes, Internet Gateways, Route Tables e Security Lists da conta OCI via assinatura HTTP Signature v1.
- `execution/oci_fix_network.py`: Cria automaticamente o Internet Gateway na VCN ativa, vincula a rota `0.0.0.0/0` na Route Table e aplica regras de entrada (Ingress) para as portas TCP `22`, `80` e `443` com `sourcePortRange: null`.

## 4. Loop de Autorrecuperação (Lições Aprendidas)
- **Problema Detectado #1:** Múltiplas VCNs com o mesmo nome (`vcn-20261009-1708`) na conta. A VCN vinculada à VM ativa não possuía Internet Gateway nem regras na Route Table, gerando `Connection timed out`.
- **Problema Detectado #2:** As regras HTTP (80) e HTTPS (443) na Security List estavam com `sourcePortRange` preenchido (80 e 443), o que bloqueia conexões reais de navegadores (que utilizam portas efêmeras altas na origem).
- **Problema Detectado #3:** Volumes fora da partição do sistema no Windows (`G:\`) podem manter permissões herdadas abertas, fazendo o OpenSSH rejeitar a chave (`WARNING: UNPROTECTED PRIVATE KEY FILE!`). Solução: espelhar a chave em `%USERPROFILE%\.ssh\oracle_vm_x86.key` com `icacls /inheritance:r`.

