"""Testes para Webhook Configs (CRUD + test dispatch)."""
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient


# ---------- helpers ----------

def _create_webhook(client: TestClient, org_id: str, **kwargs) -> dict:
    payload = {
        "name": kwargs.get("name", "Slack #marketing"),
        "provider": kwargs.get("provider", "slack"),
        "url": kwargs.get("url", "https://hooks.slack.com/services/TEST"),
        "events": kwargs.get("events", ["approve", "reject"]),
    }
    resp = client.post("/webhooks", json=payload, params={"org_id": org_id})
    assert resp.status_code in (200, 201), resp.text
    return resp.json()


# ---------- CREATE ----------

def test_create_webhook(client: TestClient, test_org):
    data = _create_webhook(client, test_org.id)
    assert data["name"] == "Slack #marketing"
    assert data["provider"] == "slack"
    assert data["is_active"] is True
    assert "approve" in data["events"]


def test_create_webhook_discord(client: TestClient, test_org):
    data = _create_webhook(
        client, test_org.id,
        name="Discord #conteudo",
        provider="discord",
        url="https://discord.com/api/webhooks/TEST",
        events=[],
    )
    assert data["provider"] == "discord"
    assert data["events"] == []  # vazio = todos os eventos


def test_create_webhook_missing_url(client: TestClient, test_org):
    resp = client.post("/webhooks", json={
        "name": "Sem URL",
        "provider": "slack",
    }, params={"org_id": test_org.id})
    assert resp.status_code == 422


# ---------- LIST ----------

def test_list_webhooks(client: TestClient, test_org):
    _create_webhook(client, test_org.id, name="Hook 1")
    _create_webhook(client, test_org.id, name="Hook 2", provider="discord", url="https://discord.com/api/webhooks/X")

    resp = client.get("/webhooks", params={"org_id": test_org.id})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 2
    names = [h["name"] for h in data]
    assert "Hook 1" in names
    assert "Hook 2" in names


def test_list_webhooks_empty(client: TestClient, test_org):
    resp = client.get("/webhooks", params={"org_id": test_org.id})
    assert resp.status_code == 200
    assert resp.json() == []


# ---------- GET ----------

def test_get_webhook(client: TestClient, test_org):
    created = _create_webhook(client, test_org.id)
    resp = client.get(f"/webhooks/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_get_webhook_not_found(client: TestClient):
    resp = client.get("/webhooks/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


# ---------- DELETE ----------

def test_delete_webhook(client: TestClient, test_org):
    created = _create_webhook(client, test_org.id)
    resp = client.delete(f"/webhooks/{created['id']}")
    assert resp.status_code == 204

    list_resp = client.get("/webhooks", params={"org_id": test_org.id})
    ids = [h["id"] for h in list_resp.json()]
    assert created["id"] not in ids


def test_delete_webhook_not_found(client: TestClient):
    resp = client.delete("/webhooks/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


# ---------- TEST DISPATCH ----------

def test_webhook_test_dispatch_success(client: TestClient, test_org):
    created = _create_webhook(client, test_org.id)
    with patch("app.services.webhook_service._dispatch_one") as mock_dispatch:
        mock_dispatch.return_value = None
        resp = client.post(f"/webhooks/{created['id']}/test")
    assert resp.status_code == 200
    mock_dispatch.assert_called_once()


def test_webhook_test_dispatch_not_found(client: TestClient):
    resp = client.post("/webhooks/00000000-0000-0000-0000-000000000000/test")
    assert resp.status_code == 404
