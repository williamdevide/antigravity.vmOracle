# SOP 07 — Procedimento Operacional Padrão: Deploy de Projetos PHP / MariaDB com Cron e Correção de Permissões

## 🎯 Objetivo
1. Corrigir o erro de `[Errno 13] Permission denied: '/opt/antigravity-oracle/execution/deployed_projects.json'`.
2. Realizar a implantação completa do projeto do aluno **LabWareNext** na VM Oracle (`147.15.2.73`).
3. Configurar o banco de dados MariaDB (`labw`), importar a estrutura SQL e injetar as credenciais `.env`.
4. Configurar o Caddy para servir a aplicação PHP via PHP-FPM (`https://labware.147.15.2.73.sslip.io`).
5. Configurar a execução periódica do script `cron_analisar.php` no daemon de Cron do Linux (`/etc/cron.d/aco-project-labware`).

---

## 🛠️ Diagnóstico de Causa Raiz (Self-Annealing)

### Erro: `[Errno 13] Permission denied: deployed_projects.json`
* **Causa:** O script de atualização inicial foi executado com `sudo bash`, o que transferiu a titularidade (ownership) do diretório `/opt/antigravity-oracle` e dos arquivos `.json` para `root:root`. Como o backend FastAPI (`antigravity-dashboard.service`) roda sob o usuário sem privilégios `ubuntu`, qualquer tentativa de gravar no arquivo resultava em bloqueio de permissão a nível de sistema operacional Linux.
* **Correção Definitiva:** Garantir que o diretório `/opt/antigravity-oracle` pertença ao usuário `ubuntu:ubuntu` com permissões `775` em `execution/` e `664` no arquivo `deployed_projects.json`.

---

## 🏗️ Especificações do Projeto Aluno (LabWareNext)

* **Repositório:** `https://github.com/Antonio-augustos2/CTDS-2026-02-Sistema-LabWareNext-Antonio-Isabelle-Nicolle.git`
* **Linguagem / Stack:** PHP 8.3 FPM nativo
* **Banco de Dados:** MariaDB `labw` (tabelas: `acesso`, `candidato`, `vaga`, `candidatura`, `membro_rh`, `api_error_log`)
* **Subdomínio:** `https://labware.147.15.2.73.sslip.io`
* **Agendamento Cron:** `*/10 * * * *` executando `/usr/bin/php /var/www/projects/labware/cron_analisar.php` com logs em `/var/log/aco-cron/labware.log`.

---

## 🚀 Execução Determinística

O script determinístico da Camada 3 está em `execution/deploy_student_project.sh`.
Ele automatiza os 12 passos de instalação, provisionamento do banco, clone do git, injeção de `.env`, configuração do Caddy e registro do card no dashboard do A.C.O.

