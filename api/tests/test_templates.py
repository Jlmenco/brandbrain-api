"""Testes para Content Templates (CRUD completo)."""
import pytest
from fastapi.testclient import TestClient

from app.models.template import ContentTemplate


# ---------- helpers ----------

def _create_template(client: TestClient, org_id: str, **kwargs) -> dict:
    payload = {
        "name": kwargs.get("name", "Template de teste"),
        "description": kwargs.get("description", "Descricao do template"),
        "provider_target": kwargs.get("provider_target", "linkedin"),
        "text_template": kwargs.get("text_template", "Ola {{nome}}, confira nossa novidade!"),
        "tags": kwargs.get("tags", ["marketing", "linkedin"]),
    }
    resp = client.post("/templates", json=payload, params={"org_id": org_id})
    assert resp.status_code in (200, 201), resp.text
    return resp.json()


# ---------- CREATE ----------

def test_create_template(client: TestClient, test_org):
    data = _create_template(client, test_org.id)
    assert data["name"] == "Template de teste"
    assert data["provider_target"] == "linkedin"
    assert "{{nome}}" in data["text_template"]
    assert data["is_active"] is True
    assert "marketing" in data["tags"]


def test_create_template_minimal(client: TestClient, test_org):
    resp = client.post("/templates", json={
        "name": "Template minimo",
        "text_template": "Texto simples sem placeholders",
    }, params={"org_id": test_org.id})
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert data["name"] == "Template minimo"
    assert data["provider_target"] == ""
    assert data["tags"] == []


def test_create_template_missing_name(client: TestClient, test_org):
    resp = client.post("/templates", json={
        "text_template": "Texto",
    }, params={"org_id": test_org.id})
    assert resp.status_code == 422


# ---------- LIST ----------

def test_list_templates(client: TestClient, test_org):
    _create_template(client, test_org.id, name="Template 1", provider_target="instagram")
    _create_template(client, test_org.id, name="Template 2", provider_target="linkedin")

    resp = client.get("/templates", params={"org_id": test_org.id})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 2
    names = [t["name"] for t in data]
    assert "Template 1" in names
    assert "Template 2" in names


def test_list_templates_filter_provider(client: TestClient, test_org):
    _create_template(client, test_org.id, name="IG Template", provider_target="instagram")
    _create_template(client, test_org.id, name="LI Template", provider_target="linkedin")

    resp = client.get("/templates", params={"org_id": test_org.id, "provider": "instagram"})
    assert resp.status_code == 200
    data = resp.json()
    assert all(t["provider_target"] == "instagram" for t in data)


def test_list_templates_empty(client: TestClient, test_org):
    resp = client.get("/templates", params={"org_id": test_org.id})
    assert resp.status_code == 200
    assert resp.json() == []


# ---------- GET ----------

def test_get_template(client: TestClient, test_org):
    created = _create_template(client, test_org.id)
    resp = client.get(f"/templates/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_get_template_not_found(client: TestClient):
    resp = client.get("/templates/nonexistent-id")
    assert resp.status_code == 404


# ---------- UPDATE ----------

def test_update_template(client: TestClient, test_org):
    created = _create_template(client, test_org.id)
    resp = client.patch(f"/templates/{created['id']}", json={
        "name": "Template atualizado",
        "tags": ["novo-tag"],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Template atualizado"
    assert "novo-tag" in data["tags"]


def test_update_template_not_found(client: TestClient):
    resp = client.patch("/templates/nonexistent-id", json={"name": "X"})
    assert resp.status_code == 404


# ---------- DELETE (soft) ----------

def test_delete_template(client: TestClient, test_org):
    created = _create_template(client, test_org.id)
    resp = client.delete(f"/templates/{created['id']}")
    assert resp.status_code == 204

    # Nao deve aparecer na listagem apos delete
    list_resp = client.get("/templates", params={"org_id": test_org.id})
    ids = [t["id"] for t in list_resp.json()]
    assert created["id"] not in ids


def test_delete_template_not_found(client: TestClient):
    resp = client.delete("/templates/nonexistent-id")
    assert resp.status_code == 404
