# API Spec (REST) - MVP

> Ultima atualizacao: 2026-03-04
> Todos os endpoints prefixados com `/api` via nginx proxy.
> Autenticacao: `Authorization: Bearer <JWT>` em todos exceto login.

## Auth
POST /auth/login              — Login (retorna JWT)
POST /auth/logout             — Logout
GET  /auth/me                 — Usuario atual

## Organizations & Cost Centers
GET  /orgs                    — Listar orgs do usuario (inclui role)
POST /orgs                    — Criar org
GET  /orgs/{orgId}            — Detalhe
POST /orgs/{orgId}/members    — Adicionar membro

GET  /cost-centers?org_id=    — Listar cost centers
POST /cost-centers?org_id=    — Criar (ADMIN_ROLES)
GET  /cost-centers/{ccId}     — Detalhe
PATCH /cost-centers/{ccId}    — Atualizar (ADMIN_ROLES)

## Influencers
GET  /influencers?org_id=     — Listar
POST /influencers?org_id=     — Criar (ADMIN_ROLES)
GET  /influencers/{id}        — Detalhe
PATCH /influencers/{id}       — Atualizar (ADMIN_ROLES)

POST /influencers/{id}/brand-kit  — Upsert brand kit (ADMIN_ROLES)
GET  /influencers/{id}/brand-kit  — Buscar brand kit

## Macro Content (Master)
POST /macro-contents                    — Criar
GET  /macro-contents?org_id=&status=    — Listar
GET  /macro-contents/{id}               — Detalhe
PATCH /macro-contents/{id}              — Atualizar
POST /macro-contents/{id}/redistribute  — Redistribuir

## Content Items
GET  /content-items?cc_id=&status=&provider=&search=&skip=&limit=  — Listar (paginado)
POST /content-items                     — Criar (EDITOR_ROLES)
GET  /content-items/{id}                — Detalhe
PATCH /content-items/{id}               — Atualizar (EDITOR_ROLES)

### Workflow
POST /content-items/{id}/submit-review     — Enviar para revisao (EDITOR_ROLES)
POST /content-items/{id}/approve           — Aprovar (ADMIN_ROLES)
POST /content-items/{id}/request-changes   — Solicitar mudancas (ADMIN_ROLES)
POST /content-items/{id}/reject            — Rejeitar (ADMIN_ROLES)
POST /content-items/{id}/schedule          — Agendar (ADMIN_ROLES)
POST /content-items/{id}/publish-now       — Publicar (ADMIN_ROLES)

## Campaigns
GET  /campaigns?cc_id=        — Listar
POST /campaigns               — Criar (ADMIN_ROLES)
PATCH /campaigns/{id}         — Atualizar (ADMIN_ROLES)

## Social Integrations (OAuth) — placeholder
POST /social/connect          — Conectar conta
GET  /social/callback         — OAuth callback
POST /social/disconnect       — Desconectar

## Tracking
POST /tracking/links                    — Criar short link
GET  /tracking/links?cost_center_id=    — Listar links
POST /tracking/events/click             — Registrar clique
POST /tracking/events/lead              — Registrar lead

## Leads
GET  /leads?cc_id=&status=    — Listar
POST /leads                   — Criar (EDITOR_ROLES)
PATCH /leads/{id}             — Atualizar (EDITOR_ROLES)

## Analytics
GET /metrics/daily?cc_id=&from_date=&to_date=  — Metricas diarias
GET /metrics/by-content/{content_item_id}       — Por conteudo
GET /metrics/overview?cc_id=                    — Visao geral agregada

## Audit Logs
GET /audit-logs?org_id=&cc_id=&action=&target_type=&skip=&limit=  — Listar (paginado)

## Notifications
GET   /notifications?org_id=&unread_only=&skip=&limit=  — Listar (paginado)
GET   /notifications/unread-count?org_id=                — Contagem nao lidas
PATCH /notifications/{id}/read                           — Marcar como lida
POST  /notifications/read-all?org_id=                    — Marcar todas como lidas

## Agents (MVP — modo mock)

### Marketing Agent
POST /agent/marketing/run     — Executar intent

### Market Agent
POST /agent/market/run            — Coletar findings
POST /agent/market/weekly-brief   — Gerar brief semanal
GET  /agent/market/findings?org_id=  — Listar findings
GET  /agent/market/briefs?org_id=    — Listar briefs
POST /agent/market/sources        — Registrar fonte
POST /agent/market/competitors    — Registrar concorrente

## RBAC

| Constante | Roles | Escopo |
|-----------|-------|--------|
| ADMIN_ROLES | owner, admin | Criar/editar campanhas, aprovar/rejeitar conteudo, gerenciar influenciadores |
| EDITOR_ROLES | owner, admin, editor | Criar/editar conteudo, leads, submeter para revisao |
