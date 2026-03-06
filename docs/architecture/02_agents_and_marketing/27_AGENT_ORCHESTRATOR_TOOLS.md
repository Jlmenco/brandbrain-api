# Agent Orchestrator — Tools e Contratos

## Objetivo
Padronizar “tools” internas para que os agentes operem com segurança (auditável, RBAC, multi-tenant).

## Princípios
- O LLM nunca acessa DB diretamente: chama tools.
- Tools são idempotentes quando possível.
- Cada tool call gera audit_log.
- Tools validam RBAC e cost_center_id.

## Tools (mínimo)
### Tenancy
- list_cost_centers(orgId)
- get_cost_center(ccId)

### Influencer
- create_influencer(payload)
- update_influencer(influencerId, payload)
- upsert_brand_kit(influencerId, payload)
- upsert_visual_bible(influencerId, payload)

### Conteúdo
- create_macro_content(payload)
- redistribute_macro_content(macroId, targets, provider_targets, mode)
- create_content_item(payload)
- update_content_item(id, payload)
- submit_for_review(id)
- approve_content(id)
- request_changes(id, notes)

### Tracking/Leads
- create_tracking_link(payload)
- create_lead(payload)

### Mercado
- upsert_market_source(payload)
- upsert_competitor(payload)
- create_market_finding(payload)
- create_market_brief(payload)
- create_content_brief(payload)

### Predição/Authority
- predict_content(payload)
- compute_authority_score(payload)

### Auditoria
- log_audit(action, target_type, target_id, metadata)

## API (sugestão)
- POST /agent/orchestrate
Body: { agentType, intent, context, userMessage }

Retorno:
- plan
- proposed_actions
- tool_calls (executed)
- outputs (ids/preview)
