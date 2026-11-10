#!/usr/bin/env bash
# ==============================================================================
# Camada 3 (Execucao): Provisionamento Deterministico da Stack PHP + MariaDB + Cron
# Instala e prepara o ambiente para receber aplicacoes PHP (Laravel/Nativo/Symfony),
# banco de dados MariaDB/MySQL e agendamentos Cron no A.C.O. (Ubuntu 26.04)
# ==============================================================================
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

echo "=== [1/4] Instalando PHP-FPM, Extensoes Essenciais e Composer ==="
sudo apt-get update -y -q
sudo apt-get install -y -q \
    php-fpm \
    php-cli \
    php-mysql \
    php-mbstring \
    php-xml \
    php-curl \
    php-zip \
    php-intl \
    php-bcmath \
    php-sqlite3 \
    composer \
    cron

# Detectar e ativar versao do php-fpm (ex: php8.3-fpm)
PHP_FPM_SERVICE=$(systemctl list-unit-files | grep -E "php.*fpm\.service" | awk '{print $1}' | head -n 1 || true)
if [ -n "$PHP_FPM_SERVICE" ]; then
    echo "    -> Ativando servico $PHP_FPM_SERVICE..."
    sudo systemctl enable "$PHP_FPM_SERVICE"
    sudo systemctl start "$PHP_FPM_SERVICE"
else
    echo "    -> Aviso: servico php-fpm nao listado diretamente, tentando php-fpm padrao..."
    sudo systemctl enable php-fpm || true
    sudo systemctl start php-fpm || true
fi

echo "=== [2/4] Provisionando MariaDB / MySQL Tuned (Baixo Consumo) ==="
if ! command -v mariadb &>/dev/null && ! command -v mysql &>/dev/null; then
    sudo apt-get install -y -q mariadb-server
fi

sudo systemctl enable mariadb
sudo systemctl start mariadb

# Tuning de memoria MariaDB para VM modesta (Micro 1GB RAM)
sudo tee /etc/mysql/mariadb.conf.d/99-aco-tuning.cnf >/dev/null <<'EOF'
[mysqld]
performance_schema = OFF
innodb_buffer_pool_size = 32M
innodb_log_buffer_size = 4M
key_buffer_size = 8M
max_connections = 50
query_cache_size = 0
query_cache_type = 0
EOF

sudo systemctl restart mariadb
echo "    -> MariaDB otimizado e ativo (porta 3306)!"

echo "=== [3/4] Garantindo Daemon do Cron Ativo e Diretorios ==="
sudo systemctl enable cron
sudo systemctl start cron
sudo mkdir -p /etc/cron.d
sudo mkdir -p /var/log/aco-cron
sudo chmod 755 /etc/cron.d
sudo chmod 755 /var/log/aco-cron

echo "=== [4/4] Verificacao de Versoes Instaladas ==="
php -v | head -n 1
composer --version | head -n 1
mariadb --version || mysql --version

echo "=== [SUCESSO] Stack PHP, MariaDB e Cron provisionada com sucesso no A.C.O.! ==="

