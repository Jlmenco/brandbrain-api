"""Editorial Planning router — AI-generated content calendars."""
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, select

from app.database import get_session
from app.dependencies import get_current_user, check_role, EDITOR_ROLES, ADMIN_ROLES
from app.models.editorial import EditorialPlan, EditorialSlot
from app.models.content import ContentItem
from app.models.influencer import Influencer, BrandKit

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class EditorialSlotResponse(BaseModel):
    id: str
    plan_id: str
    date: date
    time_slot: str
    platform: str
    pillar: str
    theme: str
    objective: str
    content_item_id: Optional[str] = None


class EditorialPlanResponse(BaseModel):
    id: str
    org_id: str
    cost_center_id: Optional[str] = None
    period_type: str
    period_start: date
    period_end: date
    status: str
    ai_rationale: Optional[str] = None
    slots: list[EditorialSlotResponse] = []


class EditorialSlotUpdate(BaseModel):
    time_slot: Optional[str] = None
    platform: Optional[str] = None
    pillar: Optional[str] = None
    theme: Optional[str] = None
    objective: Optional[str] = None


class GeneratePlanRequest(BaseModel):
    org_id: str
    cc_id: str
    period_type: str = "week"  # week | month
    platforms: list[str] = ["linkedin", "instagram"]
    objectives: list[str] = ["awareness", "engagement"]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/plans")
def list_plans(
    org_id: str = Query(...),
    cc_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """List editorial plans for an organization."""
    check_role(db, current_user.id, org_id, EDITOR_ROLES)

    stmt = select(EditorialPlan).where(EditorialPlan.org_id == org_id)
    if cc_id:
        stmt = stmt.where(EditorialPlan.cost_center_id == cc_id)
    if status:
        stmt = stmt.where(EditorialPlan.status == status)
    stmt = stmt.order_by(EditorialPlan.period_start.desc())

    plans = db.exec(stmt).all()
    result = []
    for plan in plans:
        slots = db.exec(
            select(EditorialSlot).where(EditorialSlot.plan_id == plan.id)
            .order_by(EditorialSlot.date.asc())
        ).all()
        result.append(EditorialPlanResponse(
            id=plan.id,
            org_id=plan.org_id,
            cost_center_id=plan.cost_center_id,
            period_type=plan.period_type,
            period_start=plan.period_start,
            period_end=plan.period_end,
            status=plan.status,
            ai_rationale=plan.ai_rationale,
            slots=[EditorialSlotResponse(
                id=s.id, plan_id=s.plan_id, date=s.date, time_slot=s.time_slot,
                platform=s.platform, pillar=s.pillar, theme=s.theme,
                objective=s.objective, content_item_id=s.content_item_id,
            ) for s in slots],
        ))
    return result


@router.get("/plans/{plan_id}")
def get_plan(
    plan_id: str,
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Get a single editorial plan with its slots."""
    plan = db.get(EditorialPlan, plan_id)
    if not plan:
        raise HTTPException(404, "Plano editorial nao encontrado")

    check_role(db, current_user.id, plan.org_id, EDITOR_ROLES)

    slots = db.exec(
        select(EditorialSlot).where(EditorialSlot.plan_id == plan.id)
        .order_by(EditorialSlot.date.asc())
    ).all()

    return EditorialPlanResponse(
        id=plan.id,
        org_id=plan.org_id,
        cost_center_id=plan.cost_center_id,
        period_type=plan.period_type,
        period_start=plan.period_start,
        period_end=plan.period_end,
        status=plan.status,
        ai_rationale=plan.ai_rationale,
        slots=[EditorialSlotResponse(
            id=s.id, plan_id=s.plan_id, date=s.date, time_slot=s.time_slot,
            platform=s.platform, pillar=s.pillar, theme=s.theme,
            objective=s.objective, content_item_id=s.content_item_id,
        ) for s in slots],
    )


@router.post("/generate")
def generate_plan(
    body: GeneratePlanRequest,
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Generate an editorial plan using AI."""
    check_role(db, current_user.id, body.org_id, EDITOR_ROLES)

    from app.services.embedding_service import get_embedding_service
    from app.services.prompt_builder import build_editorial_planning_prompt
    from app.services.ai_gateway import get_gateway
    import asyncio
    import json
    import re

    # Determine period
    today = date.today()
    if body.period_type == "week":
        days_until_monday = (7 - today.weekday()) % 7 or 7
        period_start = today + timedelta(days=days_until_monday)
        period_end = period_start + timedelta(days=4)
    else:
        if today.month == 12:
            period_start = date(today.year + 1, 1, 1)
        else:
            period_start = date(today.year, today.month + 1, 1)
        if period_start.month == 12:
            period_end = date(period_start.year, 12, 31)
        else:
            period_end = date(period_start.year, period_start.month + 1, 1) - timedelta(days=1)

    # Find influencer
    inf = db.exec(
        select(Influencer)
        .where(Influencer.cost_center_id == body.cc_id)
        .where(Influencer.is_active == True)
    ).first()

    # RAG context
    embedding_svc = get_embedding_service()
    brand_context = []
    if inf:
        brand_context = embedding_svc.search_brand_context(
            db=db, influencer_id=inf.id, query="plano editorial estrategia", top_k=5,
        )
        if not brand_context:
            bk = db.exec(select(BrandKit).where(BrandKit.influencer_id == inf.id)).first()
            if bk:
                chunks = embedding_svc.chunk_brand_kit(inf, bk)
                brand_context = [
                    {"chunk_type": c["chunk_type"], "chunk_text": c["chunk_text"], "similarity": 1.0}
                    for c in chunks
                ]

    # Recent content
    recent_items = db.exec(
        select(ContentItem)
        .where(ContentItem.cost_center_id == body.cc_id)
        .where(ContentItem.status == "posted")
        .order_by(ContentItem.created_at.desc())
        .limit(10)
    ).all()
    recent_summary = "\n".join(
        f"- [{ci.provider_target}] {ci.text[:80]}" for ci in recent_items
    ) if recent_items else ""

    # Build prompt and call AI
    system_prompt, user_prompt = build_editorial_planning_prompt(
        period_type=body.period_type,
        period_start=str(period_start),
        period_end=str(period_end),
        platforms=body.platforms,
        objectives=body.objectives,
        brand_context_chunks=brand_context,
        recent_content_summary=recent_summary,
        language=inf.language if inf else "pt-BR",
    )

    gateway = get_gateway()
    raw = asyncio.run(gateway.generate(
        prompt=user_prompt,
        system=system_prompt,
        temperature=0.7,
        max_tokens=2000,
    ))

    # Parse AI response
    rationale = ""
    slots_data = []
    try:
        parsed = json.loads(raw)
        rationale = parsed.get("rationale", "")
        slots_data = parsed.get("slots", [])
    except (json.JSONDecodeError, TypeError):
        match = re.search(r'\{[\s\S]*\}', raw)
        if match:
            try:
                parsed = json.loads(match.group())
                rationale = parsed.get("rationale", "")
                slots_data = parsed.get("slots", [])
            except (json.JSONDecodeError, TypeError):
                pass

    if not slots_data:
        raise HTTPException(500, "Nao foi possivel gerar o plano editorial. Tente novamente.")

    # Save plan
    plan = EditorialPlan(
        org_id=body.org_id,
        cost_center_id=body.cc_id,
        period_type=body.period_type,
        period_start=period_start,
        period_end=period_end,
        status="draft",
        ai_rationale=rationale,
        created_by=current_user.id,
    )
    db.add(plan)
    db.flush()

    created_slots = []
    for s in slots_data:
        try:
            slot_date = date.fromisoformat(s.get("date", str(period_start)))
        except (ValueError, TypeError):
            slot_date = period_start
        slot = EditorialSlot(
            plan_id=plan.id,
            date=slot_date,
            time_slot=s.get("time_slot", "morning"),
            platform=s.get("platform", body.platforms[0]),
            pillar=s.get("pillar", "Educacao"),
            theme=s.get("theme", "Tema generico"),
            objective=s.get("objective", body.objectives[0] if body.objectives else "awareness"),
        )
        db.add(slot)
        created_slots.append(slot)

    db.commit()
    db.refresh(plan)

    return EditorialPlanResponse(
        id=plan.id,
        org_id=plan.org_id,
        cost_center_id=plan.cost_center_id,
        period_type=plan.period_type,
        period_start=plan.period_start,
        period_end=plan.period_end,
        status=plan.status,
        ai_rationale=plan.ai_rationale,
        slots=[EditorialSlotResponse(
            id=s.id, plan_id=s.plan_id, date=s.date, time_slot=s.time_slot,
            platform=s.platform, pillar=s.pillar, theme=s.theme,
            objective=s.objective, content_item_id=s.content_item_id,
        ) for s in created_slots],
    )


@router.patch("/plans/{plan_id}/status")
def update_plan_status(
    plan_id: str,
    status: str = Query(...),
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Update editorial plan status (draft -> approved -> archived)."""
    plan = db.get(EditorialPlan, plan_id)
    if not plan:
        raise HTTPException(404, "Plano editorial nao encontrado")

    check_role(db, current_user.id, plan.org_id, ADMIN_ROLES)

    if status not in ("draft", "approved", "archived"):
        raise HTTPException(400, "Status invalido. Use: draft, approved, archived")

    plan.status = status
    from datetime import datetime
    plan.updated_at = datetime.utcnow()
    db.add(plan)
    db.commit()
    return {"id": plan.id, "status": plan.status}


@router.patch("/slots/{slot_id}")
def update_slot(
    slot_id: str,
    body: EditorialSlotUpdate,
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Update an editorial slot."""
    slot = db.get(EditorialSlot, slot_id)
    if not slot:
        raise HTTPException(404, "Slot nao encontrado")

    plan = db.get(EditorialPlan, slot.plan_id)
    if not plan:
        raise HTTPException(404, "Plano nao encontrado")
    check_role(db, current_user.id, plan.org_id, EDITOR_ROLES)

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(slot, field, value)
    db.add(slot)
    db.commit()
    db.refresh(slot)

    return EditorialSlotResponse(
        id=slot.id, plan_id=slot.plan_id, date=slot.date, time_slot=slot.time_slot,
        platform=slot.platform, pillar=slot.pillar, theme=slot.theme,
        objective=slot.objective, content_item_id=slot.content_item_id,
    )


@router.post("/slots/{slot_id}/generate-content")
def generate_content_from_slot(
    slot_id: str,
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Generate a ContentItem draft from an editorial slot."""
    slot = db.get(EditorialSlot, slot_id)
    if not slot:
        raise HTTPException(404, "Slot nao encontrado")

    plan = db.get(EditorialPlan, slot.plan_id)
    if not plan:
        raise HTTPException(404, "Plano nao encontrado")
    check_role(db, current_user.id, plan.org_id, EDITOR_ROLES)

    if slot.content_item_id:
        raise HTTPException(400, "Slot ja possui conteudo vinculado")

    # Find influencer
    inf = None
    if plan.cost_center_id:
        inf = db.exec(
            select(Influencer)
            .where(Influencer.cost_center_id == plan.cost_center_id)
            .where(Influencer.is_active == True)
        ).first()

    if not inf:
        raise HTTPException(400, "Nenhum influencer ativo encontrado para este centro de custo")

    # RAG + AI generation
    from app.services.embedding_service import get_embedding_service
    from app.services.prompt_builder import build_content_generation_prompt
    from app.services.ai_gateway import get_gateway
    import asyncio

    embedding_svc = get_embedding_service()
    brand_context = embedding_svc.search_brand_context(
        db=db, influencer_id=inf.id, query=slot.theme, top_k=5,
    )
    if not brand_context:
        bk = db.exec(select(BrandKit).where(BrandKit.influencer_id == inf.id)).first()
        if bk:
            chunks = embedding_svc.chunk_brand_kit(inf, bk)
            brand_context = [
                {"chunk_type": c["chunk_type"], "chunk_text": c["chunk_text"], "similarity": 1.0}
                for c in chunks
            ]

    system_prompt, user_prompt = build_content_generation_prompt(
        influencer_name=inf.name,
        channel=slot.platform,
        topic=f"[{slot.pillar}] {slot.theme}",
        objectives=[slot.objective],
        brand_context_chunks=brand_context,
        language=inf.language,
    )

    gateway = get_gateway()
    text = asyncio.run(gateway.generate(
        prompt=user_prompt,
        system=system_prompt,
        temperature=0.7,
        max_tokens=800,
    ))

    ci = ContentItem(
        cost_center_id=plan.cost_center_id,
        influencer_id=inf.id,
        provider_target=slot.platform,
        text=text,
        status="draft",
    )
    db.add(ci)
    db.flush()

    # Link slot to content item
    slot.content_item_id = ci.id
    db.add(slot)
    db.commit()
    db.refresh(ci)

    return {
        "content_item_id": ci.id,
        "slot_id": slot.id,
        "text": ci.text,
        "platform": ci.provider_target,
        "status": ci.status,
    }


@router.delete("/plans/{plan_id}")
def delete_plan(
    plan_id: str,
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Delete an editorial plan and its slots."""
    plan = db.get(EditorialPlan, plan_id)
    if not plan:
        raise HTTPException(404, "Plano editorial nao encontrado")

    check_role(db, current_user.id, plan.org_id, ADMIN_ROLES)

    # Delete slots first
    slots = db.exec(select(EditorialSlot).where(EditorialSlot.plan_id == plan.id)).all()
    for slot in slots:
        db.delete(slot)
    db.delete(plan)
    db.commit()

    return {"deleted": True, "plan_id": plan_id}
