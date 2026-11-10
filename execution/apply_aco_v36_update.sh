#!/usr/bin/env bash
# ==============================================================================
# Camada 3 (Execucao): Atualizacao A.C.O. v3.6.0
# Corrige permissoes .aco.env, limpa resquicio do labware, compila novo frontend
# com arvore de arquivos e explorador de banco de dados (estrutura e dados).
# ==============================================================================
set -euo pipefail

echo "=========================================================="
echo " 🚀 Atualizando Plataforma A.C.O. para v3.6.0 (Oracle Cloud)"
echo "=========================================================="

ACO_DIR="/opt/antigravity-oracle"
REPO_URL="https://github.com/williamdevide/antigravity.vmOracle.git"

# 1. Puxar ultimos commits do GitHub
cd "$ACO_DIR"
git remote set-url origin "$REPO_URL" || true
git fetch origin main
git reset --hard origin/main

# 2. Corrigir permissoes universais
echo "[+] Configurando permissoes de sistema para ubuntu e www-data..."
sudo usermod -a -G www-data ubuntu || true
sudo chown -R ubuntu:ubuntu "$ACO_DIR"
sudo chmod -R 775 "$ACO_DIR/execution"
if [ -f "$ACO_DIR/execution/deployed_projects.json" ]; then
    sudo chmod 664 "$ACO_DIR/execution/deployed_projects.json"
fi

# Permissoes em /var/www/projects para evitar [Errno 13] Permission Denied
sudo mkdir -p /var/www/projects
sudo chown -R www-data:ubuntu /var/www/projects
sudo chmod -R 775 /var/www/projects
sudo find /var/www/projects -type d -exec chmod 775 {} + || true

# 3. Remover definitivamente os resquicios do projeto labware excluido
echo "[+] Limpando arquivos e rotas do projeto labware removido..."
sudo rm -f /etc/caddy/sites.d/labware.caddy /etc/caddy/sites.d/labware.caddy.disabled || true
sudo rm -rf /var/www/projects/labware || true
sudo rm -f /etc/cron.d/aco-labware /etc/cron.d/aco-project-labware || true

# Limpar labware do deployed_projects.json
sudo python3 -c '
import json, os
p = "/opt/antigravity-oracle/execution/deployed_projects.json"
if os.path.exists(p):
    data = json.load(open(p))
    filtered = [x for x in data if x.get("slug") != "labware"]
    json.dump(filtered, open(p, "w"), indent=2)
    print(f"[+] deployed_projects.json limpo. Projetos ativos: {[x.get(\"slug\") for x in filtered]}")
'

# 4. Atualizar dependencias do Backend se necessario
cd "$ACO_DIR/backend"
if [ -d ".venv" ]; then
    .venv/bin/pip install -r requirements.txt -q || true
fi

# 5. Compilar o Frontend React (Vite) com as novas telas
echo "[+] Compilando Frontend React v3.6.0 (Arvore de Arquivos + DB Explorer)..."
cd "$ACO_DIR/frontend"
if [ -f "$ACO_DIR/.env" ]; then
    grep "^VITE_" "$ACO_DIR/.env" > "$ACO_DIR/frontend/.env" 2>/dev/null || true
fi
npm install --silent
npm run build

# 6. Reiniciar os servicos
sudo chown -R ubuntu:ubuntu "$ACO_DIR"
sudo systemctl restart antigravity-dashboard
sudo systemctl reload caddy || sudo systemctl restart caddy

echo "=========================================================="
echo " ✅ Atualizacao concluida com SUCESSO!"
echo " Acesse: https://147.15.2.73.sslip.io"
echo " 📁 Arvore de Arquivos: no modal do projeto (aba 'Arquivos')"
echo " 🗄️ Explorador de BD: na aba 'Bancos de Dados 1-Clique'"
echo "=========================================================="
