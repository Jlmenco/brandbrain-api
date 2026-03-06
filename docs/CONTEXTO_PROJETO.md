# Brand Brain — Documento de Contexto do Projeto

> Ultima atualizacao: 06 de marco de 2026
> Objetivo: preservar todo o contexto do que foi construído para continuidade do desenvolvimento.

---

## 1. O que é o Brand Brain

O Brand Brain é um **Autonomous Brand Intelligence System (ABIS)** — uma plataforma de marketing com IA que gerencia múltiplas marcas dentro de um grupo empresarial. O projeto foi criado para o **Grupo JLM**, que possui marcas como **Melpura** (mel natural) e **MeatFriends** (carnes premium).

A plataforma utiliza influenciadores digitais (personas de IA), inteligência de mercado automatizada e governança corporativa para criar, adaptar e distribuir conteúdo de marketing de forma autônoma.

---

## 2. Arquitetura Geral

### Stack Tecnológico

- **Backend**: FastAPI + SQLModel (Python 3.12)
- **Banco de Dados**: PostgreSQL 16 com pgvector
- **Cache/Filas**: Redis
- **Autenticação**: JWT (python-jose + passlib/bcrypt)
- **Frontend**: Next.js 14 + Tailwind CSS v3 + shadcn/ui + Recharts (8 paginas implementadas)
- **Infraestrutura**: Docker Compose com 9 servicos
- **Monitoramento**: Prometheus + Grafana + Loki

### Serviços Docker (infra/docker/compose.yml)

| Serviço | Porta | Descrição |
|---------|-------|-----------|
| postgres | 5432 | PostgreSQL 16 com pgvector |
| redis | 6379 | Cache e filas |
| api (bb_api) | 8000 | Backend FastAPI |
| worker | — | Scheduler + Publisher (mock, retry, Redis pub/sub) |
| web | 3000 | Next.js 14 (dashboard completo) |
| nginx | 80 | Proxy reverso |
| prometheus | 9090 | Métricas |
| grafana | 3001 | Dashboards + Loki |

### Roteamento Nginx

- `/` → web:3000 (Next.js)
- `/api/` → api:8000 (FastAPI, strip prefix)

---

## 3. Estrutura do Backend (apps/api/)

```
apps/api/
├── Dockerfile
├── requirements.txt
├── alembic.ini
├── test_api.sh              # Script de smoke test
├── alembic/
│   ├── env.py
│   └── versions/            # 2 migrations (23 tabelas + pgvector embeddings)
└── app/
    ├── __init__.py
    ├── main.py               # App FastAPI, lifespan, CORS, health, 13 routers
    ├── config.py              # Settings via env vars
    ├── database.py            # Engine SQLModel + get_session
    ├── dependencies.py        # get_current_user (JWT), check_role (RBAC), ADMIN_ROLES, EDITOR_ROLES
    │
    ├── models/                # 13 arquivos — tabelas do banco
    │   ├── user.py            # User, OrgMember
    │   ├── organization.py    # Organization
    │   ├── cost_center.py     # CostCenter
    │   ├── influencer.py      # Influencer, BrandKit, InfluencerAsset
    │   ├── content.py         # MacroContent, ContentItem, Approval
    │   ├── campaign.py        # Campaign
    │   ├── social.py          # SocialAccount
    │   ├── tracking.py        # TrackingLink, Event, Lead
    │   ├── metrics.py         # MetricsDaily
    │   ├── audit.py           # AuditLog
    │   ├── notification.py    # Notification (in-app + email)
    │   ├── agent.py           # AgentSession, AgentMessage, AgentAction
    │   ├── embedding.py       # BrandKitEmbedding (pgvector Vector(1536) para RAG)
    │   └── market.py          # MarketSource, Competitor, MarketFinding, MarketBrief, ContentBrief
    │
    ├── schemas/               # 12 arquivos — Pydantic request/response
    │   ├── auth.py, organization.py, cost_center.py, influencer.py
    │   ├── content.py, campaign.py, social.py, tracking.py
    │   ├── metrics.py, audit.py, agent.py, market.py
    │
    ├── routers/               # 15 arquivos — endpoints da API
    │   ├── auth.py            # POST /register, /login, /logout, GET /me
    │   ├── organizations.py   # CRUD orgs + members
    │   ├── cost_centers.py    # CRUD cost centers (ADMIN_ROLES)
    │   ├── influencers.py     # CRUD + brand kit + assets (ADMIN_ROLES)
    │   ├── macro_contents.py  # CRUD + POST /{id}/redistribute
    │   ├── content_items.py   # CRUD + workflow + RBAC + notifications + audit
    │   ├── campaigns.py       # CRUD campaigns (ADMIN_ROLES)
    │   ├── social.py          # OAuth placeholders
    │   ├── tracking.py        # Short links + UTM + eventos
    │   ├── leads.py           # CRUD leads (EDITOR_ROLES)
    │   ├── metrics.py         # Analytics (daily, by-content, overview)
    │   ├── audit.py           # GET /audit-logs (paginado, filtros)
    │   ├── notifications.py   # CRUD notifications + unread count + mark read
    │   ├── agent_marketing.py # POST /agent/marketing/run
    │   └── agent_market.py    # POST /agent/market/run, weekly-brief, findings, briefs, sources, competitors
    │
    ├── services/              # 10 arquivos — logica de negocio
    │   ├── auth_service.py    # Hash senha, JWT create/verify
    │   ├── audit_service.py   # log_action (AuditLog)
    │   ├── notification_service.py # notify_status_change (in-app + email)
    │   ├── email_service.py   # SMTP em thread separada (modo simulacao se SMTP_HOST vazio)
    │   ├── compliance.py      # Palavras proibidas, promessas absolutas
    │   ├── tracking_service.py# Slug, UTM, short links
    │   ├── redistribution.py  # Macro -> ContentItems adaptados
    │   ├── ai_gateway.py      # Abstracao LLM (mock + openai)
    │   ├── embedding_service.py # RAG: chunking + pgvector embeddings + semantic search
    │   └── prompt_builder.py  # Construcao de prompts RAG para geracao de conteudo
    │
    ├── agents/                # 3 arquivos — lógica dos agentes IA
    │   ├── marketing_agent.py # 5 intents: create_influencer, refine_brand_kit, plan_week, generate_drafts, adapt_from_master
    │   ├── market_agent.py    # Coleta findings, gera weekly briefs + content briefs
    │   └── tools.py           # Funções auditáveis dos agentes
    │
    └── scripts/
        └── seed.py            # Dados de exemplo completos
```

---

## 4. Modelo de Dados (Entidades Principais)

### Hierarquia Multi-tenant

```
Organization (Grupo JLM)
  └── CostCenter (Melpura, MeatFriends)
       ├── Influencer (persona IA por marca)
       │    └── BrandKit (tom, estilo, produtos)
       ├── ContentItem (posts adaptados)
       ├── Campaign (campanhas)
       ├── TrackingLink (links curtos)
       └── Lead (leads capturados)
```

### Entidades e Campos-Chave

- **User**: id (UUID), email, name, hashed_password, is_active
- **OrgMember**: org_id, user_id, role (owner/admin/editor/viewer)
- **Organization**: id, name, slug
- **CostCenter**: org_id, name, code, budget_monthly, budget_quarterly
- **Influencer**: org_id, cost_center_id, type (master/brand), name, niche, tone, emoji_level, forbidden_topics/words, allowed_words, cta_style, language
- **BrandKit**: influencer_id, value_propositions, products, target_audience, style_guidelines, reference_links
- **MacroContent**: org_id, master_influencer_id, theme, content_raw, status
- **ContentItem**: cost_center_id, influencer_id, source_macro_id, provider_target, text, status (draft→review→approved→scheduled→posted→failed), scheduled_at, posted_at
- **Approval**: content_item_id, reviewer_id, decision, notes
- **Campaign**: cost_center_id, name, objective, start/end dates
- **TrackingLink**: slug, cost_center_id, destination_url, content_item_id, utm (JSON)
- **Event**: tracking_link_id, type (click/lead/conversion), ip, user_agent
- **Lead**: cost_center_id, tracking_link_id, source, name, email, phone, score, status
- **MetricsDaily**: cost_center_id, content_item_id, date, impressions, likes, comments, shares, clicks, followers_delta
- **AuditLog**: org_id, actor_user_id, action, target_type, target_id, metadata_json
- **AgentSession/Message/Action**: Sessões e histórico dos agentes IA
- **MarketSource/Competitor/Finding/Brief/ContentBrief**: Inteligência de mercado

---

## 5. Autenticação e RBAC

### JWT

- Algoritmo: HS256
- Expiração: 30 minutos (configurável)
- Header: `Authorization: Bearer <token>`

### Roles (4 níveis)

| Role | Permissões |
|------|-----------|
| owner | Tudo, incluindo gerenciar membros e deletar org |
| admin | Tudo exceto deletar org |
| editor | CRUD de conteúdo, influencers, campanhas |
| viewer | Apenas leitura |

### Credenciais de Seed

- **Admin (owner)**: admin@brandbrain.dev / admin123
- **Editor**: editor@brandbrain.dev / editor123
- **Viewer**: viewer@brandbrain.dev / viewer123

---

## 6. Workflow de Conteúdo

```
draft → review → approved → scheduled → posted
                ↘ request_changes → draft (volta)
                ↘ rejected (finalizado)
         scheduled → failed (se falhar ao postar)
```

### Redistribuição

O conceito central: um **MacroContent** (conteúdo mestre) é criado pelo influenciador master e depois **redistribuído** para cada cost center/marca, gerando **ContentItems** adaptados por marca e canal (Instagram, LinkedIn, etc.).

---

## 7. Agentes IA

### Marketing Agent (POST /agent/marketing/run)

5 intents disponíveis:

| Intent | Descrição |
|--------|-----------|
| create_influencer | Cria nova persona de influenciador |
| refine_brand_kit | Atualiza brand kit de um influenciador |
| plan_week | Gera plano semanal de conteúdo |
| generate_drafts | Gera rascunhos de posts para canais específicos |
| adapt_from_master | Adapta macro content para marcas |

### Market Intelligence Agent (POST /agent/market/run)

Funcionalidades:

- **Coleta de findings**: busca por keywords, cria MarketFindings (trend, opportunity, faq, competitor, risk)
- **Weekly brief**: consolida findings da semana em MarketBrief + gera ContentBriefs
- **Sources/Competitors**: CRUD para fontes de mercado e concorrentes

### AI Gateway

Abstração para múltiplos provedores LLM:

- **mock** (padrão no MVP): retorna respostas simuladas
- **openai**: integração real com OpenAI API
- Configurável via env var `AI_DEFAULT_PROVIDER`

### RAG + Embeddings (pgvector)

Pipeline de Retrieval-Augmented Generation para geração de conteúdo contextualizado:

- **BrandKitEmbedding**: tabela separada com embeddings pgvector (Vector 1536 dims)
- **EmbeddingService**: chunking de BrandKit em 5-7 segmentos (perfil, descrição, value_props, products, audience, style_guidelines, links) + geração de embeddings (mock/OpenAI text-embedding-3-small) + busca semântica por cosine similarity
- **PromptBuilder**: construção de prompts RAG com contexto da marca para geração de conteúdo
- **Auto-embed**: embeddings gerados automaticamente ao criar/atualizar brand kit
- **Marketing Agent**: `generate_drafts` usa RAG pipeline (busca contexto → build prompt → AIGateway.generate())
- **HNSW index**: index vetorial para busca rápida sem tuning

---

## 8. Dados de Seed (scripts/seed.py)

O seed cria:

- 3 usuarios (admin/owner + editor + viewer)
- 1 organizacao (Grupo JLM) com todos como membros
- 2 cost centers: Melpura (MEL001) e MeatFriends (MF001)
- 3 influenciadores: Dr. Mel (master), Abelha Melpura (brand Melpura), Chef Marcos (brand MeatFriends)
- 3 brand kits correspondentes
- 1 macro content de exemplo
- 14 content items (todos os status do workflow)
- 4 campanhas (2 por marca, objetivos variados)
- 8 leads (4 por marca, status e fontes variados)
- 88 MetricsDaily (30 dias x marcas)
- ~50 audit logs simulando workflow completo
- 12 notificacoes demo (mix lidas/nao lidas)
- 2 market sources (Google Trends, ABEMEL)
- 2 competitors (Mel Flores do Campo, Friboi Premium)
- 17 brand kit embeddings (5 master + 6 Melpura + 6 MeatFriends)

---

## 9. Endpoints da API (Resumo)

### Auth
- `POST /api/auth/register` — Registrar usuário
- `POST /api/auth/login` — Login (retorna JWT)
- `POST /api/auth/logout` — Logout
- `GET /api/auth/me` — Usuário atual

### Organizations
- `GET /api/orgs` — Listar orgs do usuário
- `POST /api/orgs` — Criar org
- `GET /api/orgs/{id}` — Detalhe
- `POST /api/orgs/{id}/members` — Adicionar membro

### Cost Centers
- `GET /api/cost-centers?org_id=` — Listar
- `POST /api/cost-centers?org_id=` — Criar
- `GET/PATCH /api/cost-centers/{id}` — Detalhe/Atualizar

### Influencers
- `GET /api/influencers?org_id=` — Listar
- `POST /api/influencers?org_id=` — Criar
- `GET/PATCH /api/influencers/{id}` — Detalhe/Atualizar
- `POST/GET /api/influencers/{id}/brand-kit` — Brand Kit

### Macro Contents
- `GET /api/macro-contents?org_id=` — Listar
- `POST /api/macro-contents` — Criar
- `GET/PATCH /api/macro-contents/{id}` — Detalhe/Atualizar
- `POST /api/macro-contents/{id}/redistribute` — Redistribuir

### Content Items
- `GET /api/content-items` — Listar
- `POST /api/content-items` — Criar
- `GET/PATCH /api/content-items/{id}` — Detalhe/Atualizar
- `POST /api/content-items/{id}/submit-review` — Enviar para revisão
- `POST /api/content-items/{id}/approve` — Aprovar
- `POST /api/content-items/{id}/request-changes` — Solicitar mudanças
- `POST /api/content-items/{id}/reject` — Rejeitar
- `POST /api/content-items/{id}/schedule` — Agendar
- `POST /api/content-items/{id}/publish-now` — Publicar

### Campaigns
- `GET /api/campaigns?cc_id=` — Listar
- `POST /api/campaigns` — Criar (ADMIN_ROLES)
- `PATCH /api/campaigns/{id}` — Atualizar (ADMIN_ROLES)

### Social (placeholder)
- `POST /api/social/connect` — Conectar conta
- `GET /api/social/callback` — OAuth callback
- `POST /api/social/disconnect` — Desconectar

### Tracking
- `POST /api/tracking/links` — Criar short link
- `GET /api/tracking/links?cost_center_id=` — Listar links
- `POST /api/tracking/events/click` — Registrar clique
- `POST /api/tracking/events/lead` — Registrar lead

### Leads
- `GET /api/leads?cc_id=&status=` — Listar
- `POST /api/leads` — Criar (EDITOR_ROLES)
- `PATCH /api/leads/{id}` — Atualizar (EDITOR_ROLES)

### Metrics
- `GET /api/metrics/daily?cc_id=&from_date=&to_date=` — Metricas diarias
- `GET /api/metrics/by-content/{content_item_id}` — Por conteudo
- `GET /api/metrics/overview?cc_id=` — Visao geral

### Audit Logs
- `GET /api/audit-logs?org_id=&cc_id=&action=&target_type=&skip=&limit=` — Listar (paginado)

### Notifications
- `GET /api/notifications?org_id=&unread_only=&skip=&limit=` — Listar (paginado)
- `GET /api/notifications/unread-count?org_id=` — Contagem nao lidas
- `PATCH /api/notifications/{id}/read` — Marcar como lida
- `POST /api/notifications/read-all?org_id=` — Marcar todas como lidas

### Marketing Agent
- `POST /api/agent/marketing/run` — Executar intent

### Market Agent
- `POST /api/agent/market/run` — Coletar findings
- `POST /api/agent/market/weekly-brief` — Gerar brief semanal
- `GET /api/agent/market/findings?org_id=` — Listar findings
- `GET /api/agent/market/briefs?org_id=` — Listar briefs
- `POST /api/agent/market/sources` — Registrar fonte
- `POST /api/agent/market/competitors` — Registrar concorrente

---

## 10. Bugs Encontrados e Corrigidos

### CRÍTICOS

1. **body parameter com Ellipsis default** (cost_centers.py, influencers.py)
   - Problema: `body: CostCenterCreate = ...` — Ellipsis não é válido para body params no FastAPI
   - Correção: `body: CostCenterCreate` (sem default, movido antes dos Query params)

2. **SQLAlchemy API errada** (redistribution.py)
   - Problema: `db.query(Influencer)` — SQLModel usa `db.exec(select(...))`
   - Também: campos `content_raw` e `provider` não existem no ContentItem
   - Correção: `db.exec(select(...))`, campos corretos `text` e `provider_target`

3. **Tipos errados** (tracking_service.py)
   - Problema: `content_item_id: int` mas IDs são UUIDs (str)
   - Correção: Mudado para `str`

4. **SQLModel .where() com vírgula** (macro_contents.py, marketing_agent.py)
   - Problema: `.where(A == x, B == y)` — SQLModel não suporta vírgula no where
   - Correção: `.where(A == x).where(B == y)`

### MODERADOS

5. **org_id vazio no audit** (tools.py)
   - Correção: Adicionado parâmetro `org_id` às funções tool

6. **Imports circulares** (models/)
   - Correção: Removidos todos os SQLModel Relationships, mantendo apenas foreign keys

7. **Diretório src/ antigo** conflitando com nova estrutura app/
   - Correção: Deletado apps/api/src/ inteiro

8. **Migration desatualizada** (alembic/versions/)
   - Correção: Deletada migration, usando `create_db_and_tables()` no lifespan

---

## 11. Como Rodar o Projeto

### Pré-requisitos

- Docker e Docker Compose instalados
- Portas livres: 80, 5432, 6379, 8000, 3000, 3001, 9090

### Passos

```bash
# 1. Subir todos os serviços
docker compose -f infra/docker/compose.yml up -d --build

# 2. Popular dados de exemplo
docker exec -it bb_api python -m app.scripts.seed

# 3. Acessar Swagger UI
open http://localhost/api/docs

# 4. Rodar smoke test (opcional)
bash apps/api/test_api.sh
```

### Variáveis de Ambiente Importantes

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| DATABASE_URL | postgresql://brandbrain:brandbrain@postgres:5432/brandbrain | Connection string |
| REDIS_URL | redis://redis:6379/0 | Redis |
| JWT_SECRET_KEY | change-me-in-production | Chave JWT |
| JWT_ALGORITHM | HS256 | Algoritmo |
| JWT_EXPIRE_MINUTES | 30 | Expiração token |
| AI_DEFAULT_PROVIDER | mock | Provider LLM |
| OPENAI_API_KEY | — | Chave OpenAI (se provider=openai) |

---

## 12. Proximos Passos

### Ja concluidos ✅
1. ~~Subir Docker + testar seed~~
2. ~~Gerar migration Alembic~~ (migration inicial com 23 tabelas)
3. ~~Testes unitarios~~ (116 API + 22 Worker)
4. ~~Frontend Next.js~~ (8 paginas completas com CRUD, workflow, dashboard)
5. ~~Worker~~ (scheduler + publisher com retry e backoff)

6. ~~Testes E2E~~ (13 testes Playwright — auth, dashboard, content-workflow, influencers, navigation/RBAC)
7. ~~UX Polish~~ (Toast notifications sonner, Loading skeletons, Sidebar responsiva mobile, Dark mode)

### Pendente
1. **Integrar LLM real** — trocar AI_DEFAULT_PROVIDER=mock por openai (ja tem embedding_service + ai_gateway prontos)
2. **OAuth social** — Meta Business API, LinkedIn API
3. **Deploy staging** — Docker em cloud

---

## 13. Documentação de Arquitetura Existente

O projeto possui 36 documentos de arquitetura detalhados em `docs/architecture/`. Os principais são:

| Doc | Conteúdo |
|-----|----------|
| 01_VISAO_E_ESCOPO | Visão, escopo, objetivos MVP |
| 02_ARQUITETURA | Arquitetura: 9 componentes backend |
| 03_MODELO_DADOS | Modelo de dados completo (15+ entidades) |
| 04_API_SPEC | Especificação REST (80+ endpoints planejados) |
| 05_WORKFLOWS | 5 workflows do MVP |
| 11_ROADMAP_BACKLOG | Roadmap 3 fases, 9 épicos MVP |
| 14_AGENT_SPEC | Spec do Marketing Agent |
| 18_MARKET_AGENT_SPEC | Spec do Market Intelligence Agent |
| 22_BRAND_BRAIN_OVERVIEW | Conceito ABIS |
| 29_AI_GATEWAY_SPEC | Abstração LLM |

---

## 14. Frontend (apps/web/)

```
apps/web/
├── app/
│   ├── (authenticated)/       # Layout com auth guard + sidebar
│   │   ├── dashboard/         # Dashboard com metricas, graficos, resumos
│   │   ├── conteudos/         # Listagem + CRUD + workflow
│   │   ├── conteudos/[id]/    # Detalhe com editor + workflow actions
│   │   ├── influenciadores/   # Listagem + CRUD
│   │   ├── influenciadores/[id]/ # Detalhe + brand kit
│   │   ├── campanhas/         # Listagem + CRUD + filtro por objetivo
│   │   ├── leads/             # Listagem + CRUD + filtro por status
│   │   └── historico/         # Audit logs com filtros e paginacao
│   └── login/                 # Login page
├── components/
│   ├── dashboard/             # MetricsCards, MetricsChart, ContentStatusSummary, ActiveCampaigns, LeadPipeline, RecentActivity, RecentContent
│   ├── content/               # CreateContentDialog, ContentWorkflowActions, ContentEditor, ScheduleDialog
│   ├── influencer/            # CreateInfluencerDialog, EditBrandKitDialog
│   ├── campaign/              # CreateCampaignDialog, EditCampaignDialog
│   ├── lead/                  # CreateLeadDialog, EditLeadDialog
│   ├── layout/                # Sidebar, Header, NotificationBell
│   └── ui/                    # Badge, Button, Card, Dialog, Table, Gate, Popover, Skeleton, Sheet (shadcn/ui)
├── contexts/                  # AuthContext, WorkspaceContext
├── lib/
│   ├── api-client.ts          # Fetch wrapper com JWT injection
│   ├── types.ts               # Interfaces TypeScript
│   ├── constants.ts           # Labels, cores, nav items
│   ├── permissions.ts         # Permission type + ROLE_PERMISSIONS + hasPermission
│   └── utils.ts               # cn, truncate
```

## 15. Estatisticas do Codigo

**Backend (Python)**:
- 13 models, 12 schemas, 15 routers, 10 services, 3 agent modules
- 127 testes API + 22 testes Worker + 13 testes E2E (Playwright)
- 2 Alembic migrations (23 tabelas + pgvector embeddings)

**Frontend (TypeScript/React)**:
- 8 paginas, ~25 componentes
- Recharts para graficos
- shadcn/ui para UI components
- Toast (sonner), Loading skeletons, Sidebar responsiva, Dark mode

**Infra**:
- Docker Compose (9 servicos)
- Nginx proxy, Prometheus, Grafana + Loki
