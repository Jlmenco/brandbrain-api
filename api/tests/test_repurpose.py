"""Testes para repurpose de conteudo."""
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.content import ContentItem


# ---------------------------------------------------------------------------
# POST /content-items/{id}/repurpose
# ---------------------------------------------------------------------------

def test_repurpose_not_found(client: TestClient, test_org):
    resp = client.post("/content-items/nonexistent/repurpose", json={
        "target_platforms": ["instagram"],
    })
    assert resp.status_code == 404


def test_repurpose_no_platforms(client: TestClient, test_content_item):
    resp = client.post(f"/content-items/{test_content_item.id}/repurpose", json={
        "target_platforms": [],
    })
    assert resp.status_code == 400


def test_repurpose_same_platform(client: TestClient, test_content_item):
    """Adaptar para a mesma plataforma deve retornar erro."""
    resp = client.post(f"/content-items/{test_content_item.id}/repurpose", json={
        "target_platforms": [test_content_item.provider_target],
    })
    assert resp.status_code == 400
    assert "iguais" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# source_repurpose_id field
# ---------------------------------------------------------------------------

def test_content_item_has_repurpose_field(session: Session, test_cc, test_influencer):
    """ContentItem deve ter campo source_repurpose_id."""
    original = ContentItem(
        cost_center_id=test_cc.id,
        influencer_id=test_influencer.id,
        provider_target="linkedin",
        text="Original content",
        status="draft",
    )
    session.add(original)
    session.commit()
    session.refresh(original)

    repurposed = ContentItem(
        cost_center_id=test_cc.id,
        influencer_id=test_influencer.id,
        provider_target="instagram",
        text="Adapted content",
        status="draft",
        source_repurpose_id=original.id,
    )
    session.add(repurposed)
    session.commit()
    session.refresh(repurposed)

    assert repurposed.source_repurpose_id == original.id


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def test_repurpose_prompt_builder():
    from app.services.prompt_builder import build_repurpose_prompt

    system, user = build_repurpose_prompt(
        original_text="Teste de conteudo para LinkedIn",
        original_platform="linkedin",
        target_platform="instagram",
        brand_context_chunks=[
            {"chunk_type": "tone", "chunk_text": "Tom profissional"},
        ],
        language="pt-BR",
    )

    assert "instagram" in system.lower()
    assert "linkedin" in user.lower()
    assert "Teste de conteudo" in user
    assert "Tom profissional" in system
