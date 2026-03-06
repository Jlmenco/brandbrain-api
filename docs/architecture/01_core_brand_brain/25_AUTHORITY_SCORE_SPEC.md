# Authority Score™ — Spec (KPI proprietário)

## Objetivo
Criar um índice proprietário e vendável que mede **autoridade real**, não só vaidade.

## Inputs (por centro de custo e por influencer)
- consistência de postagem (cadência)
- alinhamento narrativo (pilares distribuídos)
- crescimento orgânico (followers_delta)
- qualidade de engajamento (comentários/compartilhamentos > likes)
- conversão (leads)
- diversidade de formatos (texto, carrossel, vídeo)
- risco (penalidade por incidentes/compliance)

## Cálculo (sugestão inicial)
AuthorityScore = 
  0.20 * Consistency +
  0.20 * NarrativeCoherence +
  0.15 * OrganicGrowth +
  0.15 * EngagementQuality +
  0.20 * ConversionImpact +
  0.10 * FormatDiversity
  - RiskPenalty

Cada sub-score normalizado 0..100.

## Entidades sugeridas (DB)
### authority_scores
- id
- org_id
- cost_center_id (nullable)
- influencer_id (nullable)
- period_start (date)
- period_end (date)
- score_total
- score_breakdown (jsonb)
- created_at

## API sugerida
- GET /authority?orgId=&ccId=&from=&to=
- GET /authority/trends?orgId=&ccId=&window=90d

## UI sugerida
- Score total + breakdown
- “O que subiria seu score essa semana” (recomendações)
- Benchmark interno (entre centros)

## Uso comercial (SaaS)
- Plano Pro: Authority Score + Predictor
- Plano Enterprise: benchmarking + multi-centro + governança avançada
