# Workflows (MVP)

## Workflow 1: Criar influencer (Master e Marca)
1) Admin cria Influencer Master (org, type=master, cost_center_id=null)
2) Admin cria Cost Center (Melpura)
3) Admin cria Influencer da Melpura (type=brand, cc_id=Melpura)
4) Preenche Brand Kit (tom, público, produtos, links, restrições)

## Workflow 2: Gerar macro conteúdo e redistribuir
1) Influencer Master gera MacroContent (tema + objetivos)
2) Redistribuição cria drafts por cost center:
   - Adapta tom e CTA
   - Ajusta hashtags por nicho
   - Aplica palavras proibidas/permitidas
3) Drafts vão para REVIEW

## Workflow 3: Aprovação -> Agendamento -> Publicação
1) Editor revisa e aprova
2) Agenda para data/horário
3) Worker publica (quando permitido pela API)
4) Salva provider_post_id + url
5) Collector puxa métricas diárias

## Workflow 4: Tracking e leads
1) Cada post pode receber tracking link (slug + UTM)
2) Eventos de clique/lead alimentam métricas e pipeline

## Workflow 5: Agents
- Marketing Agent cria influencer, brand kit, calendário e drafts.
- Market Agent roda diariamente/semanalmente para gerar briefs e content briefs.
