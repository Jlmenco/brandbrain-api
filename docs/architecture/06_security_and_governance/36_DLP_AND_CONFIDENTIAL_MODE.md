# DLP & Confidential Mode — Spec

## Objetivo
Garantir que dados sensíveis nunca vazem e que clientes regulados possam operar com confiança.

## DLP (Data Loss Prevention)
- Detectar:
  - PII: email, telefone, CPF, RG, endereço
  - Segredos: tokens, chaves, credenciais
  - Dados comerciais: preços, contratos (via regras/tagging)
- Ações:
  - mascarar em logs
  - bloquear envio para cloud quando data_classification >= CONFIDENTIAL
  - exigir aprovação reforçada

## Confidential Mode (por org/cc)
Quando ON:
- Cloud LLMs desabilitados
- Telemetria externa off
- Logs criptografados e armazenados localmente
- Somente conectores/armazenamento internos
- Auditoria reforçada

## Entidades sugeridas
### security_settings
- org_id
- cost_center_id (nullable)
- confidential_mode (bool)
- dlp_rules (jsonb)
- created_at

## UI
- Toggle “Confidential Mode”
- Banner indicando modo ativo
- Alertas quando tentar ação proibida

## Compliance
- evidências para auditoria (quem acessou/gerou o quê)
- export de logs (com redaction)
