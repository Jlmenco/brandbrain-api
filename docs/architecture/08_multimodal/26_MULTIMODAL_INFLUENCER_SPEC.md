# Multimodal Influencer (Digital Human) — Spec

## Objetivo
Permitir que cada influencer opere com múltiplos formatos:
- texto (posts)
- imagem (avatar + criativos)
- voz (narração)
- vídeo (avatar falando + reels curtos)
Sempre com consistência visual e governança.

## Níveis (configurável por centro)
- L1: Texto apenas
- L2: Texto + imagens (avatar consistente)
- L3: Texto + imagem + voz
- L4: Texto + imagem + voz + vídeo (avatar)
- L5 (futuro): live assistida (operador no controle)

## Consistência visual (“Visual Bible”)
### influencer_visual_bibles
- influencer_id
- base_prompt (text)
- negative_prompt (text)
- seed (text/int)
- palette (jsonb)
- wardrobe_rules (jsonb)
- environments (jsonb)
- camera_style (jsonb)
- version (int)
- is_active

## Pipeline multimodal
1) Creative Director Agent define formato
2) Gera scripts (roteiro) e storyboard
3) Gera assets (imagem/vídeo) via provedor escolhido
4) Armazena em storage + referencia em content_items.media_refs
5) Vai para review
6) Publica/agenda

## Guardrails
- Deepfake: deixar claro que é influencer digital (se necessário/adequado ao canal).
- Evitar representar pessoas reais sem autorização.
- Evitar conteúdo sensível.
- Requer aprovação humana no MVP.

## API sugerida
- POST /influencers/{id}/visual-bible
- GET /influencers/{id}/visual-bible
- POST /creative/generate-assets (gera imagens/vídeos a partir de prompt e bible)

## Observabilidade
- Guardar prompt + seed + versão do provedor para reprodutibilidade
