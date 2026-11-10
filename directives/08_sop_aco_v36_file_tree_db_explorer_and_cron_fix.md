# SOP 08 — Procedimento Operacional Padrão: Árvore de Arquivos, Inspetor de Banco de Dados, Correção de Cron e Permissões (.aco.env)

## 🎯 Objetivo
1. Eliminar o erro `[Errno 13] Permission denied: '/var/www/projects/labwarenext/.aco.env'` através de escrita segura com fallback `sudo tee` e ajuste de permissões para o usuário `ubuntu` e grupo `www-data`.
2. Remover definitivamente do painel o card fantasma de projetos excluídos (`labware`), garantindo limpeza do Caddyfile, do diretório de projeto e do daemon Cron.
3. Restaurar a visualização das variáveis de ambiente na aba `.env` do modal, lendo o arquivo `.env` real gravado no disco do servidor.
4. Restaurar a aba `Cron / Agendamentos`, corrigindo a importação do ícone `Save` e o mapeamento de arquivos do cron.
5. Implementar a **Visualização em Árvore do Projeto Publicado (File Tree Explorer)**, permitindo navegar por pastas e pré-visualizar arquivos de código diretamente pelo painel.
6. Implementar a **Visualização do Banco de Dados (Estrutura e Dados)**, permitindo inspecionar colunas, tipos de dados e os registros reais das tabelas do MariaDB/MySQL.

---

## 🛠️ Diagnóstico de Causa Raiz (Self-Annealing)

1. **Permissão .aco.env:**
   * O diretório `/var/www/projects/labwarenext` pertencia a `www-data:www-data`. Ao tentar salvar o branch ou settings, o FastAPI (`ubuntu`) não tinha permissão de escrita. Implementado `safe_write_file` com fallback via `sudo tee` e adicionado `ubuntu` ao grupo `www-data`.
2. **Card Fantasma de Projeto Excluído:**
   * O backend tentava remover com `os.remove` sem privilégios de root sobre a rota `/etc/caddy/sites.d/labware.caddy`. A rota permanecia no disco e a função `reconcile_unindexed_projects()` restaurava o card. O novo `remove_project` executa `sudo rm -f` e limpa as rotas físicas e o cron.
3. **Aba Cron Vazia:**
   * O componente React usava `<Save />` sem que o ícone estivesse importado de `lucide-react`, provocando crash silencioso ao abrir a aba. O nome do arquivo no cron.d divergia entre `aco-<slug>` e `aco-project-<slug>`.
4. **Aba .env Vazia:**
   * O modal lia apenas a propriedade `envVarsText` do JSON em memória. Criado o endpoint dedicado `GET /api/projects/{slug}/env` que lê o arquivo `.env` real gravado no disco.

---

## 🚀 Implementação Realizada

* **Backend (`backend/main.py`):**
  * `GET /api/projects/{slug}/env`: Retorna as variáveis reais do arquivo no servidor.
  * `GET /api/projects/{slug}/files`: Retorna a árvore de diretórios e arquivos com tamanho e data.
  * `GET /api/projects/{slug}/file-content`: Retorna o conteúdo de texto de arquivos selecionados.
  * `GET /api/databases/explorer/tables`: Lista as tabelas do MariaDB e quantidade de registros.
  * `GET /api/databases/explorer/schema`: Lista as colunas, tipos e constraints.
  * `GET /api/databases/explorer/data`: Retorna os registros reais tabulados com paginação.
* **Frontend (`frontend/src/App.jsx`):**
  * Nova aba **"Árvore de Arquivos"** no modal do projeto.
  * Novo painel **"Explorador de Banco de Dados"** na seção de Bancos de Dados.
* **Camada 3 (`execution/apply_aco_v36_update.sh`):**
  * Script de 1 comando para compilar e ativar o A.C.O. v3.6.0 na VM.

