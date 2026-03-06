# RAG Security & Access Policy

## Objetivo
Garantir que conhecimento e dados não vazem entre marcas/centros de custo e que o uso de cloud/local respeite confidencialidade.

## Classificação de dados (sugestão)
- PUBLIC
- INTERNAL
- CONFIDENTIAL
- RESTRICTED

## Regras por default
1) Documentos com cost_center_id pertencem apenas ao centro.
2) Documentos corporativos (cost_center_id = null) podem ser compartilháveis, mas:
   - precisam tag: shareable=true
   - caso contrário, só Master e roles altos acessam

3) Retrieval sempre filtra por:
- org_id
- cost_center_id (ou corporativo permitido)
- RBAC do usuário

4) Modo CONFIDENTIAL
- bloqueia qualquer modelo cloud
- prompts/respostas logados apenas localmente e criptografados
- desliga telemetry externa

## DLP (Data Loss Prevention)
- detectar PII (email, CPF, telefone) e segredos
- mascarar em logs
- política por centro para permitir/bloquear saída

## Auditoria
- log de quem consultou o quê
- log de quais chunks foram usados
