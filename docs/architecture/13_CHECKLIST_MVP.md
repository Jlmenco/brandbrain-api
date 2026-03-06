# Checklist do MVP

> Ultima atualizacao: 2026-03-04 (RAG + embeddings)

## Base
- [x] Login + RBAC + Organization (JWT + 4 roles + enforcement frontend/backend)
- [x] Cost Centers (CRUD)
- [x] Influencer Master + Influencer por marca
- [x] Brand Kit por influencer

## Conteudo
- [x] Criar Draft manual
- [x] Gerar Draft via IA (prompt base — modo mock)
- [x] Aprovacao (review -> approved -> request_changes -> reject)
- [x] Workflow completo: draft -> review -> approved -> scheduled -> posted

## Redistribuicao
- [x] Criar MacroContent
- [x] Redistribute -> drafts por marca
- [x] Garantir nao-duplicacao entre marcas

## Publicacao
- [x] Scheduler (worker com poll loop + Redis pub/sub)
- [ ] Publicar 1 canal real (Meta OU LinkedIn Page) — **usando mock publisher**
- [x] Registrar provider_post_id + url (simulado)
- [x] Retry + logs (3 retries, exponential backoff, audit logs)

## Tracking/Leads
- [x] Short links + UTM
- [x] Evento click
- [x] Lead form + vinculo com tracking
- [x] Lead CRUD + pipeline (novo/qualificado/ganho/perdido)

## Analytics
- [x] Metricas diarias basicas por post
- [x] Overview por Cost Center
- [x] Dashboard melhorado: grafico recharts, pipeline leads, campanhas ativas, atividade recente

## Agents
- [x] Marketing Agent: criar influencer + gerar drafts (modo mock)
- [x] Market Agent: briefs semanais + content briefs com fontes (modo mock)
- [x] RAG + Embeddings: pgvector, auto-embed brand kit, busca semantica, prompt builder, RAG no generate_drafts

## Frontend
- [x] Login page + auth guard
- [x] Dashboard com metricas, graficos, resumos
- [x] Conteudos: listagem paginada + busca + CRUD + workflow
- [x] Influenciadores: listagem + CRUD + brand kit
- [x] Campanhas: listagem + CRUD + filtro por objetivo
- [x] Leads: listagem + CRUD + filtro por status
- [x] Historico: audit logs com tabela, filtros, paginacao
- [x] Notificacoes in-app (bell + popover + polling)
- [x] RBAC frontend: Gate component + permissoes por role

## Infra/Qualidade
- [x] Docker Compose (9 servicos)
- [x] Alembic migrations (23 tabelas + pgvector embeddings)
- [x] Testes automatizados: 127 API + 22 Worker
- [x] Seed enriquecido com dados realistas

## Pendente (pos-MVP)
- [ ] Integracao LLM real (OpenAI/Anthropic)
- [ ] Providers reais (LinkedIn API, Instagram API, Meta Business)
- [ ] Deploy staging
