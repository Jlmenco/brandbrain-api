"""Testes para o router e service de reports."""
from datetime import date, datetime
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.metrics import MetricsDaily
from app.models.content import ContentItem


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _seed_content(session: Session, cc_id: str, inf_id: str):
    items = []
    for i, status in enumerate(["draft", "posted", "posted", "review"]):
        ci = ContentItem(
            cost_center_id=cc_id,
            influencer_id=inf_id,
            provider_target="linkedin",
            text=f"Conteudo {i}",
            status=status,
            created_at=datetime(2026, 3, i + 1),
        )
        session.add(ci)
        items.append(ci)
    session.commit()
    for ci in items:
        session.refresh(ci)
    return items


def _seed_metrics(session: Session, content_items: list):
    for i, ci in enumerate(content_items):
        m = MetricsDaily(
            content_item_id=ci.id,
            date=date(2026, 3, i + 1),
            impressions=500 + i * 50,
            likes=30 + i * 3,
            comments=10 + i,
            shares=10 + i * 2,
            clicks=10 + i,
            followers_delta=5 + i,
        )
        session.add(m)
    session.commit()


# ---------------------------------------------------------------------------
# GET /reports/preview
# ---------------------------------------------------------------------------

def test_preview_report(client: TestClient, test_org, test_cc, test_influencer, session: Session):
    items = _seed_content(session, test_cc.id, test_influencer.id)
    _seed_metrics(session, items)

    resp = client.get("/reports/preview", params={
        "date_from": "2026-03-01",
        "date_to": "2026-03-31",
        "org_id": test_org.id,
        "cc_id": test_cc.id,
    })
    assert resp.status_code == 200
    assert "Brand Brain" in resp.text
    assert "Seguidores" in resp.text
    assert "LinkedIn" in resp.text.title() or "linkedin" in resp.text.lower()


def test_preview_empty_metrics(client: TestClient, test_org, test_cc):
    resp = client.get("/reports/preview", params={
        "date_from": "2026-01-01",
        "date_to": "2026-01-31",
        "org_id": test_org.id,
    })
    assert resp.status_code == 200
    assert "Brand Brain" in resp.text


# ---------------------------------------------------------------------------
# POST /reports/generate
# ---------------------------------------------------------------------------

def test_generate_report(client: TestClient, test_org, test_cc, test_influencer, session: Session):
    items = _seed_content(session, test_cc.id, test_influencer.id)
    _seed_metrics(session, items)

    resp = client.post("/reports/generate", params={
        "date_from": "2026-03-01",
        "date_to": "2026-03-31",
        "org_id": test_org.id,
    })
    assert resp.status_code == 200
    # Without weasyprint, it falls back to HTML
    content_type = resp.headers.get("content-type", "")
    assert "text/html" in content_type or "application/pdf" in content_type


# ---------------------------------------------------------------------------
# Service: generate_report_html
# ---------------------------------------------------------------------------

def test_report_html_aggregation(session: Session, test_org, test_cc, test_influencer):
    from app.services.report_service import generate_report_html

    items = _seed_content(session, test_cc.id, test_influencer.id)
    _seed_metrics(session, items)

    html = generate_report_html(
        session, test_org.id, test_cc.id,
        date(2026, 3, 1), date(2026, 3, 31),
    )

    assert "Brand Brain" in html
    assert "Seguidores" in html
    assert "Impressoes" in html
    assert "Engajamentos" in html
    # Check content counts appear
    assert "Posted" in html or "posted" in html.lower()


def test_report_html_no_data(session: Session, test_org):
    from app.services.report_service import generate_report_html

    html = generate_report_html(
        session, test_org.id, None,
        date(2026, 1, 1), date(2026, 1, 31),
    )

    assert "Brand Brain" in html
    assert "Sem dados" in html or "Nenhum" in html
