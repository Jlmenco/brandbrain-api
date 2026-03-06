# Modelo de Dados (PostgreSQL)

## Entidades principais (core)
### organizations
- id (uuid)
- name
- created_at

### users
- id (uuid)
- email (unique)
- name
- created_at

### org_members
- org_id
- user_id
- role: owner | admin | editor | viewer

### cost_centers
- id (uuid)
- org_id
- name
- code (ex: MELPURA, MEATFRIENDS)
- monthly_budget_media (numeric)
- monthly_budget_ai (numeric)
- created_at

### influencers
- id (uuid)
- org_id
- cost_center_id (nullable)  # NULL => influencer master
- type: master | brand
- name
- niche
- tone
- emoji_level: none | low | medium | high
- forbidden_topics (jsonb array)
- forbidden_words (jsonb array)
- allowed_words (jsonb array)
- cta_style (text)
- language (default pt-BR)
- is_active (bool)
- created_at

### brand_kits
- id
- influencer_id
- description (text)
- value_props (jsonb)
- products (jsonb)
- audience (jsonb)
- style_guidelines (jsonb)
- links (jsonb)

### influencer_assets
- id
- influencer_id
- asset_type: avatar | logo | background | media
- storage_url
- metadata (jsonb)
- created_at

### social_accounts
- id
- org_id
- cost_center_id
- provider: meta | linkedin | x | tiktok | youtube | etc
- account_name
- account_id
- scopes (jsonb)
- token_encrypted
- refresh_token_encrypted
- token_expires_at
- status: connected | revoked | expired
- created_at

### campaigns
- id
- cost_center_id
- name
- objective: leads | awareness | traffic
- start_date
- end_date
- created_at

### macro_contents
- id
- org_id
- influencer_master_id
- theme
- content_raw (text)
- content_structured (jsonb)
- status: draft | ready | archived
- created_at

### content_items
- id
- cost_center_id
- influencer_id
- campaign_id (nullable)
- source_macro_id (nullable)
- provider_target: linkedin | instagram | facebook | etc
- text
- media_refs (jsonb)
- status: draft | review | approved | scheduled | posted | failed
- scheduled_at (timestamp)
- posted_at (timestamp)
- provider_post_id (text)
- provider_post_url (text)
- version (int)
- created_at
- updated_at

### approvals
- id
- content_item_id
- reviewer_user_id
- decision: approve | request_changes | reject
- notes
- created_at

### tracking_links
- id
- cost_center_id
- content_item_id (nullable)
- slug (unique)
- destination_url
- utm (jsonb)
- created_at

### events
- id
- org_id
- cost_center_id
- type: click | lead | conversion
- tracking_link_id (nullable)
- metadata (jsonb)
- created_at

### leads
- id
- cost_center_id
- source: form | whatsapp | dm | manual
- name
- email
- phone
- score (int)
- status: new | qualified | won | lost
- metadata (jsonb)
- created_at

### metrics_daily
- id
- content_item_id
- date
- impressions
- likes
- comments
- shares
- clicks
- followers_delta
- created_at

### audit_logs
- id
- org_id
- cost_center_id (nullable)
- actor_user_id (nullable)
- action (text)
- target_type (text)
- target_id (uuid/text)
- metadata (jsonb)
- created_at

## Entidades adicionais (Agents / Mercado)
Ver `15_MARKET_AGENT_DATA_MODEL.md` e `17_AGENT_DATA_MODEL.md`.

## Observações
- Tokens sempre criptografados.
- IDs UUID.
- Índices: (cost_center_id, status), (provider_post_id), (slug), (date).
