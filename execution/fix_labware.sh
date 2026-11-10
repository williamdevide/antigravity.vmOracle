#!/usr/bin/env bash
# ==============================================================================
# Camada 3 (Execucao): Diagnostico e Correcao Imediata do LabWareNext (PHP/MariaDB)
# ==============================================================================
set -euo pipefail

echo "=== [1/5] Verificando e Configurando MariaDB para labw ==="
sudo systemctl enable --now mariadb

# Garantir banco labw
sudo mysql -e "CREATE DATABASE IF NOT EXISTS labw CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# Configurar usuario labw com senha LabWare@2026 em localhost e 127.0.0.1
sudo mysql -e "
CREATE USER IF NOT EXISTS 'labw'@'localhost' IDENTIFIED BY 'LabWare@2026';
CREATE USER IF NOT EXISTS 'labw'@'127.0.0.1' IDENTIFIED BY 'LabWare@2026';
ALTER USER 'labw'@'localhost' IDENTIFIED BY 'LabWare@2026';
ALTER USER 'labw'@'127.0.0.1' IDENTIFIED BY 'LabWare@2026';
GRANT ALL PRIVILEGES ON labw.* TO 'labw'@'localhost';
GRANT ALL PRIVILEGES ON labw.* TO 'labw'@'127.0.0.1';
FLUSH PRIVILEGES;
"

# Testar conexao mysql com usuario labw
echo "[+] Testando conexao MariaDB com labw@127.0.0.1..."
mysql -u labw -p'LabWare@2026' -h 127.0.0.1 labw -e "SHOW TABLES;"

echo "=== [2/5] Configurando .env do LabWareNext com Permissoes Exatas ==="
PROJECT_DIR="/var/www/projects/labware"
sudo mkdir -p "$PROJECT_DIR/data" "$PROJECT_DIR/uploads"

# Gravar .env limpo com permissoes
echo "REJfSE9TVD0xMjcuMC4wLjEKREJfVVNFUj1sYWJ3CkRCX1BBU1M9TGFiV2FyZUAyMDI2CkRCX05BTUU9bGFidwpHRU1JTklfQVBJX0tFWT1BUS5BYjhSTjZMZFR3RnYxWWRONS0yT0xORTFSVGlIRUtMRGNIM1NqcWJqUEwtc3VnbjV6UQpDUk9OX1RPS0VOPWs3ai1QMnFMOW1felg1Yk4td1kzVC1yUThlRgo=" | base64 -d | sudo tee "$PROJECT_DIR/.env" >/dev/null

# Permissoes cruciais para www-data (PHP-FPM)
sudo chown -R www-data:www-data "$PROJECT_DIR"
sudo chmod -R 775 "$PROJECT_DIR"
sudo chmod 644 "$PROJECT_DIR/.env"

echo "=== [3/5] Testando index.php diretamente via CLI do PHP ==="
cd "$PROJECT_DIR"
php -r "
require 'config.php';
echo 'Conexao com banco Labw realizada com SUCESSO! Charset: ' . \$conn->character_set_name() . PHP_EOL;
" || {
    echo "[-] Erro ao carregar config.php via CLI!"
}

echo "=== [4/5] Verificando PHP-FPM e Caddy ==="
sudo systemctl restart php*-fpm
sudo systemctl reload caddy || sudo systemctl restart caddy

echo "=== [5/5] Teste HTTP Local com curl ==="
curl -s -o /dev/null -w "HTTP Status LabWare: %{http_code}\n" -H "Host: labware.147.15.2.73.sslip.io" http://127.0.0.1/ || true

echo "=========================================================="
echo " ✅ Correcao aplicada! Acesse: https://labware.147.15.2.73.sslip.io"
echo "=========================================================="
