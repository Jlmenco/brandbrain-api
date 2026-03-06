# Arquitetura

## Visão geral
- Frontend (Next.js): UI, gestão, editor, calendário, aprovações, analytics, chat do agente.
- Backend (API): auth, tenant, influencers, conteúdo, redistribuição, integrações, tracking, agents.
- Worker (Jobs): geração em lote, agendamento/publicação, coleta de métricas, coleta de mercado.
- DB: PostgreSQL
- Cache/Fila: Redis
- Storage: S3/GCS

## Componentes (Backend)
1) Auth & Tenancy
- Login, RBAC, Organization, Cost Center

2) Influencer Service
- Criação de influencer, DNA (prompt base), brand kit, regras, assets visuais

3) Content Service
- Drafts, versões, templates, validações, compliance checks

4) Redistribution Engine
- Recebe MacroContent do Master
- Gera BrandContent para cada Cost Center elegível
- Garante consistência (tom/CTA/palavras proibidas)

5) Scheduler & Publishing
- Agenda posts (quando API permitir)
- Publica e armazena provider_post_id

6) Tracking Service
- Short links
- UTM generator
- Eventos de clique/lead

7) Analytics Collector
- Coleta métricas por rede
- Consolida por post, campanha, centro de custo

8) Marketing Agent (Influencer Builder + Content Planner)
- Orquestra intenções do usuário usando ferramentas internas (create_influencer, upsert_brand_kit, create_content_item etc.)
- Default: cria drafts e envia para review; não autoposta

9) Market Intelligence Agent
- Coleta fontes públicas (RSS, Trends etc.)
- Produz Market Findings e Briefs semanais com fontes e datas
- Gera Content Briefs prontos para o Marketing Agent

## Fluxo (MVP)
Master cria MacroContent -> Redistribuição -> Drafts por marca -> Aprovação -> Agendamento -> Publicação -> Métricas -> Feedback

Market Agent (semana):
Coleta mercado -> Briefs -> Content Briefs -> Drafts -> Review

## Multi-tenant e isolamento
- Organization contém Cost Centers
- Tokens sociais isolados por Cost Center
- Logs/auditoria por Cost Center
