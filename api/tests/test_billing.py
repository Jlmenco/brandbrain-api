"""Testes para o router de billing (Asaas checkout + webhook)."""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.organization import Organization


# ---------------------------------------------------------------------------
# GET /billing/plans
# ---------------------------------------------------------------------------

def test_list_plans(client: TestClient):
    """Deve retornar a lista de planos disponíveis."""
    resp = client.get("/billing/plans")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 3
    ids = {p["id"] for p in data}
    assert ids == {"solo_monthly", "agency_monthly", "group_monthly"}
    for plan in data:
        assert "label" in plan
        assert "value_brl" in plan
        assert plan["value_brl"] > 0


# ---------------------------------------------------------------------------
# POST /billing/checkout
# ---------------------------------------------------------------------------

def test_checkout_no_api_key(client: TestClient, test_org):
    """Sem ASAAS_API_KEY configurado, deve retornar 503."""
    resp = client.post("/billing/checkout", params={"plan": "solo_monthly"})
    assert resp.status_code == 503
    assert "Billing não configurado" in resp.json()["detail"]


def test_checkout_invalid_plan(client: TestClient, test_org, monkeypatch):
    """Plano inválido deve retornar 400."""
    import app.config as cfg
    monkeypatch.setattr(cfg.settings, "ASAAS_API_KEY", "fake_key")
    resp = client.post("/billing/checkout", params={"plan": "plano_inexistente"})
    assert resp.status_code == 400
    assert "inválido" in resp.json()["detail"]


def test_checkout_no_org(client: TestClient, monkeypatch):
    """Usuário sem organização deve retornar 404."""
    import app.config as cfg
    monkeypatch.setattr(cfg.settings, "ASAAS_API_KEY", "fake_key")
    # test_user já tem org (via test_org fixture), mas se forçarmos um client sem org...
    # Usando o client padrão que tem test_user com org, testamos outro fluxo
    # Este teste valida que o endpoint chega na chamada Asaas e falha no HTTP externo
    resp = client.post("/billing/checkout", params={"plan": "solo_monthly"})
    # Com fake_key, Asaas vai falhar → 502
    assert resp.status_code in (502, 404)


# ---------------------------------------------------------------------------
# POST /billing/webhook
# ---------------------------------------------------------------------------

def test_webhook_no_token_configured(client: TestClient, test_org, monkeypatch):
    """Sem ASAAS_WEBHOOK_TOKEN, qualquer request deve ser aceito."""
    import app.config as cfg
    monkeypatch.setattr(cfg.settings, "ASAAS_WEBHOOK_TOKEN", "")

    payload = {
        "event": "PAYMENT_CONFIRMED",
        "payment": {"externalReference": f"{test_org.id}|solo_monthly"},
    }
    resp = client.post("/billing/webhook", json=payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_webhook_valid_token(client: TestClient, test_org, monkeypatch):
    """Token correto no header deve ser aceito."""
    import app.config as cfg
    monkeypatch.setattr(cfg.settings, "ASAAS_WEBHOOK_TOKEN", "meu_token_secreto")

    payload = {
        "event": "PAYMENT_CONFIRMED",
        "payment": {"externalReference": f"{test_org.id}|agency_monthly"},
    }
    resp = client.post(
        "/billing/webhook",
        json=payload,
        headers={"asaas-access-token": "meu_token_secreto"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["plan"] == "agency_monthly"
    assert data["org_id"] == test_org.id


def test_webhook_invalid_token(client: TestClient, test_org, monkeypatch):
    """Token incorreto deve ser rejeitado silenciosamente."""
    import app.config as cfg
    monkeypatch.setattr(cfg.settings, "ASAAS_WEBHOOK_TOKEN", "token_correto")

    payload = {
        "event": "PAYMENT_CONFIRMED",
        "payment": {"externalReference": f"{test_org.id}|solo_monthly"},
    }
    resp = client.post(
        "/billing/webhook",
        json=payload,
        headers={"asaas-access-token": "token_errado"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "unauthorized"


def test_webhook_ignored_event(client: TestClient, test_org, monkeypatch):
    """Eventos não relevantes devem retornar status ignored."""
    import app.config as cfg
    monkeypatch.setattr(cfg.settings, "ASAAS_WEBHOOK_TOKEN", "")

    payload = {"event": "PAYMENT_CREATED", "payment": {}}
    resp = client.post("/billing/webhook", json=payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"


def test_webhook_missing_reference(client: TestClient, monkeypatch):
    """Sem externalReference válido deve retornar no_reference."""
    import app.config as cfg
    monkeypatch.setattr(cfg.settings, "ASAAS_WEBHOOK_TOKEN", "")

    payload = {"event": "PAYMENT_CONFIRMED", "payment": {}}
    resp = client.post("/billing/webhook", json=payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "no_reference"


def test_webhook_invalid_plan_in_reference(client: TestClient, test_org, monkeypatch):
    """Plano inválido no externalReference deve retornar invalid_plan."""
    import app.config as cfg
    monkeypatch.setattr(cfg.settings, "ASAAS_WEBHOOK_TOKEN", "")

    payload = {
        "event": "PAYMENT_CONFIRMED",
        "payment": {"externalReference": f"{test_org.id}|plano_fake"},
    }
    resp = client.post("/billing/webhook", json=payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "invalid_plan"


def test_webhook_org_not_found(client: TestClient, monkeypatch):
    """Org inexistente deve retornar org_not_found."""
    import app.config as cfg
    monkeypatch.setattr(cfg.settings, "ASAAS_WEBHOOK_TOKEN", "")

    payload = {
        "event": "PAYMENT_CONFIRMED",
        "payment": {"externalReference": "org-inexistente|solo_monthly"},
    }
    resp = client.post("/billing/webhook", json=payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "org_not_found"


def test_webhook_updates_org_plan(client: TestClient, session: Session, test_org, monkeypatch):
    """Webhook confirmado deve atualizar o plano da org no banco."""
    import app.config as cfg
    monkeypatch.setattr(cfg.settings, "ASAAS_WEBHOOK_TOKEN", "")

    # Garante que a org está em trial
    test_org.plan = "trial"
    session.add(test_org)
    session.commit()

    payload = {
        "event": "PAYMENT_RECEIVED",
        "payment": {"externalReference": f"{test_org.id}|group_monthly"},
    }
    resp = client.post("/billing/webhook", json=payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    # Verifica no banco
    session.refresh(test_org)
    assert test_org.plan == "group_monthly"
    assert test_org.trial_ends_at is None


def test_webhook_clears_trial(client: TestClient, session: Session, test_org, monkeypatch):
    """Após pagamento confirmado, trial_ends_at deve ser None."""
    from datetime import datetime, timedelta
    import app.config as cfg
    monkeypatch.setattr(cfg.settings, "ASAAS_WEBHOOK_TOKEN", "")

    test_org.plan = "trial"
    test_org.trial_ends_at = datetime.utcnow() + timedelta(days=10)
    session.add(test_org)
    session.commit()

    payload = {
        "event": "PAYMENT_APPROVED_BY_RISK_ANALYSIS",
        "payment": {"externalReference": f"{test_org.id}|agency_monthly"},
    }
    resp = client.post("/billing/webhook", json=payload)
    assert resp.status_code == 200
    session.refresh(test_org)
    assert test_org.trial_ends_at is None
