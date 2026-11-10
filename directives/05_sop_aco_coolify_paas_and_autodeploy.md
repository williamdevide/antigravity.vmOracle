# 📋 SOP 05: Plataforma A.C.O. v3.0 (Coolify Edition), Auto-Deploy e Bancos de Dados

## 1. Objetivo ("O Quê" e "Por Quê")
Evoluir o **A.C.O. (Antigravity Cloud Orchestrator)** para um PaaS completo inspirado no **Coolify**, com telemetria individual de RAM e Disco por recurso (incluindo a própria plataforma A.C.O.), detecção automática de pushes no GitHub (Auto-Deploy Híbrido), histórico completo de deploys, gestão de variáveis `.env` por projeto, controle de ciclo de vida (`Start`/`Stop`/`Restart`) e provisionamento 1-Clique de Bancos de Dados.

## 2. Componentes da Camada 3 (`/execution`)
1. **`execution/deploy_project.py` (Motor PaaS Multi-Arquitetura):**
   - Suporta `fullstack` (Monorepo `/frontend` + `/backend` sob o mesmo domínio HTTPS), `react-vite` (SPA com limpeza automática de `node_modules`), `static`, `node` e `python`.
   - Mede o consumo real de **Memória RAM (`MemoryCurrent` via `systemd` cgroups)** e **Disco (`os.walk`)** de cada projeto e da própria plataforma **A.C.O. Core (`antigravity-dashboard` + `oci-arm-hunter` + `caddy`)**.
   - Gerencia variáveis de ambiente individuais por projeto (`.aco.env` e `.env`), histórico detalhado de deploys (`deploymentsHistory`), logs de runtime (`journalctl -u app-<slug>`) e detecção de novos commits (`git ls-remote`).
2. **`execution/database_manager.py` (Orquestrador de Bancos de Dados 1-Clique):**
   - Provisiona e gerencia bancos **SQLite**, **PostgreSQL (Low-Memory Tuned)**, **MariaDB/MySQL (Low-Memory Tuned)** e **Redis (32MB LRU)**.
   - Mede consumo de RAM e Disco de cada banco e injeta automaticamente `DATABASE_URL` nas variáveis de ambiente de qualquer projeto selecionado.

