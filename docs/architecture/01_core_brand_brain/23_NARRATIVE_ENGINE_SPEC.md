# Narrative Engine — Spec

## Objetivo
Manter coerência e consistência de posicionamento ao longo do tempo, por:
- Organization (tese macro)
- Cost Center (tese de marca)
- Influencer (tom e estilo)

## Conceitos
### Narrative Thesis (Tese)
Uma afirmação central que guia conteúdo e posicionamento (ex.: “Rastreabilidade é o futuro da confiança alimentar.”)

### Pillars (Pilares)
3-7 pilares de conteúdo (educação, prova social, bastidores, oferta, comunidade, inovação, ESG).

### Message Map (Mapa de mensagens)
- Mensagem principal
- 3-5 mensagens de suporte
- Provas (cases, dados, certificações)
- Objeções e respostas

### Topic Policy (Política de tópicos)
- allowlist: tópicos permitidos
- blocklist: tópicos proibidos (política/religião/temas sensíveis)
- nuance rules: tópicos permitidos com cuidado (saúde, finanças)

## Entidades sugeridas (DB)
### narrative_profiles
- id
- org_id
- cost_center_id (nullable)  # null => macro do grupo
- title
- thesis
- pillars (jsonb)
- message_map (jsonb)
- topic_policy (jsonb)
- tone_guidelines (jsonb)
- version (int)
- is_active (bool)
- created_at

### narrative_events (opcional)
- id
- narrative_profile_id
- type: update | experiment | incident
- notes
- created_at

## Regras do Narrative Engine
1) Todo conteúdo deve “marcar” pelo menos 1 pilar.
2) Conteúdo fora do topic_policy deve ser bloqueado ou exigir aprovação reforçada.
3) Evitar repetição: monitorar saturação por pilar e por canal.
4) As mensagens do Master não podem contradizer as marcas, e vice-versa.
5) Mudanças de tese/pilares geram versão nova (versionamento).

## API sugerida
- GET /narratives?orgId=&ccId=
- POST /narratives
- PATCH /narratives/{id}
- POST /narratives/{id}/activate

## Integração com agentes
- Marketing Agent: consulta narrative_profile antes de gerar conteúdo.
- Market Agent: sugere atualizações de pilares e message map quando detectar mudança de mercado.
- Compliance Agent: aplica topic_policy como regra de bloqueio.
