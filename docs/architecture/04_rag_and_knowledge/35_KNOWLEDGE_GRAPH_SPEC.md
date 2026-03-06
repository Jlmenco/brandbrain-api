# Brand Knowledge Graph — Spec (nível infra)

## Objetivo
Ir além de memória vetorial:
- mapear relações entre tese, pilares, posts, métricas, leads, feedback e incidentes
- responder perguntas estratégicas do negócio

## Grafo (conceito)
Nós:
- NarrativeThesis
- Pillar
- ContentItem
- MarketFinding
- Lead
- Conversion
- Competitor
- Incident
- Document

Arestas:
- supports / contradicts
- derived_from (conteúdo <- doc/finding)
- belongs_to (conteúdo -> pilar)
- influenced (conteúdo -> lead/conversão)
- risk_event (conteúdo -> incidente)

## Implementação
Opção A: Postgres com tabelas relacionais + materialized views (MVP)
Opção B: Neo4j/JanusGraph (Enterprise avançado)

## Use cases
- “Qual pilar gera leads de maior ticket?”
- “Qual narrativa aumentou CTR nos últimos 60 dias?”
- “Quais docs sustentam essa claim?”
- “Quais incidentes ocorreram e por quê?”

## API sugerida
- GET /graph/query (queries pré-definidas)
- GET /graph/insights?ccId=&window=
