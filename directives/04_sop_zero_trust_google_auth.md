# 📋 SOP 04: Autenticação Zero-Trust via Google Sign-In (Firebase Auth)

## 1. Objetivo ("O Quê" e "Por Quê")
Proteger integralmente o Painel Web Orquestrador (`https://147.15.2.73.sslip.io`) e todas as rotas da API FastAPI (`/api/*`), garantindo que **exclusivamente** o proprietário autenticado via Google com a conta principal `williamdevide@gmail.com` possa visualizar telemetria da VM, controlar o Robô ARM ou publicar/remover projetos.

## 2. Arquitetura de Segurança em Duas Camadas (Frontend + Backend)
1. **Camada Cliente (Frontend React + Firebase Auth SDK):**
   - Projeto Firebase dedicado: `antigravityvmoracle`.
   - Provedor único: `GoogleAuthProvider` (`prompt: 'select_account'`).
   - Caso um usuário autentique no Google com qualquer e-mail diferente de `williamdevide@gmail.com`, o cliente executa `signOut(auth)` imediatamente e exibe tela de bloqueio (`403 Acesso Negado`).
2. **Camada Servidor (Backend FastAPI — Validação Criptográfica e Identity Toolkit):**
   - Nenhuma rota de gerenciamento ou telemetria (`/api/system-status`, `/api/arm-hunter`, `/api/arm-hunter/action`, `/api/github/repos`, `/api/projects`, `/api/projects/deploy`, `DELETE /api/projects/{slug}`) responde sem o cabeçalho `Authorization: Bearer <Firebase_ID_Token>`.
   - O backend valida o `idToken` diretamente na API oficial do Google Identity Toolkit (`https://identitytoolkit.googleapis.com/v1/accounts:lookup`) e verifica os claims do JWT (`aud == "antigravityvmoracle"`, `email_verified == true` e `email == "williamdevide@gmail.com"`).
   - Requisições sem token recebem `401 Unauthorized`; requisições com token válido de qualquer outro e-mail recebem `403 Forbidden`.
3. **Escopo Público Preservado:**
   - Os pequenos projetos publicados pelo administrador nos subdomínios `https://<projeto>.147.15.2.73.sslip.io` permanecem públicos para acesso normal na web.

