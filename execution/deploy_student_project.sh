#!/usr/bin/env bash
# ==============================================================================
# Camada 3 (Execucao): Deploy Deterministico do Projeto Aluno (LabWareNext)
# PHP 8.3 FPM + MariaDB (labw) + Caddy HTTPS + Cron + A.C.O. Card
# ==============================================================================
set -euo pipefail

echo "=========================================================="
echo " 🚀 Deploy do Projeto do Aluno: LabWareNext na VM Oracle"
echo "=========================================================="

SLUG="labware"
PROJECT_DIR="/var/www/projects/$SLUG"
REPO_URL="https://github.com/Antonio-augustos2/CTDS-2026-02-Sistema-LabWareNext-Antonio-Isabelle-Nicolle.git"
VM_IP="147.15.2.73"
DOMAIN="$SLUG.$VM_IP.sslip.io"
ACO_DIR="/opt/antigravity-oracle"

# 1. Corrigir permissoes da plataforma A.C.O. (Elimina Errno 13 Permission Denied)
echo "[+] Corrigindo permissoes da pasta $ACO_DIR para usuario ubuntu..."
sudo chown -R ubuntu:ubuntu "$ACO_DIR"
sudo chmod -R 775 "$ACO_DIR/execution"
if [ -f "$ACO_DIR/execution/deployed_projects.json" ]; then
    sudo chmod 664 "$ACO_DIR/execution/deployed_projects.json"
fi

# 2. Garantir instalacao da stack PHP 8.3 e MariaDB
echo "[+] Verificando pacotes necessarios (PHP-FPM, MariaDB, Cron)..."
export DEBIAN_FRONTEND=noninteractive
sudo apt-get update -y -q
sudo apt-get install -y -q \
    php-fpm php-mysql php-curl php-gd php-mbstring php-xml php-zip php-json \
    mariadb-server mariadb-client cron curl git

# 3. Iniciar e habilitar servicos
sudo systemctl enable --now mariadb
sudo systemctl enable --now cron
sudo systemctl enable --now php*-fpm

# 4. Criar e configurar o Banco de Dados MariaDB (labw)
echo "[+] Configurando banco de dados MariaDB: labw..."
sudo mysql -e "CREATE DATABASE IF NOT EXISTS labw CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
sudo mysql -e "CREATE USER IF NOT EXISTS 'labw'@'localhost' IDENTIFIED BY 'LabWare@2026';"
sudo mysql -e "CREATE USER IF NOT EXISTS 'labw'@'127.0.0.1' IDENTIFIED BY 'LabWare@2026';"
sudo mysql -e "GRANT ALL PRIVILEGES ON labw.* TO 'labw'@'localhost';"
sudo mysql -e "GRANT ALL PRIVILEGES ON labw.* TO 'labw'@'127.0.0.1';"
sudo mysql -e "FLUSH PRIVILEGES;"

# 5. Importar o script SQL do projeto
echo "[+] Importando estrutura e dados para o banco labw..."
SQL_TMP="/tmp/labw_schema.sql"
cat > "$SQL_TMP" <<'SQL_EOF'
CREATE TABLE IF NOT EXISTS `acesso` (
  `id_acesso` int(11) NOT NULL AUTO_INCREMENT,
  `id_vaga` int(11) NOT NULL,
  `titulo_vaga` varchar(150) DEFAULT NULL,
  `visitor_id` char(64) DEFAULT NULL,
  `data_acesso` timestamp NOT NULL DEFAULT current_timestamp(),
  `tipo_acesso` varchar(30) NOT NULL DEFAULT 'pagina_vaga',
  PRIMARY KEY (`id_acesso`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `candidato` (
  `id_candidato` int(11) NOT NULL AUTO_INCREMENT,
  `nome` varchar(150) NOT NULL,
  `email` varchar(150) NOT NULL,
  `telefone` varchar(30) DEFAULT NULL,
  `cidade` varchar(100) DEFAULT NULL,
  `linkedin` varchar(255) DEFAULT NULL,
  `github` varchar(255) DEFAULT NULL,
  `portfolio` varchar(255) DEFAULT NULL,
  `curriculo_path` varchar(255) DEFAULT NULL,
  `curriculo_texto` mediumtext DEFAULT NULL,
  `data_cadastro` timestamp NOT NULL DEFAULT current_timestamp(),
  `status` enum('Pendente','Em analise','Aprovado','Reprovado') NOT NULL DEFAULT 'Pendente',
  PRIMARY KEY (`id_candidato`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `vaga` (
  `id_vaga` int(11) NOT NULL AUTO_INCREMENT,
  `titulo` varchar(150) NOT NULL,
  `descricao` text NOT NULL,
  `requisitos` text DEFAULT NULL,
  `status` enum('Aberta','Encerrada','Em analise') NOT NULL DEFAULT 'Aberta',
  `data_criacao` timestamp NOT NULL DEFAULT current_timestamp(),
  `localizacao` varchar(100) DEFAULT 'Remoto',
  `tipo_contrato` varchar(50) DEFAULT 'CLT',
  PRIMARY KEY (`id_vaga`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `candidatura` (
  `id_candidatura` int(11) NOT NULL AUTO_INCREMENT,
  `id_candidato` int(11) NOT NULL,
  `id_vaga` int(11) NOT NULL,
  `data_candidatura` timestamp NOT NULL DEFAULT current_timestamp(),
  `aderencia_geral` decimal(5,2) DEFAULT NULL,
  `resumo_analise` text DEFAULT NULL,
  `pontos_fortes` text DEFAULT NULL,
  `pontos_atencao` text DEFAULT NULL,
  `status_analise` enum('Pendente','Em analise','Concluida','Erro') NOT NULL DEFAULT 'Pendente',
  PRIMARY KEY (`id_candidatura`),
  KEY `fk_candidatura_candidato` (`id_candidato`),
  KEY `fk_candidatura_vaga` (`id_vaga`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `membro_rh` (
  `id_membro` int(11) NOT NULL AUTO_INCREMENT,
  `nome` varchar(120) NOT NULL,
  `email` varchar(150) NOT NULL,
  `senha_hash` varchar(255) NOT NULL,
  `ativo` tinyint(1) NOT NULL DEFAULT 1,
  `criado_em` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id_membro`),
  UNIQUE KEY `idx_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `api_error_log` (
  `id_log` int(11) NOT NULL AUTO_INCREMENT,
  `endpoint` varchar(100) DEFAULT NULL,
  `mensagem_erro` text DEFAULT NULL,
  `payload_resumo` text DEFAULT NULL,
  `criado_em` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id_log`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
SQL_EOF

sudo mysql labw < "$SQL_TMP"
rm -f "$SQL_TMP"

# 6. Clonar ou atualizar o repositório do aluno
echo "[+] Clonando repositorio do aluno em $PROJECT_DIR..."
sudo mkdir -p /var/www/projects
if [ -d "$PROJECT_DIR/.git" ]; then
    sudo git -C "$PROJECT_DIR" pull origin main || true
else
    sudo rm -rf "$PROJECT_DIR"
    sudo git clone "$REPO_URL" "$PROJECT_DIR"
fi

# 7. Injetar o arquivo .env
echo "[+] Configurando arquivo .env do LabWareNext..."
echo "REJfSE9TVCA9ICcxMjcuMC4wLjEnCkRCX1VTRVIgPSAnbGFidycKREJfUEFTUyA9ICdMYWJXYXJlQDIwMjYnCkRCX05BTUUgPSAnbGFidycKR0VNSU5JX0FQSV9LRVk9IkFRLkFiOFJONkxkVHdGdjFZZE41LTJPTE5FMVJUaUhFS0xEY0gzU2pxYmpQTC1zdWduNXpRIgpDUk9OX1RPS0VOID0gazdqLVAycUw5bV96WDViTi13WTNULXJROGVGCg==" | base64 -d | sudo tee "$PROJECT_DIR/.env" >/dev/null

# 8. Criar diretorios necessarios de dados e uploads com permissoes
sudo mkdir -p "$PROJECT_DIR/data" "$PROJECT_DIR/uploads"
sudo chown -R www-data:www-data "$PROJECT_DIR"
sudo chmod -R 775 "$PROJECT_DIR/data" "$PROJECT_DIR/uploads"

# 9. Descobrir socket do PHP-FPM e configurar Caddy
PHP_SOCK=$(find /run/php/ -name "php*-fpm.sock" 2>/dev/null | sort -V | tail -n 1)
if [ -z "$PHP_SOCK" ]; then
    PHP_SOCK="/run/php/php8.3-fpm.sock"
fi
echo "[+] Usando PHP-FPM socket: $PHP_SOCK"

sudo mkdir -p /etc/caddy/sites.d
sudo tee "/etc/caddy/sites.d/$SLUG.caddy" >/dev/null <<EOF
$DOMAIN {
    root * $PROJECT_DIR
    encode gzip
    php_fastcgi unix/$PHP_SOCK
    file_server
}
EOF

# 10. Configurar tarefa Cron dedicada (/etc/cron.d/aco-project-labware)
echo "[+] Configurando evento Cron para analise automatica de curriculos (a cada 10 min)..."
sudo mkdir -p /var/log/aco-cron
sudo touch "/var/log/aco-cron/$SLUG.log"
sudo chown -R www-data:www-data /var/log/aco-cron

sudo tee "/etc/cron.d/aco-project-$SLUG" >/dev/null <<EOF
# Tarefa Cron Gerenciada pelo A.C.O. - Projeto LabWareNext
*/10 * * * * www-data /usr/bin/php $PROJECT_DIR/cron_analisar.php >> /var/log/aco-cron/$SLUG.log 2>&1
EOF
sudo chmod 644 "/etc/cron.d/aco-project-$SLUG"

# 11. Registrar o projeto no deployed_projects.json do A.C.O.
echo "[+] Registrando projeto no catalogo de cards do A.C.O..."
sudo python3 -c '
import json, os, datetime

p = "/opt/antigravity-oracle/execution/deployed_projects.json"
os.makedirs(os.path.dirname(p), exist_ok=True)
data = json.load(open(p)) if os.path.exists(p) else []

now_iso = datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(timespec="seconds")
slug = "labware"

found = False
for item in data:
    if item.get("slug") == slug:
        item["status"] = "ONLINE"
        item["domain"] = "https://labware.147.15.2.73.sslip.io"
        item["url"] = "https://labware.147.15.2.73.sslip.io"
        item["updatedAt"] = now_iso
        item["architecture"] = "php"
        item["cronSchedule"] = "*/10 * * * *"
        item["cronCommand"] = "php /var/www/projects/labware/cron_analisar.php"
        found = True
        break

if not found:
    data.append({
        "slug": slug,
        "name": "LabWareNext (Recrutamento & IA)",
        "repo": "https://github.com/Antonio-augustos2/CTDS-2026-02-Sistema-LabWareNext-Antonio-Isabelle-Nicolle.git",
        "repoUrl": "https://github.com/Antonio-augustos2/CTDS-2026-02-Sistema-LabWareNext-Antonio-Isabelle-Nicolle.git",
        "architecture": "php",
        "status": "ONLINE",
        "port": None,
        "domain": "https://labware.147.15.2.73.sslip.io",
        "url": "https://labware.147.15.2.73.sslip.io",
        "workDir": "/var/www/projects/labware",
        "cronSchedule": "*/10 * * * *",
        "cronCommand": "php /var/www/projects/labware/cron_analisar.php",
        "autoDeploy": True,
        "updatedAt": now_iso,
        "lastBuildLog": "[SUCESSO] PHP 8.3 + MariaDB (labw) + Cron configurados e online!"
    })

with open(p, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)

print("[+] deployed_projects.json atualizado com sucesso!")
'

# 12. Recarregar servicos
sudo chown -R ubuntu:ubuntu "$ACO_DIR"
sudo systemctl reload caddy || sudo systemctl restart caddy
sudo systemctl restart antigravity-dashboard

echo "=========================================================="
echo " ✅ Projeto LabWareNext implantado com sucesso!"
echo " URL: https://$DOMAIN"
echo " Painel: https://$VM_IP.sslip.io"
echo " Banco: MariaDB 'labw' ativo"
echo " Cron: Ativo a cada 10 min (logs em /var/log/aco-cron/$SLUG.log)"
echo "=========================================================="
