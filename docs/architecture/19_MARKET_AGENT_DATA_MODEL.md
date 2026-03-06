# Market Intelligence Agent - Data Model

## market_sources
- id (uuid)
- org_id
- cost_center_id (nullable)  # null => fontes macro do Grupo
- name
- type: rss | website | report | trends
- url
- tags (jsonb)
- is_active (bool)
- created_at

## competitors
- id
- org_id
- cost_center_id
- name
- website_url
- social_handles (jsonb)
- notes (text)
- created_at

## market_findings
- id
- org_id
- cost_center_id (nullable)
- title
- summary
- tags (jsonb)
- source_url
- source_published_at (timestamp/date)
- extracted_evidence (text)  # pequeno trecho/resumo do porquê
- confidence (numeric)       # 0..1
- type: trend | competitor | faq | opportunity | risk
- created_at

## market_briefs
- id
- org_id
- cost_center_id (nullable)
- week_start (date)
- week_end (date)
- content (jsonb)            # estrutura do brief
- created_at

## content_briefs
- id
- org_id
- cost_center_id (nullable)
- based_on_finding_ids (jsonb array)
- title
- thesis
- arguments (jsonb array)
- proof (jsonb)              # {text, source_url, date}
- format_suggestions (jsonb) # por canal
- cta_suggestion (text)
- created_at
