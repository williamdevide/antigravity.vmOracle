# 📋 SOP 06: Suporte a PHP, Bancos MariaDB/MySQL, Cron e Repositórios Externos de Alunos

## 1. Objetivo ("O Quê" e "Por Quê")
Capacitar a plataforma **A.C.O. (Antigravity Cloud Orchestrator)** a receber projetos desenvolvidos por alunos e terceiros em qualquer repositório Git, viabilizando a publicação de aplicações **PHP nativas ou com Composer (Laravel, Symfony, etc.)**, bancos de dados relacionais **MariaDB / MySQL**, e agendamento de eventos e tarefas em segundo plano via **Cron**.

---

## 2. Diagnóstico do Sistema Manu (Causa Raiz Resolvida)
- **Causa Raiz:** O projeto **Sistema Manu (`antigravity.Manu`)** foi publicado e ativado no servidor (Caddy e serviço systemd `app-manu` ativos respondendo em `https://manu.147.15.2.73.sslip.io`), porém o registro no arquivo `deployed_projects.json` não havia sido persistido ou foi sobrescrito em uma reinicialização anterior. Como o motor `load_projects()` lia estritamente o JSON, o card não era exibido no dashboard.
- **Solução Implementada (Auto-Discovery & Self-Annealing):** Criada a rotina determinística `reconcile_unindexed_projects()` em `execution/deploy_project.py`. Toda vez que o A.C.O. carrega a lista de projetos, ele inspeciona `/etc/caddy/sites.d/*.caddy` e `/var/www/projects/*/`. Se identificar um projeto ativo no Caddy/filesystem que não conste no JSON, o sistema extrai o domínio, portas de proxy, tipo de arquitetura (`fullstack`, `php`, etc.), metadados do Git e o regenera automaticamente no banco, garantindo que o card do **Sistema Manu** e quaisquer outros projetos legados apareçam instantaneamente.

---

## 3. Especificação da Arquitetura PHP + Caddy FastCGI
1. **Detecção Automática:**
   - Detecta `index.php`, `composer.json`, `artisan` ou arquivos `.php` na raiz ou no diretório `public/`.
   - Se existir `public/index.php`, define o DocumentRoot do Caddy como `/var/www/projects/<slug>/public`.
2. **Gerenciamento de Dependências:**
   - Se `composer.json` estiver presente, executa automaticamente:
     ```bash
     composer install --no-interaction --prefer-dist --optimize-autoloader --no-dev
     ```
3. **Roteamento HTTPS Caddy:**
   - O Caddy faz o proxy reverso FastCGI para o socket UNIX do PHP-FPM detectado dinamicamente:
     ```caddy
     <slug>.147.15.2.73.sslip.io {
         encode gzip
         root * /var/www/projects/<slug>/public
         php_fastcgi unix//run/php/php8.3-fpm.sock
         file_server
     }
     ```

---

## 4. Repositórios Externos de Alunos (Híbrido)
- **Repositórios Públicos:** O A.C.O. realiza `git clone` anônimo direto, sem injetar credenciais que poderiam gerar conflito de permissão (`HTTP 403 Forbidden`).
- **Repositórios Privados:** Permite informar um **Token Git Pessoal (Deploy Token / PAT)** opcional no formulário de publicação, ou utilizar o `GITHUB_TOKEN` padrão configurado no `.env` do A.C.O.

---

## 5. Banco de Dados MariaDB / MySQL 1-Clique
- O script `execution/database_manager.py` provisiona bancos MariaDB com parâmetros de baixo consumo de RAM para a VM Micro:
  - `innodb_buffer_pool_size = 32M`
  - `performance_schema = OFF`
- Injeção das credenciais diretamente nas variáveis de ambiente do projeto:
  ```env
  DATABASE_URL="mysql://usr_<slug>:<senha>@127.0.0.1:3306/aco_<slug>"
  DB_CONNECTION="mysql"
  DB_HOST="127.0.0.1"
  DB_PORT="3306"
  DB_DATABASE="aco_<slug>"
  DB_USERNAME="usr_<slug>"
  DB_PASSWORD="<senha>"
  ```

---

## 6. Gestão de Tarefas e Eventos Cron
- **Arquivo no Repositório:** O A.C.O. busca arquivos `.cron` ou `crontab` na raiz do projeto e os aplica no deploy.
- **Painel Visual A.C.O.:** Uma nova aba dedicada **"Cron / Agendamentos"** no modal do projeto permite:
  - Ativar / pausar o agendamento (`enabled: true/false`).
  - Configurar expressões crontab com atalhos rápidos (`* * * * *`, `*/5 * * * *`, `0 * * * *`, `0 0 * * *`).
  - Definir o comando (ex: `php cron.php` ou `php artisan schedule:run`).
  - Botão **"Testar / Executar Agora"** para disparo manual imediato com visualização do código de retorno.
  - Console em tempo real exibindo a saída de logs em `/var/log/aco-cron/<slug>.log`.
  - Isolamento seguro em `/etc/cron.d/aco-<slug>`.

---

## 7. Provisionamento Automatizado na VM
O script `execution/provision_php_stack.sh` pode ser executado para preparar ou atualizar a VM Linux:
```bash
bash execution/provision_php_stack.sh
```

