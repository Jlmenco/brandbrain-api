"""Prompt Builder — Constructs rich prompts for content generation with RAG context."""


def build_content_generation_prompt(
    influencer_name: str,
    channel: str,
    topic: str,
    objectives: list[str],
    brand_context_chunks: list[dict],
    language: str = "pt-BR",
) -> tuple[str, str]:
    """Build system prompt and user prompt for content generation.

    Returns (system_prompt, user_prompt).
    """
    # Assemble brand context from retrieved chunks
    context_sections = []
    for chunk in brand_context_chunks:
        context_sections.append(f"[{chunk['chunk_type']}] {chunk['chunk_text']}")

    brand_context = "\n\n".join(context_sections) if context_sections else "(Nenhum contexto de marca disponivel)"

    system_prompt = f"""Voce e um especialista em marketing digital e criacao de conteudo.
Voce escreve como o influencer digital "{influencer_name}".
Idioma: {language}.

=== CONTEXTO DA MARCA ===
{brand_context}
=== FIM DO CONTEXTO ===

Regras:
- Respeite o tom de voz descrito no perfil do influencer.
- Nunca use palavras ou topicos proibidos.
- Adapte o formato ao canal ({channel}).
- Inclua CTA no estilo definido.
- Se o canal for Instagram, use hashtags relevantes.
- Se o canal for LinkedIn, use tom mais profissional e sem hashtags excessivas."""

    objectives_text = ", ".join(objectives) if objectives else "awareness"

    user_prompt = f"""Crie um post para {channel} sobre o tema: "{topic}"

Objetivos: {objectives_text}

O post deve:
1. Ter um hook atrativo na primeira linha
2. Desenvolver o argumento com base nos dados da marca
3. Terminar com um CTA adequado ao canal
4. Respeitar o tom e estilo do influencer

Responda apenas com o texto do post, sem explicacoes adicionais."""

    return system_prompt, user_prompt


# ---------------------------------------------------------------------------
# Repurpose Prompt
# ---------------------------------------------------------------------------

PLATFORM_RULES = {
    "linkedin": "Tom profissional, parágrafos curtos, sem hashtags excessivas (max 3), CTA empresarial.",
    "instagram": "Texto curto e visual, hashtags relevantes (5-15), emojis moderados, CTA de engajamento.",
    "facebook": "Tom conversacional, perguntas para engajamento, links permitidos, hashtags mínimas.",
    "twitter": "Máximo 280 caracteres, direto, hashtags (1-3), tom conciso e impactante.",
    "tiktok": "Linguagem informal e jovem, trends, hashtags virais, CTA de interação.",
    "youtube": "Formato script: intro hook (5s), desenvolvimento, CTA para like/subscribe.",
}


def build_repurpose_prompt(
    original_text: str,
    original_platform: str,
    target_platform: str,
    brand_context_chunks: list[dict],
    language: str = "pt-BR",
) -> tuple[str, str]:
    """Build prompts for content repurposing across platforms.

    Returns (system_prompt, user_prompt).
    """
    context_sections = []
    for chunk in brand_context_chunks:
        context_sections.append(f"[{chunk['chunk_type']}] {chunk['chunk_text']}")
    brand_context = "\n\n".join(context_sections) if context_sections else "(Sem contexto de marca)"

    original_rules = PLATFORM_RULES.get(original_platform, "")
    target_rules = PLATFORM_RULES.get(target_platform, "")

    system_prompt = f"""Voce e um especialista em adaptacao de conteudo para diferentes plataformas de redes sociais.
Idioma: {language}.

=== CONTEXTO DA MARCA ===
{brand_context}
=== FIM DO CONTEXTO ===

Regras gerais:
- Mantenha a mensagem e tom da marca do conteudo original.
- Adapte formato, comprimento, hashtags e CTA para a plataforma alvo.
- Nao invente informacoes que nao estejam no conteudo original.
- Mantenha os pontos principais do conteudo original.

Regras da plataforma de DESTINO ({target_platform}):
{target_rules}"""

    user_prompt = f"""Adapte o seguinte conteudo de {original_platform} para {target_platform}:

=== CONTEUDO ORIGINAL ({original_platform}) ===
{original_text}
=== FIM ===

Crie uma versao otimizada para {target_platform}, respeitando as regras da plataforma.
Responda apenas com o texto adaptado, sem explicacoes adicionais."""

    return system_prompt, user_prompt


# ---------------------------------------------------------------------------
# Editorial Planning Prompt
# ---------------------------------------------------------------------------

def build_editorial_planning_prompt(
    period_type: str,
    period_start: str,
    period_end: str,
    platforms: list[str],
    objectives: list[str],
    brand_context_chunks: list[dict],
    recent_content_summary: str = "",
    top_performing_summary: str = "",
    language: str = "pt-BR",
) -> tuple[str, str]:
    """Build prompts for AI editorial planning.

    Returns (system_prompt, user_prompt).
    """
    context_sections = []
    for chunk in brand_context_chunks:
        context_sections.append(f"[{chunk['chunk_type']}] {chunk['chunk_text']}")
    brand_context = "\n\n".join(context_sections) if context_sections else "(Sem contexto de marca)"

    platforms_text = ", ".join(platforms) if platforms else "linkedin, instagram"
    objectives_text = ", ".join(objectives) if objectives else "awareness, engagement"

    platform_rules_text = "\n".join(
        f"- {p}: {PLATFORM_RULES.get(p, 'Sem regras especificas')}"
        for p in platforms
    )

    system_prompt = f"""Voce e um estrategista de marketing digital especializado em planejamento editorial.
Idioma: {language}.

=== CONTEXTO DA MARCA ===
{brand_context}
=== FIM DO CONTEXTO ===

Regras por plataforma:
{platform_rules_text}

Pilares de conteudo disponiveis:
- Educacao: conteudo que ensina algo relevante ao publico
- Prova Social: depoimentos, resultados, cases de sucesso
- Bastidores: dia-a-dia, cultura, processos internos
- Oferta: produtos, servicos, promocoes
- Comunidade: engajamento, perguntas, enquetes, interacao

Regras:
- Distribua os pilares de forma equilibrada ao longo do periodo.
- Varie as plataformas se mais de uma for fornecida.
- Cada slot deve ter: date (YYYY-MM-DD), time_slot (morning/afternoon/evening), platform, pillar, theme, objective.
- Responda APENAS com um JSON valido, sem explicacoes fora do JSON."""

    recent_section = ""
    if recent_content_summary:
        recent_section = f"""

=== CONTEUDO RECENTE (ultimos 30 dias) ===
{recent_content_summary}
=== FIM ==="""

    performance_section = ""
    if top_performing_summary:
        performance_section = f"""

=== CONTEUDOS DE MELHOR PERFORMANCE ===
{top_performing_summary}
=== FIM ==="""

    user_prompt = f"""Crie um plano editorial para o periodo de {period_start} a {period_end} ({period_type}).

Plataformas: {platforms_text}
Objetivos: {objectives_text}
{recent_section}{performance_section}
Responda com um JSON no formato:
{{
  "rationale": "Explicacao da estrategia...",
  "slots": [
    {{
      "date": "YYYY-MM-DD",
      "time_slot": "morning",
      "platform": "linkedin",
      "pillar": "Educacao",
      "theme": "Tema sugerido para o slot",
      "objective": "awareness"
    }}
  ]
}}"""

    return system_prompt, user_prompt
