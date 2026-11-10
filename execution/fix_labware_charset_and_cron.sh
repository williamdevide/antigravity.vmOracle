#!/usr/bin/env bash
# ==============================================================================
# Camada 3 (Execucao): Wrapper para Correcao de Charset e Cron no LabWareNext
# ==============================================================================
set -euo pipefail

ACO_DIR="/opt/antigravity-oracle"

echo "=========================================================="
echo " 📥 Atualizando repositorio e rodando fix_labware_data_and_cron.py"
echo "=========================================================="

cd "$ACO_DIR"
git fetch origin main || true
git reset --hard origin/main || true

sudo python3 "$ACO_DIR/execution/fix_labware_data_and_cron.py"

echo "=========================================================="
echo " ✅ Operacao finalizada. Reiniciando servicos se necessario..."
echo "=========================================================="
sudo systemctl reload caddy || true
