# Market Agent - Workflows e Jobs

## Job Diário (daily)
1) Carregar fontes ativas (macro + por centro)
2) Coletar itens (RSS/Trends)
3) Resumir e taggear
4) Criar market_findings com fonte + data + confiança
5) Se detectar risco (ex.: tópico sensível), marcar type=risk

## Job Semanal (weekly)
1) Selecionar findings da semana por centro
2) Gerar market_brief (estrutura padrão)
3) Gerar 5-10 content_briefs por centro (com fontes)
4) Disponibilizar "Enviar para Marketing Agent" (gerar drafts)

## Integração com Marketing Agent
- Endpoint: POST /agent/marketing/from-content-briefs
Body:
{
  "ccId": "...",
  "contentBriefIds": ["..."],
  "providerTargets": ["linkedin","instagram"],
  "mode": "create_drafts_and_submit_review"
}
