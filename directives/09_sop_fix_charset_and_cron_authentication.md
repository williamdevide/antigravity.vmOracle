# Diretiva 09: Procedimento Operacional Padrão (SOP) — Correção de Mojibake (Charset UTF-8/cp1252) e Autenticação de Tarefas Cron

## 1. Contexto e Diagnóstico
- **Projeto Alvo:** `labwarenext` (Sistema de Recrutamento LabWare Next).
- **Problema 1 (Cron Authentication Failure):**
  - **Sintoma:** O log do Cron em `/var/log/aco-cron/labwarenext.log` registrava repetidamente `{"error":"Token inválido ou não fornecido","timestamp":"..."}` com retorno HTTP 401.
  - **Causa Raiz:** O script `cron_analisar.php` do aluno validava obrigatoriamente a presença de `$_GET['token']` comparando com a constante `CRON_TOKEN` definida no `.env`. Quando disparado pelo cron nativo do Linux via CLI (`php cron_analisar.php`), a variável `$_GET` fica vazia. Além disso, as chamadas manuais disparadas via painel A.C.O. executavam o comando sem os devidos argumentos ou headers de autenticação.
  - **Resolução:** 
    1. Ajustar `cron_analisar.php` para detectar execução em modo CLI (`php_sapi_name() === 'cli'`) e automaticamente herdar o `CRON_TOKEN` configurado no ambiente local do servidor, permitindo também passagem de parâmetro via linha de comando (`token=...`).
    2. Configurar `/etc/cron.d/aco-labwarenext` para executar explicitamente `php cron_analisar.php token=k7j-P2qL9m_zX5bN-wY3T-rQ8eF`.
    3. Atualizar o registro do projeto em `deployed_projects.json` com `cronSchedule` e `cronCommand`.

- **Problema 2 (Mojibake / Charset Duplo UTF-8 / Windows-1252):**
  - **Sintoma:** Caracteres acentuados apareciam corrompidos na interface e nos detalhes de vagas (ex: `DescriÃ§Ã£o do trabalho`, `construÃ§Ã£o`, `soluÃ§Ãµes`, `SÃ£o Paulo`, `â€¢`, `Ã¡geis`, `GestÃ£o`).
  - **Causa Raiz:** O dump original exportado do phpMyAdmin foi gerado com dupla codificação (UTF-8 interpretado como cp1252/latin1 e re-salvo em UTF-8).
  - **Resolução:**
    1. Executar rotina determinística em Python para inspecionar as tabelas `vaga`, `feedback`, `acesso` no banco MariaDB `labw`, aplicando decodificação reversa `val.encode('cp1252').decode('utf-8')`.
    2. Reimportar o arquivo `execution/labware_full.sql` corrigido e limpo.
    3. Percorrer os arquivos de template e scripts do projeto (`header.php`, `script.js`) restaurando acentos e flexibilizando expressões regulares para aceitar tanto acentuação limpa quanto títulos legados.

## 2. Scripts da Camada 3 Envolvidos
- `execution/labware_full.sql`: Dump limpo em UTF-8 (`utf8mb4_unicode_ci`) sem nenhum mojibake.
- `execution/fix_labware_data_and_cron.py`: Script Python autônomo para correção de charset no MySQL, no filesystem e configuração do Cron.
- `execution/fix_labware_charset_and_cron.sh`: Wrapper de execução idempotente para atualização via Git e acionamento no host Ubuntu.

