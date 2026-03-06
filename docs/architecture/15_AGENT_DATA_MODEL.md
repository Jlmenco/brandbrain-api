# Marketing Agent - Data Model

## Tabelas (opcionais, recomendadas)
### agent_sessions
- id (uuid)
- org_id
- cost_center_id (nullable)
- user_id
- agent_type: marketing
- status: active | closed
- created_at
- updated_at

### agent_messages
- id
- session_id
- role: user | agent | tool
- content (text/jsonb)
- created_at

### agent_actions
- id
- session_id
- action_type (text)  # create_influencer, generate_drafts, etc.
- status: proposed | executed | failed
- metadata (jsonb)
- created_at
