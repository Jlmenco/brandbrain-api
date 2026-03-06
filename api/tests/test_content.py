from datetime import datetime, timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient


def test_create_content_item(client: TestClient, test_cc, test_influencer):
    resp = client.post(
        "/content-items",
        json={
            "cost_center_id": test_cc.id,
            "influencer_id": test_influencer.id,
            "provider_target": "instagram",
            "text": "Post de teste",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["text"] == "Post de teste"
    assert data["status"] == "draft"
    assert data["provider_target"] == "instagram"
    assert data["version"] == 1


def test_list_content_items(client: TestClient, test_content_item):
    resp = client.get("/content-items")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert any(item["id"] == test_content_item.id for item in data["items"])


def test_list_content_items_filter_status(client: TestClient, test_content_item):
    resp = client.get("/content-items", params={"status": "draft"})
    assert resp.status_code == 200
    data = resp.json()
    assert all(item["status"] == "draft" for item in data["items"])


def test_list_content_items_filter_cc(client: TestClient, test_content_item, test_cc):
    resp = client.get("/content-items", params={"cc_id": test_cc.id})
    assert resp.status_code == 200
    data = resp.json()
    assert all(item["cost_center_id"] == test_cc.id for item in data["items"])


def test_get_content_item(client: TestClient, test_content_item):
    resp = client.get(f"/content-items/{test_content_item.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == test_content_item.id
    assert data["text"] == test_content_item.text


def test_get_content_item_not_found(client: TestClient):
    resp = client.get("/content-items/nonexistent-id")
    assert resp.status_code == 404


def test_update_content_item(client: TestClient, test_content_item):
    resp = client.patch(
        f"/content-items/{test_content_item.id}",
        json={"text": "Texto atualizado"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["text"] == "Texto atualizado"
    assert data["version"] == 2


def test_submit_review(client: TestClient, test_content_item):
    resp = client.post(f"/content-items/{test_content_item.id}/submit-review")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "review"


def test_submit_review_not_draft(client: TestClient, test_content_item, session):
    test_content_item.status = "review"
    session.add(test_content_item)
    session.commit()

    resp = client.post(f"/content-items/{test_content_item.id}/submit-review")
    assert resp.status_code == 400


def test_submit_review_compliance_fail(client: TestClient, test_content_item, session):
    test_content_item.text = "Oferta gratis e garantido"
    session.add(test_content_item)
    session.commit()

    resp = client.post(f"/content-items/{test_content_item.id}/submit-review")
    assert resp.status_code == 422
    data = resp.json()
    assert "compliance_issues" in data["detail"]


def test_approve(client: TestClient, test_content_item, session):
    test_content_item.status = "review"
    session.add(test_content_item)
    session.commit()

    resp = client.post(f"/content-items/{test_content_item.id}/approve")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "approved"


def test_approve_not_review(client: TestClient, test_content_item):
    resp = client.post(f"/content-items/{test_content_item.id}/approve")
    assert resp.status_code == 400


def test_request_changes(client: TestClient, test_content_item, session):
    test_content_item.status = "review"
    session.add(test_content_item)
    session.commit()

    resp = client.post(
        f"/content-items/{test_content_item.id}/request-changes",
        params={"notes": "Precisa melhorar o CTA"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "draft"


def test_reject(client: TestClient, test_content_item, session):
    test_content_item.status = "review"
    session.add(test_content_item)
    session.commit()

    resp = client.post(
        f"/content-items/{test_content_item.id}/reject",
        params={"notes": "Fora do tema"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "rejected"


def test_schedule(client: TestClient, test_content_item, session):
    test_content_item.status = "approved"
    session.add(test_content_item)
    session.commit()

    scheduled_time = (datetime.utcnow() + timedelta(hours=1)).isoformat()
    resp = client.post(
        f"/content-items/{test_content_item.id}/schedule",
        json={"scheduled_at": scheduled_time},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "scheduled"


def test_schedule_not_approved(client: TestClient, test_content_item):
    resp = client.post(
        f"/content-items/{test_content_item.id}/schedule",
        json={"scheduled_at": datetime.utcnow().isoformat()},
    )
    assert resp.status_code == 400


@patch("app.routers.content_items._signal_worker")
def test_publish_now_from_approved(mock_signal, client: TestClient, test_content_item, session):
    test_content_item.status = "approved"
    session.add(test_content_item)
    session.commit()

    resp = client.post(f"/content-items/{test_content_item.id}/publish-now")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "publishing"
    mock_signal.assert_called_once_with(test_content_item.id)


@patch("app.routers.content_items._signal_worker")
def test_publish_now_from_scheduled(mock_signal, client: TestClient, test_content_item, session):
    test_content_item.status = "scheduled"
    session.add(test_content_item)
    session.commit()

    resp = client.post(f"/content-items/{test_content_item.id}/publish-now")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "publishing"


def test_publish_now_not_allowed(client: TestClient, test_content_item):
    resp = client.post(f"/content-items/{test_content_item.id}/publish-now")
    assert resp.status_code == 400


def test_full_workflow(client: TestClient, test_cc, test_influencer):
    """Test the complete content workflow: draft → review → approved → scheduled → publish-now."""
    # 1. Create draft
    resp = client.post(
        "/content-items",
        json={
            "cost_center_id": test_cc.id,
            "influencer_id": test_influencer.id,
            "provider_target": "linkedin",
            "text": "Conteudo completo de workflow test",
        },
    )
    assert resp.status_code == 200
    item_id = resp.json()["id"]

    # 2. Submit for review
    resp = client.post(f"/content-items/{item_id}/submit-review")
    assert resp.status_code == 200
    assert resp.json()["status"] == "review"

    # 3. Approve
    resp = client.post(f"/content-items/{item_id}/approve")
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"

    # 4. Schedule
    scheduled_time = (datetime.utcnow() + timedelta(hours=2)).isoformat()
    resp = client.post(
        f"/content-items/{item_id}/schedule",
        json={"scheduled_at": scheduled_time},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "scheduled"

    # 5. Publish now
    with patch("app.routers.content_items._signal_worker"):
        resp = client.post(f"/content-items/{item_id}/publish-now")
    assert resp.status_code == 200
    assert resp.json()["status"] == "publishing"

    # 6. Verify final state
    resp = client.get(f"/content-items/{item_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "publishing"
