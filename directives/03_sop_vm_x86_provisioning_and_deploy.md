# 📋 SOP 03: Provisionamento da VM x86, Swap, HTTPS e Publicação de Projetos

## 1. Objetivo ("O Quê" e "Por Quê")
Transformar a instância modesta `VM.Standard.E2.1.Micro` (1 OCPU, 951 MB de RAM física, Ubuntu 26.04 LTS) em um servidor de aplicação resiliente, seguro e fácil de operar por usuários sem experiência prévia em Linux, permitindo publicar pequenos projetos Web e APIs com HTTPS automático gratuito.

## 2. Arquitetura de Estabilidade na VM Micro
1. **Memória Swap (4 GB em `/swapfile`):** Impede que o *OOM Killer* do kernel Linux derrube processos durante compilação de projetos (`npm run build` / `vite build`) ou picos de uso. Configurado com `vm.swappiness=15`.
2. **Firewall Interno (Netfilter / UFW / iptables):** Libera explicitamente o tráfego de entrada nas portas `22` (SSH), `80` (HTTP) e `443` (HTTPS) no sistema operacional.
3. **Reverse Proxy com HTTPS Automático (Caddy + `sslip.io`):**
   - Domínio principal do Painel Orquestrador: `https://147.15.2.73.sslip.io`
   - Subdomínios dinâmicos por projeto publicado: `https://<slug-do-projeto>.147.15.2.73.sslip.io`
   - Certificados TLS/SSL emitidos e renovados automaticamente via Let's Encrypt / ZeroSSL pelo Caddy.
4. **Motor de Deploy 1-Clique:**
   - Suporta repositórios GitHub de **Sites Estáticos (HTML/CSS/JS)**, **SPAs (React/Vite)**, **APIs Node.js** e **APIs Python (FastAPI/Flask)**.
   - Configura diretórios em `/var/www/projects/<slug>`, serviços `systemd` (para backends) e blocos de roteamento em `/etc/caddy/sites.d/<slug>.caddy`.

