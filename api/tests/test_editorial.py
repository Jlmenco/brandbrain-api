"""Testes para o router e models de editorial planning."""
from datetime import date
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models.editorial import EditorialPlan, EditorialSlot
from app.models.content import ContentItem


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_plan(session: Session, org_id: str, cc_id: str, **kwargs) -> EditorialPlan:
    plan = EditorialPlan(
        org_id=org_id,
        cost_center_id=cc_id,
        period_type=kwargs.get("period_type", "week"),
        period_start=kwargs.get("period_start", date(2026, 3, 16)),
        period_end=kwargs.get("period_end", date(2026, 3, 20)),
        status=kwargs.get("status", "draft"),
        ai_rationale=kwargs.get("ai_rationale", "Estrategia de teste"),
    )
    session.add(plan)
    session.commit()
    session.refresh(plan)
    return plan


def _create_slot(session: Session, plan_id: str, **kwargs) -> EditorialSlot:
    slot = EditorialSlot(
        plan_id=plan_id,
        date=kwargs.get("date", date(2026, 3, 16)),
        time_slot=kwargs.get("time_slot", "morning"),
        platform=kwargs.get("platform", "linkedin"),
        pillar=kwargs.get("pillar", "Educacao"),
        theme=kwargs.get("theme", "Dicas de produtividade"),
        objective=kwargs.get("objective", "awareness"),
    )
    session.add(slot)
    session.commit()
    session.refresh(slot)
    return slot


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

def test_editorial_plan_model(session: Session, test_org, test_cc):
    """EditorialPlan pode ser criado com campos basicos."""
    plan = _create_plan(session, test_org.id, test_cc.id)
    assert plan.id is not None
    assert plan.org_id == test_org.id
    assert plan.status == "draft"
    assert plan.period_type == "week"


def test_editorial_slot_model(session: Session, test_org, test_cc):
    """EditorialSlot vinculado a um plano."""
    plan = _create_plan(session, test_org.id, test_cc.id)
    slot = _create_slot(session, plan.id, platform="instagram", pillar="Prova Social")

    assert slot.plan_id == plan.id
    assert slot.platform == "instagram"
    assert slot.pillar == "Prova Social"
    assert slot.content_item_id is None


def test_slot_linked_to_content(session: Session, test_org, test_cc, test_influencer):
    """Slot pode ser vinculado a um ContentItem."""
    plan = _create_plan(session, test_org.id, test_cc.id)
    ci = ContentItem(
        cost_center_id=test_cc.id,
        influencer_id=test_influencer.id,
        provider_target="linkedin",
        text="Conteudo gerado",
        status="draft",
    )
    session.add(ci)
    session.commit()
    session.refresh(ci)

    slot = _create_slot(session, plan.id)
    slot.content_item_id = ci.id
    session.add(slot)
    session.commit()
    session.refresh(slot)

    assert slot.content_item_id == ci.id


# ---------------------------------------------------------------------------
# GET /editorial/plans
# ---------------------------------------------------------------------------

def test_list_plans(client: TestClient, test_org, test_cc, session: Session):
    _create_plan(session, test_org.id, test_cc.id)
    _create_plan(session, test_org.id, test_cc.id, period_type="month",
                 period_start=date(2026, 4, 1), period_end=date(2026, 4, 30))

    resp = client.get("/editorial/plans", params={"org_id": test_org.id})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


def test_list_plans_filter_cc(client: TestClient, test_org, test_cc, session: Session):
    _create_plan(session, test_org.id, test_cc.id)

    resp = client.get("/editorial/plans", params={
        "org_id": test_org.id,
        "cc_id": test_cc.id,
    })
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_list_plans_filter_status(client: TestClient, test_org, test_cc, session: Session):
    _create_plan(session, test_org.id, test_cc.id, status="draft")
    _create_plan(session, test_org.id, test_cc.id, status="approved",
                 period_start=date(2026, 4, 1), period_end=date(2026, 4, 30))

    resp = client.get("/editorial/plans", params={
        "org_id": test_org.id,
        "status": "approved",
    })
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["status"] == "approved"


# ---------------------------------------------------------------------------
# GET /editorial/plans/{plan_id}
# ---------------------------------------------------------------------------

def test_get_plan(client: TestClient, test_org, test_cc, session: Session):
    plan = _create_plan(session, test_org.id, test_cc.id)
    _create_slot(session, plan.id, theme="Tema A")
    _create_slot(session, plan.id, date=date(2026, 3, 17), theme="Tema B")

    resp = client.get(f"/editorial/plans/{plan.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == plan.id
    assert len(data["slots"]) == 2
    assert data["ai_rationale"] == "Estrategia de teste"


def test_get_plan_not_found(client: TestClient, test_org):
    resp = client.get("/editorial/plans/nonexistent")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /editorial/plans/{plan_id}/status
# ---------------------------------------------------------------------------

def test_update_plan_status(client: TestClient, test_org, test_cc, session: Session):
    plan = _create_plan(session, test_org.id, test_cc.id)

    resp = client.patch(f"/editorial/plans/{plan.id}/status", params={"status": "approved"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"


def test_update_plan_status_invalid(client: TestClient, test_org, test_cc, session: Session):
    plan = _create_plan(session, test_org.id, test_cc.id)

    resp = client.patch(f"/editorial/plans/{plan.id}/status", params={"status": "invalid"})
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# PATCH /editorial/slots/{slot_id}
# ---------------------------------------------------------------------------

def test_update_slot(client: TestClient, test_org, test_cc, session: Session):
    plan = _create_plan(session, test_org.id, test_cc.id)
    slot = _create_slot(session, plan.id)

    resp = client.patch(f"/editorial/slots/{slot.id}", json={
        "theme": "Novo tema atualizado",
        "pillar": "Oferta",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["theme"] == "Novo tema atualizado"
    assert data["pillar"] == "Oferta"


def test_update_slot_not_found(client: TestClient, test_org):
    resp = client.patch("/editorial/slots/nonexistent", json={"theme": "X"})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /editorial/plans/{plan_id}
# ---------------------------------------------------------------------------

def test_delete_plan(client: TestClient, test_org, test_cc, session: Session):
    plan = _create_plan(session, test_org.id, test_cc.id)
    _create_slot(session, plan.id)
    _create_slot(session, plan.id, date=date(2026, 3, 17))

    resp = client.delete(f"/editorial/plans/{plan.id}")
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True

    # Verify plan and slots deleted
    assert db_get(session, plan.id) is None


def test_delete_plan_not_found(client: TestClient, test_org):
    resp = client.delete("/editorial/plans/nonexistent")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def test_editorial_planning_prompt():
    from app.services.prompt_builder import build_editorial_planning_prompt

    system, user = build_editorial_planning_prompt(
        period_type="week",
        period_start="2026-03-16",
        period_end="2026-03-20",
        platforms=["linkedin", "instagram"],
        objectives=["awareness", "engagement"],
        brand_context_chunks=[
            {"chunk_type": "tone", "chunk_text": "Tom profissional e acessivel"},
        ],
        language="pt-BR",
    )

    assert "linkedin" in system.lower()
    assert "instagram" in system.lower()
    assert "Educacao" in system
    assert "2026-03-16" in user
    assert "2026-03-20" in user
    assert "Tom profissional" in system


def test_editorial_planning_prompt_with_context():
    from app.services.prompt_builder import build_editorial_planning_prompt

    system, user = build_editorial_planning_prompt(
        period_type="month",
        period_start="2026-04-01",
        period_end="2026-04-30",
        platforms=["tiktok"],
        objectives=["viral"],
        brand_context_chunks=[],
        recent_content_summary="- [linkedin] Post sobre produtividade",
        language="pt-BR",
    )

    assert "tiktok" in system.lower()
    assert "CONTEUDO RECENTE" in user
    assert "produtividade" in user


# ---------------------------------------------------------------------------
# Helper for DB checks
# ---------------------------------------------------------------------------

def db_get(session: Session, plan_id: str):
    return session.get(EditorialPlan, plan_id)
