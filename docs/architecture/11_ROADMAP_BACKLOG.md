# Roadmap & Backlog

> Ultima atualizacao: 2026-03-04 (RAG + embeddings)

## Fase 1 (MVP) — CONCLUIDA (modo simulacao)

### Epico A: Tenancy + RBAC ✅
- Org, membros, roles (owner/admin/editor/viewer)
- Cost centers (CRUD)
- RBAC enforcement: frontend (Gate + permissions) + backend (check_role)

### Epico B: Influencers + Brand Kit ✅
- Criar master e brand (1 por centro)
- Brand Kit CRUD (descricao, value_props, products, audience, style_guidelines, links)
- Frontend: listagem + dialogs de criacao/edicao

### Epico C: Conteudo + Aprovacao ✅
- ContentItems com versoes
- Status workflow completo: draft -> review -> approved -> scheduled -> posted
- Aprovar/rejeitar/pedir ajustes + compliance check
- Frontend: listagem paginada, busca, CRUD, workflow actions

### Epico D: Macro + Redistribuicao ✅
- MacroContents CRUD
- Endpoint redistribute
- Engine de adaptacao por marca/canal

### Epico E: Scheduler + Jobs ✅
- Schedule (worker com poll loop 30s + Redis pub/sub)
- Worker publish (mock publisher com dispatch por provider)
- Retry (3x, exponential backoff) + audit logs

### Epico F: Tracking + Leads ✅
- Short links + UTM
- Evento click
- Lead CRUD + pipeline (novo/qualificado/ganho/perdido)
- Frontend: pagina /leads com CRUD, filtros, badges

### Epico G: Analytics basico ✅
- metrics_daily ingest (seed com 88 registros)
- Dashboard: metricas cards + grafico diario (recharts) + pipeline leads + campanhas ativas

### Epico H: Marketing Agent ✅ (modo mock)
- Criar influencer via agente
- Gerar calendario e drafts
- Submeter para review

### Epico I: Market Intelligence Agent ✅ (modo mock)
- Fontes + concorrentes configuraveis
- Coleta diaria + brief semanal
- Content briefs para alimentar posts

### Extras implementados (alem do roadmap original)
- Campanhas UI: CRUD + vinculo com conteudos
- Notificacoes in-app + email (SMTP)
- Audit logs UI: pagina /historico com filtros e paginacao
- Dashboard melhorado: recharts, pipeline leads, campanhas ativas, atividade recente
- RAG + Embeddings: pgvector, BrandKitEmbedding, EmbeddingService, PromptBuilder, auto-embed, RAG no generate_drafts
- Testes automatizados: 127 API + 22 Worker
- Alembic migrations versionadas (23 tabelas + pgvector embeddings)

## Fase 1.5 (Transicao para producao) — EM ANDAMENTO
- [x] RAG + Embeddings (pgvector, embedding_service, prompt_builder, HNSW index)
- [ ] Integracao LLM real (trocar AI_DEFAULT_PROVIDER=mock por openai — infraestrutura RAG ja pronta)
- [ ] Providers reais (LinkedIn API, Instagram API, Meta Business)
- [ ] Deploy staging (Docker em cloud)
- [ ] Testes E2E (Playwright/Cypress)

## Fase 2
- Multi-influencer por centro
- Recomendador (feedback loop)
- Multiplos providers simultaneos
- Biblioteca de templates

## Fase 3
- Colaboracao cruzada entre marcas
- Videos falados / digital human
- Autopost controlado
