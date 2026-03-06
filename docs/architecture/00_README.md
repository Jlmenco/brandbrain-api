# Marketing AI Platform (Multi-Centro + Influencer Geral + Agentes)

## Objetivo
Construir uma plataforma que automatiza marketing com IA, com:
- Multi-tenant (Organization)
- Centros de custo (Cost Centers) por marca (ex.: Melpura, MeatFriends)
- 1 Influencer por Centro de Custo (MVP)
- 1 Influencer Geral (Master Persona) que pode redistribuir conteúdo para marcas
- Agente de criação de influencer + publicações (Marketing Agent)
- Agente de análise de mercado (Market Intelligence Agent)

## Princípios
1) Integrações via APIs oficiais (OAuth) quando publicar/agendar.
2) Human-in-the-loop (aprovação) como padrão no MVP.
3) Governança, auditoria e isolamento de dados por centro de custo.
4) Conteúdo “macro” do Master pode ser adaptado e republicado por cada marca.
5) Qualquer afirmação factual do Market Agent deve ter fonte + data + contexto.

## Stack sugerida (MVP)
- Frontend: Next.js + Tailwind + shadcn/ui
- Backend: FastAPI (Python) ou NestJS (Node)
- DB: PostgreSQL
- Queue: Redis + Worker (Celery/RQ ou BullMQ)
- Storage: S3/GCS
- Observabilidade: Grafana + Loki/Prometheus + Sentry

## Entregáveis do MVP
- Gestão de Org + Centros de custo
- Criação de Influencer (wizard) por centro e 1 master
- Brand Kit por influencer
- Editor + aprovação + agendamento
- Redistribuição (Master -> Centros)
- Tracking com UTM + short links
- Métricas básicas por post
- Marketing Agent (cria influencer e gera drafts/calendário)
- Market Intelligence Agent (briefs semanais, insights e content briefs com fontes)

## Como usar
1) Leia `11_ROADMAP_BACKLOG.md` e `13_CHECKLIST_MVP.md`.
2) Implemente o banco conforme `03_MODELO_DADOS.md` (+ market/agent em `15_*`).
3) Implemente a API conforme `04_API_SPEC.md` (+ agent endpoints em `14_*` e `17_*`).
4) Implemente prompts conforme `06_*` e `18_*` e `19_*`.
