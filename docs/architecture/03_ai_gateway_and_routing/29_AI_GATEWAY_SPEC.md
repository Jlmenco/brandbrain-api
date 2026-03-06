# AI Gateway (LLM Abstraction Layer) — Spec

## Objetivo
Isolar o core do produto de qualquer provedor/modelo específico, suportando:
- Cloud LLMs (OpenAI, Anthropic, Bedrock, Vertex, Azure OpenAI)
- LLMs locais (vLLM/TGI/Ollama/servidor interno)
- Roteamento por política (custo, confidencialidade, qualidade)
- Observabilidade e auditoria (prompt/result metadata)

## Componentes
1) **LLM Adapter Interface**
- generate(prompt, params) -> response
- embed(texts, params) -> vectors
- moderate(text) -> flags (opcional)
- estimate_cost(tokens) -> cost_estimate

2) **Model Registry**
- lista de modelos disponíveis, capacidades, custo e políticas

3) **Policy Engine**
- regras por org/cc/intent
- decide modelo (cloud/local), temperatura, limites, etc.

4) **Prompt Logger**
- registra metadados (sem vazar segredos)
- suporte a criptografia e retenção

5) **Fallback & Circuit Breaker**
- se cloud falhar -> local
- se local saturar -> fila/espera -> cloud (se permitido)

## Entidades sugeridas (DB)
### ai_models
- id
- org_id (nullable)      # modelos globais ou por cliente
- name
- provider_type: cloud | local
- provider_name
- model_name
- version
- capabilities (jsonb)   # chat, tools, multimodal, embeddings
- cost_profile (jsonb)   # $/1k tokens, latência esperada
- privacy_profile (jsonb)# allow_cloud, data_retention
- is_active (bool)
- created_at

### ai_policies
- id
- org_id
- cost_center_id (nullable)
- rules (jsonb)          # roteamento por intent/data_classification
- created_at

### ai_requests (audit)
- id
- org_id
- cost_center_id (nullable)
- user_id (nullable)
- agent_type (text)
- intent (text)
- model_id
- params (jsonb)
- prompt_hash (text)     # opcional: guardar hash
- prompt_encrypted (bytea/text)  # opcional: only if allowed
- response_encrypted (bytea/text)# opcional
- tokens_in
- tokens_out
- latency_ms
- status
- created_at

## API sugerida
- POST /ai/generate
- POST /ai/embed
- GET  /ai/models
- POST /ai/models
- POST /ai/policies
