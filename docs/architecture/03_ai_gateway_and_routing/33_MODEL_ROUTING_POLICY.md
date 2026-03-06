# Model Routing Policy (Cloud + Local) — Spec

## Objetivo
Escolher automaticamente o modelo certo por:
- intent (criar influencer, gerar post, compliance, market brief)
- classificação de dados (PUBLIC/INTERNAL/CONFIDENTIAL/RESTRICTED)
- custo e latência
- qualidade requerida

## Política base (exemplo)
- Se data_classification in (CONFIDENTIAL, RESTRICTED) -> **Local only**
- Se intent == compliance_check -> modelo robusto + regras determinísticas
- Se intent == simple_copy_variation -> modelo local barato
- Se intent == high_stakes_strategy -> cloud premium (se permitido)

## Inputs do roteamento
- orgId, ccId
- intent
- data_classification
- channel/provider
- required_capabilities: tools, multimodal, embeddings
- budget remaining (ai quota)
- latency target

## Outputs
- model_id
- params (temperature, max_tokens, etc.)
- fallback_order
- logging_policy

## Entidades
- ai_policies.rules (jsonb)
Exemplo de regra:
{
  "when": {"intent": "generate_drafts", "data_classification": "INTERNAL"},
  "use": {"model_tier": "local_standard"},
  "fallback": ["cloud_standard"]
}

## Observabilidade
- medir custo real por centro
- alertar quando budget estourar
