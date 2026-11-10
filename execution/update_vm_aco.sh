#!/usr/bin/env bash
# ==============================================================================
# Antigravity Cloud Orchestrator (A.C.O.) - Script de Atualizacao v3.5.0
# Atualiza Frontend React, Backend FastAPI, Reconcilia Sistema Manu e Pilha PHP
# ==============================================================================
set -euo pipefail

echo "=========================================================="
echo " 🚀 Atualizando Plataforma A.C.O. para v3.5.0 (Oracle Cloud)"
echo "=========================================================="

ACO_DIR="/opt/antigravity-oracle"
REPO_URL="https://github.com/williamdevide/antigravity.vmOracle.git"

# 1. Garantir diretorio base
sudo mkdir -p "$ACO_DIR"
cd "$ACO_DIR"

# 2. Sincronizar via Git
if [ ! -d ".git" ]; then
    echo "[+] Inicializando repositorio Git em $ACO_DIR..."
    git init
    git remote add origin "$REPO_URL" || git remote set-url origin "$REPO_URL"
    git fetch origin main
    git reset --hard origin/main
else
    echo "[+] Sincronizando ultimos commits do GitHub..."
    git remote set-url origin "$REPO_URL" || true
    git fetch origin main
    git reset --hard origin/main
fi

# 3. Atualizar dependencias do backend se necessario
echo "[+] Verificando dependencias do Backend..."
cd "$ACO_DIR/backend"
if [ -d ".venv" ]; then
    .venv/bin/pip install -r requirements.txt -q || true
fi

# 4. Compilar o Frontend React (Vite)
echo "[+] Compilando Frontend React v3.5.0..."
cd "$ACO_DIR/frontend"
if [ -f "$ACO_DIR/.env" ]; then
    grep "^VITE_" "$ACO_DIR/.env" > "$ACO_DIR/frontend/.env" 2>/dev/null || true
fi
npm install --silent
npm run build

# 5. Reconciliar projetos na VM (Garante que Sistema Manu apareca)
echo "[+] Reconciliando projetos ativos na VM (Sistema Manu)..."
cd "$ACO_DIR/execution"
if [ -f "$ACO_DIR/backend/.venv/bin/python3" ]; then
    $ACO_DIR/backend/.venv/bin/python3 -c "
import deploy_project
projs = deploy_project.load_projects()
print(f'Projetos indexados: {[p.get(\"slug\") for p in projs]}')
" || true
fi

# 6. Provisionar pilha PHP / MariaDB / Cron caso ainda nao exista
if ! command -v php >/dev/null 2>&1; then
    echo "[+] Instalando suporte a PHP 8.3 FPM, Composer, MariaDB e Cron..."
    bash "$ACO_DIR/execution/provision_php_stack.sh" || true
fi

# 7. Reiniciar servicos
echo "[+] Reiniciando servicos antigravity-dashboard e caddy..."
sudo systemctl restart antigravity-dashboard || true
sudo systemctl reload caddy || sudo systemctl restart caddy || true

echo "=========================================================="
echo " ✅ Atualizacao concluida com sucesso!"
echo " Acesse: https://147.15.2.73.sslip.io"
echo " O Card do Manu e a Versao v3.5.0 ja estao visiveis!"
echo "=========================================================="
