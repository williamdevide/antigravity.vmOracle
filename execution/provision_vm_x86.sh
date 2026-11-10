#!/usr/bin/env bash
# ==============================================================================
# Camada 3 (Execucao): Provisionamento Deterministico da VM x86 (Ubuntu 26.04)
# 1. Configura 4 GB de Swap em disco (/swapfile) com swappiness otimizado
# 2. Libera portas 80 e 443 no iptables nativo da imagem Oracle Cloud
# 3. Instala Caddy (Reverse Proxy HTTPS), Node.js, npm, Python3 venv/pip e Git
# 4. Prepara estrutura /opt/antigravity-oracle, /var/www/projects e /etc/caddy/sites.d
# ==============================================================================
set -euo pipefail

echo "=== [1/5] Configurando 4 GB de Swap em /swapfile ==="
if ! swapon --show | grep -q "/swapfile"; then
    if [ ! -f /swapfile ]; then
        sudo fallocate -l 4G /swapfile || sudo dd if=/dev/zero of=/swapfile bs=1M count=4096
        sudo chmod 600 /swapfile
        sudo mkswap /swapfile
    fi
    sudo swapon /swapfile
    if ! grep -q "/swapfile" /etc/fstab; then
        echo "/swapfile none swap sw 0 0" | sudo tee -a /etc/fstab >/dev/null
    fi
    sudo sysctl vm.swappiness=15 >/dev/null
    sudo sysctl vm.vfs_cache_pressure=50 >/dev/null
    sudo tee /etc/sysctl.d/99-antigravity-swap.conf >/dev/null <<EOF
vm.swappiness=15
vm.vfs_cache_pressure=50
EOF
    echo "    -> Swap de 4 GB ativada com sucesso!"
else
    echo "    -> Swap ja estava ativa."
fi
free -h

echo "=== [2/5] Configurando Firewall Interno (iptables Oracle Cloud) ==="
# Imagens Ubuntu da Oracle Cloud usam iptables com regra REJECT no final da chain INPUT
if sudo iptables -L INPUT -n | grep -q "REJECT"; then
    if ! sudo iptables -C INPUT -p tcp --dport 80 -j ACCEPT 2>/dev/null; then
        sudo iptables -I INPUT 5 -m state --state NEW -p tcp --dport 80 -j ACCEPT
    fi
    if ! sudo iptables -C INPUT -p tcp --dport 443 -j ACCEPT 2>/dev/null; then
        sudo iptables -I INPUT 5 -m state --state NEW -p tcp --dport 443 -j ACCEPT
    fi
    if ! sudo iptables -C INPUT -p udp --dport 443 -j ACCEPT 2>/dev/null; then
        sudo iptables -I INPUT 5 -p udp --dport 443 -j ACCEPT
    fi
    if [ -d /etc/iptables ]; then
        sudo sh -c "iptables-save > /etc/iptables/rules.v4" || true
    fi
    echo "    -> Portas 80 e 443 liberadas no iptables!"
else
    echo "    -> Sem bloqueio REJECT no iptables."
fi

echo "=== [3/5] Instalando pacotes essenciais (Caddy, Node.js, Python3, Git) ==="
export DEBIAN_FRONTEND=noninteractive
sudo apt-get update -y -q
sudo apt-get install -y -q \
    caddy \
    nodejs \
    npm \
    python3-venv \
    python3-pip \
    python3-cryptography \
    git \
    curl \
    jq \
    psmisc

echo "=== [4/5] Preparando diretórios de projetos e permissoes ==="
sudo mkdir -p /opt/antigravity-oracle/.oci
sudo mkdir -p /opt/antigravity-oracle/execution
sudo mkdir -p /opt/antigravity-oracle/backend
sudo mkdir -p /opt/antigravity-oracle/frontend/dist
sudo mkdir -p /var/www/projects
sudo mkdir -p /etc/caddy/sites.d

sudo chown -R ubuntu:ubuntu /opt/antigravity-oracle
sudo chown -R ubuntu:ubuntu /var/www/projects
sudo chmod -R 755 /var/www/projects
sudo chown -R ubuntu:caddy /etc/caddy/sites.d
sudo chmod -R 775 /etc/caddy/sites.d
sudo rm -f /etc/sudoers.d/99-antigravity-deploy

echo "=== [5/5] Verificando versoes instaladas ==="
echo "Node: $(node -v)"
echo "NPM: $(npm -v)"
echo "Python: $(python3 --version)"
echo "Caddy: $(caddy version)"
echo "PROVISIONAMENTO CONCLUIDO COM SUCESSO!"
