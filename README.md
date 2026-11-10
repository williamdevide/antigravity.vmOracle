# ☁️ A.C.O. v3.5 — Antigravity Cloud Orchestrator (Coolify Edition)

![Google Antigravity](https://img.shields.io/badge/Google_Antigravity-AI_Powered-4285F4?style=for-the-badge&logo=google&logoColor=white)
![Oracle Cloud](https://img.shields.io/badge/Oracle_Cloud-OCI_Free_Tier-F80000?style=for-the-badge&logo=oracle&logoColor=white)
![React](https://img.shields.io/badge/React_18-Vite_5-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-Coolify_Dark_UI-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)
![PHP](https://img.shields.io/badge/PHP_8.3-FastCGI_Composer-777BB4?style=for-the-badge&logo=php&logoColor=white)
![MariaDB](https://img.shields.io/badge/MariaDB-MySQL_Tuned-003545?style=for-the-badge&logo=mariadb&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Python_3.12-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Firebase Auth](https://img.shields.io/badge/Firebase_Auth-Zero_Trust_Google-FFCA28?style=for-the-badge&logo=firebase&logoColor=black)
![Caddy HTTPS](https://img.shields.io/badge/Caddy-Auto_HTTPS-22B573?style=for-the-badge&logo=letsencrypt&logoColor=white)

> **SENAI Ourinhos Edition** • Desenvolvido com **Google Antigravity** utilizando a **Arquitetura de 3 Camadas (`/agente-orquestrador`)**.

---

## 🇧🇷 Português (Brasil)

### 🎯 Sobre o Projeto
O **A.C.O. v3.5 (Antigravity Cloud Orchestrator — Coolify Edition)** é uma plataforma PaaS privada inspirada no Coolify para diagnóstico, provisionamento determinístico, gerenciamento de bancos de dados relacionais e cache 1-clique, agendamento de tarefas em segundo plano via **Cron**, e publicação contínua (**CI/CD Auto-Deploy**) de projetos desenvolvidos por instrutores e alunos em qualquer repositório Git.

### 🌐 Links Ao Vivo na VM (`147.15.2.73`)
* 🖥️ **Painel Orquestrador A.C.O. (HTTPS):** [https://147.15.2.73.sslip.io](https://147.15.2.73.sslip.io)
* 🏭 **Sistema Manu (Full-Stack SIG-Manu):** [https://manu.147.15.2.73.sslip.io](https://manu.147.15.2.73.sslip.io)
* 🚀 **Projeto Vitrine Publicado (HTTPS):** [https://demo.147.15.2.73.sslip.io](https://demo.147.15.2.73.sslip.io)
* 🩺 **Health Check da API:** [https://147.15.2.73.sslip.io/api/health](https://147.15.2.73.sslip.io/api/health)

---

### ✨ Novidades & Recursos da Versão 3.5

#### 1. 🐘 Suporte Nativo a PHP + Composer + Caddy FastCGI
* **Detecção Automática:** Reconhece arquivos `index.php`, `composer.json`, `artisan` ou estrutura de frameworks modernos (Laravel, Symfony, CodeIgniter).
* **DocumentRoot Inteligente:** Vincula automaticamente o Caddy ao subdiretório `public/` caso exista `public/index.php`.
* **Instalação de Dependências:** Executa `composer install --no-interaction --prefer-dist --optimize-autoloader --no-dev`.
* **FastCGI de Alta Performance:** Comunicação direta com o socket UNIX do `php-fpm` (`/run/php/php8.3-fpm.sock`).

#### 2. ⏰ Gerenciador Completo de Cron & Eventos Agendados
* **Aba Visual Dedicada:** Gestão intuitiva de agendamentos crontab por projeto no modal de gerenciamento.
* **Atalhos Rápidos:** Predefinições para 1 min (`* * * * *`), 5 min (`*/5 * * * *`), hora cheia (`0 * * * *`) e diário (`0 0 * * *`).
* **Execução em Sandbox:** Grava os agendamentos isolados em `/etc/cron.d/aco-<slug>` executados pelo usuário `ubuntu`.
* **Botão "Testar / Executar Agora":** Dispara a rotina sob demanda para validar saída e códigos de erro sem esperar o cronômetro.
* **Console de Logs:** Visualização em tempo real de `/var/log/aco-cron/<slug>.log`.
* **Auto-Detecção no Repositório:** Carrega automaticamente tarefas declaradas em arquivos `.cron` ou `crontab` do projeto.

#### 3. 👥 Repositórios Externos de Alunos (Híbrido)
* Suporte a repositórios Git públicos de qualquer usuário sem exigir permissões de escrita/colaborador (clone anônimo com fallback automático).
* Campo opcional para **Token de Acesso Git / Deploy Token** para repositórios privados de alunos.

#### 4. 🗄️ Bancos de Dados MariaDB / MySQL 1-Clique Tuned
* Provisionamento automático de bancos **MariaDB/MySQL** com `innodb_buffer_pool_size = 32M` e `performance_schema = OFF` para caber na VM Always Free de 1 GB de RAM.
* Injeção automática das credenciais e da `DATABASE_URL` no `.env` do projeto PHP ou Full-Stack com 1 clique.

#### 5. 🔄 Auto-Discovery & Reconciliação (Causa Raiz do Sistema Manu Resolvida)
* O motor `load_projects()` conta com a rotina determinística `reconcile_unindexed_projects()`, que inspeciona `/etc/caddy/sites.d/*.caddy` e `/var/www/projects/*/`.
* **Diagnóstico Manu:** O Sistema Manu já estava ativo no Caddy e no Systemd em `https://manu.147.15.2.73.sslip.io`, mas ausente do índice `deployed_projects.json`. A nova rotina auto-recuperou seus metadados, métricas de RAM/Disco e o restabeleceu no painel.

---

### 🤖 Agentes de IA & Skill Packs Utilizados (Google Antigravity)
* **Agente Central:** Google Antigravity Agent (`agente-orquestrador`)
* **Skills Ativadas:**
  * `agente-orquestrador`: Arquitetura em 3 Camadas (`/directives`, Camada 2 Decisão, `/execution` Determinístico).
  * `firebase-auth-basics`: Autenticação Zero-Trust com Google Sign-In exclusivo.
  * `managing-python-dependencies`: Gestão de dependências e ambientes virtuais.
* **Comandos Slash Utilizados:** `/agente-orquestrador`, `/grill-me`, `/goal`.

---

### 📁 Estrutura do Repositório
```text
├── directives/                  # Camada 1: SOPs e Diretivas Estratégicas (01 a 06)
│   ├── 01_sop_oci_network_and_vm_access.md
│   ├── 02_sop_arm_hunter_automation.md
│   ├── 03_sop_vm_x86_provisioning_and_deploy.md
│   ├── 04_sop_zero_trust_google_auth.md
│   ├── 05_sop_aco_coolify_paas_and_autodeploy.md
│   └── 06_sop_php_mariadb_cron_and_external_repos.md
├── execution/                   # Camada 3: Scripts Determinísticos de Execução
│   ├── deploy_project.py        # Motor de Deploy Multi-Arquitetura + Cron + Auto-Discovery
│   ├── database_manager.py      # Gestor de Bancos 1-Clique (MariaDB, Postgres, SQLite, Redis)
│   ├── provision_php_stack.sh   # Script de Provisionamento da Stack PHP 8.3 + MariaDB + Cron
│   ├── oci_arm_hunter.py        # Robô Caçador ARM 24/7
│   ├── oci_diagnostic.py        # Cliente OCI REST API (HTTP Signature v1)
│   └── deployed_projects.json   # Banco de Dados JSON de Projetos Publicados
├── backend/                     # Servidor FastAPI v3.5 (APIs de Cron, Deploy, Zero-Trust)
│   ├── main.py
│   └── requirements.txt
├── frontend/                    # Painel Coolify Edition (React 18, Vite, Tailwind CSS)
│   ├── src/App.jsx              # UI com Abas de Cron, Logs, .env, Bancos e Deploy Modal
│   └── src/firebase.js          # Google Sign-In Zero-Trust
├── documentation/               # Documentação Técnica e Histórico
│   ├── architecture_and_guide.md
│   └── promptHistory.md         # Registro Integral e Obrigatório de Prompts
└── README.md                    # Vitrine Bilíngue do Projeto
```

---

## 🇺🇸 English

### 🎯 Project Overview
**A.C.O. v3.5 (Antigravity Cloud Orchestrator — Coolify Edition)** is a self-hosted PaaS and continuous deployment platform for **Oracle Cloud Infrastructure (OCI)** Linux instances (`sa-saopaulo-1`), created with **Google Antigravity** using the **3-Layer Architecture (`/directives`, Orchestration, `/execution`)**.

### ✨ Highlights & New Capabilities in v3.5
* **PHP & Composer Native Support:** Full deployment for PHP applications (Laravel, Symfony, raw PHP) via Caddy `php_fastcgi` and automated `composer install`.
* **Integrated Cron Scheduler:** Manage scheduled background tasks per project with crontab syntax, quick presets, manual "Run Now" testing, and live execution logs (`/var/log/aco-cron/<slug>.log`).
* **External & Student Git Repositories:** Support for public repositories from other authors with seamless anonymous fallback, plus optional private token support.
* **1-Click Low-Memory MariaDB/MySQL:** Automated provisioning with memory tuning for 1 GB RAM micro instances and instant `.env` credential injection.
* **Auto-Discovery & Self-Annealing:** Reconciles active Caddy configurations and filesystem directories (such as the recovered **Sistema Manu**).

---
*Assinado: Agente Antigravity - SENAI Ourinhos Edition*
