# Performance Prediction Engine — Spec (Moat)

## Objetivo
Prever performance **antes** de publicar, para orientar:
- escolha de tema/formato
- tamanho do texto
- horário
- CTA
- risco reputacional
- saturação do assunto

## Outputs (scores)
- predicted_engagement (0..100)
- predicted_ctr (0..100)
- predicted_lead_score (0..100)   # se tracking/landing
- narrative_alignment (0..100)
- saturation_score (0..100)      # 100 = muito saturado
- risk_score (0..100)            # 100 = alto risco

## Versão 1 (MVP-Plus) — Heurística + Baseline
Sem ML pesado no início:
- Regras baseadas em histórico do canal + padrões (tamanho, hook, CTA)
- Penalidade por repetição e por saturação (tema repetido na semana)
- Ajuste por horário (usando histórico de métricas)

## Versão 2 — ML Leve (após dados suficientes)
- Modelo por provider e por centro de custo
- Algoritmos: regressão / gradient boosting (LightGBM) / árvores
- Features:
  - comprimento do texto
  - presença de pergunta no hook
  - tipo de CTA (comentário vs link)
  - hashtags count
  - pilar narrativo
  - horário/dia
  - histórico de performance do influencer/canal
  - tendência do tema (market findings)
  - similaridade com posts recentes (anti-duplicação)
- Labels:
  - engagement_rate
  - ctr
  - lead_rate

## Entidades sugeridas (DB)
### content_predictions
- id
- content_item_id
- predicted_engagement
- predicted_ctr
- predicted_lead_score
- narrative_alignment
- saturation_score
- risk_score
- model_version
- features (jsonb)
- created_at

## API sugerida
- POST /predict/content
Body: { contentItemId | contentDraftPayload }
Returns: scores + explicações resumidas

## UI sugerida
- Mostrar badge/score no editor:
  - “Engajamento: 78/100”
  - “Saturação: Alta”
  - “Risco: Baixo”
- Recomendações automáticas:
  - “reduza hashtags”
  - “troque CTA para comentário”
  - “poste 09:10 terça”

## Guardrails
- Scores nunca devem auto-publicar sozinhos.
- Scores devem explicar em 2-4 bullets o porquê (transparência).
