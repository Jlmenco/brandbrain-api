"""Brand kit suggestion service.

Generates structured suggestions for each brand kit field using AIGateway.
Each field has its own prompt strategy and expected output shape.
"""
import json
import logging
from typing import Any

from app.models.influencer import BrandKit, Influencer
from app.services.ai_gateway import get_gateway

logger = logging.getLogger("app.brand_kit")

SUPPORTED_FIELDS = {"description", "value_props", "products", "audience", "style_guidelines"}

_LANG_LABELS = {
    "pt-BR": "português brasileiro",
    "en-US": "inglês americano",
    "es": "espanhol",
}


def _lang_label(lang: str) -> str:
    return _LANG_LABELS.get(lang, "português brasileiro")


def _existing_context(bk: BrandKit | None) -> str:
    if not bk:
        return ""
    parts = []
    if bk.description:
        parts.append(f"Descrição já preenchida: {bk.description}")
    if bk.value_props:
        parts.append(f"Proposta de valor já preenchida: {json.dumps(bk.value_props, ensure_ascii=False)}")
    if bk.products:
        parts.append(f"Produtos já preenchidos: {json.dumps(bk.products, ensure_ascii=False)}")
    if bk.audience:
        parts.append(f"Público já preenchido: {json.dumps(bk.audience, ensure_ascii=False)}")
    if bk.style_guidelines:
        parts.append(f"Estilo já preenchido: {json.dumps(bk.style_guidelines, ensure_ascii=False)}")
    if not parts:
        return ""
    return "Contexto já preenchido pelo usuário (use para coerência):\n" + "\n".join(parts) + "\n\n"


def _build_prompt(field: str, inf: Influencer, bk: BrandKit | None, user_hint: str) -> tuple[str, str, bool]:
    """Return (system_prompt, user_prompt, expects_json)."""
    lang = _lang_label(inf.language)
    base_ctx = (
        f"Marca/Influenciador: {inf.name}\n"
        f"Nicho: {inf.niche or '(não informado)'}\n"
        f"Tom de voz: {inf.tone or '(não informado)'}\n"
        f"Idioma da saída: {lang}\n"
    )
    extra = _existing_context(bk)
    hint = f"Pista do usuário: {user_hint}\n" if user_hint else ""

    system = (
        "Você é um especialista em branding e copywriting. "
        "Suas respostas DEVEM seguir EXATAMENTE o formato pedido — sem texto extra, "
        "sem markdown, sem aspas externas, sem 'Resposta:'."
    )

    if field == "description":
        user = (
            f"{base_ctx}{extra}{hint}"
            "Tarefa: escreva uma descrição concisa da marca em 2 ou 3 frases (máx. 250 caracteres). "
            "Retorne APENAS o texto cru da descrição."
        )
        return system, user, False

    if field == "value_props":
        user = (
            f"{base_ctx}{extra}{hint}"
            "Tarefa: liste 3 a 5 propostas de valor desta marca. "
            'Retorne APENAS um objeto JSON no formato {"chave_substantivo": "frase de até 80 chars", ...}. '
            "Cada chave deve ser uma palavra curta (snake_case, sem espaços) representando o tipo da proposta. "
            "Cada valor deve ser uma frase curta e direta no idioma pedido."
        )
        return system, user, True

    if field == "products":
        user = (
            f"{base_ctx}{extra}{hint}"
            "Tarefa: liste de 3 a 5 produtos ou serviços principais que a marca oferece. "
            'Retorne APENAS um objeto JSON no formato {"nome_do_produto": "descrição curta", ...}. '
            "A chave deve ser o nome do produto em snake_case e o valor uma descrição de até 120 chars."
        )
        return system, user, True

    if field == "audience":
        user = (
            f"{base_ctx}{extra}{hint}"
            "Tarefa: caracterize o público-alvo desta marca. "
            'Retorne APENAS um objeto JSON com as chaves: perfil, idade_faixa, regiao, '
            "interesses, dores. Cada valor deve ser uma string curta (até 100 chars)."
        )
        return system, user, True

    if field == "style_guidelines":
        user = (
            f"{base_ctx}{extra}{hint}"
            "Tarefa: defina diretrizes de estilo de comunicação desta marca. "
            'Retorne APENAS um objeto JSON com as chaves: tom_voz, palavras_chave, '
            "palavras_proibidas, uso_emojis, formato_preferido. Cada valor uma string curta."
        )
        return system, user, True

    raise ValueError(f"Campo nao suportado: {field}")


def _extract_json(raw: str) -> dict:
    """Try to parse JSON object from raw model output, handling code fences."""
    text = raw.strip()
    if text.startswith("```"):
        # strip markdown fence
        text = text.split("```", 2)[1] if "```" in text[3:] else text[3:]
        text = text.removeprefix("json").strip()
        text = text.rsplit("```", 1)[0].strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"Resposta sem JSON parseavel: {raw[:200]}")
    return json.loads(text[start:end + 1])


async def generate_suggestion(
    inf: Influencer,
    bk: BrandKit | None,
    field: str,
    user_hint: str = "",
) -> Any:
    if field not in SUPPORTED_FIELDS:
        raise ValueError(f"Campo nao suportado: {field}")

    system, prompt, expects_json = _build_prompt(field, inf, bk, user_hint)
    gateway = get_gateway()

    raw = await gateway.generate(
        prompt=prompt,
        system=system,
        temperature=0.7,
        max_tokens=600,
    )

    if not expects_json:
        return raw.strip().strip('"').strip()

    try:
        data = _extract_json(raw)
    except (ValueError, json.JSONDecodeError) as e:
        logger.warning("Falha ao parsear JSON para %s: %s | raw=%s", field, e, raw[:300])
        raise

    return {str(k): str(v) for k, v in data.items()}
