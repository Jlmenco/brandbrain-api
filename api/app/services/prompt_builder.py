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
