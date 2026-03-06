# Marketing Agent - Guardrails

## Conteúdo
- Proibir tópicos configurados (ex.: política/religião)
- Proibir palavras/termos configurados por influencer
- Detectar promessas absolutas e claims de saúde/finanças
- Anti-repetição: bloquear posts muito similares no mesmo período
- Limitar volume: ex.: max 3 posts/dia por canal por centro

## Operação
- Default: sem autopost.
- Somente drafts + review.
- Se feature "autopost" existir:
  - Exigir enable explícito por centro de custo
  - Limites rígidos + allowlist de temas
  - Logs e rollback (desligar rápido)

## Segurança
- Não exibir tokens OAuth em respostas
- RBAC: editor/admin para gerar em lote e submeter review
