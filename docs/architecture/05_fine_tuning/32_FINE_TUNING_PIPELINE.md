# Fine-tuning por Cliente — Pipeline

## Objetivo
Aprimorar comportamento (tom, formato, consistência) e tasks (classificação/roteamento), sem usar fine-tune para “fatos”.

## Tipos de fine-tune
### 1) Style/Format Fine-tune (recomendado primeiro)
- padroniza saída: hook, valor, CTA, hashtags, variações
- aprende tom e jargões
- baixo risco

### 2) Task Fine-tune (fase 2/3)
- classificar pilar narrativo
- classificar risco
- sugerir canal/formato
- roteamento de modelos

## Dataset (curadoria)
- exemplos aprovados pelo cliente (golden set)
- exemplos rejeitados (anti-patterns)
- guidelines editoriais + policies
- output format schema

## Processo
1) Coletar exemplos (content_items status=posted/approved)
2) Anonimizar/limpar dados sensíveis (DLP)
3) Construir pares (input -> output) com contexto (brand kit + narrative)
4) Treinar (no ambiente do cliente se necessário)
5) Avaliar (quality gates + regressão)
6) Deploy via Model Registry (ai_models)
7) Monitorar drift (qualidade cai -> rollback)

## Entidades sugeridas (DB)
### fine_tune_jobs
- id
- org_id
- cost_center_id (nullable)
- job_type: style | task
- dataset_ref (uri)
- base_model_id
- output_model_id
- status
- metrics (jsonb)
- created_at

## Guardrails
- Sem dados RESTRICTED indo para cloud.
- Treino exige aprovação do cliente (legal/compliance).
- Versionamento e rollback obrigatórios.
