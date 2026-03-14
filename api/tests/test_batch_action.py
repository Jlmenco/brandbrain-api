"""Testes para batch-action em content items."""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.content import ContentItem


# ---------- helpers ----------

def _create_items(session: Session, cc_id: str, inf_id: str, count: int, status: str = "draft") -> list[ContentItem]:
    items = []
    for i in range(count):
        ci = ContentItem(
            cost_center_id=cc_id,
            influencer_id=inf_id,
            provider_target="linkedin",
            text=f"Conteudo batch {i}",
            status=status,
        )
        session.add(ci)
        items.append(ci)
    session.commit()
    for ci in items:
        session.refresh(ci)
    return items


# ---------- submit_review em lote ----------

def test_batch_submit_review(client: TestClient, session: Session, test_cc, test_influencer, test_org):
    items = _create_items(session, test_cc.id, test_influencer.id, 3)
    ids = [ci.id for ci in items]

    resp = client.post("/content-items/batch-action", json={
        "ids": ids,
        "action": "submit_review",
        "org_id": test_org.id,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] == 3
    assert data["errors"] == 0

    for ci_id in ids:
        get_resp = client.get(f"/content-items/{ci_id}")
        assert get_resp.json()["status"] == "review"


# ---------- approve em lote ----------

def test_batch_approve(client: TestClient, session: Session, test_cc, test_influencer, test_org):
    items = _create_items(session, test_cc.id, test_influencer.id, 2, status="review")
    ids = [ci.id for ci in items]

    resp = client.post("/content-items/batch-action", json={
        "ids": ids,
        "action": "approve",
        "org_id": test_org.id,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] == 2
    assert data["errors"] == 0

    for ci_id in ids:
        get_resp = client.get(f"/content-items/{ci_id}")
        assert get_resp.json()["status"] == "approved"


# ---------- reject em lote ----------

def test_batch_reject(client: TestClient, session: Session, test_cc, test_influencer, test_org):
    items = _create_items(session, test_cc.id, test_influencer.id, 2, status="review")
    ids = [ci.id for ci in items]

    resp = client.post("/content-items/batch-action", json={
        "ids": ids,
        "action": "reject",
        "org_id": test_org.id,
        "reason": "Fora do padrao da marca",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] == 2

    for ci_id in ids:
        get_resp = client.get(f"/content-items/{ci_id}")
        assert get_resp.json()["status"] == "rejected"


# ---------- parcialmente invalido ----------

def test_batch_partial_errors(client: TestClient, session: Session, test_cc, test_influencer, test_org):
    """Itens no estado errado devem contar como erro mas nao abortar o batch."""
    valid = _create_items(session, test_cc.id, test_influencer.id, 2, status="draft")
    # aprovacao requer status="review" — vai falhar para estes
    invalid = _create_items(session, test_cc.id, test_influencer.id, 1, status="draft")

    ids = [ci.id for ci in valid] + [ci.id for ci in invalid]

    # Tenta aprovar todos — validos estao em draft, nao em review
    resp = client.post("/content-items/batch-action", json={
        "ids": ids,
        "action": "approve",
        "org_id": test_org.id,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["errors"] >= 1


# ---------- lista vazia ----------

def test_batch_empty_ids(client: TestClient, test_org):
    resp = client.post("/content-items/batch-action", json={
        "ids": [],
        "action": "submit_review",
        "org_id": test_org.id,
    })
    assert resp.status_code in (200, 422)
    if resp.status_code == 200:
        assert resp.json()["success"] == 0


# ---------- acao invalida ----------

def test_batch_invalid_action(client: TestClient, test_cc, test_influencer, session, test_org):
    items = _create_items(session, test_cc.id, test_influencer.id, 1)
    resp = client.post("/content-items/batch-action", json={
        "ids": [items[0].id],
        "action": "acao_invalida",
        "org_id": test_org.id,
    })
    assert resp.status_code in (400, 422)
