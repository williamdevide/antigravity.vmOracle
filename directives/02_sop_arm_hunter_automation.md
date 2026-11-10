# 📋 SOP 02: Captura Automatizada da Instância ARM (Ampere A1)

## 1. Objetivo ("O Quê" e "Por Quê")
Automatizar a captura de uma instância Always Free **Ampere A1 (`VM.Standard.A1.Flex`)** na região de São Paulo (`sa-saopaulo-1`) assim que houver liberação de capacidade física nos datacenters da Oracle Cloud, executando um serviço contínuo (`systemd`) 24/7 diretamente dentro da VM x86 já ativa.

## 2. Regra de Governança Always Free e Descoberta de Limites Reais (Self-Annealing)
- Ao auditar a API de Limites da conta (`limits.sa-saopaulo-1.oci.oraclecloud.com`), descobrimos o motivo real pelo qual tentativas manuais de `4 OCPU / 24 GB RAM / 200 GB` falhavam permanentemente com `HTTP 400 (LimitExceeded)`:
  - **`standard-a1-core-count` (Teto de OCPUs ARM na conta):** `2 OCPUs`
  - **`standard-a1-memory-count` (Teto de RAM ARM na conta):** `12 GB RAM`
  - **`total-free-storage-gb` (Teto de Armazenamento Always Free):** `200 GB` (dos quais `50 GB` já estão alocados no Boot Volume da `vm-wdk-amd-x86`, restando **`150 GB` livres**).
- Portanto, o script `execution/oci_arm_hunter.py` consulta dinamicamente a API de Limites da conta antes de iniciar a caça e solicita exatamente o teto máximo permitido pela conta (**`2 OCPU`, `12 GB RAM` e `150 GB Boot Volume`** — ou `4 OCPU / 24 GB` caso o limite da tenancy seja ampliado no futuro).
- Com esse ajuste, a requisição passa por todas as validações de cota da Oracle Cloud e atinge diretamente o alocador físico de São Paulo (`Out of host capacity` até surgir vaga).

## 3. Ferramentas Determinísticas (Camada 3 — `/execution`)
- `execution/oci_arm_hunter.py`: Script autônomo que consulta a Limits API, localiza a imagem oficial mais recente do Canonical Ubuntu (`aarch64`), verifica se a instância `vm-wdk-arm-ampere` já foi criada (interrompendo o loop automaticamente em caso de sucesso), respeita *backoff* com *jitter* (65s a 95s) para evitar bloqueio `429 TooManyRequests` e grava telemetria em JSON (`arm_hunter_status.json`) para o Painel Web Orquestrador.
