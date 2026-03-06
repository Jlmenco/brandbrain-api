# Marketing Agent (Influencer Builder + Content Planner) - Spec

## Objetivo
Um agente de IA dentro do sistema que ajuda a:
1) Criar influencer (Master ou de marca)
2) Criar/atualizar Brand Kit
3) Montar calendário editorial
4) Gerar drafts em lote (A/B)
5) Preparar redistribuição a partir do Master
6) Submeter para revisão (human-in-the-loop)

## Princípios (guardrails)
- Nunca publicar diretamente no MVP.
- Sempre criar drafts e submeter para review.
- Toda ação via "tools" internas (funções do sistema), com auditoria.
- Respeitar RBAC, cost_center_id e políticas de conteúdo.

## Intenções (intents)
- create_influencer: cria influencer + brand kit base
- refine_brand_kit: ajusta persona/voz/regras
- plan_week: gera plano semanal (pilares + temas + canais)
- generate_drafts: cria N drafts por canal e centro
- adapt_from_master: chama redistribuição do macro
- prep_tracking: cria tracking links + UTM para posts aprovados

## Entrada padrão
- orgId
- ccId (opcional para master)
- influencerId (opcional)
- objetivos: leads/awareness/tráfego
- canais alvo: linkedin/instagram/facebook etc.
- restrições: tópicos proibidos, palavras proibidas, emoji level

## Saída padrão
1) Plano (o que vai fazer)
2) Ações propostas (lista)
3) Drafts gerados (IDs + preview)
4) Próximos passos (submeter review / ajustes)

## Tools internas (funções)
- list_cost_centers(orgId)
- get_cost_center(ccId)
- get_influencer(influencerId)
- create_influencer(payload)
- update_influencer(influencerId, payload)
- upsert_brand_kit(influencerId, payload)
- create_content_item(payload)
- submit_for_review(contentItemId)
- create_macro_content(payload)
- redistribute_macro_content(macroId, targets, provider_targets)
- create_tracking_link(payload)
- log_audit(action, target, metadata)

## Onde roda
- API endpoint: POST /agent/marketing/run
- Worker opcional para geração em lote: POST /agent/marketing/run-async (fase 2)

## Logs e auditoria
- Cada tool call gera audit_log (org, cc, actor, action, metadata).
