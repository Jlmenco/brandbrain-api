# Redistribuição (Master -> Marcas)

## Objetivo
Transformar um MacroContent institucional em conteúdos específicos por centro de custo.

## Input
- MacroContent (tema, conteúdo bruto, estrutura)
- Lista de centros alvo
- Canal alvo (LinkedIn/Instagram/etc)
- Brand Kit e DNA de cada influencer

## Regras
1) Manter a ideia central (não distorcer).
2) Trocar exemplos e linguagem para o nicho da marca.
3) Preservar compliance (sem promessas absolutas).
4) Ajustar CTA para o funil da marca.
5) Ajustar hashtags por nicho.
6) Evitar duplicação: cada marca deve ficar visivelmente diferente.

## Prompt de redistribuição (template)
Você recebeu um conteúdo macro do Grupo:
{MACRO_CONTENT}

Adapte para a marca {MARCA} usando o Brand Kit:
{BRAND_KIT_JSON}

Canal: {CANAL}
Objetivo: {OBJETIVO} (leads/awareness/trafego)

Restrições:
- Proibidos: {FORBIDDEN_WORDS}
- Tópicos proibidos: {FORBIDDEN_TOPICS}
- Emojis: {EMOJI_LEVEL}

Saída:
- 1 versão final
- 2 variações (A/B)
- Hashtags
- Sugestão de criativo
- Sugestão de CTA e link (se aplicável)
