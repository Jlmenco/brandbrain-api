# Governança Enterprise (modo pesado)

## Objetivo
Permitir autonomia com controle:
- proteger contas sociais
- proteger reputação
- manter compliance
- permitir auditoria e rollback

## Controles obrigatórios
1) **Kill Switch**
- por provider
- por centro de custo
- por org
Ação imediata: parar jobs de publicação e coleta.

2) **Approval Policies**
- Default: tudo passa por review.
- Policy por centro:
  - required reviewers (N)
  - temas que exigem owner/admin
  - horários permitidos
  - volume máximo diário

3) **Rate limiting & quotas**
- por provider e por cc
- quotas de IA (tokens) por centro
- volume de drafts em lote exige confirmação

4) **Explainability**
- qualquer recomendação do predictor deve ter explicação curta
- market findings devem ter fonte + data

5) **Audit trail**
- log completo de ações (agent + usuário)
- logs imutáveis (append-only) idealmente

6) **Incidents**
- registro de incidentes (post removido, reclamação, restrição)
- penalidade no Risk e no Authority Score

## Entidades sugeridas
### approval_policies
- org_id
- cost_center_id
- rules (jsonb)
- created_at

### incidents
- org_id
- cost_center_id
- provider
- content_item_id
- severity
- description
- actions_taken
- created_at

## Segurança
- tokens: KMS/Secret Manager
- principle of least privilege (scopes mínimos)
- segregação de dados por cc
- LGPD: export/delete de leads

## Operação
- “Safe Mode” ativável: apenas drafts, sem publish.
- “Compliance Mode” ativável: bloqueia temas sensíveis + exige aprovação de owner.
