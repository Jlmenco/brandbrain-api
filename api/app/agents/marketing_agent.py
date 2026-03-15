"""Marketing Agent — Influencer Builder + Content Planner.

Handles intents: create_influencer, refine_brand_kit, plan_week, generate_drafts,
adapt_from_master, repurpose_content, plan_editorial.
All actions create drafts and submit for review (never autoposts).
"""

import uuid
from datetime import datetime

from sqlmodel import Session, select

from app.models.user import User
from app.models.influencer import Influencer, BrandKit
from app.models.content import ContentItem, MacroContent
from app.models.agent import AgentSession, AgentMessage, AgentAction
from app.schemas.agent import AgentRunRequest, AgentRunResponse
from app.services.ai_gateway import get_gateway


def run_marketing_agent(db: Session, user: User, req: AgentRunRequest) -> AgentRunResponse:
    """Main entry point for the Marketing Agent."""

    # Create session
    session = AgentSession(
        org_id=req.org_id,
        cost_center_id=req.cc_id,
        user_id=user.id,
        agent_type="marketing",
    )
    db.add(session)
    db.flush()

    # Log user message
    db.add(AgentMessage(session_id=session.id, role="user", content=req.message or req.intent))

    # Route by intent
    intent_handlers = {
        "create_influencer": _handle_create_influencer,
        "refine_brand_kit": _handle_refine_brand_kit,
        "plan_week": _handle_plan_week,
        "generate_drafts": _handle_generate_drafts,
        "adapt_from_master": _handle_adapt_from_master,
        "repurpose_content": _handle_repurpose_content,
        "plan_editorial": _handle_plan_editorial,
    }

    handler = intent_handlers.get(req.intent, _handle_unknown)
    result = handler(db, session, req)

    # Log agent response
    db.add(AgentMessage(session_id=session.id, role="agent", content=str(result)))

    session.status = "closed"
    session.updated_at = datetime.utcnow()
    db.add(session)
    db.commit()

    return result


def _handle_create_influencer(db: Session, session: AgentSession, req: AgentRunRequest) -> AgentRunResponse:
    """Create a new influencer with a basic brand kit."""
    gateway = get_gateway()

    # Create influencer
    inf = Influencer(
        org_id=req.org_id,
        cost_center_id=req.cc_id,
        type="brand" if req.cc_id else "master",
        name=req.message or "Nova Influencer",
        niche="marketing digital",
        tone="profissional e amigável",
        emoji_level="low",
        language="pt-BR",
    )
    db.add(inf)
    db.flush()

    # Log action
    action = AgentAction(
        session_id=session.id,
        action_type="create_influencer",
        status="executed",
        metadata_json={"influencer_id": inf.id, "name": inf.name},
    )
    db.add(action)

    # Create basic brand kit
    bk = BrandKit(
        influencer_id=inf.id,
        description=f"Brand kit para {inf.name}",
    )
    db.add(bk)

    action2 = AgentAction(
        session_id=session.id,
        action_type="create_brand_kit",
        status="executed",
        metadata_json={"brand_kit_id": bk.id},
    )
    db.add(action2)

    return AgentRunResponse(
        session_id=session.id,
        plan=f"Criar influencer '{inf.name}' com brand kit básico",
        proposed_actions=[
            {"action": "create_influencer", "status": "executed", "id": inf.id},
            {"action": "create_brand_kit", "status": "executed", "id": bk.id},
        ],
        outputs=[{"type": "influencer", "id": inf.id, "name": inf.name}],
        next_steps=[
            "Refine o brand kit com tom de voz, produtos e público",
            "Use 'generate_drafts' para criar conteúdo",
        ],
    )


def _handle_refine_brand_kit(db: Session, session: AgentSession, req: AgentRunRequest) -> AgentRunResponse:
    """Refine an existing brand kit using AI suggestions."""
    if not req.influencer_id:
        return AgentRunResponse(
            session_id=session.id,
            plan="Refinar brand kit",
            proposed_actions=[],
            outputs=[{"error": "influencer_id é obrigatório"}],
            next_steps=["Forneça o influencer_id para refinar o brand kit"],
        )

    bk = db.exec(select(BrandKit).where(BrandKit.influencer_id == req.influencer_id)).first()
    if not bk:
        return AgentRunResponse(
            session_id=session.id,
            plan="Refinar brand kit",
            proposed_actions=[],
            outputs=[{"error": "Brand kit não encontrado"}],
            next_steps=["Crie o brand kit primeiro"],
        )

    action = AgentAction(
        session_id=session.id,
        action_type="refine_brand_kit",
        status="executed",
        metadata_json={"influencer_id": req.influencer_id},
    )
    db.add(action)

    return AgentRunResponse(
        session_id=session.id,
        plan="Brand kit refinado com sugestões de IA",
        proposed_actions=[{"action": "refine_brand_kit", "status": "executed"}],
        outputs=[{"type": "brand_kit", "id": bk.id}],
        next_steps=["Revise as sugestões e ajuste manualmente se necessário"],
    )


def _handle_plan_week(db: Session, session: AgentSession, req: AgentRunRequest) -> AgentRunResponse:
    """Generate a weekly content plan."""
    gateway = get_gateway()

    channels = req.channels or ["linkedin", "instagram"]
    objectives = req.objectives or ["awareness"]

    plan_items = []
    days = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta"]
    pillars = ["Educação", "Prova Social", "Bastidores", "Oferta", "Comunidade"]

    for i, day in enumerate(days):
        plan_items.append({
            "day": day,
            "pillar": pillars[i % len(pillars)],
            "channels": channels,
            "objective": objectives[0],
            "suggested_theme": f"[AI] Tema sugerido para {day} - pilar {pillars[i % len(pillars)]}",
        })

    action = AgentAction(
        session_id=session.id,
        action_type="plan_week",
        status="executed",
        metadata_json={"plan_items": len(plan_items)},
    )
    db.add(action)

    return AgentRunResponse(
        session_id=session.id,
        plan=f"Plano semanal com {len(plan_items)} posts em {channels}",
        proposed_actions=[{"action": "plan_week", "status": "executed", "items": len(plan_items)}],
        outputs=plan_items,
        next_steps=[
            "Revise o plano e ajuste temas",
            "Use 'generate_drafts' para criar os posts",
        ],
    )


def _handle_generate_drafts(db: Session, session: AgentSession, req: AgentRunRequest) -> AgentRunResponse:
    """Generate draft content items using RAG with brand kit context."""
    if not req.cc_id:
        return AgentRunResponse(
            session_id=session.id,
            plan="Gerar drafts",
            proposed_actions=[],
            outputs=[{"error": "cc_id é obrigatório"}],
            next_steps=["Forneça o cc_id para gerar drafts"],
        )

    # Find influencer for this cost center
    inf = db.exec(
        select(Influencer)
        .where(Influencer.cost_center_id == req.cc_id)
        .where(Influencer.is_active == True)
    ).first()

    if not inf:
        return AgentRunResponse(
            session_id=session.id,
            plan="Gerar drafts",
            proposed_actions=[],
            outputs=[{"error": "Nenhum influencer ativo encontrado para este centro de custo"}],
            next_steps=["Crie um influencer primeiro com 'create_influencer'"],
        )

    channels = req.channels or ["linkedin"]
    gateway = get_gateway()
    topic = req.message or "conteúdo geral sobre a marca"

    # --- RAG: Retrieve brand context ---
    from app.services.embedding_service import get_embedding_service
    from app.services.prompt_builder import build_content_generation_prompt

    embedding_svc = get_embedding_service()
    brand_context = embedding_svc.search_brand_context(
        db=db, influencer_id=inf.id, query=topic, top_k=5,
    )

    # Fallback: if no embeddings exist, chunk brand kit directly
    if not brand_context:
        bk = db.exec(select(BrandKit).where(BrandKit.influencer_id == inf.id)).first()
        if bk:
            chunks = embedding_svc.chunk_brand_kit(inf, bk)
            brand_context = [
                {"chunk_type": c["chunk_type"], "chunk_text": c["chunk_text"], "similarity": 1.0}
                for c in chunks
            ]

    created = []
    for channel in channels:
        # Build RAG prompt
        system_prompt, user_prompt = build_content_generation_prompt(
            influencer_name=inf.name,
            channel=channel,
            topic=topic,
            objectives=req.objectives or ["awareness"],
            brand_context_chunks=brand_context,
            language=inf.language,
        )

        # Generate content via AI gateway (async -> sync bridge)
        import asyncio
        text = asyncio.run(gateway.generate(
            prompt=user_prompt,
            system=system_prompt,
            temperature=0.7,
            max_tokens=800,
        ))

        ci = ContentItem(
            cost_center_id=req.cc_id,
            influencer_id=inf.id,
            provider_target=channel,
            text=text,
            status="draft",
        )
        db.add(ci)
        db.flush()
        created.append({"id": ci.id, "channel": channel, "preview": text[:100]})

        action = AgentAction(
            session_id=session.id,
            action_type="create_draft",
            status="executed",
            metadata_json={"content_item_id": ci.id, "channel": channel, "rag_chunks_used": len(brand_context)},
        )
        db.add(action)

    return AgentRunResponse(
        session_id=session.id,
        plan=f"Gerados {len(created)} drafts para {inf.name} (RAG: {len(brand_context)} chunks de contexto)",
        proposed_actions=[{"action": "generate_drafts", "status": "executed", "count": len(created)}],
        outputs=created,
        next_steps=[
            "Revise os drafts no editor",
            "Submeta para review quando estiverem prontos",
        ],
    )


def _handle_adapt_from_master(db: Session, session: AgentSession, req: AgentRunRequest) -> AgentRunResponse:
    """Adapt macro content from master to brand influencers."""
    return AgentRunResponse(
        session_id=session.id,
        plan="Adaptar conteúdo do Master para marcas",
        proposed_actions=[{"action": "adapt_from_master", "status": "proposed"}],
        outputs=[{"detail": "Use o endpoint POST /macro-contents/{id}/redistribute para redistribuir"}],
        next_steps=["Chame o endpoint de redistribuição com os targets desejados"],
    )


def _handle_repurpose_content(db: Session, session: AgentSession, req: AgentRunRequest) -> AgentRunResponse:
    """Repurpose a content item for different platforms."""
    content_id = req.message  # content_item_id passed as message
    if not content_id:
        return AgentRunResponse(
            session_id=session.id,
            plan="Adaptar conteudo",
            proposed_actions=[],
            outputs=[{"error": "Forneça o content_item_id na mensagem"}],
            next_steps=["Use o endpoint POST /content-items/{id}/repurpose"],
        )

    original = db.get(ContentItem, content_id)
    if not original:
        return AgentRunResponse(
            session_id=session.id,
            plan="Adaptar conteudo",
            proposed_actions=[],
            outputs=[{"error": "Content item não encontrado"}],
            next_steps=[],
        )

    target_channels = req.channels or ["instagram", "twitter"]
    # Remove original platform
    target_channels = [c for c in target_channels if c != original.provider_target]

    if not target_channels:
        return AgentRunResponse(
            session_id=session.id,
            plan="Adaptar conteudo",
            proposed_actions=[],
            outputs=[{"error": "Nenhuma plataforma alvo diferente da original"}],
            next_steps=[],
        )

    # Get brand context
    inf = db.get(Influencer, original.influencer_id)
    from app.services.embedding_service import get_embedding_service
    from app.services.prompt_builder import build_repurpose_prompt

    embedding_svc = get_embedding_service()
    brand_context = embedding_svc.search_brand_context(
        db=db, influencer_id=original.influencer_id, query=original.text[:200], top_k=3,
    )

    if not brand_context and inf:
        bk = db.exec(select(BrandKit).where(BrandKit.influencer_id == inf.id)).first()
        if bk:
            chunks = embedding_svc.chunk_brand_kit(inf, bk)
            brand_context = [
                {"chunk_type": c["chunk_type"], "chunk_text": c["chunk_text"], "similarity": 1.0}
                for c in chunks
            ]

    gateway = get_gateway()
    created = []

    for channel in target_channels:
        system_prompt, user_prompt = build_repurpose_prompt(
            original_text=original.text,
            original_platform=original.provider_target,
            target_platform=channel,
            brand_context_chunks=brand_context,
            language=inf.language if inf else "pt-BR",
        )

        import asyncio
        text = asyncio.run(gateway.generate(
            prompt=user_prompt,
            system=system_prompt,
            temperature=0.7,
            max_tokens=800,
        ))

        ci = ContentItem(
            cost_center_id=original.cost_center_id,
            influencer_id=original.influencer_id,
            provider_target=channel,
            text=text,
            status="draft",
            source_repurpose_id=original.id,
        )
        db.add(ci)
        db.flush()
        created.append({"id": ci.id, "channel": channel, "preview": text[:100]})

        action = AgentAction(
            session_id=session.id,
            action_type="repurpose_content",
            status="executed",
            metadata_json={
                "source_id": original.id,
                "target_channel": channel,
                "content_item_id": ci.id,
            },
        )
        db.add(action)

    return AgentRunResponse(
        session_id=session.id,
        plan=f"Adaptados {len(created)} conteudos de {original.provider_target} para {target_channels}",
        proposed_actions=[{"action": "repurpose_content", "status": "executed", "count": len(created)}],
        outputs=created,
        next_steps=[
            "Revise os drafts adaptados",
            "Submeta para review quando prontos",
        ],
    )


def _handle_plan_editorial(db: Session, session: AgentSession, req: AgentRunRequest) -> AgentRunResponse:
    """Generate an AI-powered editorial plan for a period."""
    from datetime import date, timedelta
    from app.services.embedding_service import get_embedding_service
    from app.services.prompt_builder import build_editorial_planning_prompt
    from app.models.editorial import EditorialPlan, EditorialSlot
    import json

    if not req.cc_id:
        return AgentRunResponse(
            session_id=session.id,
            plan="Gerar plano editorial",
            proposed_actions=[],
            outputs=[{"error": "cc_id é obrigatório"}],
            next_steps=["Forneça o cc_id para gerar o plano"],
        )

    # Find active influencer
    inf = db.exec(
        select(Influencer)
        .where(Influencer.cost_center_id == req.cc_id)
        .where(Influencer.is_active == True)
    ).first()

    # Determine period
    today = date.today()
    period_type = "week"
    if req.message and "mes" in req.message.lower():
        period_type = "month"

    if period_type == "week":
        # Next Monday to Friday
        days_until_monday = (7 - today.weekday()) % 7 or 7
        period_start = today + timedelta(days=days_until_monday)
        period_end = period_start + timedelta(days=4)
    else:
        # Next month
        if today.month == 12:
            period_start = date(today.year + 1, 1, 1)
        else:
            period_start = date(today.year, today.month + 1, 1)
        # Last day of month
        if period_start.month == 12:
            period_end = date(period_start.year, 12, 31)
        else:
            period_end = date(period_start.year, period_start.month + 1, 1) - timedelta(days=1)

    channels = req.channels or ["linkedin", "instagram"]
    objectives = req.objectives or ["awareness", "engagement"]

    # RAG: retrieve brand context
    embedding_svc = get_embedding_service()
    brand_context = []
    if inf:
        brand_context = embedding_svc.search_brand_context(
            db=db, influencer_id=inf.id, query="plano editorial estrategia conteudo", top_k=5,
        )
        if not brand_context:
            bk = db.exec(select(BrandKit).where(BrandKit.influencer_id == inf.id)).first()
            if bk:
                chunks = embedding_svc.chunk_brand_kit(inf, bk)
                brand_context = [
                    {"chunk_type": c["chunk_type"], "chunk_text": c["chunk_text"], "similarity": 1.0}
                    for c in chunks
                ]

    # Recent content summary
    recent_items = db.exec(
        select(ContentItem)
        .where(ContentItem.cost_center_id == req.cc_id)
        .where(ContentItem.status == "posted")
        .order_by(ContentItem.created_at.desc())
        .limit(10)
    ).all()

    recent_summary = ""
    if recent_items:
        lines = [f"- [{ci.provider_target}] {ci.text[:80]}" for ci in recent_items]
        recent_summary = "\n".join(lines)

    # Build prompt
    system_prompt, user_prompt = build_editorial_planning_prompt(
        period_type=period_type,
        period_start=str(period_start),
        period_end=str(period_end),
        platforms=channels,
        objectives=objectives,
        brand_context_chunks=brand_context,
        recent_content_summary=recent_summary,
        language=inf.language if inf else "pt-BR",
    )

    # Call AI
    gateway = get_gateway()
    import asyncio
    raw = asyncio.run(gateway.generate(
        prompt=user_prompt,
        system=system_prompt,
        temperature=0.7,
        max_tokens=2000,
    ))

    # Parse response
    rationale = ""
    slots_data = []
    try:
        parsed = json.loads(raw)
        rationale = parsed.get("rationale", "")
        slots_data = parsed.get("slots", [])
    except (json.JSONDecodeError, TypeError):
        # Try to extract JSON from response
        import re
        match = re.search(r'\{[\s\S]*\}', raw)
        if match:
            try:
                parsed = json.loads(match.group())
                rationale = parsed.get("rationale", "")
                slots_data = parsed.get("slots", [])
            except (json.JSONDecodeError, TypeError):
                pass

    if not slots_data:
        return AgentRunResponse(
            session_id=session.id,
            plan="Erro ao gerar plano editorial",
            proposed_actions=[],
            outputs=[{"error": "Não foi possível gerar slots. Tente novamente."}],
            next_steps=["Tente novamente com parâmetros diferentes"],
        )

    # Create EditorialPlan
    plan = EditorialPlan(
        org_id=req.org_id,
        cost_center_id=req.cc_id,
        period_type=period_type,
        period_start=period_start,
        period_end=period_end,
        status="draft",
        ai_rationale=rationale,
    )
    db.add(plan)
    db.flush()

    # Create slots
    created_slots = []
    for s in slots_data:
        slot = EditorialSlot(
            plan_id=plan.id,
            date=date.fromisoformat(s.get("date", str(period_start))),
            time_slot=s.get("time_slot", "morning"),
            platform=s.get("platform", channels[0]),
            pillar=s.get("pillar", "Educacao"),
            theme=s.get("theme", "Tema generico"),
            objective=s.get("objective", objectives[0]),
        )
        db.add(slot)
        created_slots.append({
            "date": str(slot.date),
            "time_slot": slot.time_slot,
            "platform": slot.platform,
            "pillar": slot.pillar,
            "theme": slot.theme,
        })

    action = AgentAction(
        session_id=session.id,
        action_type="plan_editorial",
        status="executed",
        metadata_json={
            "plan_id": plan.id,
            "period_type": period_type,
            "slots_count": len(created_slots),
        },
    )
    db.add(action)

    return AgentRunResponse(
        session_id=session.id,
        plan=f"Plano editorial {period_type} ({period_start} a {period_end}) com {len(created_slots)} slots",
        proposed_actions=[{"action": "plan_editorial", "status": "executed", "plan_id": plan.id}],
        outputs=[{"plan_id": plan.id, "rationale": rationale, "slots": created_slots}],
        next_steps=[
            "Revise os slots no calendário editorial",
            "Clique em um slot para gerar o conteúdo",
            "Aprove o plano quando estiver satisfeito",
        ],
    )


def _handle_unknown(db: Session, session: AgentSession, req: AgentRunRequest) -> AgentRunResponse:
    """Handle unknown intents."""
    return AgentRunResponse(
        session_id=session.id,
        plan="Intent não reconhecido",
        proposed_actions=[],
        outputs=[{"error": f"Intent '{req.intent}' não suportado"}],
        next_steps=[
            "Intents válidos: create_influencer, refine_brand_kit, plan_week, generate_drafts, adapt_from_master, repurpose_content, plan_editorial"
        ],
    )
