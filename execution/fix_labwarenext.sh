#!/usr/bin/env bash
# ==============================================================================
# Camada 3 (Execucao): Correcao Definitiva para labware e labwarenext
# ==============================================================================
set -euo pipefail

echo "=========================================================="
echo " 🚀 Sincronizando e Corrigindo LabWare / LabWareNext"
echo "=========================================================="

VM_IP="147.15.2.73"
REPO_URL="https://github.com/Antonio-augustos2/CTDS-2026-02-Sistema-LabWareNext-Antonio-Isabelle-Nicolle.git"
SQL_DUMP="/tmp/labw_schema.sql"

# 1. Configurar MariaDB de forma ultra permissiva e robusta
echo "[+] Configurando MariaDB (labw)..."
sudo systemctl enable --now mariadb

sudo mysql -e "CREATE DATABASE IF NOT EXISTS labw CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# Criar usuario labw em localhost, 127.0.0.1 e %
sudo mysql -e "
CREATE USER IF NOT EXISTS 'labw'@'localhost' IDENTIFIED BY 'LabWare@2026';
CREATE USER IF NOT EXISTS 'labw'@'127.0.0.1' IDENTIFIED BY 'LabWare@2026';
CREATE USER IF NOT EXISTS 'labw'@'%' IDENTIFIED BY 'LabWare@2026';
ALTER USER 'labw'@'localhost' IDENTIFIED BY 'LabWare@2026';
ALTER USER 'labw'@'127.0.0.1' IDENTIFIED BY 'LabWare@2026';
ALTER USER 'labw'@'%' IDENTIFIED BY 'LabWare@2026';
GRANT ALL PRIVILEGES ON labw.* TO 'labw'@'localhost';
GRANT ALL PRIVILEGES ON labw.* TO 'labw'@'127.0.0.1';
GRANT ALL PRIVILEGES ON labw.* TO 'labw'@'%';
FLUSH PRIVILEGES;
"

# 2. Garantir tabelas no banco labw
cat > "$SQL_DUMP" <<'SQL_EOF'
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

sudo mysql labw < "$SQL_DUMP"
rm -f "$SQL_DUMP"

# Inserir vaga de teste caso tabela esteja vazia
sudo mysql labw -e "
INSERT IGNORE INTO vaga (id_vaga, titulo, descricao, requisitos, status, localizacao, tipo_contrato)
VALUES (1, 'Desenvolvedor Full Stack PHP', 'Oportunidade para atuar no ecossistema LabWareNext com PHP 8 e IA.', 'PHP 8, MariaDB/MySQL, Git', 'Aberta', 'Remoto', 'CLT');
"

# 3. Descobrir PHP-FPM socket
PHP_SOCK=$(find /run/php/ -name "php*-fpm.sock" 2>/dev/null | sort -V | tail -n 1)
if [ -z "$PHP_SOCK" ]; then
    PHP_SOCK="/run/php/php8.3-fpm.sock"
fi
echo "[+] PHP Socket identificado: $PHP_SOCK"

# 4. Configurar AMBOS os slugs: labware e labwarenext
for SLUG in "labware" "labwarenext"; do
    TARGET_DIR="/var/www/projects/$SLUG"
    echo "--- Configurando $SLUG em $TARGET_DIR ---"
    sudo mkdir -p "$TARGET_DIR"

    # Se a pasta nao tiver os arquivos PHP, clonar do repositorio
    if [ ! -f "$TARGET_DIR/config.php" ]; then
        echo "[+] Clonando repositorio em $TARGET_DIR..."
        sudo git clone "$REPO_URL" "$TARGET_DIR" || true
    fi

    # Gravar o .env decodificado com permissoes universais
    echo "REJfSE9TVD0xMjcuMC4wLjEKREJfVVNFUj1sYWJ3CkRCX1BBU1M9TGFiV2FyZUAyMDI2CkRCX05BTUU9bGFidwpHRU1JTklfQVBJX0tFWT1BUS5BYjhSTjZMZFR3RnYxWWRONS0yT0xORTFSVGlIRUtMRGNIM1NqcWJqUEwtc3VnbjV6UQpDUk9OX1RPS0VOPWs3ai1QMnFMOW1felg1Yk4td1kzVC1yUThlRgo=" | base64 -d | sudo tee "$TARGET_DIR/.env" >/dev/null

    # Criar subpastas necessarias
    sudo mkdir -p "$TARGET_DIR/data" "$TARGET_DIR/uploads"

    # Ajustar permissoes para www-data e ubuntu
    sudo chown -R www-data:www-data "$TARGET_DIR"
    sudo chmod -R 775 "$TARGET_DIR"
    sudo chmod 664 "$TARGET_DIR/.env"

    # Configurar Caddy para este slug
    sudo tee "/etc/caddy/sites.d/$SLUG.caddy" >/dev/null <<CADDY_EOF
$SLUG.$VM_IP.sslip.io {
    root * $TARGET_DIR
    encode gzip
    php_fastcgi unix/$PHP_SOCK
    file_server
}
CADDY_EOF

    # Configurar tarefa Cron
    sudo tee "/etc/cron.d/aco-project-$SLUG" >/dev/null <<CRON_EOF
*/10 * * * * www-data /usr/bin/php $TARGET_DIR/cron_analisar.php >> /var/log/aco-cron/$SLUG.log 2>&1
CRON_EOF
    sudo chmod 644 "/etc/cron.d/aco-project-$SLUG"
done

# 5. Criar diretorio de logs do Cron
sudo mkdir -p /var/log/aco-cron
sudo chown -R www-data:www-data /var/log/aco-cron

# 6. Testar conexao PHP CLI diretamente
echo "=== Teste de Conexao PHP com o Banco labw ==="
php -r "
define('DB_HOST', '127.0.0.1');
define('DB_USER', 'labw');
define('DB_PASS', 'LabWare@2026');
define('DB_NAME', 'labw');
mysqli_report(MYSQLI_REPORT_OFF);
\$conn = new mysqli(DB_HOST, DB_USER, DB_PASS, DB_NAME);
if (\$conn->connect_error) {
    echo '[-] FALHA NA CONEXAO: ' . \$conn->connect_error . PHP_EOL;
    exit(1);
} else {
    echo '[+] SUCESSO: Conectado ao MariaDB labw! Tabelas encontradas:' . PHP_EOL;
    \$res = \$conn->query('SHOW TABLES');
    while (\$row = \$res->fetch_array()) {
        echo '    - ' . \$row[0] . PHP_EOL;
    }
}
"

# 7. Atualizar deployed_projects.json para incluir labware e labwarenext
sudo python3 -c '
import json, os, datetime

p = "/opt/antigravity-oracle/execution/deployed_projects.json"
os.makedirs(os.path.dirname(p), exist_ok=True)
data = json.load(open(p)) if os.path.exists(p) else []
now_iso = datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(timespec="seconds")

for slug, name in [("labware", "LabWareNext"), ("labwarenext", "LabWareNext (Sistema RH & IA)")]:
    found = False
    for item in data:
        if item.get("slug") == slug:
            item["status"] = "ONLINE"
            item["domain"] = f"https://{slug}.147.15.2.73.sslip.io"
            item["url"] = f"https://{slug}.147.15.2.73.sslip.io"
            item["architecture"] = "php"
            item["updatedAt"] = now_iso
            found = True
            break
    if not found:
        data.append({
            "slug": slug,
            "name": name,
            "repo": "https://github.com/Antonio-augustos2/CTDS-2026-02-Sistema-LabWareNext-Antonio-Isabelle-Nicolle.git",
            "repoUrl": "https://github.com/Antonio-augustos2/CTDS-2026-02-Sistema-LabWareNext-Antonio-Isabelle-Nicolle.git",
            "architecture": "php",
            "status": "ONLINE",
            "port": None,
            "domain": f"https://{slug}.147.15.2.73.sslip.io",
            "url": f"https://{slug}.147.15.2.73.sslip.io",
            "workDir": f"/var/www/projects/{slug}",
            "cronSchedule": "*/10 * * * *",
            "cronCommand": f"php /var/www/projects/{slug}/cron_analisar.php",
            "autoDeploy": True,
            "updatedAt": now_iso
        })

with open(p, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
'

# 8. Reiniciar servicos
sudo chown -R ubuntu:ubuntu /opt/antigravity-oracle
sudo systemctl restart php*-fpm
sudo systemctl reload caddy || sudo systemctl restart caddy
sudo systemctl restart antigravity-dashboard

echo "=========================================================="
echo " ✅ Sincronizacao concluida com SUCESSO!"
echo " Ambos os enderecos estao ativos e operacionais:"
echo " 🌐 https://labwarenext.147.15.2.73.sslip.io"
echo " 🌐 https://labware.147.15.2.73.sslip.io"
echo "=========================================================="
