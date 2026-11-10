#!/usr/bin/env bash
# ==============================================================================
# Camada 3 (Execucao): Importacao Integral do Banco de Dados LabWareNext (labw)
# Recria a base com UTF-8, desativa foreign keys temporariamente e importa
# todos os registros de vagas, empresas, RH, feedbacks e candidatos.
# ==============================================================================
set -euo pipefail

echo "=========================================================="
echo " 📥 Importando Dados Completos do LabWareNext no MariaDB"
echo "=========================================================="

SQL_FILE="/tmp/labware_full.sql"
REPO_SQL_URL="https://raw.githubusercontent.com/williamdevide/antigravity.vmOracle/main/execution/labware_full.sql"

# 1. Baixar o arquivo SQL integral se necessario
if [ ! -f "/opt/antigravity-oracle/execution/labware_full.sql" ]; then
    echo "[+] Baixando arquivo SQL completo do GitHub..."
    curl -sSL "$REPO_SQL_URL" -o "$SQL_FILE"
else
    SQL_FILE="/opt/antigravity-oracle/execution/labware_full.sql"
fi

# 2. Reset limpo do banco de dados labw com UTF-8
echo "[+] Recriando banco de dados labw com charset utf8mb4..."
sudo mysql -e "
DROP DATABASE IF EXISTS labw;
CREATE DATABASE labw CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

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

# 3. Importar com FOREIGN_KEY_CHECKS desativadas para garantir integridade
echo "[+] Importando tabelas e registros com FOREIGN_KEY_CHECKS=0..."
(echo "SET FOREIGN_KEY_CHECKS=0;"; cat "$SQL_FILE"; echo "SET FOREIGN_KEY_CHECKS=1;") | sudo mysql labw

# 4. Validar os dados importados
echo "=== VAGAS IMPORTADAS NO BANCO labw ==="
sudo mysql labw -e "
SELECT id_vaga, titulo, status, tipo, localizacao 
FROM vaga 
ORDER BY id_vaga DESC;
"

echo "=== CONTAGEM TOTAL DE REGISTROS ==="
sudo mysql labw -e "
SELECT 'vagas' AS tabela, COUNT(*) AS total FROM vaga
UNION ALL
SELECT 'empresas', COUNT(*) FROM empresa
UNION ALL
SELECT 'membros_rh', COUNT(*) FROM rh
UNION ALL
SELECT 'candidatos', COUNT(*) FROM candidato
UNION ALL
SELECT 'feedbacks', COUNT(*) FROM feedback;
"

# 5. Testar chamada da API de vagas localmente
echo "=== Testando api_vagas.php ==="
cd /var/www/projects/labwarenext
php -f api_vagas.php | grep -o '"title":[^,]*' | head -n 5 || true

echo "=========================================================="
echo " ✅ Dados importados com SUCESSO!"
echo " Recarregue: https://labwarenext.147.15.2.73.sslip.io"
echo "=========================================================="
