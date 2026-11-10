#!/usr/bin/env bash
# ==============================================================================
# Camada 3 (Execucao): Ativacao dos Servicos Systemd e Caddy HTTPS na VM
# 1. Remove eventual arquivo sudoers invalido
# 2. Cria .venv e instala dependencias do Backend FastAPI
# 3. Configura servico systemd antigravity-dashboard.service (FastAPI porta 8000)
# 4. Configura servico systemd oci-arm-hunter.service (Robo Cacador ARM 24/7)
# 5. Configura /etc/caddy/Caddyfile (HTTPS 147.15.2.73.sslip.io + import sites.d)
# 6. Cria projeto vitrine inicial (https://demo.147.15.2.73.sslip.io)
# ==============================================================================
set -euo pipefail

sudo rm -f /etc/sudoers.d/99-antigravity-deploy

echo "=== [1/5] Configurando ambiente virtual Python do Backend FastAPI ==="
cd /opt/antigravity-oracle/backend
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
.venv/bin/pip install --upgrade pip -q
.venv/bin/pip install -r requirements.txt -q

echo "=== [2/5] Configurando servico systemd: antigravity-dashboard.service ==="
sudo tee /etc/systemd/system/antigravity-dashboard.service >/dev/null <<'EOF'
[Unit]
Description=Antigravity Cloud Orchestrator Backend (FastAPI)
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/antigravity-oracle/backend
Environment=OCI_VM_IP=147.15.2.73
ExecStart=/opt/antigravity-oracle/backend/.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

echo "=== [3/5] Configurando servico systemd: oci-arm-hunter.service (24/7) ==="
sudo tee /etc/systemd/system/oci-arm-hunter.service >/dev/null <<'EOF'
[Unit]
Description=Antigravity OCI ARM Instance Hunter 24/7 (VM.Standard.A1.Flex)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/antigravity-oracle/execution
ExecStart=/opt/antigravity-oracle/backend/.venv/bin/python3 /opt/antigravity-oracle/execution/oci_arm_hunter.py
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF

echo "=== [4/5] Configurando projeto vitrine inicial (demo.147.15.2.73.sslip.io) ==="
sudo mkdir -p /var/www/projects/demo
sudo chown -R ubuntu:ubuntu /var/www/projects
cat > /var/www/projects/demo/index.html <<'EOF'
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Demo Online — VM Oracle Cloud (Antigravity)</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="min-h-screen bg-slate-950 text-white flex items-center justify-center p-6">
  <div class="max-w-lg w-full p-8 rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl text-center space-y-4">
    <div class="inline-flex px-3 py-1 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 text-xs font-semibold">
      HTTPS Let's Encrypt Ativo • Subdomínio Dinâmico
    </div>
    <h1 class="text-2xl font-bold">🚀 Sua VM Oracle Cloud está no ar!</h1>
    <p class="text-sm text-slate-400 leading-relaxed">
      Este é um projeto de demonstração publicado automaticamente em <strong>https://demo.147.15.2.73.sslip.io</strong> usando Reverse Proxy Caddy.
    </p>
    <div class="pt-2">
      <a href="https://147.15.2.73.sslip.io" class="inline-block px-5 py-2.5 rounded-xl bg-red-600 hover:bg-red-500 text-white text-sm font-semibold transition">
        Voltar ao Painel Orquestrador
      </a>
    </div>
  </div>
</body>
</html>
EOF

cat > /etc/caddy/sites.d/demo.caddy <<'EOF'
demo.147.15.2.73.sslip.io {
    root * /var/www/projects/demo
    encode gzip
    file_server
}
EOF

if [ ! -f /opt/antigravity-oracle/execution/deployed_projects.json ]; then
cat > /opt/antigravity-oracle/execution/deployed_projects.json <<'EOF'
[
  {
    "slug": "demo",
    "repoUrl": "https://github.com/antigravity/demo-showcase",
    "projectType": "static",
    "domain": "demo.147.15.2.73.sslip.io",
    "url": "https://demo.147.15.2.73.sslip.io",
    "port": null,
    "workDir": "/var/www/projects/demo",
    "updatedAt": "2026-11-08T23:05:00-03:00",
    "status": "ONLINE",
    "lastBuildLog": "[+] Projeto vitrine estático inicializado com sucesso em /var/www/projects/demo\n[SUCESSO] HTTPS ativado em https://demo.147.15.2.73.sslip.io"
  }
]
EOF
fi

echo "=== [5/5] Configurando /etc/caddy/Caddyfile e iniciando servicos ==="
sudo chmod -R 755 /opt/antigravity-oracle/frontend
sudo chmod -R 755 /var/www/projects

sudo tee /etc/caddy/Caddyfile >/dev/null <<'EOF'
147.15.2.73.sslip.io, :80 {
    encode gzip

    handle /api/* {
        reverse_proxy 127.0.0.1:8000
    }

    handle {
        root * /opt/antigravity-oracle/frontend/dist
        try_files {path} /index.html
        file_server
    }
}

import /etc/caddy/sites.d/*.caddy
EOF

sudo systemctl daemon-reload
sudo systemctl enable antigravity-dashboard
sudo systemctl restart antigravity-dashboard
sudo systemctl enable oci-arm-hunter
sudo systemctl restart oci-arm-hunter
sudo systemctl enable caddy
sudo systemctl restart caddy

sleep 2
echo "--- STATUS DOS SERVICOS ---"
echo "Dashboard API: $(systemctl is-active antigravity-dashboard)"
echo "ARM Hunter 24/7: $(systemctl is-active oci-arm-hunter)"
echo "Caddy HTTPS: $(systemctl is-active caddy)"

