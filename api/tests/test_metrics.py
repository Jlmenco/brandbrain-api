from datetime import date

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.metrics import MetricsDaily


def test_overview_empty(client: TestClient, test_cc):
    resp = client.get("/metrics/overview", params={"cc_id": test_cc.id})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_impressions"] == 0
    assert data["total_likes"] == 0
    assert data["total_posts"] == 0


def test_overview_with_data(client: TestClient, test_content_item, test_cc, session: Session):
    m1 = MetricsDaily(
        content_item_id=test_content_item.id,
        date=date(2025, 1, 15),
        impressions=1000,
        likes=50,
        comments=10,
        shares=5,
        clicks=100,
        followers_delta=20,
    )
    m2 = MetricsDaily(
        content_item_id=test_content_item.id,
        date=date(2025, 1, 16),
        impressions=2000,
        likes=80,
        comments=15,
        shares=10,
        clicks=200,
        followers_delta=30,
    )
    session.add(m1)
    session.add(m2)
    session.commit()

    resp = client.get("/metrics/overview", params={"cc_id": test_cc.id})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_impressions"] == 3000
    assert data["total_likes"] == 130
    assert data["total_comments"] == 25
    assert data["total_shares"] == 15
    assert data["total_clicks"] == 300
    assert data["total_followers_delta"] == 50
    assert data["total_posts"] == 1


def test_overview_with_date_filter(client: TestClient, test_content_item, test_cc, session: Session):
    m1 = MetricsDaily(
        content_item_id=test_content_item.id,
        date=date(2025, 1, 10),
        impressions=500,
        likes=20,
    )
    m2 = MetricsDaily(
        content_item_id=test_content_item.id,
        date=date(2025, 1, 20),
        impressions=800,
        likes=40,
    )
    session.add(m1)
    session.add(m2)
    session.commit()

    resp = client.get(
        "/metrics/overview",
        params={"cc_id": test_cc.id, "from_date": "2025-01-15", "to_date": "2025-01-25"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_impressions"] == 800
    assert data["total_likes"] == 40
